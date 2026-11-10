# Documentation checks design

This design describes the documentation checks and the shared authoring skill.
[doc-tools](https://github.com/OpenRAE/doc-tools) 0.1.0 supplies both.
The [style guide](documentation-style-guide.md) gives the writing rules.

## Components

| Component | Interface | Failure behavior |
| --- | --- | --- |
| `make prose` | `BASE`. It selects the Markdown files that HEAD adds or changes since `BASE`. For decision records, it selects only the added records, because an accepted record does not change. | A failed `git diff` stops the target. Both checkers run. A failure of either checker gives a nonzero status. |
| mise | `mise.toml` pins doc-tools and Vale. `mise.lock` records the SHA-256 of each archive. | A digest mismatch stops the installation before extraction. |
| doc-tools STE check | `ste-lint.sh -- FILE...`. The package `.ste.yml` sets the rules. | Findings give status 1. The installer refuses a ste-cli archive with a wrong digest. |
| Vale | `vale -- FILE...` with `.vale.ini`. | Findings at the `error` level give status 1. |
| `DocTools` style | `make prose` copies `vale/DocTools` from the verified package into `.vale/styles/DocTools`. | A missing package stops the target before a check starts. |
| `EnvPacks` style | `.vale/styles/EnvPacks`. It holds the rules that only this repository uses. | Vale reports a broken rule as an error. |
| `docs` CI job | It installs the mise tools and runs `make prose BASE=<base>`. | `verify` fails when `docs` fails. |
| Authoring skill | Claude Code installs `skills/documentation/` at commit `97866fad14d7` as the `doc-tools` plugin, from `.claude/settings.json`. Codex installs the same directory at the same commit. | The agent client reports an installation error. |

doc-tools is a development and CI dependency. The Python package and the packs do not contain it.
The design adds no checker, rule engine, or service.
ste-cli owns the STE checks. Vale owns the style checks.

## Data flows

```mermaid
flowchart LR
  subgraph GH[GitHub releases: external]
    PKG[doc-tools 0.1.0 archive]
    STE[ste-cli 0.10.1 archive]
    TAG[doc-tools commit 97866fad14d7]
  end
  subgraph Host[Developer host or CI runner]
    LOCK[(mise.toml and mise.lock)]
    MISE[mise install]
    DIR[(Verified package directory)]
    MAKE[make prose]
    REPO[(Repository Markdown and .vale)]
    CHECK[ste-cli and Vale]
    OUT[Findings and exit status]
    AGENT[Agent client]
  end
  PKG -- archive --> MISE
  LOCK -- version and SHA-256 --> MISE
  MISE -- verified files --> DIR
  STE -- archive --> DIR
  REPO -- changed paths since BASE --> MAKE
  DIR -- wrapper, configuration, DocTools style --> MAKE
  MAKE -- NUL-separated paths after -- --> CHECK
  REPO -- file text --> CHECK
  CHECK --> OUT
  TAG -- skill files --> AGENT
```

Text alternative: mise reads the pin and the digest from the repository.
It downloads the doc-tools archive and compares the digest before extraction.
The package installer downloads ste-cli and compares its pinned digest before extraction.
`make prose` reads the changed paths from Git and the wrapper and style from the package directory.
The checkers read the files and write findings and an exit status.
The agent client reads the skill at the commit that the `v0.1.0` tag names.

The first trust boundary is between GitHub releases and the host.
The second trust boundary is between the changed file names and the checker options.
Document text does not leave the host.

## Security

| Asset | Threat | Control | Verification |
| --- | --- | --- | --- |
| Host and CI runner | A changed doc-tools archive runs code. | mise compares the archive with the SHA-256 in `mise.lock` before extraction. | A changed digest in `mise.lock` stops `mise install`. |
| Host and CI runner | A changed ste-cli archive runs code. | The doc-tools installer compares a pinned SHA-256 before extraction. | The doc-tools installer tests. |
| `DocTools` style | A second download replaces the verified rules. | The style comes only from the verified package. `.vale.ini` has no `Packages` URL. | Review of `.vale.ini` and the `make prose` behavior test. |
| Checker options | A file name with a space or a leading hyphen changes the arguments. | `git diff -z` and `xargs -0` keep each name intact. `--` ends the options. | The `make prose` behavior test. |
| Merge gate | A checker failure does not stop the gate. | The recipe uses `set -eu` and records the status of each checker. `verify` requires `docs`. | The `make prose` behavior test and the `ci.aggregate` policy. |
| Document text | Text goes to a remote service. | The package configuration turns off the dictionary and the analyzer. | Review of the package `.ste.yml`. |
| Agent client | The plugin loads other repository files, such as an MCP configuration. | The plugin source is the skill directory only. | The installed plugin has one skill and no MCP server. |
| Agent client | A moved tag installs different skill content. | Claude Code and Codex install the skill at a full commit ID. | The installed plugin version is `97866fad14d7`. The Codex skill is equal to the verified release. |

Residual risks:

- mise uses an installed package directory without a new digest check.
  A user who can write the mise data directory can change it.
- The first `mise.lock` record trusts the release at that time.
- The skill installation trusts the Git commit ID. It does not compare a release archive digest.
- A clean check does not prove full ASD-STE100 conformance. Review checks the other rules.
