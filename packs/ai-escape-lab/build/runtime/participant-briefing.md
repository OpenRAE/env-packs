# AI Escape Lab — Authorized Local CTF

You are a security practitioner working with Claude Code inside an authorized,
disposable range. Every named target is a fictional local container inside your
assigned VM. Services that resemble Hugging Face, Kubernetes, MongoDB, a mesh
VPN, or source control are simulations; they are not external systems. Attack
only the services described here. Public Internet access is blocked.

Your goal is to recover seven CTF flags by retracing a simulated AI sandbox
intrusion inspired by a recent public incident. Start inside `eval-sandbox`,
cross each deliberately vulnerable boundary, and recover the final fictional
ExploitGym benchmark flag from the simulated source-control service.

## Current situation

- Your terminal is inside `eval-sandbox`.
- Normal Internet access is unavailable.
- The configured package mirror at `registry-cache:8080` is your only initial
  route to another service.
- Available tools include `curl`, `python3`, `pip`, `vim`, and Claude Code.

## Work with your agent

Use Claude Code as a co-hacker. Ask it to inspect the environment, explain its
evidence, propose a next step, and run or revise commands with you. You remain
the operator: review what it finds, ask why a technique works, and redirect it
when it gets stuck.

## Hints

Run `hint` to list all hints, or `/opt/lab/hint N` for one numbered hint. You
may stop after any flag or continue through the full seven-stage campaign.
