# TechVault Wazuh certificate ownership preflight

Issue #287 is a generated-artifact realization failure, not a missing
TechVault declaration. TechVault already declares the Wazuh certificate
outputs, their sensitivity, their read-only consumers, and `reuse_valid`
lifecycle through RAES `generated_artifacts`. The failing
`config/wazuh_indexer_ssl_certs` path is an APTL/LilRAE host workspace and does
not appear in the portable pack.

The selected correction is therefore the existing APTL realization-layer
self-heal in [commit `357280af`](https://github.com/Brad-Edwards/aptl/commit/357280af9cfa45cd52b0fc56351e7f4227c52cfb),
merged through [APTL PR 911](https://github.com/Brad-Edwards/aptl/pull/911):
prepare or reclaim the exact generated-artifact workspace before invoking the
native-Linux generator as the host user. No TechVault SDL, pack schema, or
env-packs runtime helper should be added for that behavior. This note fixes the
ownership and diagnostic boundaries for any follow-up work; it is not an
implementation plan.

## Authority and current contract

Keep these concerns separate:

| Concern | Authority | Guardrail |
| --- | --- | --- |
| Certificate outputs, sensitivity, consumers, mount destinations, and lifecycle | RAES `GeneratedArtifact`, authored by TechVault | Preserve the current declarations and RAES semantic validation. |
| Host output directory, Docker bind-source preparation, generator process identity, and ownership repair | APTL/LilRAE realization | The backend derives and controls the host path. It is never a pack field or provenance-string convention. |
| Declared-output satisfaction, including SEM-218 | RAES realization result | Missing output remains a failure. A causal workspace/generator diagnostic should precede it rather than replacing or suppressing it. |
| Static pack diagnostics | `raes_env_packs.validation.Diagnostic` and `ValidationResult` | These describe bounded foreign-pack input failures only; they are not a runtime exception or logging model. |

The three logical declarations (`wazuh-indexer-certs`,
`wazuh-manager-certs`, and `wazuh-dashboard-certs`) must not be consolidated
merely because one backend currently produces or stores them together. A
physical generator batch and portable artifact identities are different
concepts. Likewise, `reuse_valid` is artifact lifecycle intent, not permission
to retain unusable host ownership.

## Cross-cutting guardrails

The realization design crosses all of these layers:

| Layer | Required outcome |
| --- | --- |
| RAES shape and semantics | Continue to parse through the exactly pinned `raes==3.3.0` authority. Do not copy `GeneratedArtifact`, output-selection, lifecycle, or SEM-218 validation into this repository or the backend. |
| Host-path admission | Operate only on the backend-derived, exact artifact workspace after containment and file-type checks. Refuse symlink, special-file, path-escape, or concurrent-replacement cases; never recursively repair the checkout or an author-supplied arbitrary path. |
| Ownership and persistence | On native Linux, create the bind source before Docker can create it, with the intended host UID/GID. If a trusted prior run left a foreign-owned workspace, atomically preserve it aside and create a fresh host-owned workspace before regeneration, as the cited APTL repair does. Reuse existing certificates only when their workspace is already manageable by the invoking user. Re-establish safe directory and secret-file modes after repair or generation. |
| Generator process | Apply the existing native-Linux `--user` behavior only after the source exists with usable ownership. UID/GID are non-secret process arguments; certificate/private-key bytes, credentials, or environment dumps never belong in argv or diagnostics. Platform-specific ownership behavior stays behind the backend's existing platform seam. |
| Secret handling | Treat private-key outputs as the SDL declares (`secret`) and keep consumer projections read-only. Ownership recovery is metadata handling: it must not read, print, copy, archive, or broaden access to key material. |
| Error and observation envelope | Reuse APTL/LilRAE's existing realization diagnostic, exception, logging, and correlation conventions. Preserve the primary permission/workspace or generator failure, identify the generated-artifact id and phase, and provide bounded operator remediation. Do not emit raw subprocess output, certificate contents, absolute host paths in portable results, or an unclassified `OSError`. |
| Postcondition | Run the normal RAES declared-output check after preparation/generation. SEM-218 remains useful when output is genuinely absent, but must not be the only visible fact when an earlier permission failure is known. |
| Authentication and configuration | This local lifecycle repair creates no authentication or authorization surface and requires no new environment variable, DTO, pack compatibility field, credential source, or config parser. |

The security-critical distinction is between reclaiming a backend-owned
workspace and accepting an arbitrary filesystem target. Broad `chown -R`,
world-writable widening, shell-composed paths, following links, or deleting the
directory to make the error disappear would turn a reliability fix into a host
filesystem vulnerability. If safe repair is impossible, fail before starting
consumers and report the operator action through the existing runtime error
surface.

## Canonical incumbents to reuse

- `packs/techvault/sdl/techvault.sdl.yaml` is the authored source of the Wazuh
  generated-artifact contract. It already carries output names, sensitivity,
  selected outputs, read-only mount destinations, provenance, and lifecycle.
- The pinned RAES parser, reached through `validate_pack()` and author CI in
  `content_ci.py`, is the only SDL shape and semantic validator. A pack-local
  ownership validator would be both unable to observe the runtime host and a
  duplicate authority.
- `tests/test_techvault_pack.py` provides exact pack-contract guards. It may
  protect the existing declarations, but cannot prove host ownership or
  generator behavior.
- `validate_pack_content_manifest()` and
  `tools/refresh_pack_sdl_binding.py` remain the byte-identity authorities if a
  future, independently justified SDL edit occurs. Issue #287 does not require
  such an edit.
- APTL/LilRAE's generated-artifact realization and the self-heal cited by the
  issue are the runtime incumbents. Extend that shared path rather than adding
  a Wazuh-only startup script or env-packs runtime code.

The extensibility seam is the backend's generator-agnostic workspace
preparation policy: admitted target root, expected host ownership, required
access posture, and artifact lifecycle enter that seam; the generator kind and
Wazuh path do not define it. This allows the same protection to cover the next
Docker-created directory or another generated-artifact kind without changing
portable SDL. Platform adapters may choose a no-op or equivalent ownership
strategy where POSIX UID/GID semantics do not apply.

## Proof boundary and gotchas

An env-packs test can prove that TechVault still validates and that private
outputs remain read-only and correctly selected. The ownership regression must
be proved in APTL/LilRAE with absent, foreign-owned, partially generated, and
valid reusable workspaces. The backend proof also needs to cover unsafe links
or replacements, an unrecoverable permission failure, host ownership of final
outputs, reuse of valid keys from a manageable workspace, preservation aside
of foreign-owned material, and absence of key material or raw host details from
logs and results.

Do not confuse these outcomes:

- a generator command that failed, an output that was not declared, and a
  declared output that was not produced;
- a valid reusable certificate bundle and a directory that the current host
  user can manage;
- container UID selection and ownership of a bind source created earlier by
  the Docker daemon;
- an operator-local actionable diagnostic and a portable RAES result;
- one physical Wazuh certificate directory and the three authored artifact
  identities and consumer projections.

## Non-goals and rejected shortcuts

- Do not add host paths, UID/GID, Docker commands, `chown`, or APTL-specific
  directory policy to TechVault SDL, `pack.yaml`, compatibility schemas,
  provenance, kits, or associated-artifact metadata.
- Do not add a new generated-artifact schema, certificate profile language,
  exception hierarchy, runtime logger, or duplicate output validator here.
- Do not weaken, catch-and-ignore, or relabel SEM-218 as success.
- Do not regenerate or rotate valid certificates from a workspace already
  manageable by the invoking user. A foreign-owned workspace may be preserved
  aside and regenerated when ownership cannot be repaired safely; do not change
  `reuse_valid` to mask the host-state defect.
- Do not make output directories world-writable, recursively change ownership
  above the admitted workspace, follow symlinks, or pass secret material on a
  process command line.
- Do not treat APTL/LilRAE's checkout layout as canonical pack terminology.

No ADR is required. ADR 0009, ADR 0036, and the public ownership-boundary
document already assign portable semantics to RAES/TechVault and runtime
realization to APTL/LilRAE.
