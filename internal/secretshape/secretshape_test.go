package secretshape

import (
	"strings"
	"testing"
)

// Each secret-shaped test value is built from parts, so that no scanner
// reads a test file as a leaked credential.
var (
	githubToken = "ghp_" + strings.Repeat("a", 12)
	awsKey      = "AKIA" + strings.Repeat("B", 12)
	webToken    = strings.Repeat("eyJ"+strings.Repeat("c", 8)+".", 2) + strings.Repeat("d", 8)
)

func TestMatchKey(t *testing.T) {
	tests := map[string]bool{
		"token":            true,
		"API_TOKEN":        true,
		"private-key":      true,
		"Private_Key_Path": true,
		"signed-url":       true,
		"credentials":      true,
		"db_password":      true,
		"client_secret":    true,
		"ſecret":           true, // U+017F folds to "s", as in Python.
		"toKen":            true, // The Kelvin sign folds to "k", as in Python.
		"private key":      false,
		"passwd":           false,
		"name":             false,
		"":                 false,
	}
	for name, want := range tests {
		if got := MatchKey(name); got != want {
			t.Errorf("MatchKey(%q) = %v, want %v", name, got, want)
		}
	}
}

func TestMatchValue(t *testing.T) {
	tests := map[string]bool{
		"-----BEGIN RSA PRIVATE KEY-----": true,
		"-----BEGIN PRIVATE KEY-----":     true,
		"-----BEGIN PUBLIC KEY-----":      false,
		"https://h/o?X-Amz-Signature=abc": true,
		"https://h/o?a=1&SIG=1":           true,
		"mytoken=abc":                     true,
		"sıg=abc":                         true,
		"X-AMZ-SİGNATURE=abc":             true,
		"sig=\u00a0":                      true, // RE2 reads \s as ASCII white space only.
		"token=":                          false,
		"token=&a=1":                      false,
		"token= a":                        false,
		"https://user:pass@host/":         true,
		"HTTP://user:pass@host/":          true,
		"https://user@host/":              false,
		"https://host:443/path":           false,
		webToken:                          true,
		webToken[:len(webToken)-1]:        false,
		githubToken:                       true,
		"ghx_" + githubToken[4:]:          false,
		githubToken[:len(githubToken)-1]:  false,
		awsKey:                            true,
		awsKey[:len(awsKey)-1]:            false,
		"-----begin private key-----":     false,
		"akia" + awsKey[4:]:               false,
		"GHP_" + githubToken[4:]:          false,
		"a plain description":             false,
	}
	for s, want := range tests {
		if got := MatchValue(s); got != want {
			t.Errorf("MatchValue(%q) = %v, want %v", s, got, want)
		}
	}
}

func TestMatchParameter(t *testing.T) {
	tests := map[string]bool{
		"$HOME":         true,
		"${HOME}":       true,
		"${_x1}":        true,
		"env:HOME":      true,
		"ENV:home":      true,
		"${1A}":         false,
		"$":             false,
		"a$HOME":        false,
		"$HOME b":       false,
		"env:ſ":         false,
		"$K":            false,
		"envy:HOME":     false,
		githubToken:     true,
		"plain value 1": false,
	}
	for s, want := range tests {
		if got := MatchParameter(s); got != want {
			t.Errorf("MatchParameter(%q) = %v, want %v", s, got, want)
		}
	}
}

func TestScan(t *testing.T) {
	tests := []struct {
		name       string
		doc        any
		key, value bool
	}{
		{name: "clean", doc: map[string]any{"a": "b", "c": []any{"d", 1, true, nil}}},
		{name: "secret key", doc: map[string]any{"name": 1, "api_token": 1}, key: true},
		{name: "nested secret key", doc: map[string]any{"a": []any{1, map[string]any{"b": map[string]any{"password": 1}}}}, key: true},
		{name: "secret value", doc: map[string]any{"a": "b", "c": githubToken}, value: true},
		{name: "secret item", doc: map[string]any{"a": []any{"b", awsKey}}, value: true},
		{name: "secret first item", doc: []any{webToken, "b"}, value: true},
		{name: "both", doc: map[string]any{"token": "${HOME}", "b": map[string]any{"c": githubToken}}, key: true, value: true},
		{name: "coordinate value", doc: map[string]any{"a": "${HOME}"}},
		{name: "scalar", doc: 5},
	}
	for _, tt := range tests {
		if key, value := Scan(tt.doc); key != tt.key || value != tt.value {
			t.Errorf("Scan() of %s = %v, %v; want %v, %v", tt.name, key, value, tt.key, tt.value)
		}
	}
}
