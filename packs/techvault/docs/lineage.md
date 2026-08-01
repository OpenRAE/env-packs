# TechVault lineage

The authoritative machine-readable record is
[`provenance-ledger.yaml`](provenance-ledger.yaml).

## Upstream scenario

This is the existing APTL TechVault scenario, not a new scenario inspired by
it. The migration capture is pinned to APTL commit
`43f137450268f25615c07b9a24144540dfac3c34` on 2026-07-20. The operational SDL
last changed earlier in that history at `a4423db`; the later pin captures the
consumer context in which the migration was assessed.

The SDL was copied and adapted under APTL's MIT license. Its content directory
and Wazuh generated-artifact provenance paths were rewritten to resolve inside
`scenarios/techvault/`, and the referenced source files were brought with it.
Comments that made APTL Compose the authority were recast around ACES/provider
ownership. Scenario identity and ACES resource semantics remain TechVault.

## Deliberate removals

An earlier pack draft modeled an unrelated security SaaS involving a secrets
vault, data room, support workflow, and CI/CD path. Its `x-techvault` contract,
six flags, CTFd adapter, objective oracle, and agent benchmark were removed.
They were not present in APTL's TechVault ACES scenario and had consumers of
their own only inside the mistaken draft.

## Remaining migration

APTL provider realization and its battle-tested consumers are not yet copied
into this pack. Their migration must retain working behavior while continuing
APTL's move toward generic, product-agnostic ACES realization. Details that
ACES 0.23.1 cannot express should be raised as ACES gaps rather than hidden in a
TechVault-specific extension.
