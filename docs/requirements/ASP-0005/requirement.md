---
id: ASP-0005
title: "Pack-aware authoring surface with explicit effects"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
created_at: 2026-09-06T00:00:00Z
updated_at: 2026-09-06T00:00:00Z
---

# ASP-0005 — Pack-aware authoring surface with explicit effects

## Statement

A separately registered environment-pack MCP surface shall expose pack search,
inspection, examples, scaffolding, kit composition, static validation,
diagnostic explanation, compatibility cards and publication planning through
the same pack contracts and records consumed by CLI and Hub adapters. Public
pinned RAES APIs shall remain the sole authority for SDL parsing, formatting,
diagnostics, completion, compilation and execution-plan construction. Host
configuration shall restrict admitted sources, targets and operations; requests
shall not expand that authority. Default inspection and validation shall be
bounded, static, networkless and non-executing, without reading secret files or
starting a backend. Every effectful preparation and pack write shall disclose
its target and intended changes before a separate authorized operation consumes
the exact session-bound proposal. Apply shall reject unknown, stale or changed
proposals and use the existing guarded transactions. Runtime, network, billing,
credential, signing and publication mutations shall remain outside these tools.
Automated tests shall verify shared-result parity and enforce these boundaries.

## Rationale

Issue #192 adds executable MCP admission and mutation gates. This requirement
anchors their traceability without adding pack concepts to RAES or duplicating
the existing pack, catalog, wizard, kit and publication contracts.

## Traceability

- IMPLEMENTS → GITHUB_ISSUE `192`
- IMPLEMENTS → CODE_FILE `src/raes_env_packs/authoring.py`
- IMPLEMENTS → CODE_FILE `src/raes_env_packs/mcp_server.py`
- IMPLEMENTS → CODE_FILE `src/raes_env_packs/_authoring_tools.py`
- IMPLEMENTS → CODE_FILE `src/raes_env_packs/_authoring_safety.py`
- IMPLEMENTS → CODE_FILE `src/raes_env_packs/_proposal_review.py`
- IMPLEMENTS → CODE_FILE `src/raes_env_packs/kits.py`
- IMPLEMENTS → CODE_FILE `src/raes_env_packs/wizard.py`
- IMPLEMENTS → CODE_FILE `src/raes_env_packs/verify.py`
- IMPLEMENTS → CODE_FILE `src/raes_env_packs/distribution.py`
- IMPLEMENTS → CODE_FILE `src/raes_env_packs/validation.py`
- TESTS → TEST `tests/test_authoring.py`
- TESTS → TEST `tests/test_authoring_safety.py`
- TESTS → TEST `tests/test_mcp_server.py`
