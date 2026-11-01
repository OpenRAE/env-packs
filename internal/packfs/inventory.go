package packfs

import (
	"errors"
	"io"
	"os"
	"slices"

	"golang.org/x/sys/unix"
	"golang.org/x/text/cases"
)

// InventoryOptions bound and filter an inventory.
type InventoryOptions struct {
	// MaxMembers is the largest number of directory entries that the walk
	// reads. Each file and each directory counts. It must not be negative.
	MaxMembers int
	// Exclude lists the file paths that the result omits. The walk still
	// checks them.
	Exclude []string
	// ExcludeDirs lists the directory paths whose trees the walk does not
	// enter.
	ExcludeDirs []string
}

// Inventory returns the regular files of the tree, as canonical paths
// relative to the root. The walk reads the names of each directory in byte
// order, and it enters each directory at its place in that order. It rejects
// a symlink, a special file, a file with more than one link, a name that is
// not canonical, two paths that are equal after Unicode case folding, and a
// tree with more entries than the budget.
func (r *Root) Inventory(opts InventoryOptions) ([]string, error) {
	w := &walker{
		sys:         r.sys,
		maxMembers:  opts.MaxMembers,
		exclude:     setOf(opts.Exclude),
		excludeDirs: setOf(opts.ExcludeDirs),
		folded:      make(map[string]string),
		fold:        cases.Fold(),
	}
	// A new descriptor of the root starts at the first entry, also when the
	// root was listed before.
	dir, err := r.sys.Openat(r.dir, ".", dirFlags, noMode)
	if err != nil {
		return nil, fail(ReasonUntraversable, "pack directory could not be traversed", err)
	}
	defer closeReadOnly(dir)
	if err := w.walk(dir, ""); err != nil {
		return nil, err
	}
	return w.files, nil
}

// walker holds the state of one inventory.
type walker struct {
	sys         system
	maxMembers  int
	exclude     map[string]bool
	excludeDirs map[string]bool
	folded      map[string]string
	fold        cases.Caser
	members     int
	files       []string
}

// walk adds the files below the directory dir, whose path is prefix.
func (w *walker) walk(dir *os.File, prefix string) error {
	names, err := w.names(dir)
	if err != nil {
		return err
	}
	for _, name := range names {
		if err := w.visit(dir, prefix, name); err != nil {
			return err
		}
	}
	return nil
}

// names returns the sorted names of the directory dir, a new descriptor.
// Each name counts against the member budget. A read asks for one name more
// than the budget has left, so the walk never holds more names than that.
func (w *walker) names(dir *os.File) ([]string, error) {
	var names []string
	for {
		batch, err := dir.Readdirnames(w.maxMembers - w.members + 1)
		w.members += len(batch)
		if w.members > w.maxMembers {
			return nil, fail(ReasonMemberBudget, "pack member count exceeds the validation limit", nil)
		}
		names = append(names, batch...)
		switch {
		case errors.Is(err, io.EOF):
			slices.Sort(names)
			return names, nil
		case err != nil:
			return nil, fail(ReasonUntraversable, "pack directory could not be traversed", err)
		}
	}
}

// visit checks the member name of the directory dir, and adds it or the
// files below it.
func (w *walker) visit(dir *os.File, prefix, name string) error {
	rel, err := w.member(prefix, name)
	if err != nil {
		return err
	}
	st, err := w.sys.Lstatat(dir, name)
	if err != nil {
		return fail(ReasonUninspectable, "pack member could not be inspected", err)
	}
	switch st.Mode & unix.S_IFMT {
	case unix.S_IFLNK:
		return fail(ReasonSymlink, "pack contains a symlink", nil)
	case unix.S_IFDIR:
		return w.enter(dir, name, rel)
	case unix.S_IFREG:
		if st.Nlink > 1 {
			return fail(ReasonHardlink, "pack contains a multiply-linked file", nil)
		}
		if !w.exclude[rel] {
			w.files = append(w.files, rel)
		}
		return nil
	}
	return fail(ReasonSpecialFile, "pack contains a non-regular file", nil)
}

// member checks a name and returns its path. It rejects a path that is equal
// to an earlier path after case folding.
func (w *walker) member(prefix, name string) (string, error) {
	if err := checkName(name); err != nil {
		return "", err
	}
	rel := name
	if prefix != "" {
		rel = prefix + "/" + name
	}
	folded := w.fold.String(rel)
	if prior, ok := w.folded[folded]; ok && prior != rel {
		return "", fail(ReasonCaseCollision, "pack contains a case-insensitive path collision", nil)
	}
	w.folded[folded] = rel
	return rel, nil
}

// enter walks the directory name of the directory dir, unless its path rel
// is excluded.
func (w *walker) enter(dir *os.File, name, rel string) error {
	if w.excludeDirs[rel] {
		return nil
	}
	child, err := w.sys.Openat(dir, name, dirFlags, noMode)
	if err != nil {
		return fail(ReasonDirectoryUnopenable, "pack directory could not be opened", err)
	}
	defer closeReadOnly(child)
	return w.walk(child, rel)
}

// setOf returns the set of the values.
func setOf(values []string) map[string]bool {
	set := make(map[string]bool, len(values))
	for _, v := range values {
		set[v] = true
	}
	return set
}
