# Quickstart: validate your first pack

Scaffold an environment pack, add a scenario start state, and validate it. This
takes about five minutes and creates nothing outside a directory you choose.

## Before you start

- Python 3.11 or newer.
- A catalog repository: a Git repository with an `environments/` directory,
  where your packs live. The scaffolder writes into it.

Install the package:

```sh
pip install raes-env-packs
```

## 1. Scaffold a pack

From the root of your catalog repository:

```sh
raes-new-pack example-pack \
  --title "Example Pack" \
  --description "A tiny example environment pack." \
  --issue 154
```

```
created environments/example-pack
next steps:
  - edit environments/example-pack/pack.yaml
  - replace environments/example-pack/README.md with scenario-specific prose
  - fill environments/example-pack/sdl/ and environments/example-pack/docs/
  - use environments/example-pack/docs/golden-readiness-checklist.md for milestone planning
```

The scaffold is intentionally incomplete. It gives you the layout and the
required files, but you supply the two things only you know: the scenario, and
where its content came from.

## 2. Add a scenario start state

A pack describes its environment in [RAES SDL](environment-packs.md#the-scenario-start-state).
Write the smallest valid start state to `sdl/example.sdl.yaml`:

```yaml
name: example-pack
nodes:
  target:
    type: vm
```

## 3. Name the pack in its provenance ledger

Every pack ships a provenance ledger — the record of its sources, licensing, and
safety attestations. Open `environments/example-pack/docs/provenance-ledger.yaml`
and set the pack name to match the directory:

```yaml
pack:
  name: example-pack
```

## 4. Check it

`raes-pack-check` is the check a consumer runs before trusting a pack. It reads
the staged files and reports what it finds — no pack code runs and nothing
reaches the network.

```sh
raes-pack-check environments/example-pack
```

```
pack: example-pack
OK — no blocking problems found.
```

`OK` means the pack matches the contract: its identity, its provenance ledger,
and its start state all check out. If something is wrong, each problem comes with
where it is and how to fix it; see [check a pack](checking.md) for the exit codes
and JSON output. The same check is available as the
[`validate_pack` API](validating.md) when you want a result object instead.

## What you have not done

You have validated a pack's *content*, not stood up its environment. `raes` and
the runtime own that. You also have not run the fuller author checks — those add
the reference tests and release gates. See
[validating a pack](validating.md) for the difference between the two surfaces,
and [what a pack is](concepts.md) for the whole format.
