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

// Message calls a method of the predeclared error type, which has no package.
func Message(err error) string {
	return err.Error()
}
