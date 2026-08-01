# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

PRs do **not** edit this file directly. Add a fragment under
[`changelog.d/`](changelog.d/) instead; `towncrier build` collates fragments into
this file at release-prep. See [`changelog.d/README.md`](changelog.d/README.md).

<!-- towncrier release notes start -->

## [3.3.0](https://github.com/OpenRAE/env-packs/compare/v3.2.0...v3.3.0) (2026-08-01)


### Features

* require the compatibility-tested RAES 3.x runtime contract ([b7fafc4](https://github.com/OpenRAE/env-packs/commit/b7fafc444638bb71922ee9bedbad43a9b8fcecc4))
* require the compatibility-tested RAES 3.x runtime contract ([5ad5d9c](https://github.com/OpenRAE/env-packs/commit/5ad5d9c8c6cb2c78bb3357638ec4e91e7f7fab29)), closes [#217](https://github.com/OpenRAE/env-packs/issues/217)

## [3.2.0](https://github.com/OpenRAE/env-packs/compare/v3.1.0...v3.2.0) (2026-07-31)


### Features

* **catalog:** render pack cards and a machine-readable catalog index ([#206](https://github.com/OpenRAE/env-packs/issues/206)) ([58013af](https://github.com/OpenRAE/env-packs/commit/58013af7b8c34400e95e9515bc6ba161f38cbd7b))
* **consumer-api:** public single-open pack artifact resolver ([#209](https://github.com/OpenRAE/env-packs/issues/209)) ([f05338e](https://github.com/OpenRAE/env-packs/commit/f05338e392eba071e579df29f28933c4f31482d5))
* **scaffold:** replace the monolithic scaffold with a progressive wizard ([#211](https://github.com/OpenRAE/env-packs/issues/211)) ([2acc73a](https://github.com/OpenRAE/env-packs/commit/2acc73a378dd266209e3bd7128149043449e0130))

## [3.1.0](https://github.com/RAESystem/env-packs/compare/v3.0.0...v3.1.0) (2026-07-29)


### Features

* **cli:** add beginner-safe static pack check with actionable diagnostics ([#193](https://github.com/RAESystem/env-packs/issues/193)) ([2d8b29f](https://github.com/RAESystem/env-packs/commit/2d8b29ff2af6f3d20f3dbe0378856cf60cce7f9d))
* define the environment-pack publication profile for artifact satisfaction ([#184](https://github.com/RAESystem/env-packs/issues/184)) ([9af729d](https://github.com/RAESystem/env-packs/commit/9af729dc05b07d9aa39577231deb906db3b2e07c))


### Bug Fixes

* **issue-skeleton:** stop defaulting pack issues to env-packs ([#195](https://github.com/RAESystem/env-packs/issues/195)) ([91f0ca6](https://github.com/RAESystem/env-packs/commit/91f0ca642e915f00d946da7330f13508bfaf3cd6))


### Documentation

* rewrite documentation for users, splitting public from developer docs ([#186](https://github.com/RAESystem/env-packs/issues/186)) ([0d5f22c](https://github.com/RAESystem/env-packs/commit/0d5f22ce2213640e37fda88f0d0e0fbd882cba95))

## [3.0.0](https://github.com/RAESystem/env-packs/compare/v2.0.2...v3.0.0) (2026-07-28)


### ⚠ BREAKING CHANGES

* adopt RAES environment-pack identity

### Features

* adopt RAES environment-pack identity ([1fe4e57](https://github.com/RAESystem/env-packs/commit/1fe4e5749806a9e698d7b8cbb811a5d1f36f8488))
* adopt RAES environment-pack identity ([#164](https://github.com/RAESystem/env-packs/issues/164)) ([1fe4e57](https://github.com/RAESystem/env-packs/commit/1fe4e5749806a9e698d7b8cbb811a5d1f36f8488))


### Bug Fixes

* adopt RAES 2 and recover interrupted releases ([#171](https://github.com/RAESystem/env-packs/issues/171)) ([687418e](https://github.com/RAESystem/env-packs/commit/687418e03e2fdf17293cc14176f461030c96006d))
* **deps:** bump coverage from 7.13.1 to 7.15.2 ([#145](https://github.com/RAESystem/env-packs/issues/145)) ([81df034](https://github.com/RAESystem/env-packs/commit/81df0342c8c9a55386f195cddca6f8ed2fbc2892))
* **deps:** bump cyclonedx-bom from 7.3.0 to 7.3.1 ([#150](https://github.com/RAESystem/env-packs/issues/150)) ([412f11a](https://github.com/RAESystem/env-packs/commit/412f11acf1aed467d9ea6fdaef15c6dbae0dca97))
* **deps:** bump fastapi from 0.140.0 to 0.140.7 ([#167](https://github.com/RAESystem/env-packs/issues/167)) ([bf743a4](https://github.com/RAESystem/env-packs/commit/bf743a47deb75b44ac154bd6b251f173e2f4b92e))
* **deps:** bump furo from 2025.7.19 to 2025.12.19 ([#149](https://github.com/RAESystem/env-packs/issues/149)) ([7fbf5f9](https://github.com/RAESystem/env-packs/commit/7fbf5f99a14fe3f628f64c4e750aa62b647991e8))
* **deps:** bump hatchling from 1.30.0 to 1.31.0 ([#147](https://github.com/RAESystem/env-packs/issues/147)) ([5ed85e9](https://github.com/RAESystem/env-packs/commit/5ed85e95c3682c2b62c137e4057a84fcc771328d))
* **deps:** bump myst-parser from 4.0.1 to 5.1.0 ([#151](https://github.com/RAESystem/env-packs/issues/151)) ([0e265ba](https://github.com/RAESystem/env-packs/commit/0e265ba7e9a15a66d5cc194ef7f950c9017c2816))
* **deps:** bump raes from 1.1.0 to 2.0.0 ([#168](https://github.com/RAESystem/env-packs/issues/168)) ([42d0e31](https://github.com/RAESystem/env-packs/commit/42d0e31f31e12aaca7ccaf99a082fd458efd9c40))
* export verified tags for manual recovery ([#175](https://github.com/RAESystem/env-packs/issues/175)) ([a8eca33](https://github.com/RAESystem/env-packs/commit/a8eca33f267056c3216b07c159d3be4301e03056))
* pin working gitsign verifier ([#173](https://github.com/RAESystem/env-packs/issues/173)) ([4691f20](https://github.com/RAESystem/env-packs/commit/4691f20d108c18f5cc8658b72f628ea2e79395a4))
* publish only the active PyPI distribution ([#179](https://github.com/RAESystem/env-packs/issues/179)) ([7ef700e](https://github.com/RAESystem/env-packs/commit/7ef700e6b99fdbb4586da35ff1dbbb9e7841cb75))
* restore locked tooling for historical release ([#177](https://github.com/RAESystem/env-packs/issues/177)) ([d465e18](https://github.com/RAESystem/env-packs/commit/d465e18f4254087313dbe593a418843d76284863))


### Documentation

* clarify the RAES env-pack format ownership boundary ([#160](https://github.com/RAESystem/env-packs/issues/160)) ([d8b7835](https://github.com/RAESystem/env-packs/commit/d8b7835b224b353120f4f0ed576f69f6f9505aee))

## [2.0.2](https://github.com/Brad-Edwards/aces-scenario-packs/compare/v2.0.1...v2.0.2) (2026-07-20)


### Bug Fixes

* **deps:** bump aces-sdl from 0.23.0 to 0.23.1 ([#131](https://github.com/Brad-Edwards/aces-scenario-packs/issues/131)) ([6e65fd7](https://github.com/Brad-Edwards/aces-scenario-packs/commit/6e65fd73a4c879dfd7a4d54a5210ed6052c2a42e))
* reject participant/restricted artifact-boundary overlaps ([#127](https://github.com/Brad-Edwards/aces-scenario-packs/issues/127)) ([56e0eab](https://github.com/Brad-Edwards/aces-scenario-packs/commit/56e0eabc95eb4a4e09303986d1525ce5ae491f4b))


### Documentation

* record release-please signing constraints in ADR 0017 ([#130](https://github.com/Brad-Edwards/aces-scenario-packs/issues/130)) ([d20b5d7](https://github.com/Brad-Edwards/aces-scenario-packs/commit/d20b5d724d03254d94f163e88c083dfda78d090d))

## [2.0.1](https://github.com/Brad-Edwards/aces-scenario-packs/compare/v2.0.0...v2.0.1) (2026-07-17)


### Bug Fixes

* **deps:** bump aces-sdl from 0.21.0 to 0.23.0 ([#123](https://github.com/Brad-Edwards/aces-scenario-packs/issues/123)) ([db7035d](https://github.com/Brad-Edwards/aces-scenario-packs/commit/db7035d190cabe4b847c0e888ebcaddde8da262d))

## [2.0.0](https://github.com/Brad-Edwards/aces-scenario-packs/compare/v1.2.0...v2.0.0) (2026-07-15)


### ⚠ BREAKING CHANGES

* provenance schema_version is now scenario-pack-provenance/v2 with sources[].kind removed; the scenario-pack contract version is 3; a challenges[].category field is rejected by validation (ADR 0014).
* remove bespoke oracle model ([#109](https://github.com/Brad-Edwards/aces-scenario-packs/issues/109))

### Features

* align pack vocabularies to ACES concept-authority ([#111](https://github.com/Brad-Edwards/aces-scenario-packs/issues/111)) ([e8a20e6](https://github.com/Brad-Edwards/aces-scenario-packs/commit/e8a20e6008406d274a3157291d715f48e296c891))
* discover all supported pack checks ([#117](https://github.com/Brad-Edwards/aces-scenario-packs/issues/117)) ([a8ddd35](https://github.com/Brad-Edwards/aces-scenario-packs/commit/a8ddd35f8bb610facb9c5d3dd19957ac54d6b752))
* remove bespoke oracle model ([#109](https://github.com/Brad-Edwards/aces-scenario-packs/issues/109)) ([6cadaf3](https://github.com/Brad-Edwards/aces-scenario-packs/commit/6cadaf3032515cf82c0419ac420fa7825e2f3fca))


### Bug Fixes

* accept explicit pack validation roots ([#116](https://github.com/Brad-Edwards/aces-scenario-packs/issues/116)) ([74dbac8](https://github.com/Brad-Edwards/aces-scenario-packs/commit/74dbac8da4da3bf95cf523f3a918eaa31a83ab68))
* adopt ACES schema $id namespace and schema_version string form ([#110](https://github.com/Brad-Edwards/aces-scenario-packs/issues/110)) ([7c2f305](https://github.com/Brad-Edwards/aces-scenario-packs/commit/7c2f3054d487b29b4cba38ac331bbdd0c715e873))


### Documentation

* add migration scrub policy ([#108](https://github.com/Brad-Edwards/aces-scenario-packs/issues/108)) ([1913856](https://github.com/Brad-Edwards/aces-scenario-packs/commit/1913856e3988eef5c23c04695b0bf1590c1f8035))

## [1.2.0](https://github.com/Brad-Edwards/aces-scenario-packs/compare/v1.1.0...v1.2.0) (2026-07-13)


### Features

* add single-pack consumer validation API ([#104](https://github.com/Brad-Edwards/aces-scenario-packs/issues/104)) ([5d73177](https://github.com/Brad-Edwards/aces-scenario-packs/commit/5d73177640052c9f4c5f0afdc89c252c49a37937))
* add single-pack consumer validation API ([#104](https://github.com/Brad-Edwards/aces-scenario-packs/issues/104)) ([fa1383d](https://github.com/Brad-Edwards/aces-scenario-packs/commit/fa1383d0161b0e38e288a04a2a2ff3c0f35f0f62))

## [1.1.0](https://github.com/Brad-Edwards/aces-scenario-packs/compare/v1.0.0...v1.1.0) (2026-07-13)


### Features

* consume ACES associated-artifact manifests ([#98](https://github.com/Brad-Edwards/aces-scenario-packs/issues/98)) ([2b3f730](https://github.com/Brad-Edwards/aces-scenario-packs/commit/2b3f730d491c8a0e67828ede39912e31ec1010f7))

## [1.0.0](https://github.com/Brad-Edwards/aces-scenario-packs/compare/v0.1.0...v1.0.0) (2026-07-12)


### ⚠ BREAKING CHANGES

* validate pack sdl/ through ACES and cross-check flag placement ([#92](https://github.com/Brad-Edwards/aces-scenario-packs/issues/92))

### Features

* strip ACES semantic extensions and add an anti-extension guard ([#91](https://github.com/Brad-Edwards/aces-scenario-packs/issues/91)) ([7892dcf](https://github.com/Brad-Edwards/aces-scenario-packs/commit/7892dcf8bbb46e3d3a704ce34c551deedff33f8d)), closes [#83](https://github.com/Brad-Edwards/aces-scenario-packs/issues/83)
* validate pack sdl/ through ACES and cross-check flag placement ([#92](https://github.com/Brad-Edwards/aces-scenario-packs/issues/92)) ([f7129ea](https://github.com/Brad-Edwards/aces-scenario-packs/commit/f7129eac264793c1fa80f89db59d9f9a88cfb6f6))


### Documentation

* consume ACES reusable-asset trust policy for pack provenance ([#90](https://github.com/Brad-Edwards/aces-scenario-packs/issues/90)) ([dc3f106](https://github.com/Brad-Edwards/aces-scenario-packs/commit/dc3f106e4a87e13f6f652fe87637c13a107bf797))
* establish ACES-subordinate charter (ADR 0009) and align governing docs ([#88](https://github.com/Brad-Edwards/aces-scenario-packs/issues/88)) ([db73b71](https://github.com/Brad-Edwards/aces-scenario-packs/commit/db73b711c0930e4c704dc3bca8efa8316b461d31))

## [0.1.0] - 2026-07-06

### Added

- Initial release: the ACES scenario-pack definition — the layout contract,
  schemas, bundled template, and shared oracle model — together with the
  authoring/validation CLI tools (`aces-pack-validate`, `aces-pack-release`,
  `aces-new-pack`, `aces-pack-issue-skeleton`), published as the installable
  `aces-scenario-packs` package.
