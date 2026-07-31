# Quickstart: scaffold and validate your first pack

Scaffold an environment pack with the wizard and validate it. This takes about
two minutes and creates nothing outside a directory you choose.

## Before you start

- Python 3.11 or newer.
- A catalog repository: a Git repository with an `environments/` directory,
  where your packs live. The wizard writes into it.

Install the package:

```sh
pip install raes-env-packs
```

## 1. Scaffold a pack

From the root of your catalog repository, run the wizard and pick the `minimal`
route:

```sh
raes-pack-new example-pack --route minimal --yes
```

```
created environments/example-pack
validated with the static pack check (minimal route)
```

The wizard generates a **valid** minimal pack — identity, a RAES start state,
and the docs to understand it — and checks it for you before it lands. Preview
any route first with `--preview` (it writes nothing), or drop `--yes` to answer
the questions interactively. See [scaffold a pack](new-pack-script.md) for the
routes and optional layers.

## 2. Check it

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
