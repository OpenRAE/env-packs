## Summary

<!-- What changed and why, in a sentence or two. -->

## Related issues

<!-- e.g. Closes #123 -->

## Verification

- [ ] `python -m unittest discover -s tests`
- [ ] `raes-pack-validate --repo .`
- [ ] `raes-pack-release check --all`
- [ ] Docs changed: built `docs/public/` warning-free (`sphinx-build -W`).

## Checklist

- [ ] Keeps RAES semantics in RAES; adds no pack content or downstream vocabulary here.
- [ ] PR title is a Conventional Commit (a required check enforces it).
- [ ] Did not edit the version or `CHANGELOG.md` — release-please owns them.
