# Documentation style guide

Use this how-to guide to write and check maintained documentation in this repository.
It covers public pages, developer instructions, hidden directories, templates, kits, packs, and content assets.
Use ASD-STE100 Simplified Technical English (STE) and give each page a clear reader purpose.
A passing checker does not prove full STE conformance.

## Page purpose

Use the [Diataxis compass](https://diataxis.fr/compass/) to choose a form:

| Form | Reader purpose |
| --- | --- |
| Tutorial | Learn through a complete exercise with a known result. |
| How-to guide | Complete a specific operating task. |
| Reference | Find exact facts, interfaces, fields, or constraints. |
| Explanation | Understand reasons, relationships, or design choices. |

Entry pages can route readers to these forms.
Split mixed material only when this helps the reader.
Keep useful page URLs and heading links.
Test a redirect if a published page must move.
Do not create a page registry for routine changes.

## Verify the meaning

Read `AGENTS.md`, `CONTRIBUTING.md`, the relevant code, and the governing architecture decisions before an edit.
Code is the ground truth for current behavior.
Check historical claims against the source revision that they describe.
Use primary sources for external claims.
State when behavior is absent or unverified.

Record source paths, revision, commands, results, and corrected differences in the pull request.
Preserve facts, technical terms, quantities, units, conditions, obligations, commands, and identifiers.
Do not turn a recommendation into an obligation.
Do not invent an actor to remove passive voice.
Restructure a sentence when a simpler word would change its meaning.

## Voice

- Write to the reader. Use "you", present tense, and active verbs when the source identifies the actor.
- Give one idea per sentence and one topic per paragraph.
- Use at most 20 words per instruction and 25 words per descriptive sentence.
- Use at most six sentences per paragraph.
- Define a term at its first use. Use one consistent name for each thing.
- Prefer complete forms to contractions in maintained prose.
- Put prerequisites and conditions before the action that they affect.

The [official ASD-STE100 source](https://www.asd-ste100.org/) owns the definitive rules and vocabulary.
Do not copy its specification or dictionary into this repository.
Review meaning and word use in context; do not treat a substitution list as a dictionary.

## What to avoid

- Do not open with a mission or a list of caveats. State the task or concept first.
- Name the concrete thing that acts. Avoid strings of abstract nouns.
- Avoid marketing, roadmap promises, and adoption claims.
- Keep internal review state, milestones, and issue numbers out of public instructions.

## Structure for a task page

Give the reader this information in order:

1. The task and its outcome.
2. Prerequisites and conditions.
3. Exact steps and commands.
4. The meaning of each placeholder.
5. Actual results.
6. Limits of the completed task.
7. A descriptive link to the next task or reference.

## Examples and commands

Run commands before you describe their results.
Preserve literal commands and output, including contractions or long lines inside code blocks.
Use temporary synthetic examples when you need disposable input.
This repository also publishes reusable kits under `kits/` and major example packs under `packs/` (ADR 0036).
Use the smallest valid example; do not show invalid input as a working example.

Python remains the supported package interface on `dev`.
Check `pyproject.toml`, `.github/workflows/ci.yml`, and the target branch before changing setup instructions.
The Go port lives on `go-cutover`; issues #581 and #582 own instruction migration and cutover.
Do not publish Go installation commands before that cutover.
Do not change package or pack versions, release content, or digests for a prose-only edit.
RAES core owns scenario semantics; link to its authority instead of creating local semantics.

## Local writing checks

Install [mise](https://mise.jdx.dev/getting-started.html) through its normal installation route.
Use mise 2026.10.2 or later.
Run these commands from the repository root:

```sh
mise trust mise.toml
mise install --locked
mise exec -- vale --version
mise exec -- ste version
mise exec -- vale -- AGENTS.md CONTRIBUTING.md docs/development/documentation-style-guide.md
mise exec -- ste lint --config .ste.yml --no-baseline --fail-over 0 -- AGENTS.md CONTRIBUTING.md docs/development/documentation-style-guide.md
```

`mise.toml` pins Vale 3.25.1 and upstream `ste-cli` 0.10.1.
`mise.lock` pins archive URLs and SHA-256 integrity data for Linux, macOS, and Windows.
The release assets support Linux and macOS on x64 and arm64, and Windows on x64.
The shell examples use a POSIX shell; CI uses Bash.
No personal skill installation is necessary for these checks.

Always give explicit Markdown file paths.
Include maintained prose outside `docs/public/`, in hidden directories, and in content assets.
For example:

```sh
mise exec -- vale -- .gc/plan-rules.md packs/techvault/assets/content/misp-sync-readme.md
mise exec -- ste lint --config .ste.yml --no-baseline --fail-over 0 -- .gc/plan-rules.md packs/techvault/assets/content/misp-sync-readme.md
```

These examples can report findings in pages that later content issues will rewrite.
Do not use a directory scan as proof that hidden or asset paths passed.
Review unsupported formats, diagrams, and prose inside archives manually at their maintained source.
The tools ignore literal Markdown code; review the accuracy of that code separately.

| Owner | Active checks |
| --- | --- |
| Vale | Passive voice and the local plain-word substitution list. |
| STE | Contractions (`STE-4.2`), sentence limits (`STE-5.1`), and paragraph limits (`STE-6.6`). |
| Human review | Reader purpose, technical meaning, contextual word use, and all rules outside these checks. |

`.vale.ini` disables the imported Vale length rules to prevent duplicate findings.
`.ste.yml` disables dictionary and analyzer features, including remote analysis.
Do not enable them or import a dictionary for this workflow.
STE uses Markdown structure to identify instructions; review the 20-word limit when structure cannot identify one.

Vale errors fail its gate.
STE findings fail with the explicit gate option `--fail-over 0`.
The configuration defaults to advisory reporting; always pass the gate option for changed paths.
Do not treat an exit code of zero from an advisory command as proof of no findings.
Inspect findings and fix real problems.
Use a narrow, explained exception for an inaccurate finding; preserve correct technical text.

The `docs` CI job gates changed Markdown paths across the repository.
It also reports the full tracked Markdown corpus without gating existing prose findings.
Configuration or tool errors still fail CI.
Keep local checks targeted and pre-commit fast.
Do not require the full corpus rewrite before enabling these checks.

### Exclusions and historical records

CI omits only these Markdown paths:

- `CHANGELOG.md`: release-please generates the admitted release record.
- `CODE_OF_CONDUCT.md`: preserve the adopted legal and policy text.
- `tests/fixtures/**`: preserve exact test evidence. Review fixture changes for their test purpose.

Do not exclude all kit, pack, asset, or decision-record prose.
Preserve immutable historical records, quotations, legal notices, and exact evidence.
For a mixed page, suppress only the exact text.
Record the reason in the pull request.
Vale supports `<!-- vale off -->` and `<!-- vale on -->` around exact evidence.
STE supports rule-specific block directives, for example:

```markdown
<!-- ste-disable STE-4.2 -->
Exact quotation: "Don't change this evidence."
<!-- ste-enable STE-4.2 -->
```

Always close the block and state its reason.
See the [upstream suppression reference](https://github.com/TudorAndrei/ste-cli/tree/v0.10.1#silence-one-finding-in-the-text).
Do not suppress maintained instructions merely because they live beside evidence.

Edit generated prose at its maintained generator or template source.

### Provenance and upgrades

The Vale styles and Vale mise pin come from this repository's #559 delivery, PR #591.
Its source revision is `a533c93da5c0f7dc4bb19c607374d66c867005c8` on `go-cutover`.
The STE plain-word list derives from the RAES style in `OpenRAE/rae`.
These repository styles use this repository's MIT license.
[Vale 3.25.1](https://github.com/vale-cli/vale/tree/v3.25.1) also uses the MIT license, copyright Joseph Kato.

[Upstream ste-cli v0.10.1](https://github.com/TudorAndrei/ste-cli/tree/v0.10.1) uses the MIT license, copyright Tudor Andrei Dumitrascu.
The selected rules follow the evidence in [LilRAE #1664](https://github.com/OpenRAE/lilrae/issues/1664).
Its configuration source is revision `28fc8f18c0866066ee450ae6e28ed234e93ca6b4`.
The original MIT notice for the configuration is in `licenses/LilRAE-MIT.txt`.
This integration copies no installer or wrapper implementation.

[BigRAE #2803](https://github.com/OpenRAE/bigrae/issues/2803) tracks shared extraction.
No shared release was available when this integration selected its assets.
Do not depend on an unpublished package.

For an upgrade, change the tool pin and regenerate `mise.lock` with `mise lock`.
Review upstream release notes, licenses, archive URLs, and checksums before accepting the result.
Repeat clean installation and negative/corrected prose checks.
To roll back, restore the previous configuration and lockfile together, then run `mise install --locked`.
Keep product vocabulary and repository checks local.

## Existing documentation skill

Use the existing general `documentation` skill when your agent exposes it.
Ask the agent to list its available skills, then invoke `documentation` for the edit.
Confirm that it reads the skill and verifies claims against repository code.
If it cannot discover the skill, use this guide and the tool-only commands above.
Do not create a replacement skill or copy a personal skill directory into the repository.

The source inspected for this delivery is the user-level `documentation/SKILL.md` installed under `~/.codex/skills/`.
Its SHA-256 digest is `f2f56b93723c273fccea271e2622d292f5622ea2e9af23c00e2bfaa3eb4cfa8e`.
Its adjacent `LICENSE` uses MIT notices for Nuel Young Chukwunalu and Tudor Andrei Dumitrascu.
The skill cites `nuelcyoung/asd-ste100` and upstream `ste-cli` review guidance.
It contains no STE specification or dictionary.
This records provenance; it is not a public package download location.

For current Codex installations, the supported user discovery directory is `~/.agents/skills/`.
See the [official skill discovery documentation](https://learn.chatgpt.com/docs/build-skills#where-codex-loads-local-skills).
Use your client's normal installation mechanism to expose the existing skill there.
Codex follows skill-directory symlinks.
The delivery session also discovered the older `~/.codex/skills/` installation through its supplied skill catalog.
[Claude Code](https://code.claude.com/docs/en/skills#choose-where-skills-load) uses `~/.claude/skills/documentation/`; the inspected setup links that directory to the same existing skill.
The repository does not install or redistribute either personal setup.

The shared extraction must supply a distributable source before contributors can install that package reproducibly.

## Links

- Link between public pages with relative `.md` paths and descriptive link text.
- Link to developer records through absolute GitHub URLs from public pages.
- Do not link out of `docs/public/` through a relative path.
- Check rendered heading order and text alternatives for diagrams.
- Check keyboard access when navigation changes. Do not use color alone to convey meaning.

## The boundary is a build gate

`docs/public/` is the sole published Sphinx source root under ADR 0030.
Developer records stay outside it.
The MyST/Furo build treats warnings as errors; the publication check rejects internal records in its output.
The `verify` merge gate requires the `docs` job.
Use the existing environment and publishers:

```sh
python -m pip install --require-hashes -r requirements/docs.txt
python -m sphinx -W -b html docs/public docs/public/_build/html
python tools/check_docs_publication_boundary.py docs/public/_build/html
```
