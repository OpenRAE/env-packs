package architecture

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
