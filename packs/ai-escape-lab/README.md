# AI Escape Lab

AI Escape Lab is a walk-up container escape CTF with a human-directed coding agent.
Each attendee receives one disposable GCE VM and a browser terminal inside `eval-sandbox`.
You direct Claude Code, inspect its evidence, review proposed exploits, and submit seven flags to CTFd.

The lab supports participants with different security experience.
You do not need prior knowledge of container internals.
The participant briefing describes the authorized boundary.
CTFd reveals one challenge at a time and provides twenty-three optional hints.
You can stop after any flag; a complete run can take the full session.

## Start the exercise

Use the browser terminal for your assigned seat.
Read the briefing that appears in `/app`.
Type `claude` to start the agent.
Ask it to show the lab briefing again when necessary.
Review its evidence and commands before you continue.
Attack only the fictional services in your assigned range.

The [concept explanation](docs/concepts.md) describes the learning goals and network boundaries.
It contains no operator solution or exact flag value.

## Source and status

The challenge implementation uses [upstream revision fcb25ec](https://github.com/an4kronism/ai-escape-room/commit/fcb25ec9874b0676706b9aca650f22efc90f711e).
The pack redistributes that source under its MIT license.
The image build consumes the vendored archive and checks its locked checksum.
Runtime startup neither builds images nor pulls from a registry.

The pack remains `draft`.
The isolated image qualification dated 2026-10-06 covered one exact image and one participant seat.
It did not qualify a Shifter deployment, CTFd import, or twelve-seat event.
Current static checks do not establish a new runtime qualification.
The accepted image contains its original briefing; later source edits do not change that image.

The reference integration uses Shifter GCP image mapping, browser SSH, and direct Vertex access.
The golden image contains the lab runtime; it needs no custom Shifter runtime adapter.
Operators must bound model-token permissions and spending under their deployment policy.
A participant with container root access can copy a short-lived model token until expiry.
