package testgate

import (
	"slices"
	"testing"

	"github.com/google/go-cmp/cmp"
)

// The outputs of go test -json, from Go 1.27.
const (
	buildFailOutput = `{"ImportPath":"example.com/x [example.com/x.test]","Action":"build-output","Output":"# example.com/x\n"}
{"ImportPath":"example.com/x [example.com/x.test]","Action":"build-fail"}
{"Action":"start","Package":"example.com/x"}
{"Action":"fail","Package":"example.com/x","Elapsed":0,"FailedBuild":"example.com/x [example.com/x.test]"}
`
	testFailOutput = `{"Action":"start","Package":"example.com/x"}
{"Action":"run","Package":"example.com/x","Test":"TestF"}
{"Action":"output","Package":"example.com/x","Test":"TestF","Output":"--- FAIL: TestF (0.00s)\n"}
{"Action":"fail","Package":"example.com/x","Test":"TestF","Elapsed":0}
{"Action":"run","Package":"example.com/x","Test":"TestG"}
{"Action":"pass","Package":"example.com/x","Test":"TestG","Elapsed":0}
{"Action":"run","Package":"example.com/x","Test":"TestS"}
{"Action":"skip","Package":"example.com/x","Test":"TestS","Elapsed":0}
{"Action":"fail","Package":"example.com/x","Elapsed":0.002}
`
	passOutput = `{"Action":"start","Package":"example.com/x"}
{"Action":"pass","Package":"example.com/x","Elapsed":0.002}
`
	noTestsOutput = `{"Action":"start","Package":"example.com/x/nt"}
{"Action":"output","Package":"example.com/x/nt","Output":"?   \texample.com/x/nt\t[no test files]\n"}
{"Action":"skip","Package":"example.com/x/nt","Elapsed":0}
`
)

func TestParseEvents(t *testing.T) {
	got, err := parseEvents([]byte(passOutput))
	want := []event{{Action: "start", Package: "example.com/x"}, {Action: "pass", Package: "example.com/x"}}
	if err != nil {
		t.Fatalf("parseEvents() error = %v", err)
	}
	if diff := cmp.Diff(want, got); diff != "" {
		t.Errorf("parseEvents() mismatch (-want +got):\n%s", diff)
	}
	if got, err := parseEvents(nil); err != nil || got != nil {
		t.Errorf("parseEvents(nil) = %v, %v, want nil, nil", got, err)
	}
	if _, err := parseEvents([]byte("{\"Action\":\"pass\"}\nFAIL\n")); err == nil {
		t.Error("parseEvents() of text that is not JSON: error = nil, want an error")
	}
}

func TestBuildFailed(t *testing.T) {
	for output, want := range map[string]bool{buildFailOutput: true, testFailOutput: false, passOutput: false} {
		events, err := parseEvents([]byte(output))
		if err != nil {
			t.Fatalf("parseEvents() error = %v", err)
		}
		if got := buildFailed(events); got != want {
			t.Errorf("buildFailed(%q) = %v, want %v", output, got, want)
		}
	}
}

func TestOutcome(t *testing.T) {
	events, err := parseEvents([]byte(testFailOutput))
	if err != nil {
		t.Fatalf("parseEvents() error = %v", err)
	}
	tests := []struct{ pkg, test, want string }{
		{pkg: "example.com/x", test: "TestF", want: "fail"},
		{pkg: "example.com/x", test: "TestG", want: "pass"},
		{pkg: "example.com/x", test: "TestS", want: "skip"},
		{pkg: "example.com/x", test: "", want: "fail"},
		{pkg: "example.com/x", test: "TestMissing", want: ""},
		{pkg: "example.com/other", test: "TestF", want: ""},
	}
	for _, tt := range tests {
		if got := outcome(events, tt.pkg, tt.test); got != tt.want {
			t.Errorf("outcome(%q, %q) = %q, want %q", tt.pkg, tt.test, got, tt.want)
		}
	}
	late := slices.Concat(events, []event{{Action: "output", Package: "example.com/x", Test: "TestF"}})
	if got := outcome(late, "example.com/x", "TestF"); got != "fail" {
		t.Errorf("outcome() with output after the result = %q, want %q", got, "fail")
	}
	if got := packageOf(events); got != "example.com/x" {
		t.Errorf("packageOf() = %q, want %q", got, "example.com/x")
	}
	if got := packageOf([]event{{Action: "build-fail"}}); got != "" {
		t.Errorf("packageOf() without a package = %q, want the empty string", got)
	}
}
