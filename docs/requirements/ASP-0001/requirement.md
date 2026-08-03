---
id: ASP-0001
title: "Explicit pack validation roots and portable bulk convenience"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
created_at: 2026-07-15T17:59:23.591618Z
updated_at: 2026-07-15T17:59:40.186486Z
---

# ASP-0001 — Explicit pack validation roots and portable bulk convenience

## Statement

The author and release utilities shall validate an explicitly supplied pack directory without assuming a catalog layout. Optional bulk validation shall enumerate every real direct child directory of a caller-supplied packs root deterministically and validate each candidate; pack.yaml shall remain a pack-contract requirement rather than a discovery filter. Shared tooling shall contain no downstream catalog paths, names, issue history, or policy checks.

## Rationale

Scope corrected with the repository owner: single-pack validation is primary; bulk enumeration is optional convenience and must not own downstream catalog layout.

## Traceability

- TESTS → TEST `tests/test_release.py` (Release validation root tests)
- TESTS → TEST `tests/test_content_ci.py` (Author validation root and discovery tests)
- TESTS → TEST `tests/test_cli_coverage.py` (Explicit single-pack CLI coverage)
- DOCUMENTS → DOCUMENTATION `README.md` (Explicit pack validation usage)
- IMPLEMENTS → CODE_FILE `src/raes_env_packs/release.py` (Explicit pack release check and packs-root convenience)
- IMPLEMENTS → PULL_REQUEST `116` (fix: accept explicit pack validation roots)
- IMPLEMENTS → GITHUB_ISSUE `113` (Explicit pack validation roots and portable bulk convenience)
- IMPLEMENTS → CODE_FILE `src/raes_env_packs/content_ci.py` (Explicit pack validation and packs-root author gate)
