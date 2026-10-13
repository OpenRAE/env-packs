# TechVault SOC credential preflight

Issue #392 covers authored SOC credential state and consumer configuration.
The user clarified the scope in issue comment 6131576646: all SOC credentials
are in-world, and the console logins for Wazuh, TheHive, Cortex, Shuffle and MISP
must expose native `secret_fixture` account credential bindings with values.

## Decision and scope

Treat indexer `admin` and `kibanaserver` credentials as synthetic, public
scenario fixtures. The pack already fixes their bcrypt hashes and ships other
in-world plaintext credentials, including the dashboard's manager API login.
Make the matching plaintext used by the consumers authored pack content too,
using native RAES `accounts.*.credential_bindings` with `secret_fixture`
material and matching existing RAES `content` file/configuration state. MISP
administrator and sync API material belongs to declared in-world accounts too.
The value-free runtime principal/setting surfaces use `redacted` posture,
which their pinned RAES vocabulary supports; they refer to the fixture accounts.
Do not extend that closed vocabulary to invent a principal-level fixture field. Documentation
alone, an unused credential list, or backend knowledge of a default password
does not close the consumer contract.

Keep three identities separate: indexer `admin`, dashboard service account
`kibanaserver`, and manager API account `wazuh-wui`. Preserve existing account
roles and reserved status. State which indexer account manager Filebeat uses
and which the dashboard uses; a dashboard service login is not its user's
interactive login. These are in-world identities. Do not classify them as
`operator_secret`.

Do not guess a password from a hash, assume an upstream demo default, or seek
real operational credentials. Verify each chosen synthetic value against its
hash with a standard bcrypt implementation. If the existing hash cannot be
matched from approved fixture information, author a deliberate replacement
fixture and matching hash together. An incidental re-salt on every build is
not a content change worth introducing.

Use native configuration content, as `wazuh-dashboard-app-config` already
does. The dashboard's existing `opensearch_dashboards.yml` is the incumbent
consumer artifact. Filebeat currently has a declared manager component but
no authored indexer login configuration: its supported configuration must
include the required Wazuh inputs/modules as well as the authenticated output.
A fragment is sufficient only if an existing declared mechanism consumes it;
do not replace a working full configuration with an output-only file. Preserve
TLS verification, declared endpoints, and existing certificate projections.

## Cross-cutting contracts and incumbents

| Layer | Guardrail and existing authority |
| --- | --- |
| SDL shape and semantics | `raes==6.0.1`, pinned in `pyproject.toml`, and `validation.validate_pack` use RAES parsing and semantic validation. Reuse `content`, node/service references, and existing runtime inventory; unknown convenience fields are not a credential schema. Parse nested native YAML as well: an outer SDL parse cannot prove Filebeat or dashboard configuration correctness. |
| Realization policy and config shapes | `packs/techvault/validation/validate_techvault.py::validate_realization_method_contract` keeps realization open and excludes runtime environment, launch commands, backend mounts and host publication. Product-native authored files are scenario state; image environment bindings and startup recipes remain backend-owned. Do not encode `INDEXER_PASSWORD`, an image's environment mapping, or a private interpolation language as portable semantics. |
| Authentication and classification | Correct the old `misp-administrator` operator-supplied interpretation; use the native account fixture-material contract. Where a typed classification is added, use RAES's existing fixture vocabulary. Public synthetic credentials are consistent with `no_real_credentials` and the provenance ledger; that assertion must remain true. No secrets belong in artifact identity/provenance metadata. |
| OS and transport exposure | Authored fixtures may be published as pack content but do not justify broad runtime access. Existing filesystem inventory expresses owner/mode/sensitivity where needed; selected adapters must provide readable, restricted credential files. No new password-bearing argv, shell tracing, URL userinfo, health command or environment dump. Preserve certificate verification and private-key separation; do not solve authentication by disabling security. |
| Diagnostics and observations | Generic static validation uses bounded `Diagnostic`/`ValidationResult`; TechVault-specific checks return stable code/path strings. Reuse those conventions and existing unittest negative variants. Mismatched credentials/configurations must report identity/location, not plaintext, full config bodies or raw bcrypt/parser exceptions. No new logger or exception hierarchy. Backend authenticated observations remain downstream evidence, not static pack validation. |
| Artifact integrity and publication | SDL bytes, external concept bindings, and associated-artifact set digests are coupled. Reuse `tools/refresh_pack_sdl_binding.py`, `digest.py`, `_pack_fs` and content-manifest validation. Even comment edits change byte bindings. That refresh script handles SDL/binding entries, not arbitrary edited asset digests: update any changed bound README/config assets through the existing manifest/digest APIs as well. Preserve wheel/sdist and release checks. |
| Persistence | Existing retained Wazuh resources and product security-index state can retain old credentials. Initialization content is not a migration of an existing security index. Backend tests must distinguish clean initialization from restart/reuse; stale state must be diagnosed or handled through an explicit backend migration policy, never by deleting retained data silently. |

There is no new controller, service, repository, secret store, generalized
validator or workflow to introduce. Pack-specific consistency belongs beside
the current TechVault contract checks and `tests/test_techvault_pack.py`, not
in a local restatement of RAES schemas. Check actual hash/password agreement
and negative variants for omitted or contradictory consumer credentials;
avoid tests that only assert that the new comment exists. Any bcrypt test
dependency must be explicit and reproducible, not an undeclared local tool.

## Whole-repository reach and extensibility

`tests/test_techvault_study_pack.py` requires the study copy to preserve the
base scenario. Its SDL contains the same offending comment and hashes;
semantic changes must preserve that parity and refresh each pack's own
bindings without merging their identities. The shipped
`assets/content/misp-sync-readme.md` also directs Wazuh users to a backend
environment variable. Correct that conflicting credential guidance in both
copies if it remains part of the distributed content; a broader rewrite of
historical backend documentation is outside this issue.

Inspect the reusable Wazuh kit as an incumbent, but do not rewrite published
`kits/infrastructure.wazuh-security-monitoring-stack/*` releases to impose
TechVault fixture policy. The seam for another component or credential carrier
is the existing declared application/service relationship plus authored native
content, interpreted by the selected backend adapter. Another image's variable
names must not require edits to scenario identity. Changing fixture values is
an intentional authored change across hash and consumers, not an operational
environment override. Use the governed account and credential-binding
identities for fixture resolution; repeated names or prose cannot create secret-equality semantics.

Required repository gates remain those in `AGENTS.md`: the full unittest
suite, repo and packs-root validation/release checks, and byte compilation.
Also retain TechVault's pack-local validation and distribution coverage.
Static checks establish authored consistency, not live authentication or
permissions. Downstream runtime proof should cover Filebeat delivery,
dashboard indexer access, incorrect-password rejection and retained-state
reuse without leaking credentials; do not claim this preflight supplies it.

## Non-goals and anti-patterns

No backend implementation, new readiness model, account privilege redesign,
demo-user purge, automatic credential rotation, generalized secret binding,
new schema, dependency-pin advance, or release/version edit belongs here.
The other bundled demo accounts are visible adjacent state, not authorization
to expand this issue into a complete account-hardening change. Do not confuse
the indexer's certificate administrator DN with its password-based `admin`.
Do not introduce downstream deployment/catalog vocabulary into canonical
guidance or bypass validators to admit an environment workaround.

No ADR is needed: ADR 0009, ADR 0021 and ADR 0036 already establish RAES
semantic authority, environment-pack identity and first-party content ownership.
