package main

import rego.v1

valid_ownership if {
	t := flat(input.text["docs/public/ownership-boundary.md"])
	every phrase in {
		"RAES", "OpenRAE/env-packs", "LilRAE", "declared pack owner",
		"portable scenario, workflow, capture, evidence, and inventory",
		"layout contract, templates, schemas, validation, release tooling, and adoption guidance",
		"in-game content, experiment and trial design, and the data and evidence the experiment requires",
		"admitted-plan realization, lab lifecycle, trusted source acquisition, backend observation, and LilRAE-local evidence persistence",
		"APTL is being renamed to LilRAE", "selected first-party scenario packs", "remain RAES inputs",
		"A pack does not select runtime implementation", "shell commands", "backend-native identities",
		"realization-only bootstrap configuration", "host paths", "persistence paths", "collector implementations", "credentials",
		"https://github.com/OpenRAE/lilrae/issues/589", "issue-589-scenario-pack-capture-ownership-preflight.md",
	} { contains(t,phrase) }
}
violations contains "ownership.boundary" if not valid_ownership

valid_pack_description if {
	t := flat(input.text["packs/techvault/README.md"])
	contains(t,"TechVault is the first-party RAES environment pack")
	contains(t,"backend and deployment product names are not part of its identity")
}
violations contains "ownership.pack" if not valid_pack_description
violations contains "ownership.navigation" if not contains(input.text["docs/public/environment-packs.md"],"ownership-boundary.md")

valid_doc_badges if {
	pages := {trim_suffix(trim_prefix(p,"docs/public/"),".md") | some p in object.keys(input.text); startswith(p,"docs/public/"); endswith(p,".md")}
	links := [m[1] | some m in regex.find_all_string_submatch_n(`\]\(([^)]+)\)`,input.text["README.md"],-1); contains(m[1],"readthedocs")]
	count(links)>0
	every link in links { doc_link(link,pages) }
}
doc_link(link,pages) if startswith(link,"https://app.readthedocs.org/projects/raes-environment-packs/badge/")
doc_link(link,pages) if {
	prefix := "https://raes-environment-packs.readthedocs.io/en/latest/"
	startswith(link,prefix)
	p := trim_suffix(trim_prefix(link,prefix),".html")
	p in pages
}
doc_link(link,pages) if link == "https://raes-environment-packs.readthedocs.io/en/latest/"
violations contains "docs.badges" if not valid_doc_badges
