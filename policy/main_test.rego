package main

import rego.v1

test_read_only_defaults if {
	good := {"documents": {".github/workflows/x.yml": {"permissions": "read-all"}}}
	bad := {"documents": {".github/workflows/x.yml": {"permissions": "write-all"}}}
	passed := violations with input as good
	failed := violations with input as bad
	not "workflow.permissions" in passed
	"workflow.permissions" in failed
}

test_read_only_shapes if {
	every value in ["read-all", {"contents":"read"}, {"contents":"read","id-token":"none"}, {}] { read_only(value) }
	every value in [null,"write-all",{"contents":"write"},{"contents":"read","security-events":"write"},"some-nonsense",true,1,[]] { not read_only(value) }
}

test_pip_shapes if {
	every args in [
		["--require-hashes","-r","requirements/runtime.txt"],
		["--require-hashes","-r","a.txt","-r","b.txt"],
		["--no-deps","-e","."], ["--no-deps","--no-build-isolation","-e","."],
		["dist/foo.whl"], ["--no-deps","dist/foo.whl"],
		["--no-deps","-e","git+https://x/y.git@aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"],
	] { pip_pinned(args) }
	every args in [
		[], ["coverage"], ["pip-audit==2.10.1"], ["build==1.5.0"],
		["-e","."], ["-e",".","coverage"], ["-r","requirements/runtime.txt"],
		["dist/foo.whl","cyclonedx-bom==7.3.0"],
		["--no-deps","-e","git+https://x/y.git@main"],
		["--no-deps","-e","$SOURCE"],
	] { not pip_pinned(args) }
	every source in [".","./subdir","git+https://x/y.git@ffffffffffffffffffffffffffffffffffffffff"] { safe_source(source) }
	every source in ["git+https://x/y.git@main","git+https://x/y.git@v1.0","https://host/package","$SOURCE"] { not safe_source(source) }
}

# Each rule has a separate bounded test query. Every case must reject its mutation.
check_cases(rule) if {
 cases := {name: tc | some name, tc in data.policy_cases; tc.rule == rule}
 count(cases) > 0
 not violations[rule] with input as data.policy_baseline
 every _,tc in cases {
  broken := json.patch(data.policy_baseline, tc.patch)
  violations[rule] with input as broken
 }
}

test_compliant_baseline if {
	result := violations with input as data.policy_baseline
	count(result) == 0
}

test_hashed_requirement_extras if {
	text := sprintf("jsonschema[format-nongpl]==4.26.0 --hash=sha256:%s",[concat("",["aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"])])
	modified := json.patch(data.policy_baseline,[{"op":"replace","path":"/text/requirements~1sbom.txt","value":text}])
	not violations["dependency.lock-files"] with input as modified
	lock_pins(text).jsonschema == "4.26.0"
}

test_ci_aggregate if check_cases("ci.aggregate")

test_ci_cache if check_cases("ci.cache")

test_ci_completeness if check_cases("ci.completeness")

test_ci_coverage if check_cases("ci.coverage")

test_ci_independence if check_cases("ci.independence")

test_ci_secrets if check_cases("ci.secrets")

test_codeql_analysis if check_cases("codeql.analysis")

test_codeql_triggers if check_cases("codeql.triggers")

test_dependency_co_installed if check_cases("dependency.co-installed")

test_dependency_floors if check_cases("dependency.floors")

test_dependency_lock_files if check_cases("dependency.lock-files")

test_dependency_pip_pins if check_cases("dependency.pip-pins")

test_dependency_references if check_cases("dependency.references")

test_dependency_update_owners if check_cases("dependency.update-owners")

test_distribution_workflow if check_cases("distribution.workflow")

test_docs_badges if check_cases("docs.badges")

test_docs_configuration if check_cases("docs.configuration")

test_docs_navigation if check_cases("docs.navigation")

test_docs_public_boundary if check_cases("docs.public-boundary")

test_gate_same_command if check_cases("gate.same-command")

test_make_safety if check_cases("make.safety")

test_ownership_boundary if check_cases("ownership.boundary")

test_ownership_navigation if check_cases("ownership.navigation")

test_ownership_pack if check_cases("ownership.pack")

test_release_authorization if check_cases("release.authorization")

test_release_no_force if check_cases("release.no-force")

test_release_order if check_cases("release.order")

test_release_permissions if check_cases("release.permissions")

test_release_recovery if check_cases("release.recovery")

test_release_rerun if check_cases("release.rerun")

test_release_shape if check_cases("release.shape")

test_release_signed_target if check_cases("release.signed-target")

test_release_signer if check_cases("release.signer")

test_release_subjects if check_cases("release.subjects")

test_review_values if check_cases("review.values")

test_scorecard_publication if check_cases("scorecard.publication")

test_scorecard_triggers if check_cases("scorecard.triggers")

test_title_workflow if check_cases("title.workflow")

test_workflow_action_pins if check_cases("workflow.action-pins")

test_workflow_job_scopes if check_cases("workflow.job-scopes")

test_workflow_no_merge if check_cases("workflow.no-merge")

test_workflow_permissions if check_cases("workflow.permissions")
