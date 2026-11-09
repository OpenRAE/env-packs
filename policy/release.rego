package main

import rego.v1

release := doc(".github/workflows/release-please.yml")
publish := release.jobs.publish

valid_release_shape if {
	object.keys(release.on) == {"push", "workflow_dispatch"}
	release.on.push.branches == ["main"]
	release.on.workflow_dispatch.inputs.release_pr.required == true
	release.on.workflow_dispatch.inputs.release_pr.type == "string"
	release.concurrency == {"group": "release", "cancel-in-progress": false}
	c := doc("release-please-config.json")
	true in [object.get(c,"skip-github-release",false),object.get(c.packages["."],"skip-github-release",false)]
	checkouts := [s | some _,j in release.jobs; some s in j.steps; startswith(object.get(s,"uses",""),"actions/checkout@")]
	count(checkouts)>0
	every s in checkouts { s.with["persist-credentials"] == false }
}
violations contains "release.shape" if not valid_release_shape

valid_release_permissions if {
	release.jobs["release-please"].permissions == {"contents":"write","pull-requests":"write"}
	release.jobs["resume-release-please"].permissions == {"contents":"write","pull-requests":"write"}
	release.jobs["detect-release"].permissions == {"contents":"read","pull-requests":"read"}
	publish.permissions == {"contents":"write","pull-requests":"write","id-token":"write","attestations":"write"}
}
violations contains "release.permissions" if not valid_release_permissions

valid_release_authorization if {
	m := release.jobs["release-please"]
	"detect-release" in needs(m)
	contains(m["if"],"github.event_name == 'push'")
	contains(m["if"],"needs.detect-release.outputs.release != 'true'")
	not contains(m["if"],"always()")
	not contains(m["if"],"cancelled()")
	"detect-release" in needs(publish)
	contains(publish["if"],"needs.detect-release.outputs.release == 'true'")
	r := release.jobs["resume-release-please"]
	"publish" in needs(r)
	contains(r["if"],"github.event_name == 'workflow_dispatch'")
	contains(r["if"],"needs.publish.result == 'success'")
	count(step(r,"googleapis/release-please-action@"))>0
	detect := runs(release.jobs["detect-release"])
	every marker in {"release_tag_gate.py","/pulls","--merged-pr-labels-file","merge_commit_sha == env.PUSH_AFTER","RECOVERY_PR","repos/${GITHUB_REPOSITORY}/pulls/${RECOVERY_PR}","base_ref=\"$(gh api","\"main\"","merged_at=\"$(gh api","pr-labels.txt"} { contains(detect,marker) }
}
violations contains "release.authorization" if not valid_release_authorization

valid_release_signer if {
	release.env.CERT_IDENTITY == "https://github.com/OpenRAE/env-packs/.github/workflows/release-please.yml@refs/heads/main"
	release.env.CERT_OIDC_ISSUER == "https://token.actions.githubusercontent.com"
	release.env.GITSIGN_VERSION_PIN == "0.15.1"
	release.env.GITSIGN_VERSION_FLOOR == "0.15.0"
	release.env.GITSIGN_SHA256 == "8712be2e5fe89c9728c50beed20f1d37340b9f2dc3306cfb8830ef975549e170"
	install := step(publish,"gitsign_${GITSIGN_VERSION_PIN}_linux_amd64").run
	every marker in {"curl --fail","sha256sum --check --strict","GITSIGN_SHA256","GITSIGN_BIN","GITHUB_ENV"} { contains(install,marker) }
	not contains(runs(publish),"setup-gitsign@")
	contains(runs(publish),"\"${GITSIGN_BIN}\" version")
	verify := step(publish,"\"${GITSIGN_BIN}\" verify-tag").run
	every marker in {"--certificate-identity","--certificate-oidc-issuer","CERT_IDENTITY","CERT_OIDC_ISSUER","for attempt in 1 2 3 4 5","sleep","return 1"} { contains(verify,marker) }
	not contains(verify,"--certificate-identity-regexp")
	not contains(verify,"--certificate-oidc-issuer-regexp")
}
violations contains "release.signer" if not valid_release_signer

valid_release_order if {
	ordered(publish,["gitsign_${GITSIGN_VERSION_PIN}_linux_amd64","GITSIGN_VERSION_FLOOR","git tag -s","-m build","actions/attest-build-provenance@","pypa/gh-action-pypi-publish@"])
	ordered(publish,["\"${GITSIGN_BIN}\" verify-tag","-m build"])
	ordered(publish,["git tag -s","gh release create"])
	ordered(publish,["actions/attest-build-provenance@","gh release upload"])
}
violations contains "release.order" if not valid_release_order

valid_signed_target if {
	publish.env.TARGET_SHA == "${{ needs.detect-release.outputs.target }}"
	step(publish,"actions/checkout@").with.ref == "${{ needs.detect-release.outputs.target }}"
	r := step(publish,"git tag -s").run
	contains(r,"git tag -s \"${TAG}\" \"${TARGET_SHA}\"")
	signed := indexof(r,"git tag -s")
	remaining := substring(r,signed,-1)
	ordered_text(remaining,["git tag -s","verify_tag","git push origin"])
}
violations contains "release.signed-target" if not valid_signed_target

valid_release_subjects if {
	subject := step(publish,"actions/attest-build-provenance@").with["subject-path"]
	contains(subject,"*.whl")
	contains(subject,"*.tar.gz")
}
violations contains "release.subjects" if not valid_release_subjects

valid_release_recovery if {
	tag := step(publish,"git tag -s")
	tag.id == "signed-tag"
	contains(tag.run,"verified=true")
	export := step(publish,"git cat-file tag")
	condition := "${{ failure() && steps.signed-tag.outcome == 'failure' && steps.signed-tag.outputs.verified == 'true' }}"
	export["if"] == condition
	every marker in {"git cat-file -e \"${TAG}^{tag}\"","git cat-file tag \"${TAG}\"","git rev-parse \"${TAG}^{tag}\"","git rev-list -n 1 \"${TAG}\"","${RUNNER_TEMP}/signed-release-tag"} { contains(export.run,marker) }
	upload := step(publish,"actions/upload-artifact@")
	upload.uses == "actions/upload-artifact@cf430e030ddbb5b0abf93d22962f4752f3646cd9"
	upload["if"] == condition
	upload.with.name == "verified-signed-tag-${{ needs.detect-release.outputs.tag }}"
	upload.with.path == "${{ runner.temp }}/signed-release-tag"
	upload.with["retention-days"] == 1
	upload.with["if-no-files-found"] == "error"
	ordered(publish,["git tag -s","git cat-file tag","actions/upload-artifact@"])
	materialize := step(publish,"git cat-file -e \"${TARGET_SHA}:requirements/build.txt\"").run
	every lock in {"build","runtime","sbom"} {
		contains(materialize,sprintf("git cat-file -e \"${TARGET_SHA}:requirements/%s.txt\"",[lock]))
		contains(materialize,sprintf("git show \"${TARGET_SHA}:requirements/%s.txt\" > requirements/%s.txt",[lock,lock]))
	}
	contains(materialize,"exit 1")
	not contains(materialize,"GITHUB_SHA")
	ordered(publish,["${TARGET_SHA}:requirements/build.txt","-m build"])
}
violations contains "release.recovery" if not valid_release_recovery

valid_release_rerun if {
	r := step(publish,"gh release create").run
	every marker in {"--verify-tag","--notes-file","gh release view"} { contains(r,marker) }
	ordered_text(r,["gh release view","gh release create"])
	step(publish,"pypa/gh-action-pypi-publish@").with["skip-existing"] == true
	text := runs(publish)
	contains(text,"--add-label \"autorelease: tagged\"")
	contains(text,"--remove-label \"autorelease: pending\"")
	ordered(publish,["pypa/gh-action-pypi-publish@","--add-label \"autorelease: tagged\""])
	ordered(publish,["gh release upload","--add-label \"autorelease: tagged\""])
	policy := [s | some s in publish.steps; object.get(s,"id","") == "pypi-policy"][0]
	every marker in {"tomllib","distribution}\" != \"raes-env-packs\"","exit 1"} { contains(policy.run,marker) }
	not contains(policy.run,"v2.0.2")
	ordered(publish,["distribution}","gh release create"])
	ordered(publish,["distribution}","pypa/gh-action-pypi-publish@"])
}
violations contains "release.rerun" if not valid_release_rerun

valid_release_no_force if {
	every marker in {"git tag -d","git tag --delete","git tag -f","push --force","push -f","--force-with-lease"} { not contains(runs(publish),marker) }
}
violations contains "release.no-force" if not valid_release_no_force
