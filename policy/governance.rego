package main

import rego.v1

# The collector supplies facts. Decisions and exceptions stay here.
doc(file) := object.get(input.documents, file, {})
at(file, keys) := object.get(doc(file), keys, null)
flat(value) := concat(" ", regex.split(`\s+`, value))
workflows := {file: value | some file, value in input.documents; startswith(file, ".github/workflows/")}
actions(job) := [s.uses | some s in object.get(job, "steps", []); s.uses]
runs(job) := concat("\n", [s.run | some s in object.get(job, "steps", []); s.run])
step(job, needle) := job.steps[step_index(job, needle)]
step_matches(s, n) if contains(object.get(s, "uses", ""), n)
step_matches(s, n) if contains(object.get(s, "run", ""), n)
step_index(job, n) := min([i | some i, s in job.steps; step_matches(s, n)])
deny contains id if some id in violations

read_only(p) if p == "read-all"
read_only(p) if { is_object(p); every _, v in p { v in {"read", "none"} } }
valid_workflow_permissions if {
	count(workflows) > 0
	every _, w in workflows { read_only(object.get(w, "permissions", null)) }
}
violations contains "workflow.permissions" if not valid_workflow_permissions

valid_job_scopes if {
	every _, w in workflows {
		every _, j in object.get(w, "jobs", {}) { is_object(object.get(j, "permissions", {})) }
	}
}
violations contains "workflow.job-scopes" if not valid_job_scopes

pinned(a) if startswith(a, "./")
pinned(a) if startswith(a, ".github/")
pinned(a) if regex.match(`^[^@]+@[0-9a-f]{40}$`, a)
valid_action_pins if {
	every _, w in workflows {
		every _, j in object.get(w, "jobs", {}) { every a in actions(j) { pinned(a) } }
	}
}
violations contains "workflow.action-pins" if not valid_action_pins

no_merge(value) if not is_string(value)
no_merge(value) if {
	is_string(value)
	every m in {"--auto", "enablepullrequestautomerge", "enable-pull-request-auto-merge", "automerge", "auto-merge", "gh pr merge"} {
		not contains(lower(value), m)
	}
}
valid_no_merge if {
	every _, w in workflows {
		every pair in [p | walk(w,p)] { no_merge(pair[1]); every key in pair[0] { no_merge(key) } }
	}
}
violations contains "workflow.no-merge" if not valid_no_merge

weekly(schedule) if {
	count(schedule) > 0
	every s in schedule {
		fields := split(s.cron, " ")
		count(fields) == 5
		fields[0] != "0"
		fields[2] == "*"
		fields[4] != "*"
	}
}
needs(job) := {n | some n in object.get(job, "needs", [])} if is_array(object.get(job, "needs", []))
needs(job) := {job.needs} if is_string(job.needs)
ordered(job, markers) if {
	indices := [step_index(job, marker) | some marker in markers]
	count(indices) == count(markers)
	every i, a in indices { every j, b in indices { ordered_pair(i,j,a,b) } }
}
ordered_pair(i,j,a,b) if i >= j
ordered_pair(i,j,a,b) if { i < j; a < b }
ordered_text(text, markers) if {
	indices := [indexof(text, marker) | some marker in markers]
	every a in indices { a >= 0 }
	every i, a in indices { every j, b in indices { ordered_pair(i,j,a,b) } }
}

cq := doc(".github/workflows/codeql.yml")
valid_codeql_triggers if {
	object.keys(cq.on) == {"pull_request", "schedule"}
	object.get(cq.on, "pull_request", null) == null
	weekly(cq.on.schedule)
}
valid_codeql_triggers if {
	object.keys(cq.on) == {"pull_request", "schedule"}
	trigger := cq.on.pull_request
	is_object(trigger)
	not "branches" in object.keys(trigger)
	not "branches-ignore" in object.keys(trigger)
	weekly(cq.on.schedule)
}
violations contains "codeql.triggers" if not valid_codeql_triggers

valid_codeql_analysis if {
	j := cq.jobs.analyze
	cq.permissions == "read-all"
	j.permissions == {"contents": "read", "security-events": "write"}
	{"language": "python", "build-mode": "none"} in j.strategy.matrix.include
	{"language": "go", "build-mode": "autobuild"} in j.strategy.matrix.include
	s := step(j, "actions/setup-go@")
	s["if"] == "matrix.language == 'go'"
	s.with["go-version-file"] == "go.mod"
	ordered(j, ["actions/checkout@", "actions/setup-go@", "github/codeql-action/init@", "github/codeql-action/analyze@"])
	step(j, "github/codeql-action/init@").with["config-file"] == "./.github/codeql/codeql-config.yml"
	not "paths-ignore" in object.keys(doc(".github/codeql/codeql-config.yml"))
	cq.concurrency["cancel-in-progress"] == true
}
violations contains "codeql.analysis" if not valid_codeql_analysis

sc := doc(".github/workflows/scorecard.yml")
scorecard_job := j if { some _, j in sc.jobs; some a in actions(j); startswith(a, "ossf/scorecard-action@") }
valid_scorecard_triggers if {
	object.keys(sc.on) == {"push", "schedule"}
	sc.on.push.branches == ["main"]
	weekly(sc.on.schedule)
	sc.concurrency["cancel-in-progress"] == true
}
violations contains "scorecard.triggers" if not valid_scorecard_triggers

score_scope(k, v) if k in {"security-events", "id-token"}
score_scope(k, v) if { not k in {"security-events", "id-token"}; v == "read" }
score_defaults(p) if p == "read-all"
score_defaults(p) if { is_object(p); every _,v in p { v == "read" } }
approved_scorecard(a) if {
	some p in {"actions/checkout@", "ossf/scorecard-action@", "actions/upload-artifact@", "github/codeql-action/upload-sarif@"}
	startswith(a, p)
}
valid_scorecard_publication if {
	score_defaults(sc.permissions)
	j := scorecard_job
	j.permissions["security-events"] == "write"
	j.permissions["id-token"] == "write"
	every k, v in j.permissions { score_scope(k, v) }
	s := step(j, "ossf/scorecard-action@")
	s.with.publish_results == true
	s.with.results_format == "sarif"
	count(s.with.results_file) > 0
	step(j, "actions/checkout@").with["persist-credentials"] == false
	count(step(j,"actions/upload-artifact@")) > 0
	every a in actions(j) { approved_scorecard(a) }
	ordered(j, ["actions/checkout@", "ossf/scorecard-action@", "github/codeql-action/upload-sarif@"])
	readme := input.text["README.md"]
	contains(readme, "https://api.scorecard.dev/projects/github.com/OpenRAE/env-packs/badge")
	contains(readme, "https://scorecard.dev/viewer/?uri=github.com/OpenRAE/env-packs")
}
violations contains "scorecard.publication" if not valid_scorecard_publication

gc := doc(".ground-control.yaml")
valid_review if {
	w := gc.workflow
	w.codex_review.pre_push_cap == 1
	w.review_disposition == {"enabled": false, "mode": "shadow", "max_auto_overrides": 0, "judge": {"enabled": false}}
	w.base_branch == "go-cutover"
	not "test_quality_review" in object.keys(w)
	not "codex_review" in object.keys(gc)
	not "review_disposition" in object.keys(gc)
	charter := flat(input.text[".gc/plan-rules.md"])
	contains(charter, "publishes first-party infrastructure kits")
	contains(charter, "major example packs")
	not contains(charter, "does not host actual environment packs")
}
violations contains "review.values" if not valid_review

dist := doc(".github/workflows/pack-distribution.yml")
valid_distribution if {
	dist.on.workflow_dispatch.inputs.pack.default == "packs/techvault"
	dist.permissions == "read-all"
	j := dist.jobs.rehearse
	j.permissions.contents == "read"
	j.permissions["id-token"] == "write"
	startswith(j.services.registry.image, "registry:")
	ordered(j, ["sigstore/cosign-installer@", "distribution_rehearsal.py"])
	ordered(j, ["oras-project/setup-oras@", "distribution_rehearsal.py"])
	step(j, "distribution_rehearsal.py").env.REHEARSAL_PACK == "${{ inputs.pack }}"
	every s in j.steps { not contains(object.get(s, "run", ""), "${{") }
}
violations contains "distribution.workflow" if not valid_distribution

pt := doc(".github/workflows/pr-title.yml")
valid_title if {
	object.keys(pt.on) == {"pull_request"}
	j := pt.jobs["pr-title-guard"]
	j["if"] == "github.event.pull_request.base.ref != 'main'"
	step(j, "actions/checkout@").with.ref == "${{ github.event.pull_request.base.sha }}"
	contains(runs(j), "python tools/check_pr_title.py")
	not contains(runs(j), "${{ github.event.pull_request.title")
}
violations contains "title.workflow" if not valid_title

rtd := doc(".readthedocs.yaml")
valid_docs_config if {
	rtd.version == 2
	count(rtd.build.os) > 0
	rtd.build.tools.python == "3.14"
	rtd.sphinx.configuration == "docs/public/conf.py"
	rtd.sphinx.fail_on_warning == true
	{"requirements": "requirements/docs.txt"} in rtd.python.install
	every s in rtd.python.install { object.get(s, "path", "") != "." }
	conf := input.text["docs/public/conf.py"]
	every s in {"pyproject.toml", "myst_parser", "\"docs/public/\""} { contains(conf, s) }
	not contains(conf, sprintf("\"%s\"", [doc("pyproject.toml").project.version]))
}
violations contains "docs.configuration" if not valid_docs_config

page_linked(p, trees) if p == "index"
page_linked(p, trees) if contains(trees, p)
valid_docs_navigation if {
	index := input.text["docs/README.md"]
	every p in {"decisions/adrs/README.md", "development/ci.md", "development/scrub-policy.md"} { contains(index, p) }
	contains(input.text["CONTRIBUTING.md"], "docs/README.md")
	contains(input.text["docs/public/index.md"], "{toctree}")
	pages := {trim_suffix(trim_prefix(p,"docs/public/"),".md") | some p in object.keys(input.text); startswith(p,"docs/public/"); endswith(p,".md")}
	count(pages) > 1
	trees := concat("\n",[v | some p,v in input.text; startswith(p,"docs/public/"); contains(v,"{toctree}")])
	every p in pages { page_linked(p, trees) }
}
violations contains "docs.navigation" if not valid_docs_navigation

public_page_safe(p,text) if not startswith(p,"docs/public/")
public_page_safe(p,text) if {
	startswith(p,"docs/public/")
	not startswith(p,"docs/public/decisions/")
	not regex.match(`(^|/)\d{4}-`,p)
	every link in regex.find_all_string_submatch_n(`\]\(([^)]+)\)`,text,-1) {
		not startswith(trim_space(link[1]),"../")
		not startswith(trim_space(link[1]),"/")
	}
}
valid_public_boundary if {
	not "docs/public/decisions" in object.get(input,"directories",[])
	every p, text in input.text { public_page_safe(p,text) }
}
violations contains "docs.public-boundary" if not valid_public_boundary
