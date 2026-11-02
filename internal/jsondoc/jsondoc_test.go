package jsondoc

import (
	"encoding/json"
	"errors"
	"math"
	"testing"
)

// golden holds the bytes that Python gives for the value of TestMarshal:
// json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n".
const golden = "{\n  \"a\": \"quote\\\" backslash\\\\ ctrl\\u0001\\u001f\\b\\f\\n\\r\\t del\u007f nbsp\u00a0 ls\u2028 ps\u2029 emoji\U0001f600 html</>&\",\n  \"b\": [\n    1,\n    -1234567890123,\n    2.5,\n    1.0,\n    1e+16,\n    1e-05,\n    true,\n    false,\n    null,\n    {},\n    [],\n    [\n      {\n        \"z\": \"y\"\n      }\n    ]\n  ],\n  \"big\": 12345678901234567890,\n  \"n\": {\n    \"nested\": {\n      \"deep\": \"x\"\n    }\n  },\n  \"\u00e9t\u00e9\": 0\n}\n"

func TestMarshal(t *testing.T) {
	value := map[string]any{
		"b":             []any{1, int64(-1234567890123), 2.5, 1.0, 1e16, 1e-05, true, false, nil, map[string]any{}, []any{}, []any{map[string]any{"z": "y"}}},
		"a":             "quote\" backslash\\ ctrl\u0001\u001f\u0008\u000c\n\u000d\u0009 del\u007f nbsp\u00a0 ls\u2028 ps\u2029 emoji\U0001f600 html</>&",
		"n":             map[string]any{"nested": map[string]any{"deep": "x"}},
		"big":           uint64(12345678901234567890),
		"\u00e9t\u00e9": json.Number("-0"),
	}
	got, err := Marshal(value)
	if err != nil || string(got) != golden {
		t.Errorf("Marshal() = %q, %v; want %q", got, err, golden)
	}
}

func TestPythonFloat(t *testing.T) {
	// The values are those of repr in Python.
	tests := []struct {
		f    float64
		want string
	}{
		{f: 0.0, want: "0.0"},
		{f: math.Copysign(0, -1), want: "-0.0"},
		{f: 1.0, want: "1.0"},
		{f: 0.1, want: "0.1"},
		{f: 1e+16, want: "1e+16"},
		{f: 9999999999999998.0, want: "9999999999999998.0"},
		{f: 0.0001, want: "0.0001"},
		{f: 9.999999999999999e-05, want: "9.999999999999999e-05"},
		{f: 5e-324, want: "5e-324"},
		{f: 1.7976931348623157e+308, want: "1.7976931348623157e+308"},
		{f: 123456.789, want: "123456.789"},
		{f: 1000000000000000.0, want: "1000000000000000.0"},
		{f: -2.5e-07, want: "-2.5e-07"},
		{f: 0.30000000000000004, want: "0.30000000000000004"},
		{f: 100.0, want: "100.0"},
	}
	for _, tt := range tests {
		if got, err := pythonFloat(tt.f); err != nil || got != tt.want {
			t.Errorf("pythonFloat(%v) = %q, %v; want %q", tt.f, got, err, tt.want)
		}
	}
}

func TestPythonNumber(t *testing.T) {
	// The values are those of json.dumps(json.loads(literal)) in Python.
	tests := map[string]string{
		"0":                       "0",
		"-0":                      "0",
		"7":                       "7",
		"-12":                     "-12",
		"12345678901234567890123": "12345678901234567890123",
		"1.0":                     "1.0",
		"1e2":                     "100.0",
		"1E2":                     "100.0",
		"-0.0":                    "-0.0",
		"0.1":                     "0.1",
		"1.5e300":                 "1.5e+300",
		"2.5E-5":                  "2.5e-05",
		"100000000000000000000.0": "1e+20",
	}
	for literal, want := range tests {
		if got, err := pythonNumber(json.Number(literal)); err != nil || got != want {
			t.Errorf("pythonNumber(%s) = %q, %v; want %q", literal, got, err, want)
		}
	}
}

func TestMarshalErrors(t *testing.T) {
	tests := []struct {
		name  string
		value any
		want  error
	}{
		{name: "type", value: struct{}{}, want: errType},
		{name: "nested type", value: map[string]any{"a": []any{1, []string{"x"}}}, want: errType},
		{name: "infinity", value: math.Inf(1), want: errNotFinite},
		{name: "negative infinity", value: math.Inf(-1), want: errNotFinite},
		{name: "not a number", value: math.NaN(), want: errNotFinite},
		{name: "number out of range", value: json.Number("1e400"), want: errNotFinite},
		{name: "number syntax", value: json.Number("1.x"), want: errNumber},
		{name: "integer syntax", value: json.Number("x"), want: errNumber},
	}
	for _, tt := range tests {
		if got, err := Marshal(tt.value); got != nil || !errors.Is(err, tt.want) {
			t.Errorf("Marshal() of a %s = %q, %v; want %v", tt.name, got, err, tt.want)
		}
	}
	for _, value := range []any{"bad\xff", map[string]any{"bad\xff": 1}, []any{"bad\xff"}} {
		if got, err := Marshal(value); got != nil || err == nil {
			t.Errorf("Marshal(%q) = %q, %v; want an error for invalid UTF-8", value, got, err)
		}
	}
}
