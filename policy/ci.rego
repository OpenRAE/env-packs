package main

import rego.v1

ci := doc(".github/workflows/ci.yml")
mandatory := object.keys(ci.jobs) - {"verify","sonar"}
guard := s if { some s in ci.jobs.verify.steps; object.get(s,"run","") != ""; count(object.get(s,"env",{}))>0 }
mapped_results := {m[1] | some _,value in guard.env; some m in regex.find_all_string_submatch_n(`needs\.([A-Za-z0-9_-]+)\.result`,value,-1)}

valid_ci_aggregate if {
	count({"compile","tests","audit","content"} - object.keys(ci.jobs)) == 0
	needs(ci.jobs.verify) == mandatory
	contains(ci.jobs.verify["if"],"always()")
	mapped_results == mandatory
}
violations contains "ci.aggregate" if not valid_ci_aggregate

valid_ci_independence if { every name in mandatory { count(needs(ci.jobs[name])) == 0 } }
violations contains "ci.independence" if not valid_ci_independence

valid_ci_coverage if {
	needs(ci.jobs.sonar) == {"tests","go"}
	{name | some name in mandatory; contains(runs(ci.jobs[name]),"unittest discover -s tests")} == {"tests"}
	contains(runs(ci.jobs.tests),"coverage run")
	contains(runs(ci.jobs.tests),"coverage xml")
	count(step(ci.jobs.tests,"actions/upload-artifact@"))>0
	count(step(ci.jobs.sonar,"actions/download-artifact@"))>0
	"coverage-xml" in {s.with.name | some s in ci.jobs.sonar.steps; startswith(object.get(s,"uses",""),"actions/download-artifact@")}
	every marker in {"unittest discover","coverage run","go test"} { not contains(runs(ci.jobs.sonar),marker) }
	[s.with.path | some s in ci.jobs.go.steps; startswith(object.get(s,"uses",""),"actions/upload-artifact@")] == ["coverage-go.out"]
	"coverage-go" in {s.with.name | some s in ci.jobs.sonar.steps; startswith(object.get(s,"uses",""),"actions/download-artifact@")}
}
violations contains "ci.coverage" if not valid_ci_coverage

valid_ci_secrets if {
	condition := lower(ci.jobs.sonar["if"])
	every marker in {"dependabot","github.repository","pull_request"} { contains(condition,marker) }
	count([s | some s in ci.jobs.sonar.steps; "SONAR_TOKEN" in object.keys(object.get(s,"env",{}))])>0
	every _,j in ci.jobs { not contains(runs(j),"SONAR_TOKEN") }
}
violations contains "ci.secrets" if not valid_ci_secrets

valid_ci_cache if {
	every name in {"tests","audit","content"} {
		s := step(ci.jobs[name],"actions/setup-python@")
		s.with.cache == "pip"
		contains(s.with["cache-dependency-path"],"requirements")
	}
}
violations contains "ci.cache" if not valid_ci_cache

valid_ci_completeness if {
	body := concat("\n",[runs(ci.jobs[name]) | some name in mandatory])
	every marker in {"unittest discover -s tests","if pip-audit;","raes-pack-validate --repo .","raes-pack-validate --packs-root packs","raes-pack-release check --all","raes-pack-release check --packs-root packs","compileall src tests"} { contains(body,marker) }
	audit := runs(ci.jobs.audit)
	every lock in {"requirements/runtime.txt","requirements/build.txt","requirements/pip-audit.txt"} { contains(audit,lock) }
}
violations contains "ci.completeness" if not valid_ci_completeness

valid_policy_command if {
	gc.workflow.policy_command == "make policy"
	"policy" in mandatory
	contains(runs(ci.jobs.policy),"make policy")
	contains(input.text.Makefile,"conftest verify")
	contains(input.text.Makefile,"conftest test")
	contains(input.text.Makefile,"actionlint")
}
violations contains "gate.same-command" if not valid_policy_command

valid_make if {
	make := input.text.Makefile
	regex.match(`(?m)^\.DEFAULT_GOAL\s*:=\s*help\s*$`,make)
	regex.match(`(?m)^GH\s*\?=\s*gh\s*$`,make)
	phony := concat(" ",regex.find_all_string_submatch_n(`(?m)^\.PHONY:([^\n]*)`,make,-1)[0])
	contains(phony,"devmain")
	contains(phony,"help")
	recipe := regex.find_all_string_submatch_n(`(?m)^devmain:[^\n]*\n(?:\t[^\n]*\n)+`,make,-1)[0][0]
	not contains(recipe,"|| true")
	not contains(recipe,"2>/dev/null")
	not regex.match(`(?m)^\t-`,recipe)
	not contains(make,"OpenRAE/")
	not contains(make,"Brad-Edwards/")
}
violations contains "make.safety" if not valid_make
