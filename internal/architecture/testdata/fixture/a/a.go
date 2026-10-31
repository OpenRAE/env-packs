// Package a uses symbols that the loader must report.
package a

import (
	"os"

	"example.com/dep"
	"example.com/fixture/b"
)

// A returns a string.
func A() string {
	println("debug")
	return os.Getenv("HOME") + b.B() + string(rune(dep.Value()))
}
