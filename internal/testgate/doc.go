// Package testgate holds the test gates of ADR 0047: mutation testing on the
// changed lines, and the proof that each new regression test fails on the
// code before its fix.
//
// The gates run git, go-mutesting, and go test through a [Runner]. They
// report problems as [Finding] values, and they do not print, so the command
// in tools/testgate decides how to show them. See
// docs/development/designs/0002-test-gates.md.
package testgate
