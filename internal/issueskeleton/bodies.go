package issueskeleton

import (
	"bytes"
	"embed"
	"encoding/json"
	"io/fs"
	"strings"
	"text/template"
	"unicode"
	"unicode/utf8"
)

// templateFS holds the issue templates. The bodies come from the f-strings of
// issue_skeleton.py in the Python code, and issues.json lists the templates.
//
//go:embed templates
var templateFS embed.FS

// An IssueTemplate is one of the standard planning issues.
type IssueTemplate struct {
	// Key names the template and its body, such as "contract".
	Key string `json:"key"`
	// Suffix ends the title of the issue, after the pack id.
	Suffix string `json:"suffix"`
	// Labels are the labels of the issue.
	Labels []string `json:"labels"`
	// LegacySuffixes are former suffixes of the title, which still match an
	// existing issue.
	LegacySuffixes []string `json:"legacy_suffixes"`
}

// Templates holds the issue templates and their bodies.
type Templates struct {
	Issues  []IssueTemplate
	bodies  *template.Template
	anchors string
}

// bodyData are the values of a body template.
type bodyData struct {
	PackID, PackRoot, Title, Focus    string
	Sources, PackBlock, CommonAnchors string
	ChildIssueNote                    string
}

// NewTemplates returns the embedded issue templates. It panics when they are
// not valid, which TestNewTemplates rules out.
func NewTemplates() *Templates {
	t, err := loadTemplates(templateFS)
	if err != nil {
		panic(err)
	}
	return t
}

// loadTemplates returns the issue templates in the directory templates of
// fsys.
func loadTemplates(fsys fs.FS) (*Templates, error) {
	issues, err := readIssues(fsys)
	if err != nil {
		return nil, err
	}
	anchors, err := fs.ReadFile(fsys, "templates/common-anchors.txt")
	if err != nil {
		return nil, err
	}
	bodies, err := template.ParseFS(fsys, "templates/*.txt")
	if err != nil {
		return nil, err
	}
	return &Templates{Issues: issues, bodies: bodies, anchors: string(anchors)}, nil
}

// readIssues returns the list of issue templates in fsys.
func readIssues(fsys fs.FS) ([]IssueTemplate, error) {
	data, err := fs.ReadFile(fsys, "templates/issues.json")
	if err != nil {
		return nil, err
	}
	var issues []IssueTemplate
	if err := json.Unmarshal(data, &issues); err != nil {
		return nil, err
	}
	return issues, nil
}

// Body returns the body of the issue template key for plan, as the renderer of
// the Python code gives it.
func (t *Templates) Body(plan Plan, key string) (string, error) {
	data := bodyData{
		PackID: plan.PackID, PackRoot: plan.PackRoot, Title: plan.Title, Focus: plan.Focus,
		Sources: bullets(plan.Sources), CommonAnchors: t.anchors,
	}
	var err error
	if data.PackBlock, err = t.render("pack", data); err != nil {
		return "", err
	}
	if data.ChildIssueNote, err = t.render("child-issue-note", data); err != nil {
		return "", err
	}
	return t.render(key, data)
}

// render executes the body template name with data and cleans the result.
func (t *Templates) render(name string, data bodyData) (string, error) {
	var buf bytes.Buffer
	if err := t.bodies.ExecuteTemplate(&buf, name+".txt", data); err != nil {
		return "", err
	}
	return clean(buf.String()), nil
}

// bullets returns the source log as a Markdown list.
func bullets(sources []string) string {
	if len(sources) == 0 {
		return "- Source log TBD by the pack-design agent."
	}
	return "- " + strings.Join(sources, "\n- ")
}

// clean returns body as the clean function of the Python code does: it removes
// the common indent of the lines as textwrap.dedent does, strips the white
// space at both ends, removes four spaces at the start of each line, strips
// again, and adds a newline.
func clean(body string) string {
	lines := splitLines(strings.TrimFunc(dedent(body), isSpace))
	for i, line := range lines {
		lines[i] = strings.TrimPrefix(line, "    ")
	}
	return strings.TrimFunc(strings.Join(lines, "\n"), isSpace) + "\n"
}

// dedent removes the common indent of the lines of text, as textwrap.dedent
// of Python does. A line of spaces and tabs only becomes empty, and it does
// not count for the common indent.
func dedent(text string) string {
	lines := strings.Split(text, "\n")
	margin, found := "", false
	for i, line := range lines {
		rest := strings.TrimLeft(line, " \t")
		if rest == "" {
			lines[i] = ""
			continue
		}
		indent := line[:len(line)-len(rest)]
		if !found {
			margin, found = indent, true
		}
		margin = commonPrefix(margin, indent)
	}
	for i, line := range lines {
		lines[i] = strings.TrimPrefix(line, margin)
	}
	return strings.Join(lines, "\n")
}

// commonPrefix returns the longest common prefix of a and b.
func commonPrefix(a, b string) string {
	i := 0
	for i < len(a) && i < len(b) && a[i] == b[i] {
		i++
	}
	return a[:i]
}

// splitLines splits s at each line boundary of str.splitlines in Python. A
// boundary at the end of s gives no empty last line.
func splitLines(s string) []string {
	var lines []string
	for s != "" {
		i := strings.IndexFunc(s, isLineBoundary)
		if i < 0 {
			return append(lines, s)
		}
		lines = append(lines, s[:i])
		_, size := utf8.DecodeRuneInString(s[i:])
		if strings.HasPrefix(s[i:], "\r\n") {
			size = 2
		}
		s = s[i+size:]
	}
	return lines
}

// isLineBoundary reports whether r ends a line for str.splitlines in Python.
func isLineBoundary(r rune) bool {
	switch r {
	case '\n', '\r', '\v', '\f', '\x1c', '\x1d', '\x1e', '\u0085', '\u2028', '\u2029':
		return true
	}
	return false
}

// isSpace reports whether r is white space for str.strip in Python, which also
// counts the separators U+001C to U+001F.
func isSpace(r rune) bool {
	return unicode.IsSpace(r) || r >= '\x1c' && r <= '\x1f'
}
