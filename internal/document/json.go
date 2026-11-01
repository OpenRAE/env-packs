package document

import (
	"bytes"
	v1 "encoding/json"
	"encoding/json/jsontext"
	"errors"
	"io"
	"unicode/utf8"
)

// DecodeJSON decodes one pack-owned JSON document. It rejects a document over
// the limits, invalid UTF-8, a duplicate name, trailing data, and a null
// document. Numbers decode to json.Number, so no number loses digits. Objects
// decode to map[string]any and arrays to []any.
func DecodeJSON(data []byte, limits Limits) (any, error) {
	if len(data) > limits.MaxBytes {
		return nil, fail(CodeSizeLimit, 0)
	}
	if !utf8.Valid(data) {
		return nil, fail(CodeInvalidUTF8, 0)
	}
	dec := v1.NewDecoder(bytes.NewReader(data))
	dec.UseNumber()
	var value any
	if err := dec.Decode(&value); err != nil {
		return nil, fail(CodeSyntax, 0)
	}
	if _, err := dec.Token(); !errors.Is(err, io.EOF) {
		return nil, fail(CodeMultipleDocuments, 0)
	}
	// encoding/json keeps the last of two equal names. jsontext rejects
	// them, and the decode above has already accepted the rest.
	if err := jsontext.NewDecoder(bytes.NewReader(data)).SkipValue(); err != nil {
		return nil, fail(CodeDuplicateKey, 0)
	}
	if value == nil {
		return nil, fail(CodeNull, 0)
	}
	if err := checkJSONShape(value, limits); err != nil {
		return nil, err
	}
	return value, nil
}

// checkJSONShape applies the node and depth limits as the Python code does:
// each key, each value, and each item is a node one level below its parent.
// A key has the depth of its value, so the depth of the value covers both.
// The walk visits the whole value, and the depth limit comes first, so the
// result does not depend on the order of a Go map.
func checkJSONShape(value any, limits Limits) error {
	type item struct {
		value any
		depth int
	}
	pending := []item{{value: value}}
	var nodes, deepest int
	for len(pending) > 0 {
		it := pending[len(pending)-1]
		pending = pending[:len(pending)-1]
		nodes++
		deepest = max(deepest, it.depth)
		switch v := it.value.(type) {
		case map[string]any:
			nodes += len(v)
			for _, child := range v {
				pending = append(pending, item{value: child, depth: it.depth + 1})
			}
		case []any:
			for _, child := range v {
				pending = append(pending, item{value: child, depth: it.depth + 1})
			}
		}
	}
	switch {
	case deepest > limits.MaxDepth:
		return fail(CodeDepthLimit, 0)
	case nodes > limits.MaxNodes:
		return fail(CodeNodeLimit, 0)
	}
	return nil
}
