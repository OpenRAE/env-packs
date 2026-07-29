# Pack Issue Skeleton Script

`raes-pack-issue-skeleton` creates the standard top-level GitHub issues for a new
environment-pack effort, so you start from a consistent set to edit, refine, and
split into child issues. It is a GitHub issue helper only — it does not scaffold
files; use `raes-new-pack` for the pack source skeleton.

It defaults to dry-run, so you can review the plan before anything is created:

```sh
raes-pack-issue-skeleton \
  --pack-id example-pack \
  --title "Example Pack" \
  --milestone-title "Environment pack: Example Pack" \
  --source "Source label: https://example.invalid/source" \
  --focus "One sentence describing what the participant does."
```

Add `--apply` (and `--create-milestone` for a new milestone) once the dry-run
output looks right:

```sh
raes-pack-issue-skeleton \
  --pack-id example-pack \
  --title "Example Pack" \
  --milestone-title "Environment pack: Example Pack" \
  --create-milestone \
  --source "Source label: https://example.invalid/source" \
  --focus "One sentence describing what the participant does." \
  --apply
```

If the milestone already exists, pass its number instead:

```sh
raes-pack-issue-skeleton \
  --pack-id example-pack \
  --title "Example Pack" \
  --milestone-number 42 \
  --apply
```

The skeleton issues are:

- scenario contract and pack skeleton
- topology, assets, and reference-triangle design
- RAES participant/attacker behavior specification and reference proof
- flag, challenge, and reference CTFd layer
- delivery profile bundles
- golden live-infrastructure build
- automated live rehearsal
- final manual participant walkthrough
- final docs, status, evidence, and teardown reconciliation

Re-running skips existing skeleton issues by title, so it won't overwrite edits.
Pass `--refresh-existing` only when you deliberately want to reapply the current
template body to existing skeleton issues.

Extra labels are applied only if they already exist in the repository:

```sh
raes-pack-issue-skeleton \
  --pack-id example-pack \
  --milestone-number 42 \
  --label scenario:example-pack
```
