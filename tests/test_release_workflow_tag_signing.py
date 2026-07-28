"""Static workflow-contract guard for keyless Sigstore release-tag signing.

ADR 0017 makes Release Please run in PR-only mode and moves tag creation into the
canonical ``release-please.yml``, which signs an annotated tag with gitsign,
verifies it against the exact workflow identity, and only then builds, attests,
and publishes. These are static checks: end-to-end acceptance (a real
``gitsign verify-tag`` pass) needs an actual release run, but the workflow shape
that produces it is guarded here so a dropped permission, an unpinned signer, a
reordered publish, or a tag force-update fails CI. Scope is deliberately narrow —
the tag-signing contract only — and it reuses the repo's existing unittest +
PyYAML stack (mirrors ``test_release_workflow_attestation.py``).
"""

from __future__ import annotations

import json
import pathlib
import re
import unittest

import yaml

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_WORKFLOW = _ROOT / ".github" / "workflows" / "release-please.yml"
_CONFIG = _ROOT / "release-please-config.json"

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_SETUP_GITSIGN = "chainguard-dev/actions/setup-gitsign@"
_ATTEST_ACTION = "actions/attest-build-provenance@"
_PYPI_ACTION = "pypa/gh-action-pypi-publish@"
_CHECKOUT_ACTION = "actions/checkout@"

# Must track the repository's CURRENT path. The OIDC workflow ref is issued for
# wherever the repo lives now, and GitHub's transferred-repo redirect does not
# apply to certificate-identity matching -- a stale value fails verification
# closed and blocks releases (#142). Tags signed before the move to
# RAESystem/env-packs still verify against the previous identity; SECURITY.md
# documents both ranges.
_CERT_IDENTITY = (
    "https://github.com/RAESystem/env-packs/"
    ".github/workflows/release-please.yml@refs/heads/main"
)
_OIDC_ISSUER = "https://token.actions.githubusercontent.com"
_GITSIGN_FLOOR = "0.15.0"


def _load_workflow() -> dict:
    return yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))


def _job(data: dict, name: str) -> dict:
    return data["jobs"][name]


def _step_text(job: dict) -> str:
    parts = []
    for step in job.get("steps", []):
        parts.append(str(step.get("run", "")))
        parts.append(str(step.get("uses", "")))
    return "\n".join(parts)


def _index(job: dict, needle: str) -> int:
    for idx, step in enumerate(job.get("steps", [])):
        if needle in str(step.get("run", "")) or needle in str(step.get("uses", "")):
            return idx
    return -1


def _step_run(job: dict, needle: str) -> str:
    """Return the run text of the first step whose run contains ``needle``."""
    for step in job.get("steps", []):
        run = str(step.get("run", ""))
        if needle in run:
            return run
    return ""


class ReleasePleaseConfigTests(unittest.TestCase):
    def test_skip_github_release_enabled(self) -> None:
        config = json.loads(_CONFIG.read_text(encoding="utf-8"))
        # PR-only mode: Release Please maintains the release PR but never tags —
        # the workflow signs and creates the tag instead (ADR 0017).
        package = config["packages"]["."]
        root_flag = config.get("skip-github-release")
        pkg_flag = package.get("skip-github-release")
        self.assertTrue(
            root_flag is True or pkg_flag is True,
            "release-please-config.json must set skip-github-release: true",
        )


class WorkflowShapeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = _load_workflow()

    def test_triggers_on_main_push_and_explicit_recovery(self) -> None:
        # YAML 1.1 parses the bare key ``on`` as boolean True.
        on = self.data.get("on", self.data.get(True))
        self.assertEqual(set(on), {"push", "workflow_dispatch"})
        self.assertEqual(on["push"]["branches"], ["main"])
        recovery = on["workflow_dispatch"]["inputs"]["release_pr"]
        self.assertIs(recovery["required"], True)
        self.assertEqual(recovery["type"], "string")

    def test_releases_are_serialized(self) -> None:
        concurrency = self.data["concurrency"]
        self.assertEqual(concurrency["group"], "release")
        self.assertFalse(concurrency["cancel-in-progress"])

    def test_all_checkouts_do_not_persist_credentials(self) -> None:
        checkouts = 0
        for job in self.data["jobs"].values():
            for step in job.get("steps", []):
                if str(step.get("uses", "")).startswith(_CHECKOUT_ACTION):
                    checkouts += 1
                    self.assertIs(
                        step.get("with", {}).get("persist-credentials"),
                        False,
                        "every checkout must set persist-credentials: false",
                    )
        self.assertGreater(checkouts, 0, "expected at least one checkout step")

    def test_canonical_signer_identity(self) -> None:
        env = self.data.get("env", {})
        self.assertEqual(env.get("CERT_IDENTITY"), _CERT_IDENTITY)
        self.assertEqual(env.get("CERT_OIDC_ISSUER"), _OIDC_ISSUER)


class LeastPrivilegeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = _load_workflow()

    def test_release_please_job_has_no_signing_privilege(self) -> None:
        job = _job(self.data, "release-please")
        perms = job.get("permissions", {})
        self.assertEqual(perms.get("contents"), "write")
        self.assertEqual(perms.get("pull-requests"), "write")
        self.assertNotIn("id-token", perms, "PR job must not hold OIDC")
        self.assertNotIn("attestations", perms, "PR job must not hold attestations")
        self.assertIn(
            "github.event_name == 'push'",
            str(job.get("if", "")),
            "release-please must not run during explicit recovery",
        )

    def test_successful_recovery_resumes_release_pr_maintenance(self) -> None:
        job = _job(self.data, "resume-release-please")
        needs = job.get("needs", [])
        needs = [needs] if isinstance(needs, str) else needs
        self.assertIn("publish", needs)
        condition = str(job.get("if", ""))
        self.assertIn("github.event_name == 'workflow_dispatch'", condition)
        self.assertIn("needs.publish.result == 'success'", condition)
        perms = job.get("permissions", {})
        self.assertEqual(perms.get("contents"), "write")
        self.assertEqual(perms.get("pull-requests"), "write")
        self.assertNotIn("id-token", perms)
        self.assertNotIn("attestations", perms)
        self.assertIn("googleapis/release-please-action@", _step_text(job))

    def test_detect_release_job_is_read_only(self) -> None:
        job = _job(self.data, "detect-release")
        perms = job.get("permissions", {})
        self.assertEqual(perms.get("contents"), "read")
        self.assertEqual(perms.get("pull-requests"), "read")
        self.assertNotIn("id-token", perms)
        self.assertNotIn("attestations", perms)
        self.assertIn("release_tag_gate.py", _step_text(job))

    def test_release_authorized_on_release_pr_label(self) -> None:
        # Security binding: the release decision consumes the merged PR's labels
        # (the authenticated release-please signal), not just a version change.
        job = _job(self.data, "detect-release")
        text = _step_text(job)
        self.assertIn("/pulls", text,
                      "detect-release must resolve the merged PR to read its labels")
        self.assertIn("--merged-pr-labels-file", text,
                      "the gate must be authorized by the merged-PR labels")
        # Enforcing predicate: the PR query is scoped to the exact push commit, so
        # labels from an unrelated PR touching the same commit cannot authorize a
        # release. Dropping this filter is the weakening this pins.
        self.assertIn("merge_commit_sha == env.PUSH_AFTER", text,
                      "the PR-label query must be scoped to this push's merge commit")

    def test_recovery_is_bound_to_a_merged_main_release_pr(self) -> None:
        text = _step_text(_job(self.data, "detect-release"))
        self.assertIn("RECOVERY_PR", text)
        self.assertIn('repos/${GITHUB_REPOSITORY}/pulls/${RECOVERY_PR}', text)
        self.assertIn('base_ref="$(gh api', text)
        self.assertIn('"main"', text)
        self.assertIn('merged_at="$(gh api', text)
        self.assertIn("pr-labels.txt", text)
        self.assertIn("--merged-pr-labels-file", text)

    def test_publish_job_permissions(self) -> None:
        job = _job(self.data, "publish")
        perms = job.get("permissions", {})
        self.assertEqual(perms.get("contents"), "write")
        self.assertEqual(perms.get("id-token"), "write")
        self.assertEqual(perms.get("attestations"), "write")
        self.assertEqual(perms.get("pull-requests"), "write")

    def test_publish_gated_on_detect_release(self) -> None:
        job = _job(self.data, "publish")
        needs = job.get("needs", [])
        needs = [needs] if isinstance(needs, str) else needs
        self.assertIn("detect-release", needs)
        self.assertIn("detect-release", str(job.get("if", "")))
        self.assertIn("release", str(job.get("if", "")))


class TagSigningContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.data = _load_workflow()
        self.publish = _job(self.data, "publish")
        self.text = _step_text(self.publish)

    def test_setup_gitsign_is_sha_pinned(self) -> None:
        for step in self.publish["steps"]:
            uses = str(step.get("uses", ""))
            if uses.startswith(_SETUP_GITSIGN):
                ref = uses.split("@", 1)[1].split()[0]
                self.assertRegex(ref, _SHA_RE, f"setup-gitsign must be SHA-pinned: {uses!r}")
                return
        self.fail("publish job must install gitsign via setup-gitsign")

    def test_gitsign_version_floor_guard_present(self) -> None:
        # Defence in depth: fail closed if gitsign is below the CVE-2026-44310
        # floor. The floor is a single canonical env value the guard references.
        self.assertEqual(self.data.get("env", {}).get("GITSIGN_VERSION_FLOOR"),
                         _GITSIGN_FLOOR)
        self.assertIn("GITSIGN_VERSION_FLOOR", self.text,
                      "the version-floor guard must reference the canonical floor")
        self.assertIn("gitsign version", self.text,
                      "the guard must read the installed gitsign version")
        # Enforcing predicate: the floor check must run BEFORE the tag is signed,
        # or a below-floor (CVE-vulnerable) gitsign could sign the tag first.
        floor = _index(self.publish, "GITSIGN_VERSION_FLOOR")
        sign = _index(self.publish, "git tag -s")
        self.assertGreaterEqual(floor, 0)
        self.assertGreaterEqual(sign, 0)
        self.assertLess(floor, sign,
                        "the version-floor guard must precede tag signing")

    def test_signed_annotated_tag_at_exact_commit(self) -> None:
        self.assertIn("git tag -s", self.text, "tag must be signed (git tag -s)")
        # Enforcing predicate: the signed tag targets the gate-validated release
        # commit, not an implicit HEAD or the workflow-dispatch branch head.
        self.assertIn('git tag -s "${TAG}" "${TARGET_SHA}"', self.text)
        self.assertEqual(
            self.publish["env"]["TARGET_SHA"],
            "${{ needs.detect-release.outputs.target }}",
        )
        checkout = next(
            step for step in self.publish["steps"]
            if str(step.get("uses", "")).startswith(_CHECKOUT_ACTION)
        )
        self.assertEqual(checkout["with"]["ref"], "${{ needs.detect-release.outputs.target }}")

    def test_verify_tag_is_identity_bound(self) -> None:
        self.assertIn("gitsign verify-tag", self.text,
                      "workflow must verify the tag with gitsign verify-tag")
        self.assertIn("--certificate-identity", self.text)
        self.assertIn("--certificate-oidc-issuer", self.text)
        self.assertIn("CERT_IDENTITY", self.text)
        self.assertIn("CERT_OIDC_ISSUER", self.text)
        # Enforcing predicate: identity must be exact, never a wildcard/regexp
        # (ADR 0017 anti-pattern "no wildcard certificate identities").
        self.assertNotIn("--certificate-identity-regexp", self.text)
        self.assertNotIn("--certificate-oidc-issuer-regexp", self.text)

    def test_transparency_log_verification_has_bounded_retry(self) -> None:
        run = _step_run(self.publish, "gitsign verify-tag")
        self.assertIn("for attempt in 1 2 3 4 5", run)
        self.assertIn("sleep", run)
        self.assertIn("return 1", run)

    def test_release_created_from_preexisting_tag_with_file_notes(self) -> None:
        self.assertIn("gh release create", self.text)
        self.assertIn("--verify-tag", self.text,
                      "GitHub Release must consume the pre-existing signed tag")
        self.assertIn("--notes-file", self.text,
                      "release notes must be passed by file, not interpolated")

    def test_release_creation_is_idempotent(self) -> None:
        # A rerun after a later publication failure must recover, not abort
        # because the Release already exists: the create is guarded by a check.
        for step in self.publish["steps"]:
            run = str(step.get("run", ""))
            if "gh release create" in run:
                self.assertIn("gh release view", run,
                              "release creation must be guarded by an existence check")
                self.assertLess(run.index("gh release view"),
                                run.index("gh release create"),
                                "existence check must precede the create")
                return
        self.fail("no step creates the GitHub Release")

    def test_release_pr_relabeled_to_tagged(self) -> None:
        # skip-github-release leaves the merged PR "autorelease: pending"; the
        # workflow must flip it to "autorelease: tagged" or release-please aborts
        # its next run (googleapis/release-please#1561).
        self.assertIn("gh pr edit", self.text)
        # Enforcing predicate: both halves of the transition — add the tagged
        # label AND clear the pending one — or the state machine stays stuck.
        self.assertIn('--add-label "autorelease: tagged"', self.text)
        self.assertIn('--remove-label "autorelease: pending"', self.text)
        mark = _index(self.publish, '--add-label "autorelease: tagged"')
        pypi = _index(self.publish, _PYPI_ACTION)
        upload = _index(self.publish, "gh release upload")
        self.assertGreater(mark, pypi)
        self.assertGreater(mark, upload)

    def test_pypi_publication_is_rerun_safe(self) -> None:
        for step in self.publish["steps"]:
            if str(step.get("uses", "")).startswith(_PYPI_ACTION):
                self.assertIs(step.get("with", {}).get("skip-existing"), True)
                return
        self.fail("no PyPI publication step")

    def test_sign_then_verify_then_push_within_tag_step(self) -> None:
        # Enforcing predicate for the fail-closed ordering: within the single
        # tag-creation step, the tag is verified BEFORE it is pushed, so an
        # unverified tag is never published. A later edit that hoists the push
        # above verify_tag would otherwise pass every other ordering check.
        run = _step_run(self.publish, "git tag -s")
        sign = run.index("git tag -s")
        push = run.index("git push origin")
        verify_after_sign = run.index("verify_tag", sign)
        self.assertLess(sign, verify_after_sign, "must verify after signing")
        self.assertLess(verify_after_sign, push, "must verify before pushing the tag")

    def test_never_deletes_or_force_updates_tags(self) -> None:
        for forbidden in ("git tag -d", "git tag --delete", "git tag -f",
                          "push --force", "push -f", "--force-with-lease"):
            self.assertNotIn(forbidden, self.text,
                             f"workflow must never {forbidden!r} a release tag")

    def test_sign_and_verify_precede_publication(self) -> None:
        sign = _index(self.publish, "git tag -s")
        verify = _index(self.publish, "gitsign verify-tag")
        build = _index(self.publish, "-m build")
        attest = _index(self.publish, _ATTEST_ACTION)
        release_create = _index(self.publish, "gh release create")
        pypi = _index(self.publish, _PYPI_ACTION)

        for name, idx in (("sign", sign), ("verify", verify), ("build", build),
                          ("attest", attest), ("release create", release_create),
                          ("pypi", pypi)):
            self.assertGreaterEqual(idx, 0, f"could not locate the {name} step")

        # Sign+verify may share a single fail-closed step (verify before the tag
        # is pushed); both must precede every publication destination.
        for later, label in ((build, "build"), (attest, "attest"),
                             (release_create, "release create"), (pypi, "pypi")):
            self.assertLess(verify, later,
                            f"signature verification must precede {label}")
            self.assertLess(sign, later,
                            f"tag signing must precede {label}")

    def test_attestation_still_precedes_publication(self) -> None:
        # ADR 0015 invariant must survive the rewrite.
        attest = _index(self.publish, _ATTEST_ACTION)
        pypi = _index(self.publish, _PYPI_ACTION)
        self.assertGreaterEqual(attest, 0)
        self.assertGreaterEqual(pypi, 0)
        self.assertLess(attest, pypi, "attestation must precede PyPI publication")


if __name__ == "__main__":
    unittest.main()
