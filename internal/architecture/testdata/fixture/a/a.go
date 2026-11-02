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

// Streams uses process streams directly and through an alias.
func Streams() {
	out := os.Stdout
	_, _ = out.WriteString("debug")
	_, _ = os.Stderr.WriteString("debug")
	_, _ = os.Stdin.Read(nil)
}
