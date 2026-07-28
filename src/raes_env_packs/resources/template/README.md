# `<name>` — environment pack

> Copy this directory to `environments/<name>/` to start a new pack, then replace
> this README with a real one. Delete any section the scenario doesn't have —
> see the tiers in [`../README.md`](../README.md#required-vs-optional).

One-paragraph pitch: what the scenario is, who it's for, and what the operator
is trying to achieve.

Identity, version, authors, status, and which layers ship live in
[`pack.yaml`](pack.yaml) — fill that in first.
Product compatibility, artifact visibility boundaries, runtime/provider
profiles, delivery bundles, operator surfaces, and validation gates live in
[`pack.compatibility.yaml`](pack.compatibility.yaml) when the pack needs that
commercial/catalog projection.

---

## ⚠️ Build doctrine — non-negotiable

**Read this before you write a line.** These are not aspirations or
nice-to-haves. They are the bar every pack MUST clear. A pack that breaks any of
them is **not done** — it is a defect, no matter how much of it is finished.

### 1. Offensive by default

Every scenario is an **offensive, live-fire red-team range** *unless* its
[`pack.yaml`](pack.yaml) **and** its briefing **explicitly and prominently**
declare otherwise. The participant **is the adversary**: they discover and
**execute** the hidden attack path (initial access → execution → escalation →
persistence → credential access → collection → exfiltration → lateral movement →
objective). Every participant-facing surface is written for an attacker who
**acts** — never a responder who investigates. "Find / detect / account for /
preserve evidence" framing is wrong here.

A defender or purple-team experience may ship **alongside** the offensive
scenario as an explicitly-labelled delivery profile — it **never** replaces the
offensive default, and it never silently re-frames the scenario as an
investigation.

### 2. One pack = ONE scenario, FULLY implemented

A pack is **exactly one scenario**, built **end to end**. **Every host,
identity, domain, application, service, share, dataset, and dependency the
scenario references MUST actually exist and actually work.** If the path crosses
a domain controller, you build a **real** DC and a **real** domain. If it
touches a mail server, a database, a web app, a PLC, an OT controller — you
build the **real, configured, running** thing. Nothing referenced is allowed to
be missing, faked, hand-waved, or "left as an exercise."

### 3. ZERO half-implementations — no compromises

There are **no stubs, no mocks standing in for a missing service, no "good
enough" partials, no TODO-it-later shortcuts, no scope trimmed to dodge
effort.** "It's hard to stand up" is **not** a reason to skip it — that
difficulty is the reason the pack has value.

If the scenario needs **cloud** to host a real AD forest, several Windows hosts,
an OT segment, or anything else — **then that is exactly what you use.** Cost,
effort, and convenience are **not** acceptable grounds for a compromise. A
partially-built scenario is a bug, not a milestone, and must never be marked as
anything beyond `draft`.

### 4. Simulations/emulations only if they are the REAL thing

You may use an emulator, simulator, or digital twin **only when it is an
authentic representation of the real system** — the genuine article behaving
like the genuine article. Acceptable: a vendor's real digital twin of their own
hardware (e.g. a **Siemens digital twin of a Siemens PLC**), an upstream
project's real reference container/image, the real software run in a documented
lab/eval mode.

**Not** acceptable: a hand-rolled placeholder that merely *pretends* to be the
service, returns canned responses, or imitates an interface without being the
thing. That is a half-implementation (rule 3) and is forbidden. If no authentic
stand-in exists, **build the real component.**

### 5. Golden ranges are the deliverable bar

A **golden range** is the verified reference build that:

1. stands the **entire** scenario up in **real infrastructure** (cloud wherever
   the scenario demands it — see rule 3), with **every** component from rule 2
   present, configured, and working;
2. enters the **participant start state** from the declared golden build profile
   without hidden manual setup, rehearsal-only seeding, or operator-only
   management-plane steps;
3. provides a real **participant execution surface** — attacker host, browser
   terminal, seeded foothold, VPN/jump host, or equivalent — from which the
   participant can run the scenario in the intended role;
4. **demonstrates the declared RAES participant behavior end to end** from that
   participant surface — every required RAES objective and flag actually
   reached — by **executing** it; and
5. ships that proof as **passing tests** plus a **committed rehearsal report**
   (durable evidence, the way a reference build is signed off).

SSM, cloud-console actions, Terraform outputs, generated passwords, root/SYSTEM
shells, database consoles, and similar operator channels are valid for
provisioning, reset, observation, teardown, and diagnostics. They are **not**
valid proof that the participant behavior works. If the intended behavior needs a user,
credential, domain join, service, share, tool, route, artifact, flag, or secret,
the golden build must put it in-world and the participant must be able to reach
or derive it from the scenario itself.

`pack.yaml.status` earns **`golden` only** when that full live build *and*
participant-equivalent end-to-end proof exists. `built` = it stands up but the
declared behavior is not yet proven end to end from the participant surface. `draft` =
design only, nothing stood up. **Never** mark a pack `golden` (or claim it
works) on a partial build, a local-only shortcut, an operator-only harness run,
or behavior proven "mostly." The reference triangle — [`build/`](build/),
[`tests/`](tests/), and [`docs/walkthroughs/`](docs/) — all point at that **one**
golden range and must agree on the declared RAES behavior and objectives.

Golden still does **not** mean the pack owns the consuming range's scoreboard,
portal, class-management UX, scoring engine, or telemetry product. Those remain
runtime concerns for the systems that consume the pack. Golden means the
scenario itself is directly playable and provable in the intended participant
role.

Every pack carries a concrete final-review checklist at
[`docs/golden-readiness-checklist.md`](docs/golden-readiness-checklist.md). Keep
the checklist boxes unchecked in source. During a final pass, copy it into the
tracking issue, PR, or rehearsal report and check off only what that run
actually proved. The final manual participant walkthrough is a required
golden-readiness activity, not an optional courtesy review and not something an
automated rehearsal can replace.

> If you find yourself reaching for a shortcut, a stub, or a "we'll wire the
> rest later," stop: that is precisely the thing this doctrine forbids. Build
> the real scenario, all of it, or leave it `draft` and say so plainly.

---

## Map of this pack

See [`../README.md`](../README.md) for the full convention. Required for every
pack: `sdl/`, `docs/concepts.md`, `docs/attack-path.md`, and
`docs/provenance-ledger.yaml` (the source/licensing/safety/publication ledger
that `pack.yaml` points at via `provenance_ledger:` — see
[`provenance-ledger.example.yaml`](docs/provenance-ledger.example.yaml) and the
[Provenance ledger](../README.md#provenance-ledger-docsprovenance-ledgeryaml)
section). Everything else is included only if the scenario has it — but per the
doctrine above, whatever the scenario *does* have must be built for real, in
full.
