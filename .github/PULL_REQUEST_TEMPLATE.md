## Summary

<!-- What changed and why, in a sentence or two. -->

## Related issues

<!-- e.g. Closes #123 -->

## Verification

- [ ] `python -m unittest discover -s tests`
- [ ] `raes-pack-validate --repo .`
- [ ] `raes-pack-release check --all`
- [ ] `raes-pack-validate --packs-root packs`
- [ ] `raes-pack-release check --packs-root packs`
- [ ] Docs changed: built `docs/public/` warning-free (`sphinx-build -W`).

## Checklist

- [ ] Keeps RAES semantics in RAES; hosted pack content stays under `packs/`.
- [ ] PR title is a Conventional Commit (a required check enforces it).
- [ ] Did not edit the version or `CHANGELOG.md` — release-please owns them.
