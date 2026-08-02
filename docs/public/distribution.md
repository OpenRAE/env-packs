# Distribute and verify a pack

A published pack release carries everything a consumer needs to trust it before
it runs: an explicit version, the pack's content identity, a standards-backed
SBOM, and a signature over that identity. Distribution reuses the identity, lock,
and trust authorities RAES already owns — it adds no second identity, lock, trust
class, or cryptography
([ADR 0037](https://github.com/OpenRAE/env-packs/blob/main/docs/decisions/adrs/0037-compose-verified-pack-distribution-from-existing-authorities.md)).

## The pieces

- **Subject** — the pack's content identity, the validator-derived RAES
  associated-artifact *set digest*. This is what gets signed. An OCI manifest
  digest is a transport address, never the pack's identity; results always say
  which a `sha256:` value is.
- **SBOM** — a CycloneDX JSON inventory of every component the pack ships or
  immutably pins, bound to the subject. It is inventory, not a safety or
  vulnerability-free claim.
- **Provenance** — an in-toto statement binding the version, semantic parent,
  source revision, builder, lock state, view identities, and SBOM digest to the
  subject.
- **`release.yaml`** — the single publication carrier. A published release
  references the SBOM and provenance from its `evidence` block; both sit beside
  the release, never inside the identity they describe.

## Publish

Content identity is required to publish. Build the release and its evidence:

```sh
raes-pack-release build --pack packs/techvault --out dist/ --publish
```

This validates the pack, generates the SBOM and provenance, and writes them next
to the boundary-split views with `release.yaml`. Declare any components the tool
can't derive from the SDL, lock, or kits — external or vendored software — in
`publication-supply.yaml` (see the [pack reference](environment-packs.md)); a
shipped or pinned component that contradicts an incumbent, or lacks a digest,
fails the build.

Signing and pushing to a registry use established tooling (cosign, oras) and a
keyless Sigstore identity, so they run in CI, not on a laptop. The
`Pack distribution rehearsal` workflow does the full publish → sign → install →
verify pass against an ephemeral registry.

## Verify

Check an acquired release before you trust its bytes:

```sh
raes-pack-verify --pack ./techvault --release ./dist/techvault-0.1.0
```

Verification keeps five evidence states distinct rather than collapsing them into
a yes/no:

| State | Meaning |
|---|---|
| `verified` | checked and passed under the subject |
| `failed` | checked and did not pass |
| `unverified` | evidence is present but was not checked |
| `unavailable` | a verifier, registry, or policy authority was not reachable |
| `absent` | the evidence was not published |

A release is *accepted* when static validation, content byte-binding, the
publication profile, the SBOM, and the provenance all verify. Signature
authenticity is reported separately; add `--require-signature` to reject a
release whose signature does not verify.

```python
from raes_env_packs import verify_pack_release, load_release_evidence

profile, sbom, provenance = load_release_evidence(release_dir)
result = verify_pack_release(pack_root, release_profile=profile,
                             sbom_document=sbom, provenance_document=provenance)
if not result.accepted:
    reject(result.evidence)
```

## Install, update, lock

`raes-pack-dist` plans every operation before it touches anything. A plan lists
the resolved digests, the changes an apply would make, and the classified effects
(network, filesystem, signing, registry). Nothing happens without `--apply`.

```sh
raes-pack-dist install --pack ./techvault --release ./dist/techvault-0.1.0 \
  --target ./environments/techvault            # prints the plan
raes-pack-dist install ... --target ./environments/techvault --apply
```

Apply is bound to the exact plan it was authorized for — the same operation, the
same target, the same resolved subject — and **fails closed on authenticity**: a
published release must verify its signature before promotion. A caller with no
signing infrastructure accepts an unsigned release explicitly with
`--allow-unsigned`; nothing promotes integrity-only bytes silently. Apply
re-verifies the staged bytes and promotes them atomically — the live target is
never deleted or overlaid first. It writes a receipt beside the pack recording the
resolved reference, subject, evidence digests, and verification observations, so
an update can show what changes and a rollback knows the prior identity.

`lock` surfaces the reproducible subject and module-lock digests a consumer pins
against; `update` shows the version, dependency, SBOM-scope, and compatibility
changes before applying them. Every command returns stable human or `--json`
output for Hub and MCP delegation.
