// Package strictyaml decodes trusted YAML strictly: exactly one document, and
// no field that the target type does not declare (ADR 0047).
package strictyaml

import (
	"bytes"
	"errors"
	"io"

	"go.yaml.in/yaml/v3"
)

// ErrMultipleDocuments reports input with more than one YAML document.
var ErrMultipleDocuments = errors.New("more than one YAML document")

// Decode decodes data into v. It rejects a field that v does not declare,
// empty input, and input with more than one document.
func Decode(data []byte, v any) error {
	dec := yaml.NewDecoder(bytes.NewReader(data))
	dec.KnownFields(true)
	if err := dec.Decode(v); err != nil {
		return err
	}
	var extra yaml.Node
	if err := dec.Decode(&extra); !errors.Is(err, io.EOF) {
		return ErrMultipleDocuments
	}
	return nil
}
