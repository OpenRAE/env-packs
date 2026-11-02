package testgate

// Rule identifiers of the findings.
const (
	// RuleMutant marks a mutant that no test kills.
	RuleMutant = "mutant"
	// RuleRecord marks a defect in mutation.yaml.
	RuleRecord = "mutation-record"
	// RuleRegression marks a regression test that does not fail on the base.
	RuleRegression = "regression"
)
