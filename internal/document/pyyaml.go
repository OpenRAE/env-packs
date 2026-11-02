package document

import (
	"math"
	"math/big"
	"regexp"
	"strconv"
	"strings"
)

// The implicit resolvers of PyYAML (yaml/resolver.py) for plain scalars. The
// Python implementation reads pack YAML with them. PyYAML tries them in the
// order of pyResolve and takes the first match.
var (
	pyBool      = regexp.MustCompile(`^(?:yes|Yes|YES|no|No|NO|true|True|TRUE|false|False|FALSE|on|On|ON|off|Off|OFF)$`)
	pyFloat     = regexp.MustCompile(`^(?:[-+]?(?:[0-9][0-9_]*)\.[0-9_]*(?:[eE][-+][0-9]+)?|\.[0-9][0-9_]*(?:[eE][-+][0-9]+)?|[-+]?[0-9][0-9_]*(?::[0-5]?[0-9])+\.[0-9_]*|[-+]?\.(?:inf|Inf|INF)|\.(?:nan|NaN|NAN))$`)
	pyInt       = regexp.MustCompile(`^(?:[-+]?0b[0-1_]+|[-+]?0[0-7_]+|[-+]?(?:0|[1-9][0-9_]*)|[-+]?0x[0-9a-fA-F_]+|[-+]?[1-9][0-9_]*(?::[0-5]?[0-9])+)$`)
	pyNull      = regexp.MustCompile(`^(?:~|null|Null|NULL|)$`)
	pyTimestamp = regexp.MustCompile(`^(?:[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]|[0-9][0-9][0-9][0-9]-[0-9][0-9]?-[0-9][0-9]?(?:[Tt]|[ \t]+)[0-9][0-9]?:[0-9][0-9]:[0-9][0-9](?:\.[0-9]*)?(?:[ \t]*(?:Z|[-+][0-9][0-9]?(?::[0-9][0-9])?))?)$`)
)

// A pyKind is the kind of value that PyYAML constructs for a plain scalar.
type pyKind int

// The kinds of pyScalar. The kind pyFails marks a scalar that the strict
// loader of the Python code rejects: the merge key "<<", the value key "=",
// and an integer without digits.
const (
	pyString pyKind = iota
	pyBoolean
	pyInteger
	pyNumber
	pyNone
	pyTime
	pyFails
)

// A pyScalar is the value that PyYAML constructs for a plain scalar.
type pyScalar struct {
	kind pyKind
	b    bool
	i    *big.Int
	f    float64
}

// pyResolve returns the value that PyYAML constructs for the plain scalar s.
func pyResolve(s string) pyScalar {
	switch {
	case pyBool.MatchString(s):
		lower := strings.ToLower(s)
		return pyScalar{kind: pyBoolean, b: lower == "yes" || lower == "true" || lower == "on"}
	case pyFloat.MatchString(s):
		return pyScalar{kind: pyNumber, f: pyFloatValue(s)}
	case pyInt.MatchString(s):
		i, ok := pyIntValue(s)
		if !ok {
			return pyScalar{kind: pyFails}
		}
		return pyScalar{kind: pyInteger, i: i}
	case s == "<<":
		return pyScalar{kind: pyFails}
	case pyNull.MatchString(s):
		return pyScalar{kind: pyNone}
	case pyTimestamp.MatchString(s):
		return pyScalar{kind: pyTime}
	case s == "=":
		return pyScalar{kind: pyFails}
	}
	return pyScalar{kind: pyString}
}

// pyIntValue constructs an integer as construct_yaml_int of PyYAML does. It
// returns false when Python fails: a base prefix without digits.
func pyIntValue(s string) (*big.Int, bool) {
	s = strings.ReplaceAll(s, "_", "")
	sign := int64(1)
	if s[0] == '-' {
		sign = -1
	}
	s = strings.TrimLeft(s, "+-")
	var i *big.Int
	ok := true
	switch {
	case s == "0":
		i = new(big.Int)
	case strings.HasPrefix(s, "0b"):
		i, ok = new(big.Int).SetString(s[2:], 2)
	case strings.HasPrefix(s, "0x"):
		i, ok = new(big.Int).SetString(s[2:], 16)
	case s[0] == '0':
		i, ok = new(big.Int).SetString(s, 8)
	case strings.Contains(s, ":"):
		i = new(big.Int)
		for part := range strings.SplitSeq(s, ":") {
			// The pattern pyInt admits only digits between the colons.
			digit, _ := new(big.Int).SetString(part, 10)
			i.Mul(i, big.NewInt(60)).Add(i, digit)
		}
	default:
		i, ok = new(big.Int).SetString(s, 10)
	}
	if !ok {
		return nil, false
	}
	return i.Mul(i, big.NewInt(sign)), true
}

// pyFloatValue constructs a number as construct_yaml_float of PyYAML does.
func pyFloatValue(s string) float64 {
	s = strings.ToLower(strings.ReplaceAll(s, "_", ""))
	sign := 1
	if s[0] == '-' {
		sign = -1
	}
	s = strings.TrimLeft(s, "+-")
	switch s {
	case ".inf":
		return math.Inf(sign)
	case ".nan":
		return math.NaN()
	}
	value := 0.0
	for part := range strings.SplitSeq(s, ":") {
		// The pattern pyFloat admits only valid syntax, so the only error is
		// ErrRange, with which ParseFloat returns an infinity, as Python does.
		digit, _ := strconv.ParseFloat(part, 64) //nolint:errcheck // See the comment above: the result is right for each admitted input.
		value = value*60 + digit
	}
	return float64(sign) * value
}

// sameValue reports whether the Go reader value v of the plain scalar s is
// the value that PyYAML constructs for it.
func sameValue(s string, v any) bool {
	py := pyResolve(s)
	switch py.kind {
	case pyString:
		str, ok := v.(string)
		return ok && str == s
	case pyBoolean:
		b, ok := v.(bool)
		return ok && b == py.b
	case pyInteger:
		return sameInteger(py.i, v)
	case pyNumber:
		f, ok := v.(float64)
		return ok && (f == py.f || math.IsNaN(f) && math.IsNaN(py.f))
	case pyNone:
		return v == nil
	case pyTime, pyFails:
	}
	return false
}

// sameInteger reports whether v is a Go integer with the value i.
func sameInteger(i *big.Int, v any) bool {
	switch n := v.(type) {
	case int:
		return i.IsInt64() && i.Int64() == int64(n)
	case uint64:
		return i.IsUint64() && i.Uint64() == n
	}
	return false
}
