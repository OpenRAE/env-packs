---
id: ASP-0002
title: "Complete pack-local validator and test discovery"
status: ACTIVE
type: FUNCTIONAL
priority: MUST
created_at: 2026-07-15T18:09:30.283175Z
updated_at: 2026-07-15T22:35:14.542977Z
---

# ASP-0002 — Complete pack-local validator and test discovery

## Statement

The author validation utility shall deterministically execute each direct validate_*.py under sdl, validation, profiles, and flags, and shall discover unittest suites under sdl/tests, validation/tests, build/tests, profiles/tests, ctfd/tests, and pack-root tests, only for packs that pass static validation. Execution shall fail closed on unsafe or changed filesystem identity, use argv without shell construction, and bound subprocess output and lifetime. Shared tooling shall contain no downstream catalog paths, names, or skip lists.

## Rationale

Catalogs adopting the packaged author gate must retain all contract-supported pack-local checks without wrappers or package-internal imports.

## Traceability

- TESTS → TEST `tests/test_content_ci.py` (Pack-local executable discovery and safety tests)
- DOCUMENTS → ADR `docs/decisions/adrs/0013-separate-consumer-static-validation-from-author-ci.md` (Author-CI executable discovery contract)
- IMPLEMENTS → PULL_REQUEST `117` (feat: discover all supported pack checks)
- IMPLEMENTS → GITHUB_ISSUE `114` (Discover all contract-supported pack validators and test suites)
- IMPLEMENTS → CODE_FILE `src/raes_env_packs/content_ci.py` (Contract-supported validator and unittest discovery)
