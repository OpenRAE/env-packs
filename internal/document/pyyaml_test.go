package document

import (
	"math"
	"testing"
)

// TestSameValue checks the comparison with the values of PyYAML directly, so
// that it also covers values that yaml.v3 does not give today.
func TestSameValue(t *testing.T) {
	const maxUint = uint64(math.MaxUint64)
	tests := []struct {
		s    string
		v    any
		want bool
	}{
		{s: "abc", v: "abc", want: true},
		{s: "abc", v: "abd"},
		{s: "true", v: true, want: true},
		{s: "False", v: false, want: true},
		{s: "yes", v: true, want: true},
		{s: "On", v: true, want: true},
		{s: "off", v: false, want: true},
		{s: "no", v: true},
		{s: "0", v: 0, want: true},
		{s: "+12", v: 12, want: true},
		{s: "1", v: 2},
		{s: "0755", v: 493, want: true},
		{s: "0755", v: 755},
		{s: "0b1_1", v: 3, want: true},
		{s: "-0x1F", v: -31, want: true},
		{s: "1:30", v: 90, want: true},
		{s: "1:30", v: 91},
		{s: "-1:30:00", v: -5400, want: true},
		{s: "18446744073709551615", v: maxUint, want: true},
		{s: "18446744073709551615", v: maxUint - 1},
		{s: "18446744073709551621", v: 5},
		{s: "-1", v: uint64(1)},
		{s: "5", v: uint64(6)},
		{s: "1", v: int64(1)},
		{s: "1.5", v: 1.5, want: true},
		{s: "1_0.5", v: 10.5, want: true},
		{s: "1.5", v: 2.5},
		{s: "1:30.5", v: 90.5, want: true},
		{s: "-1:30.5", v: -90.5, want: true},
		{s: "1:30.5", v: 90.0},
		{s: "1.0e+999", v: math.Inf(1), want: true},
		{s: ".inf", v: math.Inf(1), want: true},
		{s: "-.Inf", v: math.Inf(-1), want: true},
		{s: "-.inf", v: math.Inf(1)},
		{s: ".nan", v: math.NaN(), want: true},
		{s: ".nan", v: 1.0},
		{s: "1.0", v: math.NaN()},
		{s: "~", v: nil, want: true},
		{s: "", v: nil, want: true},
		{s: "null", v: "null"},
		{s: "2026-11-01", v: "2026-11-01"},
		{s: "<<", v: "<<"},
		{s: "=", v: "="},
		{s: "0b_", v: "0b_"},
	}
	for _, tt := range tests {
		if got := sameValue(tt.s, tt.v); got != tt.want {
			t.Errorf("sameValue(%q, %#v) = %v, want %v", tt.s, tt.v, got, tt.want)
		}
	}
}
