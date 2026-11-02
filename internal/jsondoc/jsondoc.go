// Package jsondoc writes JSON envelopes and documents with the bytes of the
// Python implementation (design 0006).
package jsondoc

import (
	"bytes"
	"encoding/json"
	"encoding/json/jsontext"
	"errors"
	"fmt"
	"maps"
	"math"
	"math/big"
	"slices"
	"strconv"
	"strings"
)

// The errors of Marshal.
var (
	errType      = errors.New("jsondoc: a value of an unsupported type")
	errNotFinite = errors.New("jsondoc: a number that is not finite")
	errNumber    = errors.New("jsondoc: a json.Number that is not a number")
)

// Marshal returns v as JSON and a newline: the bytes of
// json.dumps(v, indent=2, sort_keys=True, ensure_ascii=False) and "\n" in
// Python. The values of v are map[string]any, []any, string, bool, nil,
// json.Number, int, int64, uint64, and float64. Marshal returns an error for
// a value of another type, a number that is not finite, and a string that is
// not valid UTF-8.
func Marshal(v any) ([]byte, error) {
	var buf bytes.Buffer
	enc := jsontext.NewEncoder(&buf,
		jsontext.WithIndent("  "),
		jsontext.SpaceAfterColon(true),
		jsontext.EscapeForHTML(false),
		jsontext.EscapeForJS(false),
	)
	if err := write(enc, v); err != nil {
		return nil, err
	}
	return buf.Bytes(), nil
}

// write writes v to enc, with the keys of each object in sorted order.
func write(enc *jsontext.Encoder, v any) error {
	switch x := v.(type) {
	case map[string]any:
		return writeObject(enc, x)
	case []any:
		return writeArray(enc, x)
	case string:
		return enc.WriteToken(jsontext.String(x))
	case bool:
		return enc.WriteToken(jsontext.Bool(x))
	case nil:
		return enc.WriteToken(jsontext.Null)
	}
	number, err := numberLiteral(v)
	if err != nil {
		return err
	}
	return enc.WriteValue(jsontext.Value(number))
}

// writeObject writes object to enc, with its keys in sorted order.
func writeObject(enc *jsontext.Encoder, object map[string]any) error {
	if err := enc.WriteToken(jsontext.BeginObject); err != nil {
		return err
	}
	for _, key := range slices.Sorted(maps.Keys(object)) {
		if err := enc.WriteToken(jsontext.String(key)); err != nil {
			return err
		}
		if err := write(enc, object[key]); err != nil {
			return err
		}
	}
	return enc.WriteToken(jsontext.EndObject)
}

// writeArray writes array to enc.
func writeArray(enc *jsontext.Encoder, array []any) error {
	if err := enc.WriteToken(jsontext.BeginArray); err != nil {
		return err
	}
	for _, item := range array {
		if err := write(enc, item); err != nil {
			return err
		}
	}
	return enc.WriteToken(jsontext.EndArray)
}

// numberLiteral returns the JSON literal of the number v, as Python writes it.
func numberLiteral(v any) (string, error) {
	switch x := v.(type) {
	case json.Number:
		return pythonNumber(x)
	case int:
		return strconv.Itoa(x), nil
	case int64:
		return strconv.FormatInt(x, 10), nil
	case uint64:
		return strconv.FormatUint(x, 10), nil
	case float64:
		return pythonFloat(x)
	}
	return "", fmt.Errorf("%w: %T", errType, v)
}

// pythonNumber returns the literal of n as Python writes it after json.loads,
// which reads an integer literal as an int and any other number as a float.
func pythonNumber(n json.Number) (string, error) {
	if !strings.ContainsAny(string(n), ".eE") {
		i, ok := new(big.Int).SetString(string(n), 10)
		if !ok {
			return "", errNumber
		}
		return i.String(), nil
	}
	f, err := n.Float64()
	if err != nil {
		if errors.Is(err, strconv.ErrRange) {
			return "", errNotFinite
		}
		return "", errNumber
	}
	return pythonFloat(f)
}

// pythonFloat returns f as the repr function of Python does: the shortest
// digits that read back as f, in positional form with at least one decimal
// from 0.0001 up to 10^16, and in exponent form outside that range.
func pythonFloat(f float64) (string, error) {
	if math.IsInf(f, 0) || math.IsNaN(f) {
		return "", errNotFinite
	}
	if a := math.Abs(f); a != 0 && (a < 1e-4 || a >= 1e16) {
		return strconv.FormatFloat(f, 'e', -1, 64), nil
	}
	s := strconv.FormatFloat(f, 'f', -1, 64)
	if !strings.Contains(s, ".") {
		s += ".0"
	}
	return s, nil
}
