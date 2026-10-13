# TechVault MISP API-key fixture preflight

Issue #460 requires a realizable `secret_fixture` key for
`accounts.misp-suricata-sync-api-key` in both TechVault packs, rejection of
invalid MISP key material during pack authoring validation, and current byte
bindings. The provided issue establishes MISP's acceptance rule: exactly 40
ASCII alphanumeric characters. The checked-in fixture has 65 characters.
This is product-specific authored-content consistency within RAES-subordinate
pack tooling; RAES credential semantics and schemas remain upstream authority.
ADR 0009, ADR 0021 and ADR 0036 already establish the boundary; no new ADR is
needed. This note defines guardrails, not an implementation plan.

## Ownership and canonical incumbents

Keep the account, primary credential binding, `auth_method: key`, credential
identity and `secret_fixture` classification. Preserve the MISP authorization's
value-free `redacted` principal, reader role and grants, and the sync forwarder's
value-free authentication setting. These are distinct carriers of material,
authorization posture and consumer intent; copying bytes into each would create
competing sources of truth. Both packs must declare the same fixture while
retaining separate pack and SDL identities.

Extend `validate_misp_contract` in each pack's existing
`validation/validate_techvault.py`, using `_as_mapping`, `_misp_error` and its
`list[str]` diagnostic contract. Reuse upstream parsing for credential shape,
classification and joins. Validate the intended primary binding, rather than
accepting any binding that happens to contain a valid-looking string. Do not
coerce, trim or truncate material: reject non-string values and require a full
match of `[A-Za-z0-9]{40}`. Unicode `isalnum`, hexadecimal-only restrictions,
and `$`-anchored matches that accept a final newline do not express the rule.
The format check must accept another valid fixture; pinning one literal is not
validation. Do not create a global API-key rule, registry or local SDL schema.

## Cross-cutting gates

| Layer | Required treatment |
| --- | --- |
| Filesystem and bounded parsing | Keep `validation.py`'s descriptor-anchored `_pack_fs` reads, limits, strict metadata loading and pinned RAES parser. Do not introduce network access, ambient configuration or new reads to validate a literal. |
| SDL and credential shapes | `parse_sdl` / `parse_sdl_file` own generic account/binding validity; the pack contract owns this MISP-specific material rule. A product key length must not constrain passwords or other products' keys. |
| Authorization and trust | Preserve MISP authentication, sync reader grants, certificate verification and generated CA selection. A syntactically valid key does not prove provisioning, role assignment or live authentication. |
| Secret handling and errors | Keep fixture bytes only in their declared material carrier. Diagnostics identify the account/binding and failed rule, never the supplied value, serialized account or caught value-bearing exception. Use `_misp_error`; no logger or exception hierarchy is needed. Generic validation already exposes `Diagnostic` / `ValidationResult`, and digest failures use `PackDigestError`. |
| Author execution | `content_ci.check_static_contract`, executable discovery/snapshots, `check_validators`, and `_run_pack_process` already enforce static eligibility, literal argv, deadlines, output bounds and abnormal-exit reporting. Reuse them; do not add another execution workflow. |
| Consumer ingestion | `validate_pack` is inert and never runs pack code. This pack-local rule is an author/release gate, not a promise that the generic consumer API rejects product-invalid keys. Keep downstream admission policy downstream; do not execute untrusted validators to satisfy it. |
| Runtime config and OS exposure | The bundled sync `Config._validate_api_key` only rejects empty/placeholder material; `Config.from_env` consumes `MISP_API_KEY`, and `MISPClient` uses the bare key as its Authorization header. The fixture must pass these existing shapes without introducing a second literal in assets. Backend adapters own delivery; use their established secret handling, never token-bearing argv, healthchecks, evidence or logs. Environment delivery is not a new portable SDL binding. |
| Retained state | MISP database/configuration state can retain an earlier provisioned key. Correcting SDL does not migrate an existing instance. Downstream realization must reconcile the declared account under its existing persistence policy, without silent substitution, rotation or deletion of retained data. |
| Integrity and distribution | Reuse `tools/refresh_pack_sdl_binding.py` for each SDL's external-concept subject digests, SDL/binding checksums and sizes, and set digest. It does **not** refresh edited validator-script entries. Use `digest.derive_pack_content_manifest` for all changed bound members and `validate_pack_content_manifest` to verify them; preserve artifact identities and metadata. |

The whole-repository reach includes both pack SDLs, validators and
`associated-artifacts.json` manifests; their concept bindings/scheme snapshots;
`validation.py`, `content_ci.py`, `_pack_fs.py`, `digest.py`, release and
distribution tooling; `pyproject.toml`'s pinned RAES dependency and bundled-pack
mappings; `.ground-control.yaml`; and existing CI and pack-distribution gates.
Scheme content does not change merely because its subjects' SDL digest changes.
Root tests are outside the pack manifest; pack-local tests and validator scripts
are bound artifacts if edited. Never weaken integrity gates to hide stale hashes.

## Verification, extensibility and boundaries

Reuse the mutation tests around `validate_misp_contract` in
`tests/test_techvault_pack.py`, its copied-pack `validate()` tests that refresh
bindings, and the study parity tests in `tests/test_techvault_study_pack.py`.
Cover both validators and their author entrypoints. Mutated SDL must have current
digests so a failing checksum cannot masquerade as format rejection. Include
short/long/empty keys, punctuation, whitespace/final newline, Unicode and wrong
material shape, plus alternate valid mixed-case alphanumeric material. Check
diagnostics do not echo rejected bytes. Preserve parse/compile coverage for
fixture propagation and unrelated credentials. Run the full `AGENTS.md` gates,
including both repo and packs-root validation/release checks and compilation.

The existing account primary-binding identity is the extensibility seam: the
authored value may vary while product validation stays stable. A future MISP
version with different constraints belongs beside the existing product-version
contract, not in a credential-wide abstraction or backend environment override.
Keep the two pack validators consistent using the repository's current mirrored
pattern; this issue does not justify extracting a shared framework.

Static validation cannot establish successful authenticated synchronization.
Runtime proof of exact declared-key provisioning, certificate-verified API access,
wrong-key rejection and retained-state reuse belongs to the backend. Do not claim
that this preflight or author validation supplies that evidence.

Non-goals: implementation of issue #460 here; backend changes; generic credential
semantics, new secret stores or schemas; permission redesign; sync-source archive
rebuilds; unrelated fixture hardening; new dependencies; or publication. Do not
patch historical 6.3.0 releases in place or hand-edit versions/CHANGELOG.md.
Follow existing release-please and Conventional Commit conventions for the
subsequent fix. Repository package release numbers and pack metadata versions
are separate identities. Do not import downstream catalog terminology or
admission workarounds into canonical pack contracts.
