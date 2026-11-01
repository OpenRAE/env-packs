package testgate

import (
	"encoding/json"
	"fmt"
	"go/ast"
	"go/parser"
	"go/token"
	"strings"
)

// mutestingReport is the part of the JSON report of go-mutesting that the gate
// reads.
type mutestingReport struct {
	Stats struct {
		Total       int `json:"totalMutantsCount"`
		Killed      int `json:"killedCount"`
		Escaped     int `json:"escapedCount"`
		NotCompiled int `json:"skippedCount"`
		Errored     int `json:"errorCount"`
	} `json:"stats"`
	Escaped []mutant `json:"escaped"`
	Killed  []mutant `json:"killed"`
}

// mutant is one mutant in the report.
type mutant struct {
	Mutator struct {
		Name     string `json:"mutatorName"`
		Original string `json:"originalSourceCode"`
		Mutated  string `json:"mutatedSourceCode"`
		File     string `json:"originalFilePath"`
	} `json:"mutator"`
}

// parseReport decodes the JSON report of go-mutesting.
func parseReport(data []byte) (mutestingReport, error) {
	var r mutestingReport
	if err := json.Unmarshal(data, &r); err != nil {
		return mutestingReport{}, fmt.Errorf("decode the go-mutesting report: %w", err)
	}
	return r, nil
}

// A Survivor is a mutant that no test kills.
type Survivor struct {
	// File is the path of the file, relative to the repository root.
	File string
	// Function is the name of the function with the mutant, "Type.Method"
	// for a method, or empty outside a function.
	Function string
	// Mutator is the name of the go-mutesting mutator.
	Mutator string
	// Start and End are the first and the last line that the mutant changes.
	Start, End int
	// Line is the text of the first changed line, without leading and
	// trailing space.
	Line string
	// Mutated is the text of that line in the mutant.
	Mutated string
}

// span returns the first and the last changed line of the mutant, and false
// for a mutant with the same source as the original.
func (m mutant) span() (start, end int, changed bool) {
	return changedRange(strings.Split(m.Mutator.Original, "\n"), strings.Split(m.Mutator.Mutated, "\n"))
}

// survivor locates the change of an escaped mutant. It returns false for a
// mutant with the same source as the original.
func survivor(m mutant) (Survivor, bool, error) {
	start, end, changed := m.span()
	if !changed {
		return Survivor{}, false, nil
	}
	original := strings.Split(m.Mutator.Original, "\n")
	mutated := strings.Split(m.Mutator.Mutated, "\n")
	function, err := functionAt(m.Mutator.Original, start)
	if err != nil {
		return Survivor{}, false, fmt.Errorf("parse %s: %w", m.Mutator.File, err)
	}
	return Survivor{
		File:     m.Mutator.File,
		Function: function,
		Mutator:  m.Mutator.Name,
		Start:    start,
		End:      end,
		Line:     lineAt(original, start),
		Mutated:  lineAt(mutated, start),
	}, true, nil
}

// lineAt returns line n of lines without leading and trailing space, or the
// empty string when lines has no line n.
func lineAt(lines []string, n int) string {
	if n > len(lines) {
		return ""
	}
	return strings.TrimSpace(lines[n-1])
}

// changedRange returns the first and the last line of original that differ
// from mutated. When mutated only inserts lines, both are the line at the
// insertion point.
func changedRange(original, mutated []string) (start, end int, changed bool) {
	i := 0
	for i < len(original) && i < len(mutated) && original[i] == mutated[i] {
		i++
	}
	if i == len(original) && i == len(mutated) {
		return 0, 0, false
	}
	limit := min(len(original), len(mutated)) - i
	j := 0
	for j < limit && original[len(original)-1-j] == mutated[len(mutated)-1-j] {
		j++
	}
	start = min(i+1, len(original))
	return start, max(start, len(original)-j), true
}

// functionAt returns the name of the function that holds line, "Type.Method"
// for a method, or the empty string outside a function.
func functionAt(src string, line int) (string, error) {
	fset := token.NewFileSet()
	f, err := parser.ParseFile(fset, "", src, parser.SkipObjectResolution)
	if err != nil {
		return "", err
	}
	for _, d := range f.Decls {
		fn, ok := d.(*ast.FuncDecl)
		if ok && fset.Position(fn.Pos()).Line <= line && line <= fset.Position(fn.End()).Line {
			return receiverPrefix(fn) + fn.Name.Name, nil
		}
	}
	return "", nil
}

// receiverPrefix returns "Type." for a method, and the empty string for a
// function. The type is the first identifier of the receiver type, so a
// pointer, parentheses, and type parameters do not change it.
func receiverPrefix(fn *ast.FuncDecl) string {
	if fn.Recv == nil {
		return ""
	}
	var name string
	ast.Inspect(fn.Recv.List[0].Type, func(n ast.Node) bool {
		if id, ok := n.(*ast.Ident); ok && name == "" {
			name = id.Name
		}
		return name == ""
	})
	return name + "."
}
