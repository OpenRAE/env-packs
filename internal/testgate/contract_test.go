package testgate

import (
	"strings"
	"testing"
)

const contractSource = `package c

func a() (int, error) {
	return 0, errBad
}

func b() (int, error) {
	return 0, nil
}

func c() (int, bool) {
	return 0, false
}

func d() error {
	return wrap(1)
}

func e() (n int, err error) {
	f := func() (int, bool) {
		return 0, true
	}
	_ = f
	return 0, fmt.Errorf("e %d", 1)
}

func g() (int, bool) {
	f := func() (int, error) {
		return 0, errBad
	}
	_ = f
	return 0, true
}

func h() {
	return
}

func i() {
	return 0, errBad
}

func j() (int, error)
`

func TestErrorResult(t *testing.T) {
	tests := []struct {
		line int
		want string
		ok   bool
	}{
		{line: 4, want: "errBad", ok: true},
		{line: 8},
		{line: 12},
		{line: 16},
		{line: 21},
		{line: 24, want: `fmt.Errorf("e %d", 1)`, ok: true},
		{line: 29, want: "errBad", ok: true},
		{line: 32},
		{line: 36},
		{line: 40},
		{line: 43},
		{line: 3},
	}
	for _, tt := range tests {
		got, ok := errorResult(contractSource, tt.line)
		if got != tt.want || ok != tt.ok {
			t.Errorf("errorResult(line %d) = %q, %v, want %q, %v", tt.line, got, ok, tt.want, tt.ok)
		}
	}
	if _, ok := errorResult("package", 1); ok {
		t.Error("errorResult() of invalid source: ok = true, want false")
	}
	if _, ok := errorResult(contractSource+"\nfunc broken(\n", 4); ok {
		t.Error("errorResult() of source with a syntax error after the statement: ok = true, want false")
	}
}

func TestErrorContract(t *testing.T) {
	mutantOf := func(name, old, replacement string) mutant {
		var m mutant
		m.Mutator.Name = name
		m.Mutator.Original = contractSource
		m.Mutator.Mutated = strings.Replace(contractSource, old, replacement, 1)
		return m
	}
	tests := []struct {
		name string
		m    mutant
		line int
		want bool
	}{
		{name: "number beside an error", m: mutantOf("numbers/incrementer", "return 0, errBad", "return 1, errBad"), line: 4, want: true},
		{name: "decremented number beside an error", m: mutantOf("numbers/decrementer", "return 0, errBad", "return -1, errBad"), line: 4, want: true},
		{name: "number in the error", m: mutantOf("numbers/incrementer", `fmt.Errorf("e %d", 1)`, `fmt.Errorf("e %d", 2)`), line: 24},
		{name: "number beside nil", m: mutantOf("numbers/incrementer", "return 0, nil", "return 1, nil"), line: 8},
		{name: "other mutator", m: mutantOf("branch/if", "return 0, errBad", "return 1, errBad"), line: 4},
		{name: "mutant that does not parse", m: mutantOf("numbers/incrementer", "return 0, errBad", "return 0, errBad +"), line: 4},
		{name: "mutant with a syntax error after the statement", m: mutantOf("numbers/incrementer", "func h() {", "func h( {"), line: 4},
	}
	for _, tt := range tests {
		if got := errorContract(tt.m, tt.line); got != tt.want {
			t.Errorf("errorContract(%s) = %v, want %v", tt.name, got, tt.want)
		}
	}
}

func TestEvaluateErrorContract(t *testing.T) {
	var m mutant
	m.Mutator.Name = "numbers/incrementer"
	m.Mutator.File = "c.go"
	m.Mutator.Original = contractSource
	m.Mutator.Mutated = strings.Replace(contractSource, "return 0, errBad", "return 1, errBad", 1)
	got, err := evaluate(mutestingReport{Escaped: []mutant{m}}, []string{"c.go"}, nil, Records{Version: 1}, true)
	if err != nil || got.Escaped != 1 || got.Equivalent != 1 || len(got.Findings) != 0 {
		t.Errorf("evaluate() of a number beside an error = %+v, %v; want one equivalent mutant and no finding", got, err)
	}
}
