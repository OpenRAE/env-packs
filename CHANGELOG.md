# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

PRs do **not** edit this file directly. Add a fragment under
[`changelog.d/`](changelog.d/) instead; `towncrier build` collates fragments into
this file at release-prep. See [`changelog.d/README.md`](changelog.d/README.md).

<!-- towncrier release notes start -->

## [5.0.0](https://github.com/OpenRAE/env-packs/compare/v4.0.3...v5.0.0) (2026-09-06)


### ⚠ BREAKING CHANGES

* adopt RAES environment-pack identity
* provenance schema_version is now scenario-pack-provenance/v2 with sources[].kind removed; the scenario-pack contract version is 3; a challenges[].category field is rejected by validation (ADR 0014).
* remove bespoke oracle model ([#109](https://github.com/OpenRAE/env-packs/issues/109))
* validate pack sdl/ through ACES and cross-check flag placement ([#92](https://github.com/OpenRAE/env-packs/issues/92))

### Features

* add reusable infrastructure kit authoring ([#226](https://github.com/OpenRAE/env-packs/issues/226)) ([ff8149d](https://github.com/OpenRAE/env-packs/commit/ff8149da3743ed3b19616cabc0c71a5e5788da0d))
* add scenario-pack validation and release tooling ([16a5889](https://github.com/OpenRAE/env-packs/commit/16a588908728faa2f70db892975603c4fa725e38))
* add single-pack consumer validation API ([#104](https://github.com/OpenRAE/env-packs/issues/104)) ([5d73177](https://github.com/OpenRAE/env-packs/commit/5d73177640052c9f4c5f0afdc89c252c49a37937))
* add single-pack consumer validation API ([#104](https://github.com/OpenRAE/env-packs/issues/104)) ([fa1383d](https://github.com/OpenRAE/env-packs/commit/fa1383d0161b0e38e288a04a2a2ff3c0f35f0f62))
* add TechVault example scenario pack ([#228](https://github.com/OpenRAE/env-packs/issues/228)) ([49a3d56](https://github.com/OpenRAE/env-packs/commit/49a3d56acc974c932518583e8fc0b0002917c431))
* add the TechVault environment pack ([#238](https://github.com/OpenRAE/env-packs/issues/238)) ([462dc23](https://github.com/OpenRAE/env-packs/commit/462dc233f5fee801219b28296104c7eff8d7cfaa))
* adopt RAES environment-pack identity ([1fe4e57](https://github.com/OpenRAE/env-packs/commit/1fe4e5749806a9e698d7b8cbb811a5d1f36f8488))
* adopt RAES environment-pack identity ([#164](https://github.com/OpenRAE/env-packs/issues/164)) ([1fe4e57](https://github.com/OpenRAE/env-packs/commit/1fe4e5749806a9e698d7b8cbb811a5d1f36f8488))
* align pack vocabularies to ACES concept-authority ([#111](https://github.com/OpenRAE/env-packs/issues/111)) ([e8a20e6](https://github.com/OpenRAE/env-packs/commit/e8a20e6008406d274a3157291d715f48e296c891))
* **catalog:** render pack cards and a machine-readable catalog index ([#206](https://github.com/OpenRAE/env-packs/issues/206)) ([58013af](https://github.com/OpenRAE/env-packs/commit/58013af7b8c34400e95e9515bc6ba161f38cbd7b))
* **cli:** add beginner-safe static pack check with actionable diagnostics ([#193](https://github.com/OpenRAE/env-packs/issues/193)) ([2d8b29f](https://github.com/OpenRAE/env-packs/commit/2d8b29ff2af6f3d20f3dbe0378856cf60cce7f9d))
* consume ACES associated-artifact manifests ([#98](https://github.com/OpenRAE/env-packs/issues/98)) ([2b3f730](https://github.com/OpenRAE/env-packs/commit/2b3f730d491c8a0e67828ede39912e31ec1010f7))
* **consumer-api:** public single-open pack artifact resolver ([#209](https://github.com/OpenRAE/env-packs/issues/209)) ([f05338e](https://github.com/OpenRAE/env-packs/commit/f05338e392eba071e579df29f28933c4f31482d5))
* define the environment-pack publication profile for artifact satisfaction ([#184](https://github.com/OpenRAE/env-packs/issues/184)) ([9af729d](https://github.com/OpenRAE/env-packs/commit/9af729dc05b07d9aa39577231deb906db3b2e07c))
* discover all supported pack checks ([#117](https://github.com/OpenRAE/env-packs/issues/117)) ([a8ddd35](https://github.com/OpenRAE/env-packs/commit/a8ddd35f8bb610facb9c5d3dd19957ac54d6b752))
* **distribution:** add verified pack supply-chain workflows ([#257](https://github.com/OpenRAE/env-packs/issues/257)) ([759ec95](https://github.com/OpenRAE/env-packs/commit/759ec95ccc8d505fd67259701f4a35bedf6674bd))
* remove bespoke oracle model ([#109](https://github.com/OpenRAE/env-packs/issues/109)) ([6cadaf3](https://github.com/OpenRAE/env-packs/commit/6cadaf3032515cf82c0419ac420fa7825e2f3fca))
* require the compatibility-tested RAES 3.x runtime contract ([b7fafc4](https://github.com/OpenRAE/env-packs/commit/b7fafc444638bb71922ee9bedbad43a9b8fcecc4))
* require the compatibility-tested RAES 3.x runtime contract ([5ad5d9c](https://github.com/OpenRAE/env-packs/commit/5ad5d9c8c6cb2c78bb3357638ec4e91e7f7fab29)), closes [#217](https://github.com/OpenRAE/env-packs/issues/217)
* **scaffold:** replace the monolithic scaffold with a progressive wizard ([#211](https://github.com/OpenRAE/env-packs/issues/211)) ([2acc73a](https://github.com/OpenRAE/env-packs/commit/2acc73a378dd266209e3bd7128149043449e0130))
* strip ACES semantic extensions and add an anti-extension guard ([#91](https://github.com/OpenRAE/env-packs/issues/91)) ([7892dcf](https://github.com/OpenRAE/env-packs/commit/7892dcf8bbb46e3d3a704ce34c551deedff33f8d)), closes [#83](https://github.com/OpenRAE/env-packs/issues/83)
* **techvault:** author operator-access proxies + capture sidecar as component builds ([7cf97fb](https://github.com/OpenRAE/env-packs/commit/7cf97fbb5cf2a9c0d28d2c98a33cedd53d7dbabb))
* **techvault:** author the indexer internal_users.yml ([58e79a9](https://github.com/OpenRAE/env-packs/commit/58e79a977997bdae76518e503675010ffe7e1417))
* **techvault:** declare aptl-tempo config and startup command ([18d2f10](https://github.com/OpenRAE/env-packs/commit/18d2f101f9102d05e94f78e1600461287c8a2a47))
* **techvault:** declare Cortex job index as ADR-088 initial service state ([#269](https://github.com/OpenRAE/env-packs/issues/269)) ([d5385f8](https://github.com/OpenRAE/env-packs/commit/d5385f810157a0b64f23e9718529fd54c5066ba0))
* **techvault:** declare misp-db and shuffle-opensearch runtime environment ([a1a1211](https://github.com/OpenRAE/env-packs/commit/a1a12111a5ee86bfba9ed32ce2ec2cb2dc8adcdd))
* **techvault:** declare SOC app configs (otel, grafana, cortex, thehive) ([#259](https://github.com/OpenRAE/env-packs/issues/259)) ([d448316](https://github.com/OpenRAE/env-packs/commit/d4483165d59d2df0d9979460b19f3c582dc2887d))
* **techvault:** declare suricata run config + cortex-index-init placement ([#259](https://github.com/OpenRAE/env-packs/issues/259)) ([02314a8](https://github.com/OpenRAE/env-packs/commit/02314a868096cd47fdd3922495972e4b69517c14))
* **techvault:** declare wazuh cluster env desired-state ([#259](https://github.com/OpenRAE/env-packs/issues/259)) ([4ef0569](https://github.com/OpenRAE/env-packs/commit/4ef0569ac35945a6e12452c05a7c51171fdb7988))
* **techvault:** declare wazuh loopback published ports ([c318349](https://github.com/OpenRAE/env-packs/commit/c31834971c30a7659e099422debe1b1cac8f6179))
* **techvault:** declare wazuh sidecar agent environment ([6abf245](https://github.com/OpenRAE/env-packs/commit/6abf245473bb4d9c1fe2697acfefecdc3df34956))
* **techvault:** declare wazuh-dashboard config content ([#259](https://github.com/OpenRAE/env-packs/issues/259)) ([a2a2ddc](https://github.com/OpenRAE/env-packs/commit/a2a2ddc6a11e94b84960233bbf789065e60cc38a))
* **techvault:** declare wazuh-indexer opensearch.yml security config ([#259](https://github.com/OpenRAE/env-packs/issues/259)) ([499bd04](https://github.com/OpenRAE/env-packs/commit/499bd04b72252c67b9891c81a03825bfbae7c62e))
* **techvault:** fully declare cortex-index-init (image, entrypoint, script) ([99973e7](https://github.com/OpenRAE/env-packs/commit/99973e75d311bd5e0131e428326b8d49bfa23cd5))
* **techvault:** replace subset SDL with the full canonical TechVault scenario ([0122582](https://github.com/OpenRAE/env-packs/commit/012258263f93f11093b71e0be10c2f1dca020e03))
* **techvault:** replace subset SDL with the full canonical TechVault scenario ([7fb9bc5](https://github.com/OpenRAE/env-packs/commit/7fb9bc5dae95e98b7b8597ffa6288c5c668cbe5c))
* validate pack sdl/ through ACES and cross-check flag placement ([#92](https://github.com/OpenRAE/env-packs/issues/92)) ([f7129ea](https://github.com/OpenRAE/env-packs/commit/f7129eac264793c1fa80f89db59d9f9a88cfb6f6))


### Bug Fixes

* accept explicit pack validation roots ([#116](https://github.com/OpenRAE/env-packs/issues/116)) ([74dbac8](https://github.com/OpenRAE/env-packs/commit/74dbac8da4da3bf95cf523f3a918eaa31a83ab68))
* adopt ACES schema $id namespace and schema_version string form ([#110](https://github.com/OpenRAE/env-packs/issues/110)) ([7c2f305](https://github.com/OpenRAE/env-packs/commit/7c2f3054d487b29b4cba38ac331bbdd0c715e873))
* adopt RAES 2 and recover interrupted releases ([#171](https://github.com/OpenRAE/env-packs/issues/171)) ([687418e](https://github.com/OpenRAE/env-packs/commit/687418e03e2fdf17293cc14176f461030c96006d))
* close TechVault Shuffle runtime image inventory ([#315](https://github.com/OpenRAE/env-packs/issues/315)) ([b51f9e7](https://github.com/OpenRAE/env-packs/commit/b51f9e793f72c7ae90588566529f97b5f56e77ca))
* complete TechVault Shuffle runtime contract ([#306](https://github.com/OpenRAE/env-packs/issues/306)) ([1f3643a](https://github.com/OpenRAE/env-packs/commit/1f3643afdb18577f6748c1585305b74ccebdef27))
* correct APTL and LilRAE boundary ([#297](https://github.com/OpenRAE/env-packs/issues/297)) ([7661bd8](https://github.com/OpenRAE/env-packs/commit/7661bd8dcd895aa1f8e2146868060fb333e2a0f3))
* **deps:** bump aces-sdl from 0.21.0 to 0.23.0 ([#123](https://github.com/OpenRAE/env-packs/issues/123)) ([db7035d](https://github.com/OpenRAE/env-packs/commit/db7035d190cabe4b847c0e888ebcaddde8da262d))
* **deps:** bump aces-sdl from 0.23.0 to 0.23.1 ([#131](https://github.com/OpenRAE/env-packs/issues/131)) ([6e65fd7](https://github.com/OpenRAE/env-packs/commit/6e65fd73a4c879dfd7a4d54a5210ed6052c2a42e))
* **deps:** bump annotated-doc from 0.0.4 to 0.0.5 ([#201](https://github.com/OpenRAE/env-packs/issues/201)) ([c2811a9](https://github.com/OpenRAE/env-packs/commit/c2811a98556fc6abe757734a3c6677caec30fd78))
* **deps:** bump cffi from 2.1.0 to 2.1.1 ([#291](https://github.com/OpenRAE/env-packs/issues/291)) ([44a6ece](https://github.com/OpenRAE/env-packs/commit/44a6ecec853eb58a7428263f13bcfce352c3810f))
* **deps:** bump coverage from 7.13.1 to 7.15.2 ([#145](https://github.com/OpenRAE/env-packs/issues/145)) ([81df034](https://github.com/OpenRAE/env-packs/commit/81df0342c8c9a55386f195cddca6f8ed2fbc2892))
* **deps:** bump cyclonedx-bom from 7.3.0 to 7.3.1 ([#150](https://github.com/OpenRAE/env-packs/issues/150)) ([412f11a](https://github.com/OpenRAE/env-packs/commit/412f11acf1aed467d9ea6fdaef15c6dbae0dca97))
* **deps:** bump fastapi from 0.140.0 to 0.140.7 ([#167](https://github.com/OpenRAE/env-packs/issues/167)) ([bf743a4](https://github.com/OpenRAE/env-packs/commit/bf743a47deb75b44ac154bd6b251f173e2f4b92e))
* **deps:** bump fastapi from 0.140.7 to 0.141.1 ([#199](https://github.com/OpenRAE/env-packs/issues/199)) ([6535ff5](https://github.com/OpenRAE/env-packs/commit/6535ff593e623d7fc2a2cb41623aa16211dbe4a3))
* **deps:** bump furo from 2025.7.19 to 2025.12.19 ([#149](https://github.com/OpenRAE/env-packs/issues/149)) ([7fbf5f9](https://github.com/OpenRAE/env-packs/commit/7fbf5f99a14fe3f628f64c4e750aa62b647991e8))
* **deps:** bump hatchling from 1.30.0 to 1.31.0 ([#147](https://github.com/OpenRAE/env-packs/issues/147)) ([5ed85e9](https://github.com/OpenRAE/env-packs/commit/5ed85e95c3682c2b62c137e4057a84fcc771328d))
* **deps:** bump myst-parser from 4.0.1 to 5.1.0 ([#151](https://github.com/OpenRAE/env-packs/issues/151)) ([0e265ba](https://github.com/OpenRAE/env-packs/commit/0e265ba7e9a15a66d5cc194ef7f950c9017c2816))
* **deps:** bump raes from 1.1.0 to 2.0.0 ([#168](https://github.com/OpenRAE/env-packs/issues/168)) ([42d0e31](https://github.com/OpenRAE/env-packs/commit/42d0e31f31e12aaca7ccaf99a082fd458efd9c40))
* **deps:** bump uvicorn from 0.51.0 to 0.52.0 ([#202](https://github.com/OpenRAE/env-packs/issues/202)) ([c502425](https://github.com/OpenRAE/env-packs/commit/c502425518b087322b55b298fd2fff070496cbd4))
* **deps:** bump uvicorn from 0.52.0 to 0.52.1 ([#290](https://github.com/OpenRAE/env-packs/issues/290)) ([778d2cd](https://github.com/OpenRAE/env-packs/commit/778d2cd1537285709f2e0d18d740d83001ea7176))
* **deps:** bump websockets from 16.1.1 to 17.0 ([#243](https://github.com/OpenRAE/env-packs/issues/243)) ([6f52cc2](https://github.com/OpenRAE/env-packs/commit/6f52cc2b2fd9215ba83716d2f1e850936764b62f))
* enable TechVault Cortex enrichment ([#313](https://github.com/OpenRAE/env-packs/issues/313)) ([05d2d60](https://github.com/OpenRAE/env-packs/commit/05d2d60540030ed1e5ea9661626fffabba34b451))
* export verified tags for manual recovery ([#175](https://github.com/OpenRAE/env-packs/issues/175)) ([a8eca33](https://github.com/OpenRAE/env-packs/commit/a8eca33f267056c3216b07c159d3be4301e03056))
* **issue-skeleton:** stop defaulting pack issues to env-packs ([#195](https://github.com/OpenRAE/env-packs/issues/195)) ([91f0ca6](https://github.com/OpenRAE/env-packs/commit/91f0ca642e915f00d946da7330f13508bfaf3cd6))
* pin RAES 3.3.0 ([#247](https://github.com/OpenRAE/env-packs/issues/247)) ([f900df5](https://github.com/OpenRAE/env-packs/commit/f900df51d69acd1e36bcb426e8d17c1e6afe7696))
* pin working gitsign verifier ([#173](https://github.com/OpenRAE/env-packs/issues/173)) ([4691f20](https://github.com/OpenRAE/env-packs/commit/4691f20d108c18f5cc8658b72f628ea2e79395a4))
* publish infrastructure kits in env-packs ([#232](https://github.com/OpenRAE/env-packs/issues/232)) ([079cb84](https://github.com/OpenRAE/env-packs/commit/079cb847f58d4da0a88f3ff5156ad1b81f72c33c))
* publish only the active PyPI distribution ([#179](https://github.com/OpenRAE/env-packs/issues/179)) ([7ef700e](https://github.com/OpenRAE/env-packs/commit/7ef700e6b99fdbb4586da35ff1dbbb9e7841cb75))
* reject participant/restricted artifact-boundary overlaps ([#127](https://github.com/OpenRAE/env-packs/issues/127)) ([56e0eab](https://github.com/OpenRAE/env-packs/commit/56e0eabc95eb4a4e09303986d1525ce5ae491f4b))
* restore locked tooling for historical release ([#177](https://github.com/OpenRAE/env-packs/issues/177)) ([d465e18](https://github.com/OpenRAE/env-packs/commit/d465e18f4254087313dbe593a418843d76284863))
* restore TechVault Suricata detection content ([#311](https://github.com/OpenRAE/env-packs/issues/311)) ([effec1b](https://github.com/OpenRAE/env-packs/commit/effec1b2b3c50c911d2ea7061ca363e60bc5a783))
* ship TechVault in PyPI distributions ([#253](https://github.com/OpenRAE/env-packs/issues/253)) ([1b5b99c](https://github.com/OpenRAE/env-packs/commit/1b5b99c54ad236c8952ed0fa1669543b6ed4ff20))
* **techvault:** align soc-certificate output paths with the issued layout ([f4444a9](https://github.com/OpenRAE/env-packs/commit/f4444a9c605e9882de8b22b59c510e3f4af11fdf))
* **techvault:** declare thehive-es ES env (single-node, security off, 512m heap) ([#259](https://github.com/OpenRAE/env-packs/issues/259)) ([8601f71](https://github.com/OpenRAE/env-packs/commit/8601f71bdccf06994a3e4c434efc42cd8a2f6cc3))
* **techvault:** mark cortex-index-init as one-shot (autoremove) ([#259](https://github.com/OpenRAE/env-packs/issues/259)) ([09ff951](https://github.com/OpenRAE/env-packs/commit/09ff9517cc4ea5b8db505c3c6dc7b63d80230281))
* **techvault:** materialize detection content and SOC ports ([#275](https://github.com/OpenRAE/env-packs/issues/275)) ([9e9509e](https://github.com/OpenRAE/env-packs/commit/9e9509e2bb0eb06e73f9f6054d8dd039241b75d0))
* **techvault:** realize the misp-sync TLS flag and the db-log forwarding source ([74ba39d](https://github.com/OpenRAE/env-packs/commit/74ba39deeb02ff6a89a9e7394905c24112f7f599))
* **techvault:** suricata direct exec, cortex-init ES wait, ad samba caps ([#259](https://github.com/OpenRAE/env-packs/issues/259)) ([32857a9](https://github.com/OpenRAE/env-packs/commit/32857a96c756492ffd8282fb252f0f9027cbe7e0))
* **techvault:** update proxy component-build spec digests ([1d842ce](https://github.com/OpenRAE/env-packs/commit/1d842ce2d7d1a6f7f33ab3621e65b2ccb5293ef3))


### Reverts

* 21 contract-v1 provenance ledger; restore provenance.v0 ([95991af](https://github.com/OpenRAE/env-packs/commit/95991aff8bd914a8725df8f1eaa3a0d649db4065))
* contract-v1 provenance ledger ([#21](https://github.com/OpenRAE/env-packs/issues/21)) — content-safety attestation unworkable for live-fire ([5e88f70](https://github.com/OpenRAE/env-packs/commit/5e88f70a218a00f32ee1a8adb3bd7cb42be0a134))


### Documentation

* add ACES scenario-pack contract (ASP-0002) ([42a524e](https://github.com/OpenRAE/env-packs/commit/42a524ebacb423729d59d93d9c89c090ce0fa903))
* add documentation scrub policy and migration scrub checklist ([5e705e2](https://github.com/OpenRAE/env-packs/commit/5e705e274f72051ebc3b43028f1bc07d1a9f0360))
* add Ground Control requirement specs as repo-local files ([#264](https://github.com/OpenRAE/env-packs/issues/264)) ([ed7d966](https://github.com/OpenRAE/env-packs/commit/ed7d9661b67ba1114c745c5211418ebfcd7ca1bd))
* add migration scrub policy ([#108](https://github.com/OpenRAE/env-packs/issues/108)) ([1913856](https://github.com/OpenRAE/env-packs/commit/1913856e3988eef5c23c04695b0bf1590c1f8035))
* add template scenario-pack scaffold (ASP-0003) ([e0b6b77](https://github.com/OpenRAE/env-packs/commit/e0b6b77a24589c0e19aa64878563d4f9776e5f8e))
* add versioning and branch-protection governance for ASP-0001 ([71fe219](https://github.com/OpenRAE/env-packs/commit/71fe2199e6bbbc13d19b9890c1c3ef9e81981885))
* clarify the RAES env-pack format ownership boundary ([#160](https://github.com/OpenRAE/env-packs/issues/160)) ([d8b7835](https://github.com/OpenRAE/env-packs/commit/d8b7835b224b353120f4f0ed576f69f6f9505aee))
* consume ACES reusable-asset trust policy for pack provenance ([#90](https://github.com/OpenRAE/env-packs/issues/90)) ([dc3f106](https://github.com/OpenRAE/env-packs/commit/dc3f106e4a87e13f6f652fe87637c13a107bf797))
* establish ACES-subordinate charter (ADR 0009) and align governing docs ([#88](https://github.com/OpenRAE/env-packs/issues/88)) ([db73b71](https://github.com/OpenRAE/env-packs/commit/db73b711c0930e4c704dc3bca8efa8316b461d31))
* fix contract reference doc tool paths (aces-pack-validate/release) ([bb8864b](https://github.com/OpenRAE/env-packs/commit/bb8864b401c169ea7be557a2984bb61c3e628447))
* make current for first release; remove Ground Control from docs ([2af0225](https://github.com/OpenRAE/env-packs/commit/2af02252c3a1dd1c0cd53e572fe9c1ff447f64fd))
* move scenario-pack definition from penumbra-scenarios ([a376bca](https://github.com/OpenRAE/env-packs/commit/a376bca03c7c7764717da219adf04e162bf342fc))
* record authoring and tooling ownership plan (ASP-0013) ([622d024](https://github.com/OpenRAE/env-packs/commit/622d0248119bd604ff970f589a841f8a4431c0ac))
* record capture workflow placement decision for ASP-0014 ([4485f2d](https://github.com/OpenRAE/env-packs/commit/4485f2d8da6bb147cde913f124cc8040d7ab3ef0))
* record release-please signing constraints in ADR 0017 ([#130](https://github.com/OpenRAE/env-packs/issues/130)) ([d20b5d7](https://github.com/OpenRAE/env-packs/commit/d20b5d724d03254d94f163e88c083dfda78d090d))
* record TechVault Wazuh cert ownership boundary ([#310](https://github.com/OpenRAE/env-packs/issues/310)) ([c3b5743](https://github.com/OpenRAE/env-packs/commit/c3b5743023079c4801d9a9400d84761cfd5f944c))
* rewrite documentation for users, splitting public from developer docs ([#186](https://github.com/OpenRAE/env-packs/issues/186)) ([0d5f22c](https://github.com/OpenRAE/env-packs/commit/0d5f22ce2213640e37fda88f0d0e0fbd882cba95))

## [4.0.3](https://github.com/OpenRAE/env-packs/compare/v4.0.2...v4.0.3) (2026-09-06)


### Bug Fixes

* close TechVault Shuffle runtime image inventory ([#315](https://github.com/OpenRAE/env-packs/issues/315)) ([b51f9e7](https://github.com/OpenRAE/env-packs/commit/b51f9e793f72c7ae90588566529f97b5f56e77ca))
* enable TechVault Cortex enrichment ([#313](https://github.com/OpenRAE/env-packs/issues/313)) ([05d2d60](https://github.com/OpenRAE/env-packs/commit/05d2d60540030ed1e5ea9661626fffabba34b451))
* restore TechVault Suricata detection content ([#311](https://github.com/OpenRAE/env-packs/issues/311)) ([effec1b](https://github.com/OpenRAE/env-packs/commit/effec1b2b3c50c911d2ea7061ca363e60bc5a783))


### Documentation

* record TechVault Wazuh cert ownership boundary ([#310](https://github.com/OpenRAE/env-packs/issues/310)) ([c3b5743](https://github.com/OpenRAE/env-packs/commit/c3b5743023079c4801d9a9400d84761cfd5f944c))

## [4.0.2](https://github.com/OpenRAE/env-packs/compare/v4.0.1...v4.0.2) (2026-09-03)


### Bug Fixes

* complete TechVault Shuffle runtime contract ([#306](https://github.com/OpenRAE/env-packs/issues/306)) ([1f3643a](https://github.com/OpenRAE/env-packs/commit/1f3643afdb18577f6748c1585305b74ccebdef27))
* correct APTL and LilRAE boundary ([#297](https://github.com/OpenRAE/env-packs/issues/297)) ([7661bd8](https://github.com/OpenRAE/env-packs/commit/7661bd8dcd895aa1f8e2146868060fb333e2a0f3))
* **deps:** bump cffi from 2.1.0 to 2.1.1 ([#291](https://github.com/OpenRAE/env-packs/issues/291)) ([44a6ece](https://github.com/OpenRAE/env-packs/commit/44a6ecec853eb58a7428263f13bcfce352c3810f))
* **deps:** bump uvicorn from 0.52.0 to 0.52.1 ([#290](https://github.com/OpenRAE/env-packs/issues/290)) ([778d2cd](https://github.com/OpenRAE/env-packs/commit/778d2cd1537285709f2e0d18d740d83001ea7176))

## [4.0.1](https://github.com/OpenRAE/env-packs/compare/v4.0.0...v4.0.1) (2026-08-04)


### Bug Fixes

* **techvault:** materialize detection content and SOC ports ([#275](https://github.com/OpenRAE/env-packs/issues/275)) ([9e9509e](https://github.com/OpenRAE/env-packs/commit/9e9509e2bb0eb06e73f9f6054d8dd039241b75d0))

## [4.0.0](https://github.com/OpenRAE/env-packs/compare/v3.9.0...v4.0.0) (2026-08-04)


### ⚠ BREAKING CHANGES

* adopt RAES environment-pack identity
* provenance schema_version is now scenario-pack-provenance/v2 with sources[].kind removed; the scenario-pack contract version is 3; a challenges[].category field is rejected by validation (ADR 0014).
* remove bespoke oracle model ([#109](https://github.com/OpenRAE/env-packs/issues/109))
* validate pack sdl/ through ACES and cross-check flag placement ([#92](https://github.com/OpenRAE/env-packs/issues/92))

### Features

* add reusable infrastructure kit authoring ([#226](https://github.com/OpenRAE/env-packs/issues/226)) ([ff8149d](https://github.com/OpenRAE/env-packs/commit/ff8149da3743ed3b19616cabc0c71a5e5788da0d))
* add scenario-pack validation and release tooling ([16a5889](https://github.com/OpenRAE/env-packs/commit/16a588908728faa2f70db892975603c4fa725e38))
* add single-pack consumer validation API ([#104](https://github.com/OpenRAE/env-packs/issues/104)) ([5d73177](https://github.com/OpenRAE/env-packs/commit/5d73177640052c9f4c5f0afdc89c252c49a37937))
* add single-pack consumer validation API ([#104](https://github.com/OpenRAE/env-packs/issues/104)) ([fa1383d](https://github.com/OpenRAE/env-packs/commit/fa1383d0161b0e38e288a04a2a2ff3c0f35f0f62))
* add TechVault example scenario pack ([#228](https://github.com/OpenRAE/env-packs/issues/228)) ([49a3d56](https://github.com/OpenRAE/env-packs/commit/49a3d56acc974c932518583e8fc0b0002917c431))
* add the TechVault environment pack ([#238](https://github.com/OpenRAE/env-packs/issues/238)) ([462dc23](https://github.com/OpenRAE/env-packs/commit/462dc233f5fee801219b28296104c7eff8d7cfaa))
* adopt RAES environment-pack identity ([1fe4e57](https://github.com/OpenRAE/env-packs/commit/1fe4e5749806a9e698d7b8cbb811a5d1f36f8488))
* adopt RAES environment-pack identity ([#164](https://github.com/OpenRAE/env-packs/issues/164)) ([1fe4e57](https://github.com/OpenRAE/env-packs/commit/1fe4e5749806a9e698d7b8cbb811a5d1f36f8488))
* align pack vocabularies to ACES concept-authority ([#111](https://github.com/OpenRAE/env-packs/issues/111)) ([e8a20e6](https://github.com/OpenRAE/env-packs/commit/e8a20e6008406d274a3157291d715f48e296c891))
* **catalog:** render pack cards and a machine-readable catalog index ([#206](https://github.com/OpenRAE/env-packs/issues/206)) ([58013af](https://github.com/OpenRAE/env-packs/commit/58013af7b8c34400e95e9515bc6ba161f38cbd7b))
* **cli:** add beginner-safe static pack check with actionable diagnostics ([#193](https://github.com/OpenRAE/env-packs/issues/193)) ([2d8b29f](https://github.com/OpenRAE/env-packs/commit/2d8b29ff2af6f3d20f3dbe0378856cf60cce7f9d))
* consume ACES associated-artifact manifests ([#98](https://github.com/OpenRAE/env-packs/issues/98)) ([2b3f730](https://github.com/OpenRAE/env-packs/commit/2b3f730d491c8a0e67828ede39912e31ec1010f7))
* **consumer-api:** public single-open pack artifact resolver ([#209](https://github.com/OpenRAE/env-packs/issues/209)) ([f05338e](https://github.com/OpenRAE/env-packs/commit/f05338e392eba071e579df29f28933c4f31482d5))
* define the environment-pack publication profile for artifact satisfaction ([#184](https://github.com/OpenRAE/env-packs/issues/184)) ([9af729d](https://github.com/OpenRAE/env-packs/commit/9af729dc05b07d9aa39577231deb906db3b2e07c))
* discover all supported pack checks ([#117](https://github.com/OpenRAE/env-packs/issues/117)) ([a8ddd35](https://github.com/OpenRAE/env-packs/commit/a8ddd35f8bb610facb9c5d3dd19957ac54d6b752))
* **distribution:** add verified pack supply-chain workflows ([#257](https://github.com/OpenRAE/env-packs/issues/257)) ([759ec95](https://github.com/OpenRAE/env-packs/commit/759ec95ccc8d505fd67259701f4a35bedf6674bd))
* remove bespoke oracle model ([#109](https://github.com/OpenRAE/env-packs/issues/109)) ([6cadaf3](https://github.com/OpenRAE/env-packs/commit/6cadaf3032515cf82c0419ac420fa7825e2f3fca))
* require the compatibility-tested RAES 3.x runtime contract ([b7fafc4](https://github.com/OpenRAE/env-packs/commit/b7fafc444638bb71922ee9bedbad43a9b8fcecc4))
* require the compatibility-tested RAES 3.x runtime contract ([5ad5d9c](https://github.com/OpenRAE/env-packs/commit/5ad5d9c8c6cb2c78bb3357638ec4e91e7f7fab29)), closes [#217](https://github.com/OpenRAE/env-packs/issues/217)
* **scaffold:** replace the monolithic scaffold with a progressive wizard ([#211](https://github.com/OpenRAE/env-packs/issues/211)) ([2acc73a](https://github.com/OpenRAE/env-packs/commit/2acc73a378dd266209e3bd7128149043449e0130))
* strip ACES semantic extensions and add an anti-extension guard ([#91](https://github.com/OpenRAE/env-packs/issues/91)) ([7892dcf](https://github.com/OpenRAE/env-packs/commit/7892dcf8bbb46e3d3a704ce34c551deedff33f8d)), closes [#83](https://github.com/OpenRAE/env-packs/issues/83)
* **techvault:** author operator-access proxies + capture sidecar as component builds ([7cf97fb](https://github.com/OpenRAE/env-packs/commit/7cf97fbb5cf2a9c0d28d2c98a33cedd53d7dbabb))
* **techvault:** author the indexer internal_users.yml ([58e79a9](https://github.com/OpenRAE/env-packs/commit/58e79a977997bdae76518e503675010ffe7e1417))
* **techvault:** declare aptl-tempo config and startup command ([18d2f10](https://github.com/OpenRAE/env-packs/commit/18d2f101f9102d05e94f78e1600461287c8a2a47))
* **techvault:** declare Cortex job index as ADR-088 initial service state ([#269](https://github.com/OpenRAE/env-packs/issues/269)) ([d5385f8](https://github.com/OpenRAE/env-packs/commit/d5385f810157a0b64f23e9718529fd54c5066ba0))
* **techvault:** declare misp-db and shuffle-opensearch runtime environment ([a1a1211](https://github.com/OpenRAE/env-packs/commit/a1a12111a5ee86bfba9ed32ce2ec2cb2dc8adcdd))
* **techvault:** declare SOC app configs (otel, grafana, cortex, thehive) ([#259](https://github.com/OpenRAE/env-packs/issues/259)) ([d448316](https://github.com/OpenRAE/env-packs/commit/d4483165d59d2df0d9979460b19f3c582dc2887d))
* **techvault:** declare suricata run config + cortex-index-init placement ([#259](https://github.com/OpenRAE/env-packs/issues/259)) ([02314a8](https://github.com/OpenRAE/env-packs/commit/02314a868096cd47fdd3922495972e4b69517c14))
* **techvault:** declare wazuh cluster env desired-state ([#259](https://github.com/OpenRAE/env-packs/issues/259)) ([4ef0569](https://github.com/OpenRAE/env-packs/commit/4ef0569ac35945a6e12452c05a7c51171fdb7988))
* **techvault:** declare wazuh loopback published ports ([c318349](https://github.com/OpenRAE/env-packs/commit/c31834971c30a7659e099422debe1b1cac8f6179))
* **techvault:** declare wazuh sidecar agent environment ([6abf245](https://github.com/OpenRAE/env-packs/commit/6abf245473bb4d9c1fe2697acfefecdc3df34956))
* **techvault:** declare wazuh-dashboard config content ([#259](https://github.com/OpenRAE/env-packs/issues/259)) ([a2a2ddc](https://github.com/OpenRAE/env-packs/commit/a2a2ddc6a11e94b84960233bbf789065e60cc38a))
* **techvault:** declare wazuh-indexer opensearch.yml security config ([#259](https://github.com/OpenRAE/env-packs/issues/259)) ([499bd04](https://github.com/OpenRAE/env-packs/commit/499bd04b72252c67b9891c81a03825bfbae7c62e))
* **techvault:** fully declare cortex-index-init (image, entrypoint, script) ([99973e7](https://github.com/OpenRAE/env-packs/commit/99973e75d311bd5e0131e428326b8d49bfa23cd5))
* **techvault:** replace subset SDL with the full canonical TechVault scenario ([0122582](https://github.com/OpenRAE/env-packs/commit/012258263f93f11093b71e0be10c2f1dca020e03))
* **techvault:** replace subset SDL with the full canonical TechVault scenario ([7fb9bc5](https://github.com/OpenRAE/env-packs/commit/7fb9bc5dae95e98b7b8597ffa6288c5c668cbe5c))
* validate pack sdl/ through ACES and cross-check flag placement ([#92](https://github.com/OpenRAE/env-packs/issues/92)) ([f7129ea](https://github.com/OpenRAE/env-packs/commit/f7129eac264793c1fa80f89db59d9f9a88cfb6f6))


### Bug Fixes

* accept explicit pack validation roots ([#116](https://github.com/OpenRAE/env-packs/issues/116)) ([74dbac8](https://github.com/OpenRAE/env-packs/commit/74dbac8da4da3bf95cf523f3a918eaa31a83ab68))
* adopt ACES schema $id namespace and schema_version string form ([#110](https://github.com/OpenRAE/env-packs/issues/110)) ([7c2f305](https://github.com/OpenRAE/env-packs/commit/7c2f3054d487b29b4cba38ac331bbdd0c715e873))
* adopt RAES 2 and recover interrupted releases ([#171](https://github.com/OpenRAE/env-packs/issues/171)) ([687418e](https://github.com/OpenRAE/env-packs/commit/687418e03e2fdf17293cc14176f461030c96006d))
* **deps:** bump aces-sdl from 0.21.0 to 0.23.0 ([#123](https://github.com/OpenRAE/env-packs/issues/123)) ([db7035d](https://github.com/OpenRAE/env-packs/commit/db7035d190cabe4b847c0e888ebcaddde8da262d))
* **deps:** bump aces-sdl from 0.23.0 to 0.23.1 ([#131](https://github.com/OpenRAE/env-packs/issues/131)) ([6e65fd7](https://github.com/OpenRAE/env-packs/commit/6e65fd73a4c879dfd7a4d54a5210ed6052c2a42e))
* **deps:** bump annotated-doc from 0.0.4 to 0.0.5 ([#201](https://github.com/OpenRAE/env-packs/issues/201)) ([c2811a9](https://github.com/OpenRAE/env-packs/commit/c2811a98556fc6abe757734a3c6677caec30fd78))
* **deps:** bump coverage from 7.13.1 to 7.15.2 ([#145](https://github.com/OpenRAE/env-packs/issues/145)) ([81df034](https://github.com/OpenRAE/env-packs/commit/81df0342c8c9a55386f195cddca6f8ed2fbc2892))
* **deps:** bump cyclonedx-bom from 7.3.0 to 7.3.1 ([#150](https://github.com/OpenRAE/env-packs/issues/150)) ([412f11a](https://github.com/OpenRAE/env-packs/commit/412f11acf1aed467d9ea6fdaef15c6dbae0dca97))
* **deps:** bump fastapi from 0.140.0 to 0.140.7 ([#167](https://github.com/OpenRAE/env-packs/issues/167)) ([bf743a4](https://github.com/OpenRAE/env-packs/commit/bf743a47deb75b44ac154bd6b251f173e2f4b92e))
* **deps:** bump fastapi from 0.140.7 to 0.141.1 ([#199](https://github.com/OpenRAE/env-packs/issues/199)) ([6535ff5](https://github.com/OpenRAE/env-packs/commit/6535ff593e623d7fc2a2cb41623aa16211dbe4a3))
* **deps:** bump furo from 2025.7.19 to 2025.12.19 ([#149](https://github.com/OpenRAE/env-packs/issues/149)) ([7fbf5f9](https://github.com/OpenRAE/env-packs/commit/7fbf5f99a14fe3f628f64c4e750aa62b647991e8))
* **deps:** bump hatchling from 1.30.0 to 1.31.0 ([#147](https://github.com/OpenRAE/env-packs/issues/147)) ([5ed85e9](https://github.com/OpenRAE/env-packs/commit/5ed85e95c3682c2b62c137e4057a84fcc771328d))
* **deps:** bump myst-parser from 4.0.1 to 5.1.0 ([#151](https://github.com/OpenRAE/env-packs/issues/151)) ([0e265ba](https://github.com/OpenRAE/env-packs/commit/0e265ba7e9a15a66d5cc194ef7f950c9017c2816))
* **deps:** bump raes from 1.1.0 to 2.0.0 ([#168](https://github.com/OpenRAE/env-packs/issues/168)) ([42d0e31](https://github.com/OpenRAE/env-packs/commit/42d0e31f31e12aaca7ccaf99a082fd458efd9c40))
* **deps:** bump uvicorn from 0.51.0 to 0.52.0 ([#202](https://github.com/OpenRAE/env-packs/issues/202)) ([c502425](https://github.com/OpenRAE/env-packs/commit/c502425518b087322b55b298fd2fff070496cbd4))
* **deps:** bump websockets from 16.1.1 to 17.0 ([#243](https://github.com/OpenRAE/env-packs/issues/243)) ([6f52cc2](https://github.com/OpenRAE/env-packs/commit/6f52cc2b2fd9215ba83716d2f1e850936764b62f))
* export verified tags for manual recovery ([#175](https://github.com/OpenRAE/env-packs/issues/175)) ([a8eca33](https://github.com/OpenRAE/env-packs/commit/a8eca33f267056c3216b07c159d3be4301e03056))
* **issue-skeleton:** stop defaulting pack issues to env-packs ([#195](https://github.com/OpenRAE/env-packs/issues/195)) ([91f0ca6](https://github.com/OpenRAE/env-packs/commit/91f0ca642e915f00d946da7330f13508bfaf3cd6))
* pin RAES 3.3.0 ([#247](https://github.com/OpenRAE/env-packs/issues/247)) ([f900df5](https://github.com/OpenRAE/env-packs/commit/f900df51d69acd1e36bcb426e8d17c1e6afe7696))
* pin working gitsign verifier ([#173](https://github.com/OpenRAE/env-packs/issues/173)) ([4691f20](https://github.com/OpenRAE/env-packs/commit/4691f20d108c18f5cc8658b72f628ea2e79395a4))
* publish infrastructure kits in env-packs ([#232](https://github.com/OpenRAE/env-packs/issues/232)) ([079cb84](https://github.com/OpenRAE/env-packs/commit/079cb847f58d4da0a88f3ff5156ad1b81f72c33c))
* publish only the active PyPI distribution ([#179](https://github.com/OpenRAE/env-packs/issues/179)) ([7ef700e](https://github.com/OpenRAE/env-packs/commit/7ef700e6b99fdbb4586da35ff1dbbb9e7841cb75))
* reject participant/restricted artifact-boundary overlaps ([#127](https://github.com/OpenRAE/env-packs/issues/127)) ([56e0eab](https://github.com/OpenRAE/env-packs/commit/56e0eabc95eb4a4e09303986d1525ce5ae491f4b))
* restore locked tooling for historical release ([#177](https://github.com/OpenRAE/env-packs/issues/177)) ([d465e18](https://github.com/OpenRAE/env-packs/commit/d465e18f4254087313dbe593a418843d76284863))
* ship TechVault in PyPI distributions ([#253](https://github.com/OpenRAE/env-packs/issues/253)) ([1b5b99c](https://github.com/OpenRAE/env-packs/commit/1b5b99c54ad236c8952ed0fa1669543b6ed4ff20))
* **techvault:** align soc-certificate output paths with the issued layout ([f4444a9](https://github.com/OpenRAE/env-packs/commit/f4444a9c605e9882de8b22b59c510e3f4af11fdf))
* **techvault:** declare thehive-es ES env (single-node, security off, 512m heap) ([#259](https://github.com/OpenRAE/env-packs/issues/259)) ([8601f71](https://github.com/OpenRAE/env-packs/commit/8601f71bdccf06994a3e4c434efc42cd8a2f6cc3))
* **techvault:** mark cortex-index-init as one-shot (autoremove) ([#259](https://github.com/OpenRAE/env-packs/issues/259)) ([09ff951](https://github.com/OpenRAE/env-packs/commit/09ff9517cc4ea5b8db505c3c6dc7b63d80230281))
* **techvault:** realize the misp-sync TLS flag and the db-log forwarding source ([74ba39d](https://github.com/OpenRAE/env-packs/commit/74ba39deeb02ff6a89a9e7394905c24112f7f599))
* **techvault:** suricata direct exec, cortex-init ES wait, ad samba caps ([#259](https://github.com/OpenRAE/env-packs/issues/259)) ([32857a9](https://github.com/OpenRAE/env-packs/commit/32857a96c756492ffd8282fb252f0f9027cbe7e0))
* **techvault:** update proxy component-build spec digests ([1d842ce](https://github.com/OpenRAE/env-packs/commit/1d842ce2d7d1a6f7f33ab3621e65b2ccb5293ef3))


### Reverts

* 21 contract-v1 provenance ledger; restore provenance.v0 ([95991af](https://github.com/OpenRAE/env-packs/commit/95991aff8bd914a8725df8f1eaa3a0d649db4065))
* contract-v1 provenance ledger ([#21](https://github.com/OpenRAE/env-packs/issues/21)) — content-safety attestation unworkable for live-fire ([5e88f70](https://github.com/OpenRAE/env-packs/commit/5e88f70a218a00f32ee1a8adb3bd7cb42be0a134))


### Documentation

* add ACES scenario-pack contract (ASP-0002) ([42a524e](https://github.com/OpenRAE/env-packs/commit/42a524ebacb423729d59d93d9c89c090ce0fa903))
* add documentation scrub policy and migration scrub checklist ([5e705e2](https://github.com/OpenRAE/env-packs/commit/5e705e274f72051ebc3b43028f1bc07d1a9f0360))
* add Ground Control requirement specs as repo-local files ([#264](https://github.com/OpenRAE/env-packs/issues/264)) ([ed7d966](https://github.com/OpenRAE/env-packs/commit/ed7d9661b67ba1114c745c5211418ebfcd7ca1bd))
* add migration scrub policy ([#108](https://github.com/OpenRAE/env-packs/issues/108)) ([1913856](https://github.com/OpenRAE/env-packs/commit/1913856e3988eef5c23c04695b0bf1590c1f8035))
* add template scenario-pack scaffold (ASP-0003) ([e0b6b77](https://github.com/OpenRAE/env-packs/commit/e0b6b77a24589c0e19aa64878563d4f9776e5f8e))
* add versioning and branch-protection governance for ASP-0001 ([71fe219](https://github.com/OpenRAE/env-packs/commit/71fe2199e6bbbc13d19b9890c1c3ef9e81981885))
* clarify the RAES env-pack format ownership boundary ([#160](https://github.com/OpenRAE/env-packs/issues/160)) ([d8b7835](https://github.com/OpenRAE/env-packs/commit/d8b7835b224b353120f4f0ed576f69f6f9505aee))
* consume ACES reusable-asset trust policy for pack provenance ([#90](https://github.com/OpenRAE/env-packs/issues/90)) ([dc3f106](https://github.com/OpenRAE/env-packs/commit/dc3f106e4a87e13f6f652fe87637c13a107bf797))
* establish ACES-subordinate charter (ADR 0009) and align governing docs ([#88](https://github.com/OpenRAE/env-packs/issues/88)) ([db73b71](https://github.com/OpenRAE/env-packs/commit/db73b711c0930e4c704dc3bca8efa8316b461d31))
* fix contract reference doc tool paths (aces-pack-validate/release) ([bb8864b](https://github.com/OpenRAE/env-packs/commit/bb8864b401c169ea7be557a2984bb61c3e628447))
* make current for first release; remove Ground Control from docs ([2af0225](https://github.com/OpenRAE/env-packs/commit/2af02252c3a1dd1c0cd53e572fe9c1ff447f64fd))
* move scenario-pack definition from penumbra-scenarios ([a376bca](https://github.com/OpenRAE/env-packs/commit/a376bca03c7c7764717da219adf04e162bf342fc))
* record authoring and tooling ownership plan (ASP-0013) ([622d024](https://github.com/OpenRAE/env-packs/commit/622d0248119bd604ff970f589a841f8a4431c0ac))
* record capture workflow placement decision for ASP-0014 ([4485f2d](https://github.com/OpenRAE/env-packs/commit/4485f2d8da6bb147cde913f124cc8040d7ab3ef0))
* record release-please signing constraints in ADR 0017 ([#130](https://github.com/OpenRAE/env-packs/issues/130)) ([d20b5d7](https://github.com/OpenRAE/env-packs/commit/d20b5d724d03254d94f163e88c083dfda78d090d))
* rewrite documentation for users, splitting public from developer docs ([#186](https://github.com/OpenRAE/env-packs/issues/186)) ([0d5f22c](https://github.com/OpenRAE/env-packs/commit/0d5f22ce2213640e37fda88f0d0e0fbd882cba95))

## [3.9.0](https://github.com/OpenRAE/env-packs/compare/v3.8.0...v3.9.0) (2026-08-04)


### Features

* **techvault:** declare Cortex job index as ADR-088 initial service state ([#269](https://github.com/OpenRAE/env-packs/issues/269)) ([d5385f8](https://github.com/OpenRAE/env-packs/commit/d5385f810157a0b64f23e9718529fd54c5066ba0))

## [3.8.0](https://github.com/OpenRAE/env-packs/compare/v3.7.0...v3.8.0) (2026-08-03)


### Features

* **techvault:** author operator-access proxies + capture sidecar as component builds ([7cf97fb](https://github.com/OpenRAE/env-packs/commit/7cf97fbb5cf2a9c0d28d2c98a33cedd53d7dbabb))
* **techvault:** author the indexer internal_users.yml ([58e79a9](https://github.com/OpenRAE/env-packs/commit/58e79a977997bdae76518e503675010ffe7e1417))
* **techvault:** declare aptl-tempo config and startup command ([18d2f10](https://github.com/OpenRAE/env-packs/commit/18d2f101f9102d05e94f78e1600461287c8a2a47))
* **techvault:** declare misp-db and shuffle-opensearch runtime environment ([a1a1211](https://github.com/OpenRAE/env-packs/commit/a1a12111a5ee86bfba9ed32ce2ec2cb2dc8adcdd))
* **techvault:** declare SOC app configs (otel, grafana, cortex, thehive) ([#259](https://github.com/OpenRAE/env-packs/issues/259)) ([d448316](https://github.com/OpenRAE/env-packs/commit/d4483165d59d2df0d9979460b19f3c582dc2887d))
* **techvault:** declare suricata run config + cortex-index-init placement ([#259](https://github.com/OpenRAE/env-packs/issues/259)) ([02314a8](https://github.com/OpenRAE/env-packs/commit/02314a868096cd47fdd3922495972e4b69517c14))
* **techvault:** declare wazuh cluster env desired-state ([#259](https://github.com/OpenRAE/env-packs/issues/259)) ([4ef0569](https://github.com/OpenRAE/env-packs/commit/4ef0569ac35945a6e12452c05a7c51171fdb7988))
* **techvault:** declare wazuh loopback published ports ([c318349](https://github.com/OpenRAE/env-packs/commit/c31834971c30a7659e099422debe1b1cac8f6179))
* **techvault:** declare wazuh sidecar agent environment ([6abf245](https://github.com/OpenRAE/env-packs/commit/6abf245473bb4d9c1fe2697acfefecdc3df34956))
* **techvault:** declare wazuh-dashboard config content ([#259](https://github.com/OpenRAE/env-packs/issues/259)) ([a2a2ddc](https://github.com/OpenRAE/env-packs/commit/a2a2ddc6a11e94b84960233bbf789065e60cc38a))
* **techvault:** declare wazuh-indexer opensearch.yml security config ([#259](https://github.com/OpenRAE/env-packs/issues/259)) ([499bd04](https://github.com/OpenRAE/env-packs/commit/499bd04b72252c67b9891c81a03825bfbae7c62e))
* **techvault:** fully declare cortex-index-init (image, entrypoint, script) ([99973e7](https://github.com/OpenRAE/env-packs/commit/99973e75d311bd5e0131e428326b8d49bfa23cd5))


### Bug Fixes

* **techvault:** align soc-certificate output paths with the issued layout ([f4444a9](https://github.com/OpenRAE/env-packs/commit/f4444a9c605e9882de8b22b59c510e3f4af11fdf))
* **techvault:** declare thehive-es ES env (single-node, security off, 512m heap) ([#259](https://github.com/OpenRAE/env-packs/issues/259)) ([8601f71](https://github.com/OpenRAE/env-packs/commit/8601f71bdccf06994a3e4c434efc42cd8a2f6cc3))
* **techvault:** mark cortex-index-init as one-shot (autoremove) ([#259](https://github.com/OpenRAE/env-packs/issues/259)) ([09ff951](https://github.com/OpenRAE/env-packs/commit/09ff9517cc4ea5b8db505c3c6dc7b63d80230281))
* **techvault:** realize the misp-sync TLS flag and the db-log forwarding source ([74ba39d](https://github.com/OpenRAE/env-packs/commit/74ba39deeb02ff6a89a9e7394905c24112f7f599))
* **techvault:** suricata direct exec, cortex-init ES wait, ad samba caps ([#259](https://github.com/OpenRAE/env-packs/issues/259)) ([32857a9](https://github.com/OpenRAE/env-packs/commit/32857a96c756492ffd8282fb252f0f9027cbe7e0))
* **techvault:** update proxy component-build spec digests ([1d842ce](https://github.com/OpenRAE/env-packs/commit/1d842ce2d7d1a6f7f33ab3621e65b2ccb5293ef3))

## [3.7.0](https://github.com/OpenRAE/env-packs/compare/v3.6.2...v3.7.0) (2026-08-02)


### Features

* **distribution:** add verified pack supply-chain workflows ([#257](https://github.com/OpenRAE/env-packs/issues/257)) ([759ec95](https://github.com/OpenRAE/env-packs/commit/759ec95ccc8d505fd67259701f4a35bedf6674bd))

## [3.6.2](https://github.com/OpenRAE/env-packs/compare/v3.6.1...v3.6.2) (2026-08-02)


### Bug Fixes

* ship TechVault in PyPI distributions ([#253](https://github.com/OpenRAE/env-packs/issues/253)) ([1b5b99c](https://github.com/OpenRAE/env-packs/commit/1b5b99c54ad236c8952ed0fa1669543b6ed4ff20))

## [3.6.1](https://github.com/OpenRAE/env-packs/compare/v3.6.0...v3.6.1) (2026-08-02)


### Bug Fixes

* **deps:** bump websockets from 16.1.1 to 17.0 ([#243](https://github.com/OpenRAE/env-packs/issues/243)) ([6f52cc2](https://github.com/OpenRAE/env-packs/commit/6f52cc2b2fd9215ba83716d2f1e850936764b62f))
* pin RAES 3.3.0 ([#247](https://github.com/OpenRAE/env-packs/issues/247)) ([f900df5](https://github.com/OpenRAE/env-packs/commit/f900df51d69acd1e36bcb426e8d17c1e6afe7696))

## [3.6.0](https://github.com/OpenRAE/env-packs/compare/v3.5.0...v3.6.0) (2026-08-02)


### Features

* add the TechVault environment pack ([#238](https://github.com/OpenRAE/env-packs/issues/238)) ([462dc23](https://github.com/OpenRAE/env-packs/commit/462dc233f5fee801219b28296104c7eff8d7cfaa))


### Bug Fixes

* publish infrastructure kits in env-packs ([#232](https://github.com/OpenRAE/env-packs/issues/232)) ([079cb84](https://github.com/OpenRAE/env-packs/commit/079cb847f58d4da0a88f3ff5156ad1b81f72c33c))

## [3.5.0](https://github.com/OpenRAE/env-packs/compare/v3.4.0...v3.5.0) (2026-08-01)


### Features

* **techvault:** replace subset SDL with the full canonical TechVault scenario ([0122582](https://github.com/OpenRAE/env-packs/commit/012258263f93f11093b71e0be10c2f1dca020e03))
* **techvault:** replace subset SDL with the full canonical TechVault scenario ([7fb9bc5](https://github.com/OpenRAE/env-packs/commit/7fb9bc5dae95e98b7b8597ffa6288c5c668cbe5c))

## [3.4.0](https://github.com/OpenRAE/env-packs/compare/v3.3.0...v3.4.0) (2026-08-01)


### Features

* add reusable infrastructure kit authoring ([#226](https://github.com/OpenRAE/env-packs/issues/226)) ([ff8149d](https://github.com/OpenRAE/env-packs/commit/ff8149da3743ed3b19616cabc0c71a5e5788da0d))
* add TechVault example scenario pack ([#228](https://github.com/OpenRAE/env-packs/issues/228)) ([49a3d56](https://github.com/OpenRAE/env-packs/commit/49a3d56acc974c932518583e8fc0b0002917c431))

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
