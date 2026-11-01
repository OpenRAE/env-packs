package architecture

import (
	"cmp"
	"slices"
)

// Rule identifiers of the checks that the model does not define.
const (
	// RuleModel marks a defect inside the model.
	RuleModel = "model"
	// RuleDesign marks a design record that does not agree with the model.
	RuleDesign = "design"
	// RulePackageOwner marks a package that no component owns.
	RulePackageOwner = "package-owner"
	// RuleUnknownPackage marks a model package that the code does not have.
	RuleUnknownPackage = "unknown-package"
	// RuleComponentDependency marks an import that the model does not permit.
	RuleComponentDependency = "component-dependency"
	// RuleExternalModule marks an import of a module that a component may not use.
	RuleExternalModule = "external-module"
	// RuleUnreadPath marks a path of the module that the checks cannot read.
	RuleUnreadPath = "unread-path"
	// RuleC4View marks a C4 view file that differs from the rendered model.
	RuleC4View = "c4-view"
)

// A Finding is one difference between the model and the code, the design
// records, or the model itself.
type Finding struct {
	// Location is "file:line", or a file or directory when no line applies.
	Location string
	// Rule is the identifier of the broken rule.
	Rule string
	// Message states the problem.
	Message string
	// Fix tells how to correct the problem.
	Fix string
}

// String formats the finding as two lines: the location, the rule, and the
// message, then the fix.
func (f Finding) String() string {
	return f.Location + ": " + f.Rule + ": " + f.Message + "\n\tfix: " + f.Fix
}

// SortFindings sorts findings by location, rule, and message, and removes
// exact duplicates. It returns the sorted slice.
func SortFindings(findings []Finding) []Finding {
	slices.SortFunc(findings, func(a, b Finding) int {
		return cmp.Or(
			cmp.Compare(a.Location, b.Location),
			cmp.Compare(a.Rule, b.Rule),
			cmp.Compare(a.Message, b.Message),
			cmp.Compare(a.Fix, b.Fix),
		)
	})
	return slices.Compact(findings)
}
