// Package b has a blank import.
package b

import _ "embed"

// B returns a string.
func B() string { return "b" }
