# Documentation style guide

How the public docs (`docs/public/`) are written. Follow it so a new page reads
like the rest. The model is [Stripe's documentation](https://docs.stripe.com):
plain, short, and built around a working example.

## Voice

- Write to the reader. Use "you", present tense, and active verbs.
- One idea per sentence. Prefer a short sentence to a long one with a clause.
- Lead with the concrete. A worked example beats a paragraph of abstraction.
- Define a term once, where it first appears. Use it precisely after that.
- Cut hedging and restated context. Say the thing.

## What to avoid

- Opening a page with a boundary statement, a mission, or a caveat wall. State
  what the thing is and what it's for, then the limits.
- Strings of abstract nouns ("the canonical shared contract boundary"). Name the
  concrete thing that does the work.
- Marketing: no "seamless", "powerful", "robust", no roadmap promises, no
  adoption claims.
- Internal process vocabulary (issue numbers, milestones, review state) in
  user-facing prose. That belongs in the developer docs.

## Structure for a task page

An entry page (quickstart, how-to) follows this order:

1. The task and its outcome, in one line.
2. Prerequisites.
3. The exact steps, as commands.
4. What any placeholder means.
5. The real output.
6. The boundary — what the reader has *not* done.
7. A link onward.

## Examples and commands

- Every command is paired with its real output. Run it; do not paraphrase it.
- Examples are synthetic and temporary, created in a scratch directory, as the
  test suite does. This repository never checks in an environment pack.
- Show the smallest example that is genuinely valid, not a toy that would fail.

## Links

- Link freely **between** public pages with relative `.md` paths.
- To reference a developer record (an ADR, CI notes) from a public page, use an
  absolute GitHub URL — never a relative path out of `docs/public/`, which would
  break the build and expose an internal record on the site.

## The boundary is a build gate

`docs/public/` is the only tree the site builds (ADR 0030). Keep internal records
out of it. The docs build is warning-strict and part of the `verify` merge gate,
so a broken cross-reference fails CI, not a reader.
