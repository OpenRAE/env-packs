// Package schema validates pack documents against the packaged JSON Schemas
// in full, with a JSON Schema 2020-12 validator (design 0005).
//
// Each failure is a diagnostic with the code "schema.<keyword>" and the path
// of the value as its field (design 0006). A diagnostic never holds a message
// of the validator or text of the document.
package schema

import (
	"cmp"
	"errors"
	"fmt"
	"io/fs"
	"path"
	"slices"
	"strconv"
	"strings"
	"unicode"

	"github.com/santhosh-tekuri/jsonschema/v6"
	"github.com/santhosh-tekuri/jsonschema/v6/kind"

	envpacks "github.com/OpenRAE/env-packs"
	"github.com/OpenRAE/env-packs/internal/diagnostic"
	"github.com/OpenRAE/env-packs/internal/document"
)

// schemaSuffix ends the name of each schema file.
const schemaSuffix = ".schema.yaml"

// errNoID reports a schema without a string $id.
var errNoID = errors.New("the schema has no $id")

// A Set holds compiled schemas, by name. The name of a schema is the name of
// its file without ".schema.yaml", for example "provenance".
type Set struct {
	schemas map[string]*jsonschema.Schema
}

// Compile compiles each packaged schema.
func Compile() (*Set, error) {
	return compile(envpacks.Schemas, envpacks.SchemaDir)
}

// compile compiles each schema file in the directory dir of fsys. The
// compiler asserts formats. It has no URL loader, so a reference cannot load a
// file or a URL.
func compile(fsys fs.FS, dir string) (*Set, error) {
	files, err := fs.Glob(fsys, path.Join(dir, "*"+schemaSuffix))
	if err != nil {
		return nil, fmt.Errorf("list the schemas: %w", err)
	}
	c := jsonschema.NewCompiler()
	c.AssertFormat()
	c.UseLoader(jsonschema.SchemeURLLoader{})
	ids := make(map[string]string, len(files))
	for _, file := range files {
		data, err := fs.ReadFile(fsys, file)
		if err != nil {
			return nil, fmt.Errorf("read the schema: %w", err)
		}
		doc, err := document.DecodeYAML(data, document.DefaultLimits())
		if err != nil {
			return nil, fmt.Errorf("decode %s: %w", file, err)
		}
		id, err := schemaID(doc)
		if err != nil {
			return nil, fmt.Errorf("%s: %w", file, err)
		}
		if err := c.AddResource(id, doc); err != nil {
			return nil, fmt.Errorf("add %s: %w", file, err)
		}
		ids[strings.TrimSuffix(path.Base(file), schemaSuffix)] = id
	}
	s := &Set{schemas: make(map[string]*jsonschema.Schema, len(ids))}
	for name, id := range ids {
		compiled, err := c.Compile(id)
		if err != nil {
			return nil, fmt.Errorf("compile the schema %s: %w", name, err)
		}
		s.schemas[name] = compiled
	}
	return s, nil
}

// schemaID returns the $id of the schema document doc.
func schemaID(doc any) (string, error) {
	if mapping, ok := doc.(map[string]any); ok {
		if id, ok := mapping["$id"].(string); ok {
			return id, nil
		}
	}
	return "", errNoID
}

// Validate returns the failures of value against the schema name, sorted by
// field and code. The value must come from the document package. The code of
// a failure is "schema.<keyword>": "schema.required" and "schema.unknown" for
// a missing and an unknown field, the keyword in lower case words joined by
// hyphens for the other keywords, such as "schema.min-length", and
// "schema.schema" for a value that a subschema rejects as a whole. The field
// is the path of the value, such as "$.pack.name" or "$.files[2]", and it
// ends with the name of a missing or an unknown field. A failure has no file:
// the caller adds it, and the prefix of its code, such as "provenance". The
// error reports an unknown schema or a failure of the validator.
func (s *Set) Validate(name string, value any) ([]diagnostic.Diagnostic, error) {
	compiled, ok := s.schemas[name]
	if !ok {
		return nil, fmt.Errorf("no schema %q", name)
	}
	err := compiled.Validate(value)
	verr, ok := errors.AsType[*jsonschema.ValidationError](err)
	if !ok {
		// A valid value gives a nil error. Any other error is a failure of
		// the validator.
		return nil, err
	}
	var failures []diagnostic.Diagnostic
	collect(verr, value, &failures)
	slices.SortFunc(failures, func(a, b diagnostic.Diagnostic) int {
		return cmp.Or(strings.Compare(a.Field(), b.Field()), strings.Compare(a.Code(), b.Code()))
	})
	return failures, nil
}

// collect adds the failures of the leaves of the error tree e.
func collect(e *jsonschema.ValidationError, value any, failures *[]diagnostic.Diagnostic) {
	if len(e.Causes) > 0 {
		for _, cause := range e.Causes {
			collect(cause, value, failures)
		}
		return
	}
	at := fieldPath(value, e.InstanceLocation)
	switch k := e.ErrorKind.(type) {
	case *kind.Required:
		for _, name := range k.Missing {
			*failures = append(*failures, diagnostic.New("schema.required", "", at+"."+name))
		}
	case *kind.AdditionalProperties:
		for _, name := range k.Properties {
			*failures = append(*failures, diagnostic.New("schema.unknown", "", at+"."+name))
		}
	default:
		*failures = append(*failures, diagnostic.New("schema."+keywordCode(e.ErrorKind.KeywordPath()), "", at))
	}
}

// fieldPath writes an instance location in the form of the Python paths: "$",
// then ".name" for a field of an object and "[i]" for an item of an array.
func fieldPath(value any, location []string) string {
	var b strings.Builder
	b.WriteString("$")
	for _, token := range location {
		switch v := value.(type) {
		case []any:
			b.WriteString("[" + token + "]")
			value = itemAt(v, token)
		case map[string]any:
			b.WriteString("." + token)
			value = v[token]
		}
	}
	return b.String()
}

// itemAt returns the item of array at the index token, or nil when token is
// not an index of array.
func itemAt(array []any, token string) any {
	i, err := strconv.Atoi(token)
	if err != nil || i < 0 || i >= len(array) {
		return nil
	}
	return array[i]
}

// keywordCode returns the code of the last keyword of a keyword path, such as
// "min-length" for "minLength". A rejection by a whole subschema, such as a
// false schema, has no keyword and gets the code "schema".
func keywordCode(keywordPath []string) string {
	if len(keywordPath) == 0 {
		return "schema"
	}
	var b strings.Builder
	for _, r := range keywordPath[len(keywordPath)-1] {
		if unicode.IsUpper(r) {
			b.WriteByte('-')
			r = unicode.ToLower(r)
		}
		b.WriteRune(r)
	}
	return b.String()
}
