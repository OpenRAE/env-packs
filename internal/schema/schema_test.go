package schema

import (
	"errors"
	"io/fs"
	"maps"
	"os"
	"path"
	"path/filepath"
	"slices"
	"strings"
	"testing"
	"testing/fstest"

	"github.com/google/go-cmp/cmp"
	"github.com/santhosh-tekuri/jsonschema/v6"

	"github.com/OpenRAE/env-packs/internal/diagnostic"
	"github.com/OpenRAE/env-packs/internal/document"
)

// testSchema uses each keyword of the packaged schemas.
const testSchema = `$schema: https://json-schema.org/draft/2020-12/schema
$id: https://example.test/test.json
type: object
additionalProperties: false
required: [name]
properties:
  name: {type: string, minLength: 2, maxLength: 3, pattern: "^[a-z]+$"}
  kind: {const: pack}
  mode: {enum: [a, b]}
  count: {type: integer, minimum: 1}
  when: {type: string, format: date-time}
  tags: {type: array, minItems: 1, uniqueItems: true, items: {type: string}}
  rows: {type: array, items: {$ref: "#/$defs/row"}}
  map: {type: object, additionalProperties: {type: string}}
  none: {type: array, items: false}
$defs:
  row:
    type: object
    additionalProperties: false
    required: [id]
    properties:
      id: {type: string}
`

// testSet compiles the schema files of fsys in the directory "schemas".
func testSet(t *testing.T, files map[string]string) *Set {
	t.Helper()
	s, err := compile(mapFS(files), "schemas")
	if err != nil {
		t.Fatalf("compile() error = %v", err)
	}
	return s
}

// mapFS returns a file system with the files, by path.
func mapFS(files map[string]string) fstest.MapFS {
	fsys := fstest.MapFS{}
	for name, data := range files {
		fsys[name] = &fstest.MapFile{Data: []byte(data)}
	}
	return fsys
}

// decode decodes a YAML document for a test.
func decode(t *testing.T, text string) any {
	t.Helper()
	value, err := document.DecodeYAML([]byte(text), document.DefaultLimits())
	if err != nil {
		t.Fatalf("DecodeYAML(%q) error = %v", text, err)
	}
	return value
}

// strs returns the code and the field of each diagnostic, for a readable
// diff. A failure of a schema has no file.
func strs(diagnostics []diagnostic.Diagnostic) []string {
	var out []string
	for _, d := range diagnostics {
		out = append(out, d.Code()+" "+d.Field()+" "+d.File())
	}
	return out
}

func TestCompile(t *testing.T) {
	s, err := Compile()
	if err != nil {
		t.Fatalf("Compile() error = %v", err)
	}
	want := []string{
		"catalog", "kit", "kit-catalog", "kit-materializations",
		"pack-compatibility", "provenance", "publication-profile", "publication-supply",
	}
	if got := slices.Sorted(maps.Keys(s.schemas)); !slices.Equal(got, want) {
		t.Errorf("Compile() schemas = %v, want %v", got, want)
	}
}

func TestValidate(t *testing.T) {
	s := testSet(t, map[string]string{"schemas/test.schema.yaml": testSchema})
	tests := []struct {
		doc  string
		want []diagnostic.Diagnostic
	}{
		{doc: "name: abc\nkind: pack\nmode: a\ncount: 1\nwhen: '2026-11-01T10:00:00Z'\ntags: [x]\nrows: [{id: r}]\nmap: {k: v}\nnone: []\n"},
		{doc: "{}", want: []diagnostic.Diagnostic{diagnostic.New("schema.required", "", "$.name")}},
		{doc: "[]", want: []diagnostic.Diagnostic{diagnostic.New("schema.type", "", "$")}},
		{
			doc: "name: A\nkind: x\nmode: c\ncount: 0\nwhen: yesterday\ntags: []\nother: 1\n",
			want: []diagnostic.Diagnostic{
				diagnostic.New("schema.minimum", "", "$.count"),
				diagnostic.New("schema.const", "", "$.kind"),
				diagnostic.New("schema.enum", "", "$.mode"),
				diagnostic.New("schema.min-length", "", "$.name"),
				diagnostic.New("schema.pattern", "", "$.name"),
				diagnostic.New("schema.unknown", "", "$.other"),
				diagnostic.New("schema.min-items", "", "$.tags"),
				diagnostic.New("schema.format", "", "$.when"),
			},
		},
		{
			doc:  "name: abcd\ntags: [a, a]\n",
			want: []diagnostic.Diagnostic{diagnostic.New("schema.max-length", "", "$.name"), diagnostic.New("schema.unique-items", "", "$.tags")},
		},
		{
			doc: "name: abc\nrows: [{id: r}, {id: 1, extra: true}, {}]\nmap: {'0': 1}\nnone: [1]\n",
			want: []diagnostic.Diagnostic{
				diagnostic.New("schema.type", "", "$.map.0"),
				diagnostic.New("schema.schema", "", "$.none[0]"),
				diagnostic.New("schema.unknown", "", "$.rows[1].extra"),
				diagnostic.New("schema.type", "", "$.rows[1].id"),
				diagnostic.New("schema.required", "", "$.rows[2].id"),
			},
		},
	}
	for _, tt := range tests {
		got, err := s.Validate("test", decode(t, tt.doc))
		if err != nil {
			t.Errorf("Validate(%q) error = %v", tt.doc, err)
			continue
		}
		if diff := cmp.Diff(strs(tt.want), strs(got)); diff != "" {
			t.Errorf("Validate(%q) violations mismatch (-want +got):\n%s", tt.doc, diff)
		}
	}
}

func TestValidatePackaged(t *testing.T) {
	s, err := Compile()
	if err != nil {
		t.Fatalf("Compile() error = %v", err)
	}
	// Python gives the same violations for this document.
	got, err := s.Validate("provenance", decode(t, "schema_version: environment-pack-provenance/v2\npack: {name: Bad, extra: 1}\n"))
	if err != nil {
		t.Fatalf("Validate() error = %v", err)
	}
	want := []diagnostic.Diagnostic{
		diagnostic.New("schema.required", "", "$.artifacts"),
		diagnostic.New("schema.required", "", "$.content_safety"),
		diagnostic.New("schema.unknown", "", "$.pack.extra"),
		diagnostic.New("schema.pattern", "", "$.pack.name"),
		diagnostic.New("schema.required", "", "$.review"),
		diagnostic.New("schema.const", "", "$.schema_version"),
		diagnostic.New("schema.required", "", "$.sources"),
	}
	if diff := cmp.Diff(strs(want), strs(got)); diff != "" {
		t.Errorf("Validate() violations mismatch (-want +got):\n%s", diff)
	}
}

func TestValidateUnknownSchema(t *testing.T) {
	s := testSet(t, map[string]string{"schemas/test.schema.yaml": testSchema})
	if got, err := s.Validate("missing", map[string]any{}); err == nil || got != nil {
		t.Errorf("Validate() of an unknown schema = %v, %v; want an error", got, err)
	}
}

func TestCompileErrors(t *testing.T) {
	const other = "$id: https://example.test/test.json\n"
	tests := []struct {
		name  string
		fsys  fs.FS
		dir   string
		check func(error) bool
	}{
		{
			name:  "bad pattern",
			fsys:  fstest.MapFS{},
			dir:   "[",
			check: func(err error) bool { return errors.Is(err, path.ErrBadPattern) },
		},
		{
			name:  "unreadable file",
			fsys:  fstest.MapFS{"schemas/test.schema.yaml/file": &fstest.MapFile{}},
			check: func(err error) bool { return errors.Is(err, fs.ErrInvalid) },
		},
		{
			name: "invalid YAML",
			fsys: mapFS(map[string]string{"schemas/test.schema.yaml": "a: ["}),
			check: func(err error) bool {
				derr, ok := errors.AsType[*document.Error](err)
				return ok && derr.Code == document.CodeSyntax
			},
		},
		{
			name:  "not a mapping",
			fsys:  mapFS(map[string]string{"schemas/test.schema.yaml": "- 1\n"}),
			check: func(err error) bool { return errors.Is(err, errNoID) },
		},
		{
			name:  "id not a string",
			fsys:  mapFS(map[string]string{"schemas/test.schema.yaml": "$id: 1\n"}),
			check: func(err error) bool { return errors.Is(err, errNoID) },
		},
		{
			name: "duplicate id",
			fsys: mapFS(map[string]string{"schemas/a.schema.yaml": other, "schemas/b.schema.yaml": other}),
			check: func(err error) bool {
				_, ok := errors.AsType[*jsonschema.ResourceExistsError](err)
				return ok
			},
		},
		{
			name: "invalid schema",
			fsys: mapFS(map[string]string{"schemas/test.schema.yaml": other + "type: 5\n"}),
			check: func(err error) bool {
				_, ok := errors.AsType[*jsonschema.SchemaValidationError](err)
				return ok
			},
		},
		{
			name:  "reference to a URL",
			fsys:  mapFS(map[string]string{"schemas/test.schema.yaml": other + "$ref: https://example.test/other.json\n"}),
			check: isLoadRefused,
		},
		{
			name:  "reference to a file",
			fsys:  mapFS(map[string]string{"schemas/test.schema.yaml": other + "$ref: file:///etc/hostname\n"}),
			check: isLoadRefused,
		},
	}
	for _, tt := range tests {
		dir := tt.dir
		if dir == "" {
			dir = "schemas"
		}
		if s, err := compile(tt.fsys, dir); s != nil || !tt.check(err) {
			t.Errorf("compile() with a %s = %v, %v; want the error of that case", tt.name, s, err)
		}
	}
}

// isLoadRefused reports whether err shows that the compiler refused to load
// a referenced schema.
func isLoadRefused(err error) bool {
	lerr, ok := errors.AsType[*jsonschema.LoadURLError](err)
	if !ok {
		return false
	}
	_, ok = errors.AsType[*jsonschema.UnsupportedURLSchemeError](lerr.Err)
	return ok
}

func TestItemAt(t *testing.T) {
	array := []any{"a", "b"}
	for token, want := range map[string]any{"0": "a", "1": "b", "2": nil, "-1": nil, "x": nil} {
		if got := itemAt(array, token); got != want {
			t.Errorf("itemAt(%v, %q) = %v, want %v", array, token, got, want)
		}
	}
}

// TestHostedDocuments checks that each hosted kit manifest, pack
// compatibility manifest, and pack provenance ledger of this repository
// decodes and has no violation.
func TestHostedDocuments(t *testing.T) {
	s, err := Compile()
	if err != nil {
		t.Fatalf("Compile() error = %v", err)
	}
	for pattern, name := range map[string]string{
		"../../kits/*/*/kit.yaml":                   "kit",
		"../../packs/*/pack.compatibility.yaml":     "pack-compatibility",
		"../../packs/*/docs/provenance-ledger.yaml": "provenance",
	} {
		files, err := filepath.Glob(pattern)
		if err != nil || len(files) == 0 {
			t.Fatalf("Glob(%q) = %v, %v; want hosted documents", pattern, files, err)
		}
		for _, file := range files {
			checkHosted(t, s, name, file)
		}
	}
}

// checkHosted checks that the hosted document file decodes and has no
// violation of the schema name.
func checkHosted(t *testing.T, s *Set, name, file string) {
	t.Helper()
	data, err := os.ReadFile(file) //nolint:gosec // G304 false positive: the test reads the hosted documents of this repository.
	if err != nil {
		t.Fatalf("read %s: %v", file, err)
	}
	doc, err := document.DecodeYAML(data, document.DefaultLimits())
	if err != nil {
		t.Errorf("DecodeYAML(%s) error = %v", file, err)
		return
	}
	if got, err := s.Validate(name, doc); err != nil || got != nil {
		t.Errorf("Validate(%q, %s) = %v, %v; want no violation", name, file, got, err)
	}
}

// TestValidateHoldsNoValue checks that a failure holds codes and the paths of
// values, and never a value of the document.
func TestValidateHoldsNoValue(t *testing.T) {
	s := testSet(t, map[string]string{"schemas/test.schema.yaml": testSchema})
	const authored = "AUTHORED-VALUE-7"
	doc := decode(t, strings.ReplaceAll("name: V\nkind: V\nmode: V\nwhen: V\ntags: [V, V]\nmap: {k: [V]}\nrows: [{id: r, extra: V}]\n", "V", authored))
	got, err := s.Validate("test", doc)
	if err != nil || len(got) < 7 {
		t.Fatalf("Validate() = %v, %v; want a failure for each field", strs(got), err)
	}
	for _, d := range got {
		if strings.Contains(d.Code()+d.Field()+d.File(), authored) {
			t.Errorf("Validate() gave %q, which holds a value of the document", d.Code()+" "+d.Field())
		}
	}
}
