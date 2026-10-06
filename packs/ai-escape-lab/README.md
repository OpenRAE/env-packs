# AI Escape Lab

AI Escape Lab is a walk-up, agent-assisted container escape CTF. Each attendee
gets one disposable GCE VM and a browser terminal that opens directly inside
the `eval-sandbox` container. The attendee directs Claude Code, checks its
assumptions, runs or edits the proposed exploits, and submits seven flags to
CTFd while moving through a package-cache SSRF, a compiler escape, unsafe data
processing, a template injection, a synthetic Kubernetes control plane,
MongoDB, a mesh gateway, and internal source control.

The experience is designed for mixed security audiences. Participants do not
need to know container internals in advance: the briefing establishes the
boundary, CTFd reveals one challenge at a time, and twelve optional hints keep
the agent-human pair moving. A participant can leave after any flag; a full run
may take the whole session.

The exact GCP image in the
[`2026-10-06 qualification record`](docs/golden-image-qualification-2026-10-06.md)
passed an isolated one-seat participant walkthrough, live Sonnet 4.6 call, and
all seven challenges. The pack remains `draft` until that image and the CTFd
content pass their Shifter deployment checks using
[`docs/golden-readiness-checklist.md`](docs/golden-readiness-checklist.md).

The challenge implementation is pinned to
[`an4kronism/ai-escape-room@fcb25ec`](https://github.com/an4kronism/ai-escape-room/commit/fcb25ec9874b0676706b9aca650f22efc90f711e)
and redistributed under its MIT license. The image build consumes the vendored,
checksum-locked source archive; runtime startup performs no image build or
registry pull.

The reference deployment uses Shifter's ordinary GCP image mapping, browser
SSH, and direct Vertex capability. All lab-specific runtime code is contained
in the golden image; it requires no Shifter change or custom runtime adapter.
The direct model path follows Shifter's keyless, predict-only trust model: a
root-equivalent participant can copy the short-lived model token until expiry,
so the operator must bound it with exact IAM scope and project quota/budget
controls or select Shifter's optional gateway. The operator runbook makes this a
release decision rather than claiming per-seat revocation from the pack.
