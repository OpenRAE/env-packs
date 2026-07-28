# `ctfd/` — reference CTFd loader

The reference loader that maps `flags/placement.yaml` + `challenges/challenges.yaml`
onto CTFd's challenge / hint / scoring model. **Required-if-present** with the
rest of the flag layer — ship it whenever the pack ships flags.

It is *a reference*: a consumer uses it as-is, adapts it, or discards it in
favor of their own loader.
