package document

import (
	"encoding/json"
	"errors"
	"fmt"
	"strings"
	"testing"

	"github.com/google/go-cmp/cmp"
	"go.yaml.in/yaml/v3"
)

// codeOf returns the code of err, or the empty string when err is not an
// *Error.
func codeOf(err error) Code {
	if e, ok := errors.AsType[*Error](err); ok {
		return e.Code
	}
	return ""
}

func TestDefaultLimits(t *testing.T) {
	want := Limits{MaxBytes: 1048576, MaxNodes: 20000, MaxAliases: 64, MaxDepth: 64}
	if diff := cmp.Diff(want, DefaultLimits()); diff != "" {
		t.Errorf("DefaultLimits() mismatch (-want +got):\n%s", diff)
	}
}

func TestErrorMessage(t *testing.T) {
	if got := fail(CodeSyntax, 0).Error(); got != "document.syntax" {
		t.Errorf("Error() = %q, want %q", got, "document.syntax")
	}
	if got := fail(CodeDuplicateKey, 3).Error(); got != "document.duplicate-key at line 3" {
		t.Errorf("Error() = %q, want %q", got, "document.duplicate-key at line 3")
	}
}

func TestDecodeYAMLValues(t *testing.T) {
	src := "name: demo\nquoted: \"yes\"\nsingle: 'on'\nflag: true\noctal: 0755\nbig: 1_000\nbinary: 0b11\nhex: 0x1F\n" +
		"float: 1.\nfraction: .5\nsigned: +12\nnothing: ~\nempty:\nletter: y\nlist: [1, two]\nnested: {a: 1}\n" +
		"anchor: &a [x]\nalias: *a\ntext: |\n  1:30\nnegative: -7\nzero: 0\nnegfloat: -1.5\npair: [&p [1], *p]\n"
	got, err := DecodeYAML([]byte(src), DefaultLimits())
	if err != nil {
		t.Fatalf("DecodeYAML() error = %v", err)
	}
	want := map[string]any{
		"name": "demo", "quoted": "yes", "single": "on", "flag": true, "octal": 493, "big": 1000, "binary": 3,
		"hex": 31, "float": 1.0, "fraction": 0.5, "signed": 12, "nothing": nil, "empty": nil, "letter": "y",
		"list": []any{1, "two"}, "nested": map[string]any{"a": 1}, "anchor": []any{"x"}, "alias": []any{"x"},
		"text": "1:30\n", "negative": -7, "zero": 0, "negfloat": -1.5, "pair": []any{[]any{1}, []any{1}},
	}
	if diff := cmp.Diff(want, got); diff != "" {
		t.Errorf("DecodeYAML() mismatch (-want +got):\n%s", diff)
	}
}

func TestDecodeYAMLRejections(t *testing.T) {
	tests := []struct {
		name string
		src  string
		code Code
		line int
	}{
		{name: "yes", src: "k: yes\n", code: CodeAmbiguousScalar, line: 1},
		{name: "No", src: "k: No\n", code: CodeAmbiguousScalar, line: 1},
		{name: "on", src: "k: on\n", code: CodeAmbiguousScalar, line: 1},
		{name: "OFF key", src: "OFF: 1\n", code: CodeAmbiguousScalar, line: 1},
		{name: "exponent without a dot", src: "k: 1e3\n", code: CodeAmbiguousScalar, line: 1},
		{name: "exponent without a sign", src: "k: 1.5e3\n", code: CodeAmbiguousScalar, line: 1},
		{name: "0o octal", src: "k: 0o755\n", code: CodeAmbiguousScalar, line: 1},
		{name: "leading zero with 8", src: "k: 012345678\n", code: CodeAmbiguousScalar, line: 1},
		{name: "sexagesimal integer", src: "k: 1:30\n", code: CodeAmbiguousScalar, line: 1},
		{name: "sexagesimal number", src: "k: 190:20:30.15\n", code: CodeAmbiguousScalar, line: 1},
		{name: "date", src: "k: 2026-11-01\n", code: CodeAmbiguousScalar, line: 1},
		{name: "time with spaces", src: "k: 2001-12-14 21:59:43.10 -5\n", code: CodeAmbiguousScalar, line: 1},
		{name: "value key", src: "k: =\n", code: CodeAmbiguousScalar, line: 1},
		{name: "binary without digits", src: "k: 0b_\n", code: CodeAmbiguousScalar, line: 1},
		{name: "merge key", src: "a: &a {x: 1}\nb:\n  <<: *a\n", code: CodeAmbiguousScalar, line: 3},
		{name: "explicit tag", src: "k: !!str 1\n", code: CodeExplicitTag, line: 1},
		{name: "explicit tag on a collection", src: "k: !!map {a: 1}\n", code: CodeExplicitTag, line: 1},
		{name: "explicit tag on a key", src: "!!str k: 1\n", code: CodeExplicitTag, line: 1},
		{name: "infinity", src: "k: .inf\n", code: CodeNonFinite, line: 1},
		{name: "negative infinity", src: "k: -.inf\n", code: CodeNonFinite, line: 1},
		{name: "alias in its own sequence", src: "a: &x [*x]\n", code: CodeAliasCycle, line: 1},
		{name: "alias in its own document", src: "&x [*x]\n", code: CodeAliasCycle, line: 1},
		{name: "alias deep in its own mapping", src: "a: &x\n  b:\n    - *x\n", code: CodeAliasCycle, line: 3},
		{name: "not a number", src: "k: .NaN\n", code: CodeNonFinite, line: 1},
		{name: "duplicate key", src: "a: 1\nb: 2\na: 3\n", code: CodeDuplicateKey, line: 3},
		{name: "integer key", src: "1: a\n", code: CodeKeyType, line: 1},
		{name: "null key", src: "~: a\n", code: CodeKeyType, line: 1},
		{name: "alias key", src: "a: &k x\n*k : y\n", code: CodeKeyType, line: 2},
		{name: "sequence key", src: "? [a]\n: b\n", code: CodeKeyType, line: 1},
		{name: "two documents", src: "a: 1\n---\nb: 2\n", code: CodeMultipleDocuments, line: 2},
		{name: "empty", src: "", code: CodeNull},
		{name: "null", src: "~\n", code: CodeNull, line: 1},
		{name: "syntax", src: "a: [1\n", code: CodeSyntax},
		{name: "invalid UTF-8", src: "a: \xff\n", code: CodeInvalidUTF8},
		{name: "nodes mostly from aliases", src: aliasChain(9), code: CodeAliasLimit},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := DecodeYAML([]byte(tt.src), DefaultLimits())
			e, ok := errors.AsType[*Error](err)
			if got != nil || !ok || e.Code != tt.code || e.Line != tt.line {
				t.Errorf("DecodeYAML(%q) = %v, %v; want %s at line %d", tt.src, got, err, tt.code, tt.line)
			}
		})
	}
}

// nested returns n mappings nested in YAML flow style.
func nested(n int) string {
	return strings.Repeat("{a: ", n) + "1" + strings.Repeat("}", n) + "\n"
}

func TestDecodeYAMLLimits(t *testing.T) {
	small := Limits{MaxBytes: 64, MaxNodes: 10, MaxAliases: 2, MaxDepth: 3}
	tests := []struct {
		name string
		src  string
		want error
	}{
		{name: "at the depth limit", src: nested(3)},
		{name: "over the depth limit", src: nested(4), want: fail(CodeDepthLimit, 1)},
		{name: "at the byte limit", src: "a: " + strings.Repeat("x", 60) + "\n"},
		{name: "over the byte limit", src: "a: " + strings.Repeat("x", 61) + "\n", want: fail(CodeSizeLimit, 0)},
		{name: "at the node limit", src: "[1, 2, 3, 4, 5, 6, 7, 8, 9]\n"},
		{name: "over the node limit", src: "[1, 2, 3, 4, 5, 6, 7, 8, 9,\n10]\n", want: fail(CodeNodeLimit, 2)},
		{name: "over the node limit at a collection", src: "[1, 2, 3, 4, 5, 6, 7, 8, 9,\n[]]\n", want: fail(CodeNodeLimit, 2)},
		{name: "at the alias limit", src: "[&a 1, *a, *a]\n"},
		{name: "over the alias limit", src: "[&a 1, *a, *a,\n*a]\n", want: fail(CodeAliasLimit, 2)},
		{name: "over the expansion bound", src: "[&a 1, 2, 3, 4, *a,\n*a]\n", want: fail(CodeNodeLimit, 2)},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := DecodeYAML([]byte(tt.src), small)
			if diff := cmp.Diff(tt.want, err); diff != "" || tt.want != nil && got != nil {
				t.Errorf("DecodeYAML(%q) = %v, %v; want error %v", tt.src, got, err, tt.want)
			}
		})
	}
}

func TestDecodeJSON(t *testing.T) {
	got, err := DecodeJSON([]byte(`{"a": [1, 2.5, "x", true, null], "big": 12345678901234567890}`), DefaultLimits())
	if err != nil {
		t.Fatalf("DecodeJSON() error = %v", err)
	}
	want := map[string]any{
		"a":   []any{json.Number("1"), json.Number("2.5"), "x", true, nil},
		"big": json.Number("12345678901234567890"),
	}
	if diff := cmp.Diff(want, got); diff != "" {
		t.Errorf("DecodeJSON() mismatch (-want +got):\n%s", diff)
	}
}

func TestDecodeJSONRejections(t *testing.T) {
	small := Limits{MaxBytes: 64, MaxNodes: 6, MaxAliases: 2, MaxDepth: 2}
	tests := []struct {
		name string
		src  string
		code Code
	}{
		{name: "duplicate name", src: `{"a": 1, "a": 2}`, code: CodeDuplicateKey},
		{name: "nested duplicate name", src: `{"a": {"b": 1, "b": 1}}`, code: CodeDuplicateKey},
		{name: "syntax", src: `{"a": }`, code: CodeSyntax},
		{name: "non-finite", src: `{"a": NaN}`, code: CodeSyntax},
		{name: "trailing value", src: `{} {}`, code: CodeMultipleDocuments},
		{name: "null", src: `null`, code: CodeNull},
		{name: "invalid UTF-8", src: "\"\xff\"", code: CodeInvalidUTF8},
		{name: "at the byte limit", src: `"` + strings.Repeat("x", 62) + `"`},
		{name: "over the byte limit", src: `"` + strings.Repeat("x", 63) + `"`, code: CodeSizeLimit},
		{name: "at the depth limit", src: `{"a": {"b": 1}}`},
		{name: "over the depth limit", src: `{"a": {"b": [1]}}`, code: CodeDepthLimit},
		{name: "at the node limit", src: `{"a": 1, "b": [2]}`},
		{name: "over the node limit", src: `{"a": 1, "b": 2, "c": 3}`, code: CodeNodeLimit},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := DecodeJSON([]byte(tt.src), small)
			var want error
			if tt.code != "" {
				want = fail(tt.code, 0)
			}
			if diff := cmp.Diff(want, err); diff != "" || want != nil && got != nil {
				t.Errorf("DecodeJSON(%q) = %v, %v; want error %v", tt.src, got, err, want)
			}
		})
	}
}

// TestDecodeJSONLimitOrder checks that a document over both limits always
// gets the same code. Go visits the members of a map in a random order, so
// the test decodes the document many times.
func TestDecodeJSONLimitOrder(t *testing.T) {
	small := Limits{MaxBytes: 64, MaxNodes: 6, MaxAliases: 2, MaxDepth: 2}
	src := []byte(`{"a": {"x": {"y": 1}}, "b": 0}`)
	want := fail(CodeDepthLimit, 0)
	for range 64 {
		if got, err := DecodeJSON(src, small); got != nil || !cmp.Equal(error(want), err) {
			t.Fatalf("DecodeJSON(%s) = %v, %v; want error %v", src, got, err, want)
		}
	}
}

// TestDecodeYAMLExpansion checks a chain of aliases that passes the counts of
// the Python code but expands to more nodes than the limit.
func TestDecodeYAMLExpansion(t *testing.T) {
	var b strings.Builder
	b.WriteString("a: &a [1, 1, 1, 1, 1, 1, 1, 1]\n")
	for level, name := range []string{"b", "c", "d", "e"} {
		prior := string(rune('a' + level))
		fmt.Fprintf(&b, "%s: &%s [%s]\n", name, name, strings.TrimSuffix(strings.Repeat("*"+prior+", ", 8), ", "))
	}
	b.WriteString("f: [" + strings.TrimSuffix(strings.Repeat("*e, ", 8), ", ") + "]\n")
	got, err := DecodeYAML([]byte(b.String()), DefaultLimits())
	if diff := cmp.Diff(error(fail(CodeNodeLimit, 0)), err); diff != "" || got != nil {
		t.Errorf("DecodeYAML() of an alias chain = %v, %v; want %s", got, err, CodeNodeLimit)
	}
}

// aliasChain returns a mapping with an alias chain of n levels. Each level
// holds two aliases of the level before it, so nearly all of the nodes of the
// decoded value come from aliases.
func aliasChain(n int) string {
	var b strings.Builder
	b.WriteString("l0: &l0 [x, x]\n")
	for level := 1; level <= n; level++ {
		fmt.Fprintf(&b, "l%d: &l%d [*l%d, *l%d]\n", level, level, level-1, level-1)
	}
	return b.String()
}

func TestExpandedSize(t *testing.T) {
	tests := []struct {
		src   string
		limit int
		want  int
	}{
		{src: "[a, b, c]\n", limit: 100, want: 4},
		{src: "[a, b, c]\n", limit: 4, want: 4},
		{src: "[a, b, c]\n", limit: 2, want: 3},
		{src: "[a, b, c]\n", limit: 1, want: 2},
		{src: "[&a [x, y], *a]\n", limit: 100, want: 7},
	}
	for _, tt := range tests {
		var root yaml.Node
		if err := yaml.Unmarshal([]byte(tt.src), &root); err != nil {
			t.Fatalf("parse %q: %v", tt.src, err)
		}
		if got := expandedSize(&root, tt.limit); got != tt.want {
			t.Errorf("expandedSize(%q, %d) = %d, want %d", tt.src, tt.limit, got, tt.want)
		}
	}
}

func TestDecodeYAMLIntegers(t *testing.T) {
	tests := []struct {
		src  string
		want any
		code Code
	}{
		{src: "k: 18446744073709551615\n", want: map[string]any{"k": uint64(18446744073709551615)}},
		{src: "k: 18446744073709551616\n", code: CodeAmbiguousScalar},
		{src: "k: 0x_\n", code: CodeAmbiguousScalar},
	}
	for _, tt := range tests {
		got, err := DecodeYAML([]byte(tt.src), DefaultLimits())
		if codeOf(err) != tt.code || !cmp.Equal(tt.want, got) {
			t.Errorf("DecodeYAML(%q) = %v, %v; want %v and code %q", tt.src, got, err, tt.want, tt.code)
		}
	}
}
