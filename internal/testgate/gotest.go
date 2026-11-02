package testgate

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
)

// event is one line of the output of go test -json.
type event struct {
	Action  string `json:"Action"`
	Package string `json:"Package"`
	Test    string `json:"Test"`
}

// parseEvents decodes the output of go test -json.
func parseEvents(out []byte) ([]event, error) {
	var events []event
	dec := json.NewDecoder(bytes.NewReader(out))
	for {
		var e event
		err := dec.Decode(&e)
		if errors.Is(err, io.EOF) {
			return events, nil
		}
		if err != nil {
			return nil, fmt.Errorf("decode the output of go test -json: %w", err)
		}
		events = append(events, e)
	}
}

// buildFailed reports whether a package of the test run did not compile.
func buildFailed(events []event) bool {
	for _, e := range events {
		if e.Action == "build-fail" {
			return true
		}
	}
	return false
}

// packageOf returns the import path of the first package in the events.
func packageOf(events []event) string {
	for _, e := range events {
		if e.Package != "" {
			return e.Package
		}
	}
	return ""
}

// outcome returns the last "pass", "fail", or "skip" action of test in
// package pkg, or the empty string when the test did not end. An empty test
// selects the result of the package.
func outcome(events []event, pkg, test string) string {
	result := ""
	for _, e := range events {
		if e.Package == pkg && e.Test == test && (e.Action == "pass" || e.Action == "fail" || e.Action == "skip") {
			result = e.Action
		}
	}
	return result
}
