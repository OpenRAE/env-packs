package main

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/google/go-cmp/cmp"
)

// gitEnvironment isolates the disposable repository from host Git
// configuration, so no host hook, signing key, or identity applies.
var gitEnvironment = []string{
	"GIT_CONFIG_GLOBAL=/dev/null",
	"GIT_CONFIG_NOSYSTEM=1",
	"GIT_AUTHOR_NAME=fixture",
	"GIT_AUTHOR_EMAIL=fixture@example.invalid",
	"GIT_COMMITTER_NAME=fixture",
	"GIT_COMMITTER_EMAIL=fixture@example.invalid",
}

func gitFixture(t *testing.T, dir string, args ...string) string {
	t.Helper()
	output, err := child(t, dir, gitEnvironment, "git", args...)
	if err != nil {
		t.Fatalf("git %q: %v: %s", args, err, output)
	}
	return strings.TrimSpace(string(output))
}

func writeTree(t *testing.T, dir string, files ...string) {
	t.Helper()
	for _, name := range files {
		path := filepath.Join(dir, filepath.FromSlash(name))
		if err := os.MkdirAll(filepath.Dir(path), 0o700); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(path, []byte("# Title\n"), 0o600); err != nil {
			t.Fatal(err)
		}
	}
}

// proseRepository returns a repository with one base commit and one change
// commit. The change adds checked, excluded, and non-Markdown files, and it
// deletes a Markdown file.
func proseRepository(t *testing.T) (repo, base string) {
	t.Helper()
	repo = t.TempDir()
	gitFixture(t, repo, "init", "-q")
	writeTree(t, repo, "gone.md", "docs/decisions/adrs/0001-old.md", "docs/decisions/adrs/README.md")
	gitFixture(t, repo, "add", "-A")
	gitFixture(t, repo, "commit", "-q", "-m", "base")
	base = gitFixture(t, repo, "rev-parse", "HEAD")
	writeTree(t, repo, "a b.md", "-lead.md", "docs/guide.md", "CHANGELOG.md", "code.go",
		"internal/x/testdata/case.md", "tests/fixtures/sample.md",
		"packs/p/assets/world.md", "kits/k/v1/assets/world.md", "docs/decisions/adrs/0002-new.md")
	for _, name := range []string{"docs/decisions/adrs/0001-old.md", "docs/decisions/adrs/README.md"} {
		if err := os.WriteFile(filepath.Join(repo, filepath.FromSlash(name)), []byte("# Changed\n"), 0o600); err != nil {
			t.Fatal(err)
		}
	}
	if err := os.Remove(filepath.Join(repo, "gone.md")); err != nil {
		t.Fatal(err)
	}
	gitFixture(t, repo, "add", "-A")
	gitFixture(t, repo, "commit", "-q", "-m", "change")
	return repo, base
}

// proseTools returns a fake mise that runs its command with a fake doc-tools
// package and a fake Vale on PATH, as `mise exec` does with the real tools.
// Each checker writes its arguments, NUL-separated, to a record file and
// exits with the status in its *_RESULT variable.
func proseTools(t *testing.T) (mise, records string) {
	t.Helper()
	dir := t.TempDir()
	records = t.TempDir()
	pkg := filepath.Join(dir, "doc-tools")
	bin := filepath.Join(dir, "bin")
	for _, d := range []string{filepath.Join(pkg, "tools"), filepath.Join(pkg, "vale", "DocTools"), bin} {
		if err := os.MkdirAll(d, 0o700); err != nil {
			t.Fatal(err)
		}
	}
	if err := os.WriteFile(filepath.Join(pkg, "vale", "DocTools", "Rule.yml"), []byte("level: error\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	executable(t, filepath.Join(pkg, "tools"), "ste-lint.sh", `printf '%s\000' "$@" > "$RECORDS/ste"
exit "${STE_RESULT:-0}"
`)
	executable(t, bin, "vale", `printf '%s\000' "$@" > "$RECORDS/vale"
exit "${VALE_RESULT:-0}"
`)
	mise = executable(t, dir, "mise", `[ "$1" = exec ] || exit 64
shift
[ "$1" = -- ] && shift
PATH="`+filepath.Join(pkg, "tools")+":"+bin+`:$PATH" exec "$@"
`)
	return mise, records
}

func recordedArguments(t *testing.T, dir, name string) []string {
	t.Helper()
	return strings.Split(strings.TrimSuffix(string(readFixture(t, dir, name)), "\x00"), "\x00")
}

func makefile(t *testing.T) string {
	t.Helper()
	path, err := filepath.Abs("../../Makefile")
	if err != nil {
		t.Fatal(err)
	}
	return path
}

// runProse runs `make prose` in repo with the fake tools of proseTools.
func runProse(t *testing.T, repo, base, mise, records string, environment ...string) ([]byte, error) {
	t.Helper()
	return child(t, repo, append([]string{"RECORDS=" + records}, environment...), "make", "-f", makefile(t), "prose", "BASE="+base, "MISE="+mise)
}

// TestProseGateArguments checks that each changed file name reaches both
// checkers intact, after "--", and that the excluded paths do not. An
// accepted decision record is immutable, so the gate checks a decision record
// that the change adds, and not one that it changes.
// Regression test for #674: the earlier recipe split names at white space.
func TestProseGateArguments(t *testing.T) {
	repo, base := proseRepository(t)
	mise, records := proseTools(t)
	if output, err := runProse(t, repo, base, mise, records); err != nil {
		t.Fatalf("make prose failed: %v: %s", err, output)
	}
	want := []string{"--", "-lead.md", "a b.md", "docs/decisions/adrs/README.md", "docs/guide.md", "docs/decisions/adrs/0002-new.md"}
	for _, checker := range []string{"ste", "vale"} {
		if diff := cmp.Diff(want, recordedArguments(t, records, checker)); diff != "" {
			t.Errorf("%s arguments (-want +got):\n%s", checker, diff)
		}
	}
	if _, err := os.Stat(filepath.Join(repo, ".vale", "styles", "DocTools", "Rule.yml")); err != nil {
		t.Errorf("DocTools style not installed from the package: %v", err)
	}
}

func TestProseGateRunsEachCheckerAndFails(t *testing.T) {
	repo, base := proseRepository(t)
	for _, failing := range []string{"STE_RESULT=1", "VALE_RESULT=1"} {
		mise, records := proseTools(t)
		if _, err := runProse(t, repo, base, mise, records, failing); err == nil {
			t.Errorf("make prose ignored checker failure %s", failing)
		}
		for _, checker := range []string{"ste", "vale"} {
			if _, err := os.Stat(filepath.Join(records, checker)); err != nil {
				t.Errorf("with %s, %s did not run: %v", failing, checker, err)
			}
		}
	}
}

func TestProseGateNeedsDocTools(t *testing.T) {
	repo, base := proseRepository(t)
	output, err := runProse(t, repo, base, "false", t.TempDir())
	if err == nil || !strings.Contains(string(output), "run mise install") {
		t.Errorf("make prose without doc-tools: err=%v output=%q", err, output)
	}
}

func TestProseGateSkipsAnUnchangedTree(t *testing.T) {
	repo, _ := proseRepository(t)
	mise, records := proseTools(t)
	output, err := runProse(t, repo, "HEAD", mise, records)
	if err != nil {
		t.Fatalf("make prose failed: %v: %s", err, output)
	}
	if !strings.Contains(string(output), "prose: no changed Markdown file") {
		t.Errorf("output = %q, want the skip message", output)
	}
	entries, err := os.ReadDir(records)
	if err != nil {
		t.Fatal(err)
	}
	if len(entries) != 0 {
		t.Errorf("a checker ran on an unchanged tree: %v", entries)
	}
}
