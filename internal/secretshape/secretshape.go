// Package secretshape holds the one policy for secret-shaped keys and values
// in pack and kit documents (design 0005).
//
// The policy is a heuristic. It rejects common shapes of credentials, and it
// does not prove that a document holds no secret.
package secretshape

import (
	"regexp"
	"strings"

	"golang.org/x/text/cases"
)

// keyPattern matches the parts of a folded key or name that mark a secret.
var keyPattern = regexp.MustCompile(`credential|password|private_key|secret|signed_url|token`)

// valuePattern matches the secret-shaped parts of a value: a private key, a
// signature or a token in a query, credentials in a URL, a JSON Web Token, and
// a GitHub or AWS access key.
//
// The patterns are those of the Python code. Python also folds "ı" and "İ" to
// "i", so the query keys list them. Python reads \s as Unicode white space and
// RE2 reads it as ASCII white space, so these patterns match a few more values.
var valuePattern = regexp.MustCompile(strings.Join([]string{
	`-{5}BEGIN [A-Z ]*PRIVATE KEY-{5}`,
	`(?i:x-amz-s[iıİ]gnature|s[iıİ]g|s[iıİ]gnature|token)=[^&\s]+`,
	`(?i:https?)://[^/:@\s]+:[^/@\s]+@`,
	`(?:eyJ[A-Za-z0-9_-]{8,}\.){2}[A-Za-z0-9_-]{8,}`,
	`(?:gh[pousr]_|AKIA)[A-Za-z0-9_-]{12,}`,
}, "|"))

// coordinatePattern matches an environment coordinate, such as "$NAME",
// "${NAME}", or "env:NAME". The letters match in each case, in ASCII only.
var coordinatePattern = regexp.MustCompile(`^(?:\$\{?[A-Za-z_]\w*\}?|[Ee][Nn][Vv]:[A-Za-z_]\w*)$`)

// MatchKey reports whether a mapping key or a parameter name holds a secret
// fragment, such as "token" or "private_key". The match folds the letter case
// of each Unicode letter, and it reads "-" as "_".
func MatchKey(name string) bool {
	return keyPattern.MatchString(strings.ReplaceAll(cases.Fold().String(name), "-", "_"))
}

// MatchValue reports whether s holds a secret-shaped part.
func MatchValue(s string) bool {
	return valuePattern.MatchString(s)
}

// MatchParameter reports whether a value that must be public, such as a
// parameter value or a source revision, is secret-shaped: it holds a
// secret-shaped part, or it is an environment coordinate.
func MatchParameter(s string) bool {
	return coordinatePattern.MatchString(s) || MatchValue(s)
}

// Scan reports whether a document from the document package has a mapping
// key that [MatchKey] matches, and whether it has a string that [MatchValue]
// matches. Scan reads each string of the document, in mappings and in arrays.
func Scan(doc any) (key, value bool) {
	var scan func(node any)
	scan = func(node any) {
		switch v := node.(type) {
		case map[string]any:
			for name, item := range v {
				if MatchKey(name) {
					key = true
				}
				scan(item)
			}
		case []any:
			for _, item := range v {
				scan(item)
			}
		case string:
			if MatchValue(v) {
				value = true
			}
		}
	}
	scan(doc)
	return key, value
}
