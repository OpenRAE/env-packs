# `tests/` — participant-behavior rehearsal (reference)

Scripts that exercise the declared RAES participant behavior and objectives
against the **live golden AWS range** and confirm each flag. The tests target
the golden range, not an abstraction or a competing semantic model.
**Required-if-present** with the rest of the reference triangle (`build/` +
`docs/walkthroughs/`).

Each tested behavior should have a matching human walkthrough under
`docs/walkthroughs/` — same participant actions, same expected output, same
objective or flag.
