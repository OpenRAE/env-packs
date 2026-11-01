// Package architecture checks this repository against its architecture model
// (ADR 0047).
//
// The model, architecture/model.yaml, names the containers and the components
// of the Go implementation, the packages that each component owns, the
// permitted dependencies and modules, and the rules for each component. The
// design records in docs/development/designs/ record each change to the
// structure of the model.
//
// The package reports differences as [report.Finding] values. It does not print, so
// the command in tools/archcheck decides how to show them.
package architecture
