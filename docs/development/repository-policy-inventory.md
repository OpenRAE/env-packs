# Repository policy invariant inventory

This inventory compares the sixteen source modules at `c5df5bd` with the delivery for issue #577.
Each row identifies one source assertion, including assertions inside loops, setup, and helpers.
A loop row covers every case in that source table.

The invariant column uses the source test name.
This change retains every source assertion. The old tests continue in the Python CI lane until cutover.
Rows marked `PY-*` identify current Python product checks and their explicit retirement boundary under ADR 0047.
The title-validator rows remain command tests; `title.workflow` adds the workflow policy without another grammar.

## Evidence keys

A Rego identifier names the rule in `policy/` and its bounded test in `policy/main_test.rego`.
Every rule passes `policy/testdata/baseline.json` and rejects every case assigned to it in `policy/testdata/cases.json`.
The fixture index below names those failing cases. Ingestion and executable probes provide additional evidence at the actual boundaries.

| Key | Passing and failing evidence or retained-control reason |
| --- | --- |
| `GO-SHELL` | tools/policyinput/main_test.go: TestShellCommands; wrapped and quoted complete arguments pass; malformed syntax fails. Native Bash parsing replaces continuation and token helpers. |
| `GO-INPUT` | tools/policyinput/main_test.go: TestCollectorFailsClosed, TestReadInput; boundary_test.go: TestDiscoveryBoundaries, TestRootRejectsEscapingInput, TestReadFailures, TestWorkflowShapes; ingestion_test.go: TestCollectorDiscoveryPopulation, TestDirectoryInspectionFailure, TestReadBudgetStopsAfterOversizeDetection, TestUnencodableInputFailsWithoutPartialJSON. Real inputs pass; missing, malformed, symlinked, oversized and wrongly shaped inputs fail. |
| `GO-PROMOTION` | tools/policyinput/behavior_test.go: TestPromotionBehavior; actual make/help invokes no GitHub command; devmain captures exact creation arguments; fake GitHub failure blocks the target. |
| `GO-PLATFORMS` | tools/policyinput/behavior_test.go: TestGoPlatformGateBehavior; discovery failures stop lint/audit, and audit visits every declared platform. Existing go-lint and go-audit supply module tidiness, integrity, and vulnerability checks. |
| `GO-AGGREGATE` | tools/policyinput/behavior_test.go: TestAggregateScriptBehavior; all successes pass, then every mandatory result independently fails for failure, cancellation, skipping, and empty input. |
| `GO-IDENTITY` | internal/contractalignment/identity_test.go: TestIdentityContracts; checks the actual module, packaged schema IDs/versions, locator scheme, release identity, and lock references. TestRetiredIdentityRule supplies positive and negative identity inputs. |
| `GO-BOUND-IDENTITY` | internal/contractalignment/identity_test.go: TestBoundProjectIdentities; actual Ground Control and Sonar bindings are exact. The tracked scan checks each permitted bound line occurs exactly once. |
| `GO-RETIRED-IDENTITY` | internal/contractalignment/identity_test.go: TestTrackedFilesDoNotReviveRetiredIdentity and TestRetiredIdentityRule; tracked-file scan retains exact historical exceptions, while canonical identities pass and every retired form fails. |
| `GO-CONCEPT` | internal/contractalignment/alignment_test.go: TestSchemasDeferToLiveConceptAuthority, TestSchemaVocabularyTraversal, TestForbiddenTactic; actual nonempty upstream catalogs and packaged schemas, nested enum/const mutations, property homographs, tactic IDs, and ordinary terms. internal/raesadapter/vocabulary_test.go tests real catalog terms, unknown IDs, and isolated returned slices. |
| `GO-CHALLENGES` | internal/contractalignment/alignment_test.go: TestChallengeTemplate; actual template challenges omit category. CONFORMANCE-CATEGORY supplies the rejected declaration. |
| `GO-AUTHORITY` | internal/contractalignment/alignment_test.go: TestAuthorityReferences; actual schema, layout, public guide and identity ADR reference the upstream authority. Missing records or markers fail. |
| `GO-PROVENANCE` | internal/contractalignment/alignment_test.go: TestProvenanceAuthority, TestProvenanceVocabulary, TestProvenanceExample, TestAuthorityReferences, TestSchemaVocabularyTraversal; real schemas and full compiled example validation pass; unknown source kind fails. Traversal tests enumerate nested properties, enums, constants and ignored prose. |
| `CONFORMANCE-CATEGORY` | conformance/testdata/raes-pack-check/concept-authority.txtar; the actual command rejects category with the exact diagnostic and field, and omits that diagnostic for an uncategorized challenge. The current Python command passes; the Go command inherits this corpus at cutover. |
| `PY-SYNTAX` | Retained in tests/test_dependency_pinning.py until ADR 0047 removes the Python product in #582: PEP syntax compatibility and the Sonar Python floor concern that product. Go equivalents are the go.mod toolchain, go-check, and go-lint. Docs Python remains independently checked by docs.configuration. |
| `PY-METADATA` | Retained in tests/test_dependency_pinning.py while the Python product ships: PEP dependency constraint satisfaction, metadata/input agreement, and exact Python update ownership. ADR 0047 removes these product-specific subjects in #582. Go equivalents are go.mod/go.sum, go-audit, go-lint, and dependency.update-owners. Documentation hash locks and security floors remain Rego controls after cutover. |
| `PY-IDENTITY` | Retained in tests/test_raes_identity.py while Python distribution names, entry points, import tree and upstream requirement exist. ADR 0047 removes those product-specific subjects at #582. TestIdentityContracts checks the Go module and common contract identity; go.mod/go.sum bind the actual upstream Go dependency. |
| `TITLE-VALIDATOR` | Retained tests/test_pr_title_guard.py tests the canonical validator and its CLI, rather than workflow structure. title.workflow checks trusted workflow wiring to that validator. This migration defines no second title grammar; the repository-tool port owns the command replacement. Existing accepted/rejected title tables and event/CLI tests remain active. |

## test_workflow_permissions.py

| Source assertion | Invariant | Replacement and evidence |
| --- | --- | --- |
| `PermissionRuleTests.test_read_only_values_are_accepted` L116 `assertTrue` | `read_only_values_are_accepted` | `workflow.permissions` |
| `PermissionRuleTests.test_write_and_undeclared_values_are_rejected` L127 `assertFalse` | `write_and_undeclared_values_are_rejected` | `workflow.permissions` |
| `TopLevelPermissionsTests.test_every_workflow_declares_top_level_permissions` L137 `assertIn` | `every_workflow_declares_top_level_permissions` | `workflow.permissions` |
| `TopLevelPermissionsTests.test_top_level_permissions_are_read_only` L149 `assertTrue` | `top_level_permissions_are_read_only` | `workflow.permissions` |
| `JobLevelPermissionsTests.test_jobs_that_declare_permissions_use_a_mapping` L170 `assertIsInstance` | `jobs_that_declare_permissions_use_a_mapping` | `workflow.job-scopes` |
| `JobLevelPermissionsTests.test_no_job_grants_write_without_a_read_only_top_level` L191 `assertTrue` | `no_job_grants_write_without_a_read_only_top_level` | `workflow.permissions` |
| `ActionPinningTests.test_every_third_party_action_is_sha_pinned` L211 `assertIn` | `every_third_party_action_is_sha_pinned` | `workflow.action-pins` |
| `ActionPinningTests.test_every_third_party_action_is_sha_pinned` L217 `assertRegex` | `every_third_party_action_is_sha_pinned` | `workflow.action-pins` |
| `NoAutoMergeTests.test_no_workflow_enables_auto_merge` L238 `assertNotIn` | `no_workflow_enables_auto_merge` | `workflow.no-merge` |
| `NoAutoMergeTests.test_no_workflow_merges_a_pull_request` L252 `assertNotIn` | `no_workflow_merges_a_pull_request` | `workflow.no-merge` |
| `NoAutoMergeTests.test_the_guard_would_catch_the_removed_workflow` L271 `assertTrue` | `the_guard_would_catch_the_removed_workflow` | `workflow.no-merge` |
| `NoAutoMergeTests.test_the_guard_would_catch_the_removed_workflow` L275 `assertIn` | `the_guard_would_catch_the_removed_workflow` | `workflow.no-merge` |
| `NoAutoMergeTests.test_the_guard_ignores_prose_about_auto_merge` L291 `assertNotIn` | `the_guard_ignores_prose_about_auto_merge` | `workflow.no-merge` |

## test_dependency_pinning.py

| Source assertion | Invariant | Replacement and evidence |
| --- | --- | --- |
| `PythonAnalysisCompatibilityTests.test_analysis_and_source_syntax_include_the_declared_python_floor` L200 `assertIsNotNone` | `analysis_and_source_syntax_include_the_declared_python_floor` | `PY-SYNTAX` |
| `PythonAnalysisCompatibilityTests.test_analysis_and_source_syntax_include_the_declared_python_floor` L204 `assertIsNotNone` | `analysis_and_source_syntax_include_the_declared_python_floor` | `PY-SYNTAX` |
| `PythonAnalysisCompatibilityTests.test_analysis_and_source_syntax_include_the_declared_python_floor` L206 `assertIn` | `analysis_and_source_syntax_include_the_declared_python_floor` | `PY-SYNTAX` |
| `PipPinningRuleTests.test_pinned_shapes_are_accepted` L251 `assertFalse` | `pinned_shapes_are_accepted` | `dependency.pip-pins` |
| `PipPinningRuleTests.test_unpinned_shapes_are_rejected` L259 `assertTrue` | `unpinned_shapes_are_rejected` | `dependency.pip-pins` |
| `PipPinningRuleTests.test_editable_source_pinning` L265 `assertTrue` | `editable_source_pinning` | `dependency.pip-pins` |
| `PipPinningRuleTests.test_editable_source_pinning` L266 `assertTrue` | `editable_source_pinning` | `dependency.pip-pins` |
| `PipPinningRuleTests.test_editable_source_pinning` L267 `assertTrue` | `editable_source_pinning` | `dependency.pip-pins` |
| `PipPinningRuleTests.test_editable_source_pinning` L268 `assertFalse` | `editable_source_pinning` | `dependency.pip-pins` |
| `PipPinningRuleTests.test_editable_source_pinning` L269 `assertFalse` | `editable_source_pinning` | `dependency.pip-pins` |
| `ShellParsingTests.test_backslash_continuations_are_folded` L277 `assertEqual` | `backslash_continuations_are_folded` | `GO-SHELL` |
| `ShellParsingTests.test_multiple_continuations_fold_into_one_line` L284 `assertEqual` | `multiple_continuations_fold_into_one_line` | `GO-SHELL` |
| `ShellParsingTests.test_a_wrapped_install_is_read_in_full` L291 `assertEqual` | `a_wrapped_install_is_read_in_full` | `GO-SHELL` |
| `ShellParsingTests.test_a_wrapped_install_is_read_in_full` L292 `assertFalse` | `a_wrapped_install_is_read_in_full` | `GO-SHELL` |
| `ShellParsingTests.test_unwrapped_installs_still_parse` L296 `assertEqual` | `unwrapped_installs_still_parse` | `GO-SHELL` |
| `ShellParsingTests.test_non_install_pip_commands_are_ignored` L299 `assertEqual` | `non_install_pip_commands_are_ignored` | `GO-SHELL` |
| `WorkflowPipPinningTests.test_every_pip_install_is_pinned` L311 `assertFalse` | `every_pip_install_is_pinned` | `dependency.pip-pins` |
| `WorkflowPipPinningTests.test_every_pip_install_is_pinned` L318 `assertGreater` | `every_pip_install_is_pinned` | `dependency.pip-pins` |
| `WorkflowPipPinningTests.test_every_referenced_lock_file_exists` L327 `assertTrue` | `every_referenced_lock_file_exists` | `dependency.references` |
| `LockFileIntegrityTests.test_audit_lock_excludes_pip_affected_by_pysec_2026_3721` L339 `assertGreaterEqual` | `audit_lock_excludes_pip_affected_by_pysec_2026_3721` | `dependency.floors` |
| `LockFileIntegrityTests.test_audit_lock_excludes_msgpack_affected_by_cve_2026_114613` L343 `assertGreaterEqual` | `audit_lock_excludes_msgpack_affected_by_cve_2026_114613` | `dependency.floors` |
| `LockFileIntegrityTests.test_locks_exclude_certifi_affected_by_pysec_2026_4320` L349 `assertGreaterEqual` | `locks_exclude_certifi_affected_by_pysec_2026_4320` | `dependency.floors` |
| `LockFileIntegrityTests.test_every_requirement_is_exactly_pinned_and_hashed` L356 `assertTrue` | `every_requirement_is_exactly_pinned_and_hashed` | `dependency.lock-files` |
| `LockFileIntegrityTests.test_every_requirement_is_exactly_pinned_and_hashed` L359 `assertGreaterEqual` | `every_requirement_is_exactly_pinned_and_hashed` | `dependency.lock-files` |
| `LockFileIntegrityTests.test_every_requirement_is_exactly_pinned_and_hashed` L369 `assertNotIn` | `every_requirement_is_exactly_pinned_and_hashed` | `dependency.lock-files` |
| `LockFileIntegrityTests.test_co_installed_locks_agree_on_shared_packages` L394 `assertEqual` | `co_installed_locks_agree_on_shared_packages` | `dependency.co-installed` |
| `LockMatchesProjectMetadataTests.test_runtime_lock_satisfies_declared_dependencies` L415 `assertIn` | `runtime_lock_satisfies_declared_dependencies` | `PY-METADATA` |
| `LockMatchesProjectMetadataTests.test_runtime_lock_satisfies_declared_dependencies` L420 `assertTrue` | `runtime_lock_satisfies_declared_dependencies` | `PY-METADATA` |
| `LockMatchesProjectMetadataTests.test_runtime_input_copies_declared_dependencies` L433 `assertEqual` | `runtime_input_copies_declared_dependencies` | `PY-METADATA` |
| `LockMatchesProjectMetadataTests.test_dependabot_owners_match_declared_dependencies` L455 `assertEqual` | `dependabot_owners_match_declared_dependencies` | `PY-METADATA` |
| `LockMatchesProjectMetadataTests.test_dependabot_owners_match_declared_dependencies` L456 `assertLessEqual` | `dependabot_owners_match_declared_dependencies` | `PY-METADATA` |
| `LockMatchesProjectMetadataTests.test_dependabot_updates_go_modules` L463 `assertEqual` | `dependabot_updates_go_modules` | `dependency.update-owners` |
| `LockMatchesProjectMetadataTests.test_dependabot_updates_go_modules` L465 `assertEqual` | `dependabot_updates_go_modules` | `dependency.update-owners` |
| `LockMatchesProjectMetadataTests.test_dependabot_updates_go_modules` L466 `assertEqual` | `dependabot_updates_go_modules` | `dependency.update-owners` |
| `LockMatchesProjectMetadataTests.test_dependabot_updates_go_modules` L467 `assertEqual` | `dependabot_updates_go_modules` | `dependency.update-owners` |
| `LockMatchesProjectMetadataTests.test_declared_floor_is_not_rewritten_as_a_lock` L474 `assertTrue` | `declared_floor_is_not_rewritten_as_a_lock` | `PY-METADATA` |

## test_codeql_workflow.py

| Source assertion | Invariant | Replacement and evidence |
| --- | --- | --- |
| `CodeqlWorkflowContractTests.test_pull_request_has_no_branch_filter` L72 `assertNotIn` | `pull_request_has_no_branch_filter` | `codeql.triggers` |
| `CodeqlWorkflowContractTests.test_pull_request_has_no_branch_filter` L73 `assertNotIn` | `pull_request_has_no_branch_filter` | `codeql.triggers` |
| `CodeqlWorkflowContractTests.test_has_weekly_schedule` L77 `assertTrue` | `has_weekly_schedule` | `codeql.triggers` |
| `CodeqlWorkflowContractTests.test_has_weekly_schedule` L79 `assertTrue` | `has_weekly_schedule` | `codeql.triggers` |
| `CodeqlWorkflowContractTests.test_has_weekly_schedule` L82 `assertEqual` | `has_weekly_schedule` | `codeql.triggers` |
| `CodeqlWorkflowContractTests.test_has_weekly_schedule` L85 `assertNotEqual` | `has_weekly_schedule` | `codeql.triggers` |
| `CodeqlWorkflowContractTests.test_has_weekly_schedule` L86 `assertEqual` | `has_weekly_schedule` | `codeql.triggers` |
| `CodeqlWorkflowContractTests.test_has_weekly_schedule` L88 `assertNotEqual` | `has_weekly_schedule` | `codeql.triggers` |
| `CodeqlWorkflowContractTests.test_trigger_surface_is_pr_and_schedule_only` L93 `assertEqual` | `trigger_surface_is_pr_and_schedule_only` | `codeql.triggers` |
| `CodeqlWorkflowContractTests.test_least_privilege_permissions` L104 `assertEqual` | `least_privilege_permissions` | `codeql.analysis` |
| `CodeqlWorkflowContractTests.test_least_privilege_permissions` L107 `assertIsNotNone` | `least_privilege_permissions` | `codeql.analysis` |
| `CodeqlWorkflowContractTests.test_least_privilege_permissions` L108 `assertEqual` | `least_privilege_permissions` | `codeql.analysis` |
| `CodeqlWorkflowContractTests.test_least_privilege_permissions` L112 `assertEqual` | `least_privilege_permissions` | `codeql.analysis` |
| `CodeqlWorkflowContractTests.test_least_privilege_permissions` L113 `assertEqual` | `least_privilege_permissions` | `codeql.analysis` |
| `CodeqlWorkflowContractTests.test_python_build_mode_none_matrix` L120 `assertIsNotNone` | `python_build_mode_none_matrix` | `codeql.analysis` |
| `CodeqlWorkflowContractTests.test_python_build_mode_none_matrix` L121 `assertEqual` | `python_build_mode_none_matrix` | `codeql.analysis` |
| `CodeqlWorkflowContractTests.test_go_autobuild_matrix_with_the_pinned_toolchain` L128 `assertIsNotNone` | `go_autobuild_matrix_with_the_pinned_toolchain` | `codeql.analysis` |
| `CodeqlWorkflowContractTests.test_go_autobuild_matrix_with_the_pinned_toolchain` L129 `assertEqual` | `go_autobuild_matrix_with_the_pinned_toolchain` | `codeql.analysis` |
| `CodeqlWorkflowContractTests.test_go_autobuild_matrix_with_the_pinned_toolchain` L131 `assertGreaterEqual` | `go_autobuild_matrix_with_the_pinned_toolchain` | `codeql.analysis` |
| `CodeqlWorkflowContractTests.test_go_autobuild_matrix_with_the_pinned_toolchain` L132 `assertLess` | `go_autobuild_matrix_with_the_pinned_toolchain` | `codeql.analysis` |
| `CodeqlWorkflowContractTests.test_go_autobuild_matrix_with_the_pinned_toolchain` L134 `assertEqual` | `go_autobuild_matrix_with_the_pinned_toolchain` | `codeql.analysis` |
| `CodeqlWorkflowContractTests.test_go_autobuild_matrix_with_the_pinned_toolchain` L135 `assertEqual` | `go_autobuild_matrix_with_the_pinned_toolchain` | `codeql.analysis` |
| `CodeqlWorkflowContractTests.test_codeql_scans_the_complete_repository` L143 `assertEqual` | `codeql_scans_the_complete_repository` | `codeql.analysis` |
| `CodeqlWorkflowContractTests.test_codeql_scans_the_complete_repository` L148 `assertNotIn` | `codeql_scans_the_complete_repository` | `codeql.analysis` |
| `CodeqlWorkflowContractTests.test_codeql_actions_present_and_sha_pinned` L158 `assertIsNotNone` | `codeql_actions_present_and_sha_pinned` | `codeql.analysis + workflow.action-pins` |
| `CodeqlWorkflowContractTests.test_codeql_actions_present_and_sha_pinned` L160 `assertRegex` | `codeql_actions_present_and_sha_pinned` | `codeql.analysis + workflow.action-pins` |
| `CodeqlWorkflowContractTests.test_checkout_then_init_then_analyze_order` L168 `assertGreaterEqual` | `checkout_then_init_then_analyze_order` | `codeql.analysis` |
| `CodeqlWorkflowContractTests.test_checkout_then_init_then_analyze_order` L169 `assertLess` | `checkout_then_init_then_analyze_order` | `codeql.analysis` |
| `CodeqlWorkflowContractTests.test_checkout_then_init_then_analyze_order` L170 `assertLess` | `checkout_then_init_then_analyze_order` | `codeql.analysis` |
| `CodeqlWorkflowContractTests.test_concurrency_cancels_in_progress` L175 `assertIsNotNone` | `concurrency_cancels_in_progress` | `codeql.analysis` |
| `CodeqlWorkflowContractTests.test_concurrency_cancels_in_progress` L176 `assertTrue` | `concurrency_cancels_in_progress` | `codeql.analysis` |

## test_scorecard_workflow.py

| Source assertion | Invariant | Replacement and evidence |
| --- | --- | --- |
| `ScorecardWorkflowContractTests.test_trigger_surface_is_schedule_and_push_only` L100 `assertEqual` | `trigger_surface_is_schedule_and_push_only` | `scorecard.triggers` |
| `ScorecardWorkflowContractTests.test_push_targets_main_only` L104 `assertEqual` | `push_targets_main_only` | `scorecard.triggers` |
| `ScorecardWorkflowContractTests.test_has_weekly_schedule` L112 `assertTrue` | `has_weekly_schedule` | `scorecard.triggers` |
| `ScorecardWorkflowContractTests.test_has_weekly_schedule` L114 `assertTrue` | `has_weekly_schedule` | `scorecard.triggers` |
| `ScorecardWorkflowContractTests.test_has_weekly_schedule` L117 `assertEqual` | `has_weekly_schedule` | `scorecard.triggers` |
| `ScorecardWorkflowContractTests.test_has_weekly_schedule` L120 `assertNotEqual` | `has_weekly_schedule` | `scorecard.triggers` |
| `ScorecardWorkflowContractTests.test_has_weekly_schedule` L121 `assertEqual` | `has_weekly_schedule` | `scorecard.triggers` |
| `ScorecardWorkflowContractTests.test_has_weekly_schedule` L123 `assertNotEqual` | `has_weekly_schedule` | `scorecard.triggers` |
| `ScorecardWorkflowContractTests.test_workflow_level_permissions_read_only` L128 `assertIsNotNone` | `workflow_level_permissions_read_only` | `scorecard.publication + workflow.action-pins` |
| `ScorecardWorkflowContractTests.test_workflow_level_permissions_read_only` L130 `assertEqual` | `workflow_level_permissions_read_only` | `scorecard.publication + workflow.action-pins` |
| `ScorecardWorkflowContractTests.test_workflow_level_permissions_read_only` L133 `assertEqual` | `workflow_level_permissions_read_only` | `scorecard.publication + workflow.action-pins` |
| `ScorecardWorkflowContractTests.test_job_permissions_least_privilege` L137 `assertIsNotNone` | `job_permissions_least_privilege` | `scorecard.publication + workflow.action-pins` |
| `ScorecardWorkflowContractTests.test_job_permissions_least_privilege` L138 `assertEqual` | `job_permissions_least_privilege` | `scorecard.publication + workflow.action-pins` |
| `ScorecardWorkflowContractTests.test_job_permissions_least_privilege` L140 `assertEqual` | `job_permissions_least_privilege` | `scorecard.publication + workflow.action-pins` |
| `ScorecardWorkflowContractTests.test_job_permissions_least_privilege` L142 `assertNotEqual` | `job_permissions_least_privilege` | `scorecard.publication + workflow.action-pins` |
| `ScorecardWorkflowContractTests.test_job_permissions_least_privilege` L148 `assertEqual` | `job_permissions_least_privilege` | `scorecard.publication + workflow.action-pins` |
| `ScorecardWorkflowContractTests.test_scorecard_publishes_results_as_sarif` L153 `assertTrue` | `scorecard_publishes_results_as_sarif` | `scorecard.publication + workflow.action-pins` |
| `ScorecardWorkflowContractTests.test_scorecard_publishes_results_as_sarif` L155 `assertEqual` | `scorecard_publishes_results_as_sarif` | `scorecard.publication + workflow.action-pins` |
| `ScorecardWorkflowContractTests.test_scorecard_publishes_results_as_sarif` L156 `assertTrue` | `scorecard_publishes_results_as_sarif` | `scorecard.publication + workflow.action-pins` |
| `ScorecardWorkflowContractTests.test_checkout_does_not_persist_credentials` L165 `assertIs` | `checkout_does_not_persist_credentials` | `scorecard.publication + workflow.action-pins` |
| `ScorecardWorkflowContractTests.test_only_approved_actions_used` L171 `assertTrue` | `only_approved_actions_used` | `scorecard.publication + workflow.action-pins` |
| `ScorecardWorkflowContractTests.test_required_actions_present_and_sha_pinned` L179 `assertIsNotNone` | `required_actions_present_and_sha_pinned` | `scorecard.publication + workflow.action-pins` |
| `ScorecardWorkflowContractTests.test_required_actions_present_and_sha_pinned` L182 `assertRegex` | `required_actions_present_and_sha_pinned` | `scorecard.publication + workflow.action-pins` |
| `ScorecardWorkflowContractTests.test_checkout_then_scorecard_then_upload_sarif_order` L190 `assertGreaterEqual` | `checkout_then_scorecard_then_upload_sarif_order` | `scorecard.publication + workflow.action-pins` |
| `ScorecardWorkflowContractTests.test_checkout_then_scorecard_then_upload_sarif_order` L191 `assertLess` | `checkout_then_scorecard_then_upload_sarif_order` | `scorecard.publication + workflow.action-pins` |
| `ScorecardWorkflowContractTests.test_checkout_then_scorecard_then_upload_sarif_order` L192 `assertLess` | `checkout_then_scorecard_then_upload_sarif_order` | `scorecard.publication + workflow.action-pins` |
| `ScorecardWorkflowContractTests.test_concurrency_cancels_in_progress` L197 `assertIsNotNone` | `concurrency_cancels_in_progress` | `scorecard.triggers` |
| `ScorecardWorkflowContractTests.test_concurrency_cancels_in_progress` L198 `assertTrue` | `concurrency_cancels_in_progress` | `scorecard.triggers` |
| `ScorecardBadgeTests.test_readme_has_official_scorecard_badge` L205 `assertIn` | `readme_has_official_scorecard_badge` | `scorecard.publication + workflow.action-pins` |
| `ScorecardBadgeTests.test_readme_has_official_scorecard_badge` L210 `assertIn` | `readme_has_official_scorecard_badge` | `scorecard.publication + workflow.action-pins` |

## test_release_workflow_attestation.py

| Source assertion | Invariant | Replacement and evidence |
| --- | --- | --- |
| `ReleaseAttestationContractTests.test_attest_step_is_present_and_sha_pinned` L57 `assertRegex` | `attest_step_is_present_and_sha_pinned` | `release.order + workflow.action-pins` |
| `ReleaseAttestationContractTests.test_publish_job_grants_attestations_write_and_keeps_oidc` L66 `assertEqual` | `publish_job_grants_attestations_write_and_keeps_oidc` | `release.permissions` |
| `ReleaseAttestationContractTests.test_publish_job_grants_attestations_write_and_keeps_oidc` L69 `assertEqual` | `publish_job_grants_attestations_write_and_keeps_oidc` | `release.permissions` |
| `ReleaseAttestationContractTests.test_publish_job_grants_attestations_write_and_keeps_oidc` L71 `assertEqual` | `publish_job_grants_attestations_write_and_keeps_oidc` | `release.permissions` |
| `ReleaseAttestationContractTests.test_subject_path_covers_wheel_and_sdist` L76 `assertIsNotNone` | `subject_path_covers_wheel_and_sdist` | `release.subjects` |
| `ReleaseAttestationContractTests.test_subject_path_covers_wheel_and_sdist` L79 `assertIn` | `subject_path_covers_wheel_and_sdist` | `release.subjects` |
| `ReleaseAttestationContractTests.test_subject_path_covers_wheel_and_sdist` L80 `assertIn` | `subject_path_covers_wheel_and_sdist` | `release.subjects` |
| `ReleaseAttestationContractTests.test_attestation_runs_before_publication_destinations` L94 `assertGreaterEqual` | `attestation_runs_before_publication_destinations` | `release.order` |
| `ReleaseAttestationContractTests.test_attestation_runs_before_publication_destinations` L96 `assertLess` | `attestation_runs_before_publication_destinations` | `release.order` |
| `ReleaseAttestationContractTests.test_attestation_runs_before_publication_destinations` L97 `assertLess` | `attestation_runs_before_publication_destinations` | `release.order` |
| `ReleaseAttestationContractTests.test_attestation_runs_before_publication_destinations` L98 `assertLess` | `attestation_runs_before_publication_destinations` | `release.order` |

## test_release_workflow_tag_signing.py

| Source assertion | Invariant | Replacement and evidence |
| --- | --- | --- |
| `ReleasePleaseConfigTests.test_skip_github_release_enabled` L91 `assertTrue` | `skip_github_release_enabled` | `release.shape` |
| `WorkflowShapeTests.test_triggers_on_main_push_and_explicit_recovery` L104 `assertEqual` | `triggers_on_main_push_and_explicit_recovery` | `release.shape` |
| `WorkflowShapeTests.test_triggers_on_main_push_and_explicit_recovery` L105 `assertEqual` | `triggers_on_main_push_and_explicit_recovery` | `release.shape` |
| `WorkflowShapeTests.test_triggers_on_main_push_and_explicit_recovery` L107 `assertIs` | `triggers_on_main_push_and_explicit_recovery` | `release.shape` |
| `WorkflowShapeTests.test_triggers_on_main_push_and_explicit_recovery` L108 `assertEqual` | `triggers_on_main_push_and_explicit_recovery` | `release.shape` |
| `WorkflowShapeTests.test_releases_are_serialized` L112 `assertEqual` | `releases_are_serialized` | `release.shape` |
| `WorkflowShapeTests.test_releases_are_serialized` L113 `assertFalse` | `releases_are_serialized` | `release.shape` |
| `WorkflowShapeTests.test_all_checkouts_do_not_persist_credentials` L121 `assertIs` | `all_checkouts_do_not_persist_credentials` | `release.shape` |
| `WorkflowShapeTests.test_all_checkouts_do_not_persist_credentials` L126 `assertGreater` | `all_checkouts_do_not_persist_credentials` | `release.shape` |
| `WorkflowShapeTests.test_canonical_signer_identity` L130 `assertEqual` | `canonical_signer_identity` | `release.signer + release.order` |
| `WorkflowShapeTests.test_canonical_signer_identity` L131 `assertEqual` | `canonical_signer_identity` | `release.signer + release.order` |
| `LeastPrivilegeTests.test_release_please_job_has_no_signing_privilege` L141 `assertEqual` | `release_please_job_has_no_signing_privilege` | `release.permissions` |
| `LeastPrivilegeTests.test_release_please_job_has_no_signing_privilege` L142 `assertEqual` | `release_please_job_has_no_signing_privilege` | `release.permissions` |
| `LeastPrivilegeTests.test_release_please_job_has_no_signing_privilege` L143 `assertNotIn` | `release_please_job_has_no_signing_privilege` | `release.permissions` |
| `LeastPrivilegeTests.test_release_please_job_has_no_signing_privilege` L144 `assertNotIn` | `release_please_job_has_no_signing_privilege` | `release.permissions` |
| `LeastPrivilegeTests.test_release_please_job_has_no_signing_privilege` L145 `assertIn` | `release_please_job_has_no_signing_privilege` | `release.permissions` |
| `LeastPrivilegeTests.test_successful_recovery_resumes_release_pr_maintenance` L155 `assertIn` | `successful_recovery_resumes_release_pr_maintenance` | `release.authorization` |
| `LeastPrivilegeTests.test_successful_recovery_resumes_release_pr_maintenance` L157 `assertIn` | `successful_recovery_resumes_release_pr_maintenance` | `release.authorization` |
| `LeastPrivilegeTests.test_successful_recovery_resumes_release_pr_maintenance` L158 `assertIn` | `successful_recovery_resumes_release_pr_maintenance` | `release.authorization` |
| `LeastPrivilegeTests.test_successful_recovery_resumes_release_pr_maintenance` L160 `assertEqual` | `successful_recovery_resumes_release_pr_maintenance` | `release.authorization` |
| `LeastPrivilegeTests.test_successful_recovery_resumes_release_pr_maintenance` L161 `assertEqual` | `successful_recovery_resumes_release_pr_maintenance` | `release.authorization` |
| `LeastPrivilegeTests.test_successful_recovery_resumes_release_pr_maintenance` L162 `assertNotIn` | `successful_recovery_resumes_release_pr_maintenance` | `release.authorization` |
| `LeastPrivilegeTests.test_successful_recovery_resumes_release_pr_maintenance` L163 `assertNotIn` | `successful_recovery_resumes_release_pr_maintenance` | `release.authorization` |
| `LeastPrivilegeTests.test_successful_recovery_resumes_release_pr_maintenance` L164 `assertIn` | `successful_recovery_resumes_release_pr_maintenance` | `release.authorization` |
| `LeastPrivilegeTests.test_release_pr_maintenance_is_sequenced_behind_release_detection` L176 `assertIn` | `release_pr_maintenance_is_sequenced_behind_release_detection` | `release.authorization` |
| `LeastPrivilegeTests.test_release_pr_maintenance_excludes_the_release_push` L186 `assertIn` | `release_pr_maintenance_excludes_the_release_push` | `release.authorization` |
| `LeastPrivilegeTests.test_release_pr_maintenance_excludes_the_release_push` L190 `assertIn` | `release_pr_maintenance_excludes_the_release_push` | `release.authorization` |
| `LeastPrivilegeTests.test_release_pr_maintenance_fails_closed_on_a_detector_failure` L200 `assertNotIn` | `release_pr_maintenance_fails_closed_on_a_detector_failure` | `release.authorization` |
| `LeastPrivilegeTests.test_release_pr_maintenance_fails_closed_on_a_detector_failure` L201 `assertNotIn` | `release_pr_maintenance_fails_closed_on_a_detector_failure` | `release.authorization` |
| `LeastPrivilegeTests.test_maintenance_and_publication_are_mutually_exclusive` L208 `assertIn` | `maintenance_and_publication_are_mutually_exclusive` | `release.authorization` |
| `LeastPrivilegeTests.test_maintenance_and_publication_are_mutually_exclusive` L209 `assertIn` | `maintenance_and_publication_are_mutually_exclusive` | `release.authorization` |
| `LeastPrivilegeTests.test_detect_release_job_is_read_only` L214 `assertEqual` | `detect_release_job_is_read_only` | `release.permissions` |
| `LeastPrivilegeTests.test_detect_release_job_is_read_only` L215 `assertEqual` | `detect_release_job_is_read_only` | `release.permissions` |
| `LeastPrivilegeTests.test_detect_release_job_is_read_only` L216 `assertNotIn` | `detect_release_job_is_read_only` | `release.permissions` |
| `LeastPrivilegeTests.test_detect_release_job_is_read_only` L217 `assertNotIn` | `detect_release_job_is_read_only` | `release.permissions` |
| `LeastPrivilegeTests.test_detect_release_job_is_read_only` L218 `assertIn` | `detect_release_job_is_read_only` | `release.permissions` |
| `LeastPrivilegeTests.test_release_authorized_on_release_pr_label` L225 `assertIn` | `release_authorized_on_release_pr_label` | `release.authorization` |
| `LeastPrivilegeTests.test_release_authorized_on_release_pr_label` L227 `assertIn` | `release_authorized_on_release_pr_label` | `release.authorization` |
| `LeastPrivilegeTests.test_release_authorized_on_release_pr_label` L232 `assertIn` | `release_authorized_on_release_pr_label` | `release.authorization` |
| `LeastPrivilegeTests.test_recovery_is_bound_to_a_merged_main_release_pr` L237 `assertIn` | `recovery_is_bound_to_a_merged_main_release_pr` | `release.authorization` |
| `LeastPrivilegeTests.test_recovery_is_bound_to_a_merged_main_release_pr` L238 `assertIn` | `recovery_is_bound_to_a_merged_main_release_pr` | `release.authorization` |
| `LeastPrivilegeTests.test_recovery_is_bound_to_a_merged_main_release_pr` L239 `assertIn` | `recovery_is_bound_to_a_merged_main_release_pr` | `release.authorization` |
| `LeastPrivilegeTests.test_recovery_is_bound_to_a_merged_main_release_pr` L240 `assertIn` | `recovery_is_bound_to_a_merged_main_release_pr` | `release.authorization` |
| `LeastPrivilegeTests.test_recovery_is_bound_to_a_merged_main_release_pr` L241 `assertIn` | `recovery_is_bound_to_a_merged_main_release_pr` | `release.authorization` |
| `LeastPrivilegeTests.test_recovery_is_bound_to_a_merged_main_release_pr` L242 `assertIn` | `recovery_is_bound_to_a_merged_main_release_pr` | `release.authorization` |
| `LeastPrivilegeTests.test_recovery_is_bound_to_a_merged_main_release_pr` L243 `assertIn` | `recovery_is_bound_to_a_merged_main_release_pr` | `release.authorization` |
| `LeastPrivilegeTests.test_publish_job_permissions` L248 `assertEqual` | `publish_job_permissions` | `release.permissions` |
| `LeastPrivilegeTests.test_publish_job_permissions` L249 `assertEqual` | `publish_job_permissions` | `release.permissions` |
| `LeastPrivilegeTests.test_publish_job_permissions` L250 `assertEqual` | `publish_job_permissions` | `release.permissions` |
| `LeastPrivilegeTests.test_publish_job_permissions` L251 `assertEqual` | `publish_job_permissions` | `release.permissions` |
| `LeastPrivilegeTests.test_publish_gated_on_detect_release` L257 `assertIn` | `publish_gated_on_detect_release` | `release.authorization` |
| `LeastPrivilegeTests.test_publish_gated_on_detect_release` L258 `assertIn` | `publish_gated_on_detect_release` | `release.authorization` |
| `LeastPrivilegeTests.test_publish_gated_on_detect_release` L259 `assertIn` | `publish_gated_on_detect_release` | `release.authorization` |
| `TagSigningContractTests.test_gitsign_binary_is_version_and_digest_pinned` L270 `assertEqual` | `gitsign_binary_is_version_and_digest_pinned` | `release.signer + release.order` |
| `TagSigningContractTests.test_gitsign_binary_is_version_and_digest_pinned` L271 `assertEqual` | `gitsign_binary_is_version_and_digest_pinned` | `release.signer + release.order` |
| `TagSigningContractTests.test_gitsign_binary_is_version_and_digest_pinned` L273 `assertIn` | `gitsign_binary_is_version_and_digest_pinned` | `release.signer + release.order` |
| `TagSigningContractTests.test_gitsign_binary_is_version_and_digest_pinned` L274 `assertIn` | `gitsign_binary_is_version_and_digest_pinned` | `release.signer + release.order` |
| `TagSigningContractTests.test_gitsign_binary_is_version_and_digest_pinned` L275 `assertIn` | `gitsign_binary_is_version_and_digest_pinned` | `release.signer + release.order` |
| `TagSigningContractTests.test_gitsign_binary_is_version_and_digest_pinned` L276 `assertIn` | `gitsign_binary_is_version_and_digest_pinned` | `release.signer + release.order` |
| `TagSigningContractTests.test_gitsign_binary_is_version_and_digest_pinned` L277 `assertIn` | `gitsign_binary_is_version_and_digest_pinned` | `release.signer + release.order` |
| `TagSigningContractTests.test_gitsign_binary_is_version_and_digest_pinned` L278 `assertNotIn` | `gitsign_binary_is_version_and_digest_pinned` | `release.signer + release.order` |
| `TagSigningContractTests.test_gitsign_version_floor_guard_present` L287 `assertEqual` | `gitsign_version_floor_guard_present` | `release.signer + release.order` |
| `TagSigningContractTests.test_gitsign_version_floor_guard_present` L289 `assertIn` | `gitsign_version_floor_guard_present` | `release.signer + release.order` |
| `TagSigningContractTests.test_gitsign_version_floor_guard_present` L291 `assertIn` | `gitsign_version_floor_guard_present` | `release.signer + release.order` |
| `TagSigningContractTests.test_gitsign_version_floor_guard_present` L298 `assertGreaterEqual` | `gitsign_version_floor_guard_present` | `release.signer + release.order` |
| `TagSigningContractTests.test_gitsign_version_floor_guard_present` L299 `assertGreaterEqual` | `gitsign_version_floor_guard_present` | `release.signer + release.order` |
| `TagSigningContractTests.test_gitsign_version_floor_guard_present` L300 `assertGreaterEqual` | `gitsign_version_floor_guard_present` | `release.signer + release.order` |
| `TagSigningContractTests.test_gitsign_version_floor_guard_present` L301 `assertLess` | `gitsign_version_floor_guard_present` | `release.signer + release.order` |
| `TagSigningContractTests.test_gitsign_version_floor_guard_present` L303 `assertLess` | `gitsign_version_floor_guard_present` | `release.signer + release.order` |
| `TagSigningContractTests.test_signed_annotated_tag_at_exact_commit` L307 `assertIn` | `signed_annotated_tag_at_exact_commit` | `release.signed-target` |
| `TagSigningContractTests.test_signed_annotated_tag_at_exact_commit` L310 `assertIn` | `signed_annotated_tag_at_exact_commit` | `release.signed-target` |
| `TagSigningContractTests.test_signed_annotated_tag_at_exact_commit` L311 `assertEqual` | `signed_annotated_tag_at_exact_commit` | `release.signed-target` |
| `TagSigningContractTests.test_signed_annotated_tag_at_exact_commit` L319 `assertEqual` | `signed_annotated_tag_at_exact_commit` | `release.signed-target` |
| `TagSigningContractTests.test_verify_tag_is_identity_bound` L322 `assertIn` | `verify_tag_is_identity_bound` | `release.signer + release.order` |
| `TagSigningContractTests.test_verify_tag_is_identity_bound` L324 `assertIn` | `verify_tag_is_identity_bound` | `release.signer + release.order` |
| `TagSigningContractTests.test_verify_tag_is_identity_bound` L325 `assertIn` | `verify_tag_is_identity_bound` | `release.signer + release.order` |
| `TagSigningContractTests.test_verify_tag_is_identity_bound` L326 `assertIn` | `verify_tag_is_identity_bound` | `release.signer + release.order` |
| `TagSigningContractTests.test_verify_tag_is_identity_bound` L327 `assertIn` | `verify_tag_is_identity_bound` | `release.signer + release.order` |
| `TagSigningContractTests.test_verify_tag_is_identity_bound` L330 `assertNotIn` | `verify_tag_is_identity_bound` | `release.signer + release.order` |
| `TagSigningContractTests.test_verify_tag_is_identity_bound` L331 `assertNotIn` | `verify_tag_is_identity_bound` | `release.signer + release.order` |
| `TagSigningContractTests.test_transparency_log_verification_has_bounded_retry` L335 `assertIn` | `transparency_log_verification_has_bounded_retry` | `release.signer + release.order` |
| `TagSigningContractTests.test_transparency_log_verification_has_bounded_retry` L336 `assertIn` | `transparency_log_verification_has_bounded_retry` | `release.signer + release.order` |
| `TagSigningContractTests.test_transparency_log_verification_has_bounded_retry` L337 `assertIn` | `transparency_log_verification_has_bounded_retry` | `release.signer + release.order` |
| `TagSigningContractTests.test_release_created_from_preexisting_tag_with_file_notes` L340 `assertIn` | `release_created_from_preexisting_tag_with_file_notes` | `release.rerun` |
| `TagSigningContractTests.test_release_created_from_preexisting_tag_with_file_notes` L341 `assertIn` | `release_created_from_preexisting_tag_with_file_notes` | `release.rerun` |
| `TagSigningContractTests.test_release_created_from_preexisting_tag_with_file_notes` L343 `assertIn` | `release_created_from_preexisting_tag_with_file_notes` | `release.rerun` |
| `TagSigningContractTests.test_release_creation_is_idempotent` L352 `assertIn` | `release_creation_is_idempotent` | `release.rerun` |
| `TagSigningContractTests.test_release_creation_is_idempotent` L354 `assertLess` | `release_creation_is_idempotent` | `release.rerun` |
| `TagSigningContractTests.test_release_pr_relabeled_to_tagged` L364 `assertIn` | `release_pr_relabeled_to_tagged` | `release.rerun` |
| `TagSigningContractTests.test_release_pr_relabeled_to_tagged` L367 `assertIn` | `release_pr_relabeled_to_tagged` | `release.rerun` |
| `TagSigningContractTests.test_release_pr_relabeled_to_tagged` L368 `assertIn` | `release_pr_relabeled_to_tagged` | `release.rerun` |
| `TagSigningContractTests.test_release_pr_relabeled_to_tagged` L372 `assertGreater` | `release_pr_relabeled_to_tagged` | `release.rerun` |
| `TagSigningContractTests.test_release_pr_relabeled_to_tagged` L373 `assertGreater` | `release_pr_relabeled_to_tagged` | `release.rerun` |
| `TagSigningContractTests.test_pypi_publication_is_rerun_safe` L378 `assertIs` | `pypi_publication_is_rerun_safe` | `release.rerun` |
| `TagSigningContractTests.test_pypi_policy_allows_only_the_active_distribution` L388 `assertIn` | `pypi_policy_allows_only_the_active_distribution` | `release.rerun` |
| `TagSigningContractTests.test_pypi_policy_allows_only_the_active_distribution` L389 `assertIn` | `pypi_policy_allows_only_the_active_distribution` | `release.rerun` |
| `TagSigningContractTests.test_pypi_policy_allows_only_the_active_distribution` L390 `assertIn` | `pypi_policy_allows_only_the_active_distribution` | `release.rerun` |
| `TagSigningContractTests.test_pypi_policy_allows_only_the_active_distribution` L391 `assertNotIn` | `pypi_policy_allows_only_the_active_distribution` | `release.rerun` |
| `TagSigningContractTests.test_pypi_policy_allows_only_the_active_distribution` L396 `assertLess` | `pypi_policy_allows_only_the_active_distribution` | `release.rerun` |
| `TagSigningContractTests.test_pypi_policy_allows_only_the_active_distribution` L397 `assertLess` | `pypi_policy_allows_only_the_active_distribution` | `release.rerun` |
| `TagSigningContractTests.test_sign_then_verify_then_push_within_tag_step` L408 `assertLess` | `sign_then_verify_then_push_within_tag_step` | `release.signed-target` |
| `TagSigningContractTests.test_sign_then_verify_then_push_within_tag_step` L409 `assertLess` | `sign_then_verify_then_push_within_tag_step` | `release.signed-target` |
| `TagSigningContractTests.test_verified_tag_is_exported_when_only_its_push_fails` L417 `assertEqual` | `verified_tag_is_exported_when_only_its_push_fails` | `release.recovery` |
| `TagSigningContractTests.test_verified_tag_is_exported_when_only_its_push_fails` L427 `assertEqual` | `verified_tag_is_exported_when_only_its_push_fails` | `release.recovery` |
| `TagSigningContractTests.test_verified_tag_is_exported_when_only_its_push_fails` L428 `assertIn` | `verified_tag_is_exported_when_only_its_push_fails` | `release.recovery` |
| `TagSigningContractTests.test_verified_tag_is_exported_when_only_its_push_fails` L434 `assertIn` | `verified_tag_is_exported_when_only_its_push_fails` | `release.recovery` |
| `TagSigningContractTests.test_verified_tag_is_exported_when_only_its_push_fails` L435 `assertIn` | `verified_tag_is_exported_when_only_its_push_fails` | `release.recovery` |
| `TagSigningContractTests.test_verified_tag_is_exported_when_only_its_push_fails` L436 `assertIn` | `verified_tag_is_exported_when_only_its_push_fails` | `release.recovery` |
| `TagSigningContractTests.test_verified_tag_is_exported_when_only_its_push_fails` L437 `assertIn` | `verified_tag_is_exported_when_only_its_push_fails` | `release.recovery` |
| `TagSigningContractTests.test_verified_tag_is_exported_when_only_its_push_fails` L438 `assertIn` | `verified_tag_is_exported_when_only_its_push_fails` | `release.recovery` |
| `TagSigningContractTests.test_verified_tag_is_exported_when_only_its_push_fails` L444 `assertEqual` | `verified_tag_is_exported_when_only_its_push_fails` | `release.recovery` |
| `TagSigningContractTests.test_verified_tag_is_exported_when_only_its_push_fails` L445 `assertEqual` | `verified_tag_is_exported_when_only_its_push_fails` | `release.recovery` |
| `TagSigningContractTests.test_verified_tag_is_exported_when_only_its_push_fails` L446 `assertEqual` | `verified_tag_is_exported_when_only_its_push_fails` | `release.recovery` |
| `TagSigningContractTests.test_verified_tag_is_exported_when_only_its_push_fails` L450 `assertEqual` | `verified_tag_is_exported_when_only_its_push_fails` | `release.recovery` |
| `TagSigningContractTests.test_verified_tag_is_exported_when_only_its_push_fails` L454 `assertEqual` | `verified_tag_is_exported_when_only_its_push_fails` | `release.recovery` |
| `TagSigningContractTests.test_verified_tag_is_exported_when_only_its_push_fails` L455 `assertEqual` | `verified_tag_is_exported_when_only_its_push_fails` | `release.recovery` |
| `TagSigningContractTests.test_verified_tag_is_exported_when_only_its_push_fails` L456 `assertLess` | `verified_tag_is_exported_when_only_its_push_fails` | `release.recovery` |
| `TagSigningContractTests.test_verified_tag_is_exported_when_only_its_push_fails` L457 `assertLess` | `verified_tag_is_exported_when_only_its_push_fails` | `release.recovery` |
| `TagSigningContractTests.test_release_materializes_the_target_hash_locked_tooling` L466 `assertIn` | `release_materializes_the_target_hash_locked_tooling` | `release.recovery` |
| `TagSigningContractTests.test_release_materializes_the_target_hash_locked_tooling` L470 `assertIn` | `release_materializes_the_target_hash_locked_tooling` | `release.recovery` |
| `TagSigningContractTests.test_release_materializes_the_target_hash_locked_tooling` L475 `assertIn` | `release_materializes_the_target_hash_locked_tooling` | `release.recovery` |
| `TagSigningContractTests.test_release_materializes_the_target_hash_locked_tooling` L476 `assertNotIn` | `release_materializes_the_target_hash_locked_tooling` | `release.recovery` |
| `TagSigningContractTests.test_release_materializes_the_target_hash_locked_tooling` L483 `assertLess` | `release_materializes_the_target_hash_locked_tooling` | `release.recovery` |
| `TagSigningContractTests.test_never_deletes_or_force_updates_tags` L488 `assertNotIn` | `never_deletes_or_force_updates_tags` | `release.no-force` |
| `TagSigningContractTests.test_sign_and_verify_precede_publication` L502 `assertGreaterEqual` | `sign_and_verify_precede_publication` | `release.order` |
| `TagSigningContractTests.test_sign_and_verify_precede_publication` L508 `assertLess` | `sign_and_verify_precede_publication` | `release.order` |
| `TagSigningContractTests.test_sign_and_verify_precede_publication` L510 `assertLess` | `sign_and_verify_precede_publication` | `release.order` |
| `TagSigningContractTests.test_attestation_still_precedes_publication` L517 `assertGreaterEqual` | `attestation_still_precedes_publication` | `release.order` |
| `TagSigningContractTests.test_attestation_still_precedes_publication` L518 `assertGreaterEqual` | `attestation_still_precedes_publication` | `release.order` |
| `TagSigningContractTests.test_attestation_still_precedes_publication` L519 `assertLess` | `attestation_still_precedes_publication` | `release.order` |

## test_readthedocs_config.py

| Source assertion | Invariant | Replacement and evidence |
| --- | --- | --- |
| `ReadTheDocsConfigTests.test_uses_config_version_two` L67 `assertEqual` | `uses_config_version_two` | `docs.configuration` |
| `ReadTheDocsConfigTests.test_build_image_and_python_are_declared` L71 `assertIsInstance` | `build_image_and_python_are_declared` | `docs.configuration` |
| `ReadTheDocsConfigTests.test_build_image_and_python_are_declared` L72 `assertTrue` | `build_image_and_python_are_declared` | `docs.configuration` |
| `ReadTheDocsConfigTests.test_build_image_and_python_are_declared` L73 `assertEqual` | `build_image_and_python_are_declared` | `docs.configuration` |
| `ReadTheDocsConfigTests.test_sphinx_configuration_points_at_public_conf_py` L82 `assertIsInstance` | `sphinx_configuration_points_at_public_conf_py` | `docs.configuration` |
| `ReadTheDocsConfigTests.test_sphinx_configuration_points_at_public_conf_py` L83 `assertEqual` | `sphinx_configuration_points_at_public_conf_py` | `docs.configuration` |
| `ReadTheDocsConfigTests.test_sphinx_configuration_points_at_public_conf_py` L89 `assertTrue` | `sphinx_configuration_points_at_public_conf_py` | `docs.configuration` |
| `ReadTheDocsConfigTests.test_build_fails_on_warning` L94 `assertIs` | `build_fails_on_warning` | `docs.configuration` |
| `ReadTheDocsConfigTests.test_docs_requirements_are_hash_locked` L103 `assertTrue` | `docs_requirements_are_hash_locked` | `docs.configuration + dependency.lock-files` |
| `ReadTheDocsConfigTests.test_docs_requirements_are_hash_locked` L105 `assertIn` | `docs_requirements_are_hash_locked` | `docs.configuration + dependency.lock-files` |
| `ReadTheDocsConfigTests.test_docs_requirements_are_hash_locked` L111 `assertTrue` | `docs_requirements_are_hash_locked` | `docs.configuration + dependency.lock-files` |
| `ReadTheDocsConfigTests.test_docs_requirements_are_hash_locked` L113 `assertIn` | `docs_requirements_are_hash_locked` | `docs.configuration + dependency.lock-files` |
| `ReadTheDocsConfigTests.test_package_itself_is_not_installed_for_docs` L120 `assertNotIn` | `package_itself_is_not_installed_for_docs` | `docs.configuration` |
| `SphinxConfTests.test_conf_py_does_not_hardcode_the_version` L135 `assertNotIn` | `conf_py_does_not_hardcode_the_version` | `docs.configuration` |
| `SphinxConfTests.test_conf_py_does_not_hardcode_the_version` L140 `assertIn` | `conf_py_does_not_hardcode_the_version` | `docs.configuration` |
| `SphinxConfTests.test_markdown_is_parsed_by_myst` L144 `assertIn` | `markdown_is_parsed_by_myst` | `docs.configuration` |
| `SphinxConfTests.test_theme_edit_links_stay_in_the_public_root` L150 `assertIn` | `theme_edit_links_stay_in_the_public_root` | `docs.configuration` |
| `PublicationBoundaryTests.test_no_decision_records_under_the_public_root` L162 `assertFalse` | `no_decision_records_under_the_public_root` | `docs.public-boundary + GO-INPUT` |
| `PublicationBoundaryTests.test_no_decision_records_under_the_public_root` L171 `assertEqual` | `no_decision_records_under_the_public_root` | `docs.public-boundary + GO-INPUT` |
| `PublicationBoundaryTests.test_internal_records_live_outside_the_public_root` L183 `assertTrue` | `internal_records_live_outside_the_public_root` | `docs.public-boundary + GO-INPUT` |
| `PublicationBoundaryTests.test_internal_records_live_outside_the_public_root` L184 `assertNotIn` | `internal_records_live_outside_the_public_root` | `docs.public-boundary + GO-INPUT` |
| `PublicationBoundaryTests.test_public_pages_do_not_relative_link_outside_the_root` L199 `assertFalse` | `public_pages_do_not_relative_link_outside_the_root` | `docs.public-boundary + GO-INPUT` |
| `DeveloperIndexTests.test_developer_index_exists_and_reaches_the_records` L211 `assertTrue` | `developer_index_exists_and_reaches_the_records` | `docs.navigation` |
| `DeveloperIndexTests.test_developer_index_exists_and_reaches_the_records` L219 `assertIn` | `developer_index_exists_and_reaches_the_records` | `docs.navigation` |
| `DeveloperIndexTests.test_contributing_reaches_the_developer_index` L227 `assertIn` | `contributing_reaches_the_developer_index` | `docs.navigation` |
| `DocsNavigationTests.test_public_index_declares_a_toctree` L235 `assertIn` | `public_index_declares_a_toctree` | `docs.navigation` |
| `DocsNavigationTests.test_every_public_page_is_reachable` L253 `assertIn` | `every_public_page_is_reachable` | `docs.navigation` |
| `DocsBadgeTests.test_readme_links_the_documentation` L262 `assertIn` | `readme_links_the_documentation` | `docs.badges` |
| `DocsBadgeTests.test_readme_links_the_live_project_and_real_pages` L274 `assertTrue` | `readme_links_the_live_project_and_real_pages` | `docs.badges` |
| `DocsBadgeTests.test_readme_links_the_live_project_and_real_pages` L279 `assertTrue` | `readme_links_the_live_project_and_real_pages` | `docs.badges` |
| `DocsBadgeTests.test_readme_links_the_live_project_and_real_pages` L286 `assertTrue` | `readme_links_the_live_project_and_real_pages` | `docs.badges` |
| `DocsBadgeTests.test_readme_links_the_live_project_and_real_pages` L290 `assertIn` | `readme_links_the_live_project_and_real_pages` | `docs.badges` |

## test_makefile.py

| Source assertion | Invariant | Replacement and evidence |
| --- | --- | --- |
| `DevmainInvocationTests._devmain_argv` L95 `assertEqual` | `devmain_argv` | `GO-PROMOTION` |
| `DevmainInvocationTests._devmain_argv` L100 `assertTrue` | `devmain_argv` | `GO-PROMOTION` |
| `DevmainInvocationTests.test_creates_a_pull_request` L105 `assertEqual` | `creates_a_pull_request` | `GO-PROMOTION` |
| `DevmainInvocationTests.test_promotes_dev_into_main` L111 `assertIn` | `promotes_dev_into_main` | `GO-PROMOTION` |
| `DevmainInvocationTests.test_promotes_dev_into_main` L112 `assertEqual` | `promotes_dev_into_main` | `GO-PROMOTION` |
| `DevmainInvocationTests.test_promotes_dev_into_main` L113 `assertIn` | `promotes_dev_into_main` | `GO-PROMOTION` |
| `DevmainInvocationTests.test_promotes_dev_into_main` L114 `assertEqual` | `promotes_dev_into_main` | `GO-PROMOTION` |
| `DevmainInvocationTests.test_title_is_the_deterministic_non_releasing_subject` L118 `assertIn` | `title_is_the_deterministic_non_releasing_subject` | `GO-PROMOTION` |
| `DevmainInvocationTests.test_title_is_the_deterministic_non_releasing_subject` L120 `assertEqual` | `title_is_the_deterministic_non_releasing_subject` | `GO-PROMOTION` |
| `DevmainInvocationTests.test_title_is_the_deterministic_non_releasing_subject` L122 `assertNotEqual` | `title_is_the_deterministic_non_releasing_subject` | `GO-PROMOTION` |
| `DevmainInvocationTests.test_title_is_the_deterministic_non_releasing_subject` L125 `assertRegex` | `title_is_the_deterministic_non_releasing_subject` | `GO-PROMOTION` |
| `DevmainInvocationTests.test_title_is_the_deterministic_non_releasing_subject` L127 `assertNotIn` | `title_is_the_deterministic_non_releasing_subject` | `GO-PROMOTION` |
| `DevmainInvocationTests.test_body_tells_the_merger_not_to_squash` L131 `assertIn` | `body_tells_the_merger_not_to_squash` | `GO-PROMOTION` |
| `DevmainInvocationTests.test_body_tells_the_merger_not_to_squash` L133 `assertTrue` | `body_tells_the_merger_not_to_squash` | `GO-PROMOTION` |
| `DevmainInvocationTests.test_body_tells_the_merger_not_to_squash` L135 `assertIn` | `body_tells_the_merger_not_to_squash` | `GO-PROMOTION` |
| `DevmainInvocationTests.test_body_tells_the_merger_not_to_squash` L136 `assertRegex` | `body_tells_the_merger_not_to_squash` | `GO-PROMOTION` |
| `DevmainInvocationTests.test_body_tells_the_merger_not_to_squash` L140 `assertIn` | `body_tells_the_merger_not_to_squash` | `GO-PROMOTION` |
| `DevmainInvocationTests.test_does_not_delegate_the_body_to_the_template_or_an_editor` L150 `assertNotIn` | `does_not_delegate_the_body_to_the_template_or_an_editor` | `GO-PROMOTION` |
| `DevmainInvocationTests.test_opens_the_pr_and_nothing_else` L157 `assertNotIn` | `opens_the_pr_and_nothing_else` | `GO-PROMOTION` |
| `DevmainInvocationTests.test_opens_the_pr_and_nothing_else` L158 `assertNotIn` | `opens_the_pr_and_nothing_else` | `GO-PROMOTION` |
| `DevmainInvocationTests.test_opens_the_pr_and_nothing_else` L159 `assertNotIn` | `opens_the_pr_and_nothing_else` | `GO-PROMOTION` |
| `MakefileSafetyTests.test_bare_make_does_not_open_a_pull_request` L172 `assertEqual` | `bare_make_does_not_open_a_pull_request` | `GO-PROMOTION` |
| `MakefileSafetyTests.test_bare_make_does_not_open_a_pull_request` L176 `assertEqual` | `bare_make_does_not_open_a_pull_request` | `GO-PROMOTION` |
| `MakefileSafetyTests.test_gh_failure_fails_the_target` L186 `assertNotEqual` | `gh_failure_fails_the_target` | `GO-PROMOTION` |
| `MakefileSafetyTests.test_go_platform_discovery_failure_stops_gates` L202 `assertNotEqual` | `go_platform_discovery_failure_stops_gates` | `GO-PLATFORMS` |
| `MakefileSafetyTests.test_go_security_checks_every_platform` L216 `assertEqual` | `go_security_checks_every_platform` | `GO-PLATFORMS` |
| `MakefileSafetyTests.test_go_security_checks_every_platform` L217 `assertEqual` | `go_security_checks_every_platform` | `GO-PLATFORMS` |
| `MakefileStaticTests.setUp` L223 `assertTrue` | `setUp` | `make.safety` |
| `MakefileStaticTests.test_targets_are_phony` L228 `assertIn` | `targets_are_phony` | `make.safety` |
| `MakefileStaticTests.test_targets_are_phony` L229 `assertIn` | `targets_are_phony` | `make.safety` |
| `MakefileStaticTests.test_declares_a_safe_default_goal` L233 `assertIsNotNone` | `declares_a_safe_default_goal` | `make.safety` |
| `MakefileStaticTests.test_declares_a_safe_default_goal` L234 `assertNotEqual` | `declares_a_safe_default_goal` | `make.safety` |
| `MakefileStaticTests.test_gh_is_overridable_for_testing` L240 `assertIsNotNone` | `gh_is_overridable_for_testing` | `make.safety` |
| `MakefileStaticTests.test_devmain_recipe_does_not_suppress_failure` L249 `assertIsNotNone` | `devmain_recipe_does_not_suppress_failure` | `make.safety` |
| `MakefileStaticTests.test_devmain_recipe_does_not_suppress_failure` L251 `assertNotIn` | `devmain_recipe_does_not_suppress_failure` | `make.safety` |
| `MakefileStaticTests.test_devmain_recipe_does_not_suppress_failure` L252 `assertNotIn` | `devmain_recipe_does_not_suppress_failure` | `make.safety` |
| `MakefileStaticTests.test_devmain_recipe_does_not_suppress_failure` L254 `assertFalse` | `devmain_recipe_does_not_suppress_failure` | `make.safety` |
| `MakefileStaticTests.test_no_owner_or_repository_is_hardcoded` L263 `assertNotIn` | `no_owner_or_repository_is_hardcoded` | `make.safety` |
| `MakefileStaticTests.test_no_owner_or_repository_is_hardcoded` L264 `assertNotIn` | `no_owner_or_repository_is_hardcoded` | `make.safety` |

## test_ground_control_review_config.py

| Source assertion | Invariant | Replacement and evidence |
| --- | --- | --- |
| `_IntPinAssertions.assertIntPin` L48 `assertNotIsInstance` | `assertIntPin` | `review.values` |
| `_IntPinAssertions.assertIntPin` L53 `assertIsInstance` | `assertIntPin` | `review.values` |
| `_IntPinAssertions.assertIntPin` L54 `assertEqual` | `assertIntPin` | `review.values` |
| `PrePushReviewCapTests.test_codex_review_cap_is_pinned_to_one` L65 `assertIsInstance` | `codex_review_cap_is_pinned_to_one` | `review.values` |
| `PrePushReviewCapTests.test_codex_review_cap_is_pinned_to_one` L71 `assertIntPin` | `codex_review_cap_is_pinned_to_one` | `review.values` |
| `ReviewDispositionTests.setUp` L82 `assertIsInstance` | `setUp` | `review.values` |
| `ReviewDispositionTests.test_automatic_disposition_is_disabled` L90 `assertIs` | `automatic_disposition_is_disabled` | `review.values` |
| `ReviewDispositionTests.test_mode_remains_shadow` L97 `assertEqual` | `mode_remains_shadow` | `review.values` |
| `ReviewDispositionTests.test_no_automatic_overrides_are_granted` L102 `assertIntPin` | `no_automatic_overrides_are_granted` | `review.values` |
| `ReviewDispositionTests.test_judge_does_not_participate` L109 `assertIsInstance` | `judge_does_not_participate` | `review.values` |
| `ReviewDispositionTests.test_judge_does_not_participate` L110 `assertIs` | `judge_does_not_participate` | `review.values` |
| `ReviewConfigPlacementTests.test_retired_test_quality_review_key_is_absent` L116 `assertNotIn` | `retired_test_quality_review_key_is_absent` | `review.values` |
| `ReviewConfigPlacementTests.test_review_keys_live_under_workflow` L129 `assertNotIn` | `review_keys_live_under_workflow` | `review.values` |
| `RepositoryBoundaryPlanRuleTests.test_plan_rules_include_first_party_content_charter` L139 `assertIn` | `plan_rules_include_first_party_content_charter` | `review.values` |
| `RepositoryBoundaryPlanRuleTests.test_plan_rules_include_first_party_content_charter` L140 `assertIn` | `plan_rules_include_first_party_content_charter` | `review.values` |
| `RepositoryBoundaryPlanRuleTests.test_plan_rules_include_first_party_content_charter` L141 `assertNotIn` | `plan_rules_include_first_party_content_charter` | `review.values` |
| `GoWorkflowBaseTests.test_issue_workflows_target_the_go_integration_branch` L146 `assertEqual` | `issue_workflows_target_the_go_integration_branch` | `review.values` |

## test_ci_topology.py

| Source assertion | Invariant | Replacement and evidence |
| --- | --- | --- |
| `AggregateGateTests.test_required_context_still_exists` L102 `assertIn` | `required_context_still_exists` | `ci.aggregate` |
| `AggregateGateTests.test_the_split_actually_happened` L113 `assertIn` | `the_split_actually_happened` | `ci.aggregate` |
| `AggregateGateTests.test_verify_gates_exactly_the_mandatory_set` L122 `assertEqual` | `verify_gates_exactly_the_mandatory_set` | `ci.aggregate` |
| `AggregateGateTests.test_verify_gates_exactly_the_mandatory_set` L127 `assertNotIn` | `verify_gates_exactly_the_mandatory_set` | `ci.aggregate` |
| `AggregateGateTests.test_verify_runs_even_when_a_dependency_fails` L135 `assertIn` | `verify_runs_even_when_a_dependency_fails` | `ci.aggregate` |
| `AggregateGateTests.test_verify_env_references_every_mandatory_result` L145 `assertEqual` | `verify_env_references_every_mandatory_result` | `ci.aggregate` |
| `AggregateGateTests.test_verify_gate_script_blocks_on_each_mandatory_failure` L163 `assertTrue` | `verify_gate_script_blocks_on_each_mandatory_failure` | `GO-AGGREGATE` |
| `AggregateGateTests.test_verify_gate_script_blocks_on_each_mandatory_failure` L175 `assertEqual` | `verify_gate_script_blocks_on_each_mandatory_failure` | `GO-AGGREGATE` |
| `AggregateGateTests.test_verify_gate_script_blocks_on_each_mandatory_failure` L187 `assertNotEqual` | `verify_gate_script_blocks_on_each_mandatory_failure` | `GO-AGGREGATE` |
| `JobIndependenceTests.test_mandatory_jobs_have_no_cross_dependencies` L203 `assertEqual` | `mandatory_jobs_have_no_cross_dependencies` | `ci.independence` |
| `JobIndependenceTests.test_sonar_depends_only_on_the_coverage_producers` L211 `assertEqual` | `sonar_depends_only_on_the_coverage_producers` | `ci.coverage` |
| `CoverageAuthorityTests.test_the_unit_suite_is_discovered_exactly_once` L235 `assertEqual` | `the_unit_suite_is_discovered_exactly_once` | `ci.coverage` |
| `CoverageAuthorityTests.test_tests_job_is_the_coverage_authority` L243 `assertIn` | `tests_job_is_the_coverage_authority` | `ci.coverage` |
| `CoverageAuthorityTests.test_tests_job_is_the_coverage_authority` L244 `assertIn` | `tests_job_is_the_coverage_authority` | `ci.coverage` |
| `CoverageAuthorityTests.test_tests_job_is_the_coverage_authority` L248 `assertIn` | `tests_job_is_the_coverage_authority` | `ci.coverage` |
| `CoverageAuthorityTests.test_sonar_consumes_the_artifact_and_does_not_rerun_the_suite` L256 `assertIn` | `sonar_consumes_the_artifact_and_does_not_rerun_the_suite` | `ci.coverage` |
| `CoverageAuthorityTests.test_sonar_consumes_the_artifact_and_does_not_rerun_the_suite` L260 `assertNotIn` | `sonar_consumes_the_artifact_and_does_not_rerun_the_suite` | `ci.coverage` |
| `CoverageAuthorityTests.test_sonar_consumes_the_artifact_and_does_not_rerun_the_suite` L265 `assertNotIn` | `sonar_consumes_the_artifact_and_does_not_rerun_the_suite` | `ci.coverage` |
| `CoverageAuthorityTests.test_go_job_hands_its_coverage_profile_to_sonar` L272 `assertEqual` | `go_job_hands_its_coverage_profile_to_sonar` | `ci.coverage` |
| `CoverageAuthorityTests.test_go_job_hands_its_coverage_profile_to_sonar` L280 `assertIn` | `go_job_hands_its_coverage_profile_to_sonar` | `ci.coverage` |
| `CoverageAuthorityTests.test_go_job_hands_its_coverage_profile_to_sonar` L281 `assertNotIn` | `go_job_hands_its_coverage_profile_to_sonar` | `ci.coverage` |
| `GateCompletenessTests.test_every_verification_command_survives_the_split` L303 `assertIn` | `every_verification_command_survives_the_split` | `ci.completeness` |
| `GateCompletenessTests.test_pip_audit_population_is_not_narrowed` L317 `assertIn` | `pip_audit_population_is_not_narrowed` | `ci.completeness` |
| `SecretEligibilityTests.test_sonar_still_skips_fork_and_dependabot_prs` L332 `assertIn` | `sonar_still_skips_fork_and_dependabot_prs` | `ci.secrets` |
| `SecretEligibilityTests.test_sonar_still_skips_fork_and_dependabot_prs` L333 `assertIn` | `sonar_still_skips_fork_and_dependabot_prs` | `ci.secrets` |
| `SecretEligibilityTests.test_sonar_still_skips_fork_and_dependabot_prs` L334 `assertIn` | `sonar_still_skips_fork_and_dependabot_prs` | `ci.secrets` |
| `SecretEligibilityTests.test_sonar_token_is_passed_by_environment_not_argv` L343 `assertTrue` | `sonar_token_is_passed_by_environment_not_argv` | `ci.secrets` |
| `SecretEligibilityTests.test_sonar_token_is_passed_by_environment_not_argv` L349 `assertNotIn` | `sonar_token_is_passed_by_environment_not_argv` | `ci.secrets` |
| `CachingTests.test_installing_jobs_cache_pip_keyed_on_locks` L370 `assertTrue` | `installing_jobs_cache_pip_keyed_on_locks` | `ci.cache` |
| `CachingTests.test_installing_jobs_cache_pip_keyed_on_locks` L372 `assertEqual` | `installing_jobs_cache_pip_keyed_on_locks` | `ci.cache` |
| `CachingTests.test_installing_jobs_cache_pip_keyed_on_locks` L377 `assertIn` | `installing_jobs_cache_pip_keyed_on_locks` | `ci.cache` |

## test_pack_distribution_workflow.py

| Source assertion | Invariant | Replacement and evidence |
| --- | --- | --- |
| `DistributionWorkflowContractTests.test_manually_triggered_only` L48 `assertIn` | `manually_triggered_only` | `distribution.workflow` |
| `DistributionWorkflowContractTests.test_top_level_permissions_are_read_only` L52 `assertEqual` | `top_level_permissions_are_read_only` | `distribution.workflow` |
| `DistributionWorkflowContractTests.test_job_keeps_oidc_and_stays_least_privilege` L56 `assertEqual` | `job_keeps_oidc_and_stays_least_privilege` | `distribution.workflow` |
| `DistributionWorkflowContractTests.test_job_keeps_oidc_and_stays_least_privilege` L58 `assertEqual` | `job_keeps_oidc_and_stays_least_privilege` | `distribution.workflow` |
| `DistributionWorkflowContractTests.test_registry_service_is_present` L63 `assertTrue` | `registry_service_is_present` | `distribution.workflow` |
| `DistributionWorkflowContractTests.test_signing_and_transport_tools_are_sha_pinned` L69 `assertIsNotNone` | `signing_and_transport_tools_are_sha_pinned` | `distribution.workflow + workflow.action-pins` |
| `DistributionWorkflowContractTests.test_signing_and_transport_tools_are_sha_pinned` L71 `assertRegex` | `signing_and_transport_tools_are_sha_pinned` | `distribution.workflow + workflow.action-pins` |
| `DistributionWorkflowContractTests.test_every_action_is_sha_pinned` L76 `assertRegex` | `every_action_is_sha_pinned` | `distribution.workflow + workflow.action-pins` |
| `DistributionWorkflowContractTests.test_pip_installs_are_pinned` L83 `assertTrue` | `pip_installs_are_pinned` | `dependency.pip-pins` |
| `DistributionWorkflowContractTests.test_rehearsal_runs_after_tools_are_installed` L98 `assertGreaterEqual` | `rehearsal_runs_after_tools_are_installed` | `distribution.workflow` |
| `DistributionWorkflowContractTests.test_rehearsal_runs_after_tools_are_installed` L99 `assertLess` | `rehearsal_runs_after_tools_are_installed` | `distribution.workflow` |
| `DistributionWorkflowContractTests.test_rehearsal_runs_after_tools_are_installed` L100 `assertLess` | `rehearsal_runs_after_tools_are_installed` | `distribution.workflow` |
| `DistributionWorkflowContractTests.test_rehearsal_step_passes_the_pack_input_through_env` L104 `assertEqual` | `rehearsal_step_passes_the_pack_input_through_env` | `distribution.workflow` |
| `DistributionWorkflowContractTests.test_rehearsal_step_passes_the_pack_input_through_env` L106 `assertEqual` | `rehearsal_step_passes_the_pack_input_through_env` | `distribution.workflow` |
| `DistributionWorkflowContractTests.test_no_run_body_interpolates_an_expression` L113 `assertNotIn` | `no_run_body_interpolates_an_expression` | `distribution.workflow` |

## test_ownership_boundary_doc.py

| Source assertion | Invariant | Replacement and evidence |
| --- | --- | --- |
| `OwnershipBoundaryDocTests.test_doc_exists` L84 `assertTrue` | `doc_exists` | `ownership.boundary` |
| `OwnershipBoundaryDocTests.test_names_four_distinct_owners` L89 `assertIn` | `names_four_distinct_owners` | `ownership.boundary` |
| `OwnershipBoundaryDocTests.test_names_four_distinct_owners` L90 `assertIn` | `names_four_distinct_owners` | `ownership.boundary` |
| `OwnershipBoundaryDocTests.test_each_owner_keeps_its_responsibilities` L100 `assertIn` | `each_owner_keeps_its_responsibilities` | `ownership.boundary` |
| `OwnershipBoundaryDocTests.test_aptl_and_lilrae_are_one_project_across_a_rename` L106 `assertIn` | `aptl_and_lilrae_are_one_project_across_a_rename` | `ownership.boundary` |
| `OwnershipBoundaryDocTests.test_format_owner_can_host_selected_packs_without_owning_semantics` L115 `assertIn` | `format_owner_can_host_selected_packs_without_owning_semantics` | `ownership.boundary` |
| `OwnershipBoundaryDocTests.test_format_owner_can_host_selected_packs_without_owning_semantics` L119 `assertIn` | `format_owner_can_host_selected_packs_without_owning_semantics` | `ownership.boundary` |
| `OwnershipBoundaryDocTests.test_pack_cannot_select_runtime_implementation` L125 `assertIn` | `pack_cannot_select_runtime_implementation` | `ownership.boundary` |
| `OwnershipBoundaryDocTests.test_pack_cannot_select_runtime_implementation` L128 `assertIn` | `pack_cannot_select_runtime_implementation` | `ownership.boundary` |
| `OwnershipBoundaryDocTests.test_scenario_owner_scope_stays_at_the_portable_boundary` L137 `assertIn` | `scenario_owner_scope_stays_at_the_portable_boundary` | `ownership.boundary` |
| `OwnershipBoundaryDocTests.test_links_the_lilrae_projects_aptl_era_ownership_record` L144 `assertIn` | `links_the_lilrae_projects_aptl_era_ownership_record` | `ownership.boundary` |
| `OwnershipBoundaryDocTests.test_links_the_lilrae_projects_aptl_era_ownership_record` L148 `assertIn` | `links_the_lilrae_projects_aptl_era_ownership_record` | `ownership.boundary` |
| `OwnershipBoundaryDocTests.test_techvault_is_only_a_scenario_pack` L155 `assertIn` | `techvault_is_only_a_scenario_pack` | `ownership.pack` |
| `OwnershipBoundaryDocTests.test_techvault_is_only_a_scenario_pack` L156 `assertIn` | `techvault_is_only_a_scenario_pack` | `ownership.pack` |
| `OwnershipBoundaryDocTests.test_reachable_from_the_pack_definition` L163 `assertIn` | `reachable_from_the_pack_definition` | `ownership.navigation` |

## test_pr_title_guard.py

| Source assertion | Invariant | Replacement and evidence |
| --- | --- | --- |
| `PrTitleGuardTests.test_valid_conventional_titles_pass` L54 `assertEqual` | `valid_conventional_titles_pass` | `TITLE-VALIDATOR` |
| `PrTitleGuardTests.test_branded_prefixes_rejected` L59 `assertIn` | `branded_prefixes_rejected` | `TITLE-VALIDATOR` |
| `PrTitleGuardTests.test_tool_name_later_in_subject_is_allowed` L62 `assertEqual` | `tool_name_later_in_subject_is_allowed` | `TITLE-VALIDATOR` |
| `PrTitleGuardTests.test_non_conventional_rejected` L67 `assertIn` | `non_conventional_rejected` | `TITLE-VALIDATOR` |
| `PrTitleGuardTests.test_uppercase_subject_rejected` L70 `assertIn` | `uppercase_subject_rejected` | `TITLE-VALIDATOR` |
| `PrTitleGuardTests.test_empty_rejected` L73 `assertIn` | `empty_rejected` | `TITLE-VALIDATOR` |
| `PrTitleGuardTests.test_main_accepts_via_title_arg` L76 `assertEqual` | `main_accepts_via_title_arg` | `TITLE-VALIDATOR` |
| `PrTitleGuardTests.test_main_rejects_via_title_arg` L79 `assertEqual` | `main_rejects_via_title_arg` | `TITLE-VALIDATOR` |
| `PrTitleGuardTests.test_event_path_validates_human_titles` L88 `assertEqual` | `event_path_validates_human_titles` | `TITLE-VALIDATOR` |
| `PrTitleGuardTests.test_event_path_validates_human_titles` L89 `assertEqual` | `event_path_validates_human_titles` | `TITLE-VALIDATOR` |
| `PrTitleGuardTests.test_bot_authors_are_exempt` L94 `assertEqual` | `bot_authors_are_exempt` | `TITLE-VALIDATOR` |

## test_raes_identity.py

| Source assertion | Invariant | Replacement and evidence |
| --- | --- | --- |
| `PackageIdentityTests.test_distribution_import_tree_and_scripts_use_one_identity` L109 `assertEqual` | `distribution_import_tree_and_scripts_use_one_identity` | `PY-IDENTITY` |
| `PackageIdentityTests.test_distribution_import_tree_and_scripts_use_one_identity` L110 `assertTrue` | `distribution_import_tree_and_scripts_use_one_identity` | `PY-IDENTITY` |
| `PackageIdentityTests.test_distribution_import_tree_and_scripts_use_one_identity` L111 `assertFalse` | `distribution_import_tree_and_scripts_use_one_identity` | `PY-IDENTITY` |
| `PackageIdentityTests.test_distribution_import_tree_and_scripts_use_one_identity` L112 `assertEqual` | `distribution_import_tree_and_scripts_use_one_identity` | `PY-IDENTITY` |
| `PackageIdentityTests.test_raes_is_the_single_upstream_floor` L137 `assertEqual` | `raes_is_the_single_upstream_floor` | `PY-IDENTITY` |
| `PackageIdentityTests.test_raes_is_the_single_upstream_floor` L138 `assertRegex` | `raes_is_the_single_upstream_floor` | `PY-IDENTITY` |
| `PackageIdentityTests.test_raes_is_the_single_upstream_floor` L139 `assertFalse` | `raes_is_the_single_upstream_floor` | `PY-IDENTITY` |
| `PackageIdentityTests.test_raes_is_the_single_upstream_floor` L147 `assertEqual` | `raes_is_the_single_upstream_floor` | `PY-IDENTITY` |
| `PackContractIdentityTests.test_pack_owned_contracts_advance_together` L159 `assertEqual` | `pack_owned_contracts_advance_together` | `GO-IDENTITY` |
| `PackContractIdentityTests.test_pack_owned_contracts_advance_together` L163 `assertEqual` | `pack_owned_contracts_advance_together` | `GO-IDENTITY` |
| `PackContractIdentityTests.test_pack_owned_contracts_advance_together` L167 `assertEqual` | `pack_owned_contracts_advance_together` | `GO-IDENTITY` |
| `PackContractIdentityTests.test_pack_owned_contracts_advance_together` L171 `assertEqual` | `pack_owned_contracts_advance_together` | `GO-IDENTITY` |
| `PackContractIdentityTests.test_pack_owned_contracts_advance_together` L179 `assertIn` | `pack_owned_contracts_advance_together` | `GO-IDENTITY` |
| `PackContractIdentityTests.test_pack_owned_contracts_advance_together` L182 `assertIn` | `pack_owned_contracts_advance_together` | `GO-IDENTITY` |
| `PackContractIdentityTests.test_current_surfaces_use_the_raes_lockfile_name` L185 `assertEqual` | `current_surfaces_use_the_raes_lockfile_name` | `GO-IDENTITY` |
| `PackContractIdentityTests.test_current_surfaces_use_the_raes_lockfile_name` L195 `assertIn` | `current_surfaces_use_the_raes_lockfile_name` | `GO-IDENTITY` |
| `PackContractIdentityTests.test_current_surfaces_use_the_raes_lockfile_name` L196 `assertNotIn` | `current_surfaces_use_the_raes_lockfile_name` | `GO-IDENTITY` |
| `PackContractIdentityTests.test_release_please_tracks_the_new_distribution` L202 `assertEqual` | `release_please_tracks_the_new_distribution` | `GO-IDENTITY` |
| `RepositoryIdentityTests.test_current_surfaces_do_not_reintroduce_retired_names` L221 `assertEqual` | `current_surfaces_do_not_reintroduce_retired_names` | `GO-RETIRED-IDENTITY` |
| `RepositoryIdentityTests.test_current_surfaces_do_not_reintroduce_retired_names` L231 `assertEqual` | `current_surfaces_do_not_reintroduce_retired_names` | `GO-RETIRED-IDENTITY` |
| `RepositoryIdentityTests.test_ground_control_and_sonar_use_their_bound_project_identities` L242 `assertEqual` | `ground_control_and_sonar_use_their_bound_project_identities` | `GO-BOUND-IDENTITY` |
| `RepositoryIdentityTests.test_ground_control_and_sonar_use_their_bound_project_identities` L243 `assertEqual` | `ground_control_and_sonar_use_their_bound_project_identities` | `GO-BOUND-IDENTITY` |
| `RepositoryIdentityTests.test_ground_control_and_sonar_use_their_bound_project_identities` L244 `assertEqual` | `ground_control_and_sonar_use_their_bound_project_identities` | `GO-BOUND-IDENTITY` |
| `RepositoryIdentityTests.test_ground_control_and_sonar_use_their_bound_project_identities` L248 `assertEqual` | `ground_control_and_sonar_use_their_bound_project_identities` | `GO-BOUND-IDENTITY` |
| `RepositoryIdentityTests.test_ground_control_and_sonar_use_their_bound_project_identities` L252 `assertEqual` | `ground_control_and_sonar_use_their_bound_project_identities` | `GO-BOUND-IDENTITY` |
| `RepositoryIdentityTests.test_ground_control_and_sonar_use_their_bound_project_identities` L261 `assertIn` | `ground_control_and_sonar_use_their_bound_project_identities` | `GO-BOUND-IDENTITY` |
| `RepositoryIdentityTests.test_ground_control_and_sonar_use_their_bound_project_identities` L262 `assertIn` | `ground_control_and_sonar_use_their_bound_project_identities` | `GO-BOUND-IDENTITY` |

## test_concept_authority_alignment.py

| Source assertion | Invariant | Replacement and evidence |
| --- | --- | --- |
| `ProvenanceSourceKindRemovedTests.setUp` L128 `assertIsInstance` | `setUp` | `GO-PROVENANCE` |
| `ProvenanceSourceKindRemovedTests._source_item_schema` L133 `assertIsInstance` | `source_item_schema` | `GO-PROVENANCE` |
| `ProvenanceSourceKindRemovedTests.test_source_kind_property_is_gone` L139 `assertNotIn` | `source_kind_property_is_gone` | `GO-PROVENANCE` |
| `ProvenanceSourceKindRemovedTests.test_source_kind_is_not_required` L146 `assertNotIn` | `source_kind_is_not_required` | `GO-PROVENANCE` |
| `ProvenanceSourceKindRemovedTests.test_source_kind_is_rejected_as_unknown` L151 `assertIs` | `source_kind_is_rejected_as_unknown` | `GO-PROVENANCE` |
| `ConceptAuthorityRestatementTests.test_no_schema_restates_aces_tactic_vocabulary` L160 `assertTrue` | `no_schema_restates_aces_tactic_vocabulary` | `GO-CONCEPT` |
| `ConceptAuthorityRestatementTests.test_no_schema_restates_aces_tactic_vocabulary` L167 `assertEqual` | `no_schema_restates_aces_tactic_vocabulary` | `GO-CONCEPT` |
| `ConceptAuthorityRestatementTests.test_no_schema_restates_aces_tactic_vocabulary` L171 `assertEqual` | `no_schema_restates_aces_tactic_vocabulary` | `GO-CONCEPT` |
| `ConceptAuthorityRestatementTests.test_authority_is_referenced_in_schema_contract_and_docs` L179 `assertTrue` | `authority_is_referenced_in_schema_contract_and_docs` | `GO-AUTHORITY` |
| `ConceptAuthorityRestatementTests.test_authority_is_referenced_in_schema_contract_and_docs` L180 `assertIn` | `authority_is_referenced_in_schema_contract_and_docs` | `GO-AUTHORITY` |
| `ChallengeCategoryTemplateTests.test_template_challenges_declare_no_category` L192 `assertNotIn` | `template_challenges_declare_no_category` | `GO-CHALLENGES` |
| `ChallengeCategoryGuardTests.test_category_is_rejected_at_exact_path` L213 `assertTrue` | `category_is_rejected_at_exact_path` | `CONFORMANCE-CATEGORY` |
| `ChallengeCategoryGuardTests.test_category_free_challenges_carry_no_forbidden_code` L221 `assertFalse` | `category_free_challenges_carry_no_forbidden_code` | `CONFORMANCE-CATEGORY` |

## test_provenance_raes_alignment.py

| Source assertion | Invariant | Replacement and evidence |
| --- | --- | --- |
| `ProvenanceAcesAlignmentTests.setUp` L107 `assertIsInstance` | `setUp` | `GO-PROVENANCE` |
| `ProvenanceAcesAlignmentTests.test_schema_references_aces_trust_authority` L112 `assertIn` | `schema_references_aces_trust_authority` | `GO-PROVENANCE` |
| `ProvenanceAcesAlignmentTests.test_schema_references_aces_trust_authority` L114 `assertTrue` | `schema_references_aces_trust_authority` | `GO-PROVENANCE` |
| `ProvenanceAcesAlignmentTests.test_schema_documents_field_disposition` L121 `assertIsInstance` | `schema_documents_field_disposition` | `GO-PROVENANCE` |
| `ProvenanceAcesAlignmentTests.test_schema_documents_field_disposition` L124 `assertIn` | `schema_documents_field_disposition` | `GO-PROVENANCE` |
| `ProvenanceAcesAlignmentTests.test_schema_does_not_redefine_aces_evidence_classes` L131 `assertEqual` | `schema_does_not_redefine_aces_evidence_classes` | `GO-PROVENANCE` |
| `ProvenanceAcesAlignmentTests.test_contract_and_docs_reference_aces_policy` L141 `assertTrue` | `contract_and_docs_reference_aces_policy` | `GO-PROVENANCE` |
| `ProvenanceAcesAlignmentTests.test_contract_and_docs_reference_aces_policy` L142 `assertIn` | `contract_and_docs_reference_aces_policy` | `GO-PROVENANCE` |
| `ProvenanceAcesAlignmentTests.test_example_ledger_still_validates` L148 `assertIsInstance` | `example_ledger_still_validates` | `GO-PROVENANCE` |
| `ProvenanceAcesAlignmentTests.test_example_ledger_still_validates` L151 `assertEqual` | `example_ledger_still_validates` | `GO-PROVENANCE` |
| `ProvenanceAcesAlignmentTests.test_template_ledger_parses_and_references_aces` L156 `assertTrue` | `template_ledger_parses_and_references_aces` | `GO-PROVENANCE` |
| `ProvenanceAcesAlignmentTests.test_template_ledger_parses_and_references_aces` L158 `assertIsInstance` | `template_ledger_parses_and_references_aces` | `GO-PROVENANCE` |
| `ProvenanceAcesAlignmentTests.test_template_ledger_parses_and_references_aces` L159 `assertIn` | `template_ledger_parses_and_references_aces` | `GO-PROVENANCE` |

## Rego fixture index

| Rule | Rejected fixture names |
| --- | --- |
| `ci.aggregate` | `ci.aggregate/jobs.verify.needs`; `ci.aggregate/jobs.verify.if`; `ci.aggregate/jobs.new-mandatory`; `ci.aggregate/jobs.verify.steps.0.env` |
| `ci.cache` | `ci.cache/jobs.tests.steps.1.with.cache`; `ci.cache/jobs.audit.steps.1.with.cache`; `ci.cache/jobs.content.steps.1.with.cache` |
| `ci.completeness` | `ci.completeness/pip-audit`; `ci.completeness/raes-pack-validate`; `ci.completeness/raes-pack-release`; `ci.completeness/compileall src tests` |
| `ci.coverage` | `ci.coverage/jobs.sonar.needs`; `ci.coverage/coverage run`; `ci.coverage/coverage xml`; `ci.coverage/actions/upload-artifact@`; `ci.coverage/actions/download-artifact@` |
| `ci.independence` | `ci.independence/jobs.tests.needs` |
| `ci.secrets` | `ci.secrets/jobs.sonar.if`; `ci.secrets/jobs.sonar.steps.3.env`; `ci.secrets/jobs.tests.steps.0.run` |
| `codeql.analysis` | `codeql.analysis/permissions`; `codeql.analysis/jobs.analyze.permissions`; `codeql.analysis/jobs.analyze.strategy.matrix.include`; `codeql.analysis/concurrency.cancel-in-progress`; `codeql.analysis/actions/setup-go@`; `codeql.analysis/github/codeql-action/init@`; `codeql.analysis/github/codeql-action/analyze@`; `codeql.analysis/paths-ignore` |
| `codeql.triggers` | `codeql.triggers/branches`; `codeql.triggers/schedule` |
| `dependency.co-installed` | `dependency.co-installed/conflicting` |
| `dependency.floors` | `dependency.floors/certifi` |
| `dependency.lock-files` | `dependency.lock-files/unhashed` |
| `dependency.pip-pins` | `dependency.pip-pins/unpinned`; `dynamic editable source` |
| `dependency.references` | `dependency.references/missing` |
| `dependency.update-owners` | `dependency.update-owners/updates` |
| `distribution.workflow` | `distribution.workflow/permissions`; `distribution.workflow/on.workflow_dispatch.inputs.pack.default`; `distribution.workflow/jobs.rehearse.permissions.contents`; `distribution.workflow/jobs.rehearse.permissions.id-token`; `distribution.workflow/jobs.rehearse.services.registry.image`; `distribution.workflow/sigstore/cosign-installer@`; `distribution.workflow/oras-project/setup-oras@`; `distribution.workflow/distribution_rehearsal.py`; `distribution.workflow/interpolation` |
| `docs.badges` | `docs.badges/rtd` |
| `docs.configuration` | `docs.configuration/sphinx.configuration`; `docs.configuration/sphinx.fail_on_warning`; `docs.configuration/python.install`; `docs.configuration/build.os`; `docs.configuration/build.tools.python`; `docs.configuration/version`; `docs.configuration/sphinx-conf` |
| `docs.navigation` | `docs.navigation/docs/README.md`; `docs.navigation/CONTRIBUTING.md`; `docs.navigation/docs/public/index.md` |
| `docs.public-boundary` | `docs.public-boundary/escape`; `docs.public-boundary/internal`; `public empty decisions directory`; `public padded internal link` |
| `gate.same-command` | `gate.same-command/workflow.policy_command` |
| `make.safety` | `make.safety/default` |
| `ownership.boundary` | `ownership.boundary/missing` |
| `ownership.navigation` | `ownership.navigation/missing` |
| `ownership.pack` | `ownership.pack/missing` |
| `release.authorization` | `release.authorization/jobs.release-please.if`; `release.authorization/jobs.resume-release-please.if`; `release.authorization/jobs.publish.if`; `release.authorization/release_tag_gate.py` |
| `release.no-force` | `release.no-force/jobs.publish.steps.0.run` |
| `release.order` | `release.order/gitsign_${GITSIGN_VERSION_PIN}_linux_amd64`; `release.order/git tag -s`; `release.order/gh release create`; `release.order/gh release upload`; `release.order/actions/attest-build-provenance@`; `release.order/pypa/gh-action-pypi-publish@` |
| `release.permissions` | `release.permissions/jobs.release-please.permissions`; `release.permissions/jobs.resume-release-please.permissions`; `release.permissions/jobs.detect-release.permissions`; `release.permissions/jobs.publish.permissions` |
| `release.recovery` | `release.recovery/git cat-file tag`; `release.recovery/git cat-file -e "${TARGET_SHA}:requirements/build.txt"` |
| `release.rerun` | `release.rerun/gh release create`; `release.rerun/pypa/gh-action-pypi-publish@`; `release.rerun/--add-label "autorelease: tagged"`; `release.rerun/tomllib` |
| `release.shape` | `release.shape/concurrency.group`; `release.shape/concurrency.cancel-in-progress`; `release.shape/on.push.branches`; `release.shape/on.workflow_dispatch.inputs.release_pr.required`; `release.shape/on.workflow_dispatch.inputs.release_pr.type` |
| `release.signed-target` | `release.signed-target/git tag -s`; `release.signed-target/jobs.publish.env.TARGET_SHA`; `release.signed-target/jobs.publish.steps.0.with.ref` |
| `release.signer` | `release.signer/env.CERT_IDENTITY`; `release.signer/env.CERT_OIDC_ISSUER`; `release.signer/env.GITSIGN_VERSION_PIN`; `release.signer/env.GITSIGN_SHA256`; `release.signer/env.GITSIGN_VERSION_FLOOR` |
| `release.subjects` | `release.subjects/jobs.publish.steps.9.with.subject-path` |
| `review.values` | `review.values/workflow.codex_review.pre_push_cap`; `review.values/workflow.review_disposition.enabled`; `review.values/workflow.review_disposition.max_auto_overrides`; `review.values/workflow.review_disposition.mode`; `review.values/workflow.review_disposition.judge.enabled`; `review.values/workflow.base_branch`; `review.values/workflow.test_quality_review`; `review.values/codex_review`; `review.values/charter` |
| `scorecard.publication` | `scorecard.publication/ossf/scorecard-action@`; `scorecard.publication/github/codeql-action/upload-sarif@`; `scorecard.publication/jobs.analysis.permissions.contents`; `scorecard.publication/jobs.analysis.steps.0.with.persist-credentials`; `scorecard.publication/badge`; `scorecard scope none` |
| `scorecard.triggers` | `scorecard.triggers/on.push.branches`; `scorecard.triggers/on.schedule`; `scorecard.triggers/concurrency.cancel-in-progress` |
| `title.workflow` | `title.workflow/jobs.pr-title-guard.steps.0.with.ref` |
| `workflow.action-pins` | `workflow.action-pins/jobs.tests.steps.0.uses` |
| `workflow.job-scopes` | `workflow.job-scopes/jobs.tests.permissions` |
| `workflow.no-merge` | `workflow.no-merge/jobs.tests.steps.0.run` |
| `workflow.permissions` | `workflow.permissions/None`; `workflow.permissions/write-all`; `workflow.permissions/{'contents': 'write'}`; `workflow.permissions/True`; `workflow.permissions/nonsense` |

## Common gate and transition checks

`make policy` runs Rego tests, real collection and evaluation, actionlint, and the targeted Go tests.
`TestPolicyGateStopsAtEachFailure` proves each stage stops subsequent stages.

The CI job and Ground Control both call this target; `gate.same-command` checks their binding.
Actionlint owns workflow syntax and expression checks. Rego owns repository decisions.
`TestRepositoryRAESImportBoundary` uses the actual architecture model: the adapter import passes, and imports from the collector or alignment component fail.
Python checks listed as retained continue to run in the existing Python suite.
Their subjects must retire or acquire an equivalent check before the cutover removes that suite.

The docs toolchain, publication boundary, signing identities, release authorization, tag recovery, and attestation survive the product cutover.
Release-subject assertions currently guard wheel and source distributions.
The distribution port must bind them to its actual Go subjects and preserve the ordering and authorization controls.
