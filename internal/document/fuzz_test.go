package document

import (
	"encoding/json"
	"math"
	"slices"
	"testing"

	"github.com/google/go-cmp/cmp"
)

// codes are the codes that a decoder can return.
var codes = []Code{
	CodeSizeLimit, CodeInvalidUTF8, CodeSyntax, CodeMultipleDocuments, CodeNull, CodeDuplicateKey,
	CodeKeyType, CodeExplicitTag, CodeAmbiguousScalar, CodeNodeLimit, CodeAliasLimit, CodeAliasCycle,
	CodeDepthLimit, CodeNonFinite,
}

// FuzzDecodeYAML checks that DecodeYAML returns a JSON value or an error
// with a known code, and the same result for the same input.
func FuzzDecodeYAML(f *testing.F) {
	for _, seed := range []string{
		"a: 1\n", "a: yes\n", "[&a 1, *a]\n", "a: 1\na: 2\n", "k: !!str 1\n", "1: a\n", "a: 1:30\n",
		"{a: {b: {c: [1, 2]}}}\n", "a: |\n  text\n", "---\na: 1\n---\nb: 2\n", "a: .inf\n", "",
		"a: &x [*x]\n", "a: &x {b: [&y [*x]]}\n", "[&a [x], *a, &a [*a]]\n",
	} {
		f.Add([]byte(seed))
	}
	limits := Limits{MaxBytes: 4096, MaxNodes: 200, MaxAliases: 8, MaxDepth: 8}
	f.Fuzz(func(t *testing.T, data []byte) {
		checkDecode(t, DecodeYAML, data, limits)
	})
}

// FuzzDecodeJSON checks DecodeJSON as FuzzDecodeYAML checks DecodeYAML.
func FuzzDecodeJSON(f *testing.F) {
	for _, seed := range []string{
		`{"a": 1}`, `{"a": 1, "a": 2}`, `[1, 2.5e3, "x", true, null]`, `{} {}`, `null`, `{"a": {"b": {"c": []}}}`,
	} {
		f.Add([]byte(seed))
	}
	limits := Limits{MaxBytes: 4096, MaxNodes: 200, MaxAliases: 8, MaxDepth: 8}
	f.Fuzz(func(t *testing.T, data []byte) {
		checkDecode(t, DecodeJSON, data, limits)
	})
}

// checkDecode decodes data twice with decode and checks the result.
func checkDecode(t *testing.T, decode func([]byte, Limits) (any, error), data []byte, limits Limits) {
	t.Helper()
	got, err := decode(data, limits)
	again, againErr := decode(data, limits)
	if codeOf(err) != codeOf(againErr) || !cmp.Equal(got, again) {
		t.Fatalf("decode(%q) = %v, %v, then %v, %v; want the same result", data, got, err, again, againErr)
	}
	if err != nil {
		if got != nil || !slices.Contains(codes, codeOf(err)) {
			t.Fatalf("decode(%q) = %v, %v; want nil and a known code", data, got, err)
		}
		return
	}
	if got == nil || !jsonValue(got) {
		t.Fatalf("decode(%q) = %#v; want a JSON value that is not null", data, got)
	}
}

// jsonValue reports whether v holds only JSON values: string keys and
// finite numbers.
func jsonValue(v any) bool {
	switch x := v.(type) {
	case nil, bool, string, json.Number, int, uint64:
		return true
	case float64:
		return !math.IsInf(x, 0) && !math.IsNaN(x)
	case []any:
		return !slices.ContainsFunc(x, func(item any) bool { return !jsonValue(item) })
	case map[string]any:
		for _, item := range x {
			if !jsonValue(item) {
				return false
			}
		}
		return true
	}
	return false
}
