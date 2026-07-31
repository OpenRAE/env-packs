# Wizard integration runbook

End-to-end proof for the scaffold wizard (`raes-pack-new`, issue #189). The unit
tests in `tests/test_wizard.py` run in CI and cover the wizard's logic. This
runbook covers the layer unit tests cannot: driving the **real shipped commands**
as subprocesses, scaffolding packs into a real catalog directory, and proving the
pack a consumer receives passes the same static check.

These walkthroughs are deliberately **not** wired into CI. The normal suite is
`unittest discover -s tests`; this harness lives in `tests_integration/`, outside
that path, so it never runs automatically. Run it by hand before merging a change
to the wizard and attach the output to the PR.

## What it proves

- One **non-developer task per primary persona** (hub ADR 0003): AI researcher,
  security researcher, DR/resilience practitioner, product test engineer, AI
  engineer. Each scaffolds a pack through the persona's starter route and the
  pack passes `raes-pack-check`.
- The **machine-readable replay** contract (Hub/MCP): a versioned wizard-input
  document on stdin yields a versioned result on stdout and a valid pack.
- The **no-silent-overwrite** guarantee: a second run against an existing target
  fails instead of clobbering it.

## Run it

From the repository root:

```sh
.venv/bin/python tests_integration/wizard_persona_walkthrough.py
```

Expected tail:

```
28 passed, 0 failed
```

Exit status is `0` when every walkthrough passes, non-zero otherwise. The harness
sets `PYTHONPATH` to the working tree's `src/`, so it exercises your current
changes without a reinstall.

## When to run

- Before merging any change to `src/raes_env_packs/wizard.py` or the packaged
  template resources it selects.
- When adding a starter route or optional capability layer.

## What it does not cover

It validates pack **content** end to end; it does not stand up a live
environment, run pack code, or contact a backend. RAES and the runtime own that.
Route the deeper checks through `raes-pack-validate` and `raes-pack-release`.
