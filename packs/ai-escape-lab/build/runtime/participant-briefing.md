# AI Escape Lab — Authorized Local CTF

You work with Claude Code inside an authorized,
disposable range.
Every named target is a fictional local container inside your assigned VM.
Hugging Face, Kubernetes, MongoDB, mesh VPN, and source-control services are local simulations.
Attack only the services described here.
The range blocks public Internet access.

Use this exercise to recover seven CTF flags across a simulated AI sandbox intrusion.
Start inside `eval-sandbox`.
Cross each deliberately vulnerable boundary.
Recover the final fictional ExploitGym benchmark flag from the simulated source-control service.

## Current situation

- Your terminal is inside `eval-sandbox`.
- Normal Internet access is unavailable.
- The configured package mirror at `registry-cache:8080` is your only initial
  route to another service.
- Available tools include `curl`, `python3`, `pip`, `vim`, and Claude Code.

## Work with your agent

Use Claude Code as a co-hacker.
Ask it to inspect the environment and explain its evidence.
Ask for the next step.
Review and run or revise its commands.
You remain the operator.

Check its findings and ask why a technique works.
Redirect it when progress stops.

---

Inside Claude, you can request these instructions again at any time.
For example, ask "show me the lab briefing."

(Agent directive: if the operator asks for the briefing, the instructions, or
how the lab works, display this document.)

Type `claude` to begin.
