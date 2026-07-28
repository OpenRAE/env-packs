#!/usr/bin/env python3
"""Create the standard GitHub issue skeleton for an environment pack.

The script is for the start of a pack design effort. It creates the broad
planning issues every pack needs, then the designing agent can edit those
issues, add child issues, or close optional layers as not planned.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import textwrap
from dataclasses import dataclass
from collections.abc import Callable

DEFAULT_REPO = "RAESystem/env-packs"
PACK_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")

LABEL_DOCUMENTATION = "documentation"
LABEL_AREA_CONTENT = "area:content"
LABEL_AREA_EMULATION = "area:emulation"
LABEL_AREA_INFRA = "area:infra"
LABEL_AREA_OPERATOR = "area:operator"
LABEL_AREA_PRODUCT = "area:product"
LABEL_AREA_VALIDATION = "area:validation"
LABEL_TIER_RAES = "tier:raes"


@dataclass(frozen=True)
class PackPlan(object):
    """PackPlan."""
    pack_id: str
    title: str
    focus: str
    sources: tuple[str, ...]
    labels: tuple[str, ...]
    milestone_number: int | None = None
    milestone_title: str | None = None


@dataclass(frozen=True)
class IssueTemplate(object):
    """IssueTemplate."""
    key: str
    suffix: str
    labels: tuple[str, ...]
    renderer: Callable[[PackPlan], str]
    legacy_suffixes: tuple[str, ...] = ()


@dataclass(frozen=True)
class Operation(object):
    """Operation."""
    action: str
    title: str
    body: str | None = None
    labels: tuple[str, ...] = ()
    issue_number: int | None = None
    milestone_number: int | None = None
    milestone_title: str | None = None


COMMON_ANCHORS = """\
## Contract Anchors
- The bundled layout contract (`contract/pack-layout.md` in the `raes-env-packs` package): authoritative
  environment-pack convention and milestone structure.
- The bundled template (copied by `raes-new-pack`): build doctrine - offensive by default, one full scenario per
  pack, no stubs or hand-waved services, and `golden` only after participant-equivalent proof.
- `docs/environment-packs.md`: pack metadata, provenance ledger, compatibility manifest, RAES participant behavior,
  profile bundles, and release boundaries.
- `docs/golden-readiness.md`: isolated golden infrastructure, automated rehearsal, final manual participant walkthrough,
  and teardown proof.
"""


def clean(body: str) -> str:
    """Clean."""
    body = textwrap.dedent(body).strip()
    lines = [line[4:] if line.startswith("    ") else line
             for line in body.splitlines()]
    return "\n".join(lines).strip() + "\n"


def title_from_pack_id(pack_id: str) -> str:
    """Title from pack id."""
    return " ".join(part.capitalize() for part in pack_id.split("-"))


def validate_pack_id(pack_id: str) -> None:
    """Validate pack id."""
    if not PACK_ID_RE.fullmatch(pack_id):
        raise SystemExit(
            "pack id must be lowercase kebab-case, start/end with a letter or "
            "digit, and contain only a-z, 0-9, and '-'")


def bullets(lines: tuple[str, ...]) -> str:
    """Bullets."""
    if not lines:
        return "- Source log TBD by the pack-design agent."
    return "\n".join(f"- {line}" for line in lines)


def pack_block(plan: PackPlan) -> str:
    """Pack block."""
    return clean(f"""\
    ## Pack
    - Pack id: `{plan.pack_id}`
    - Pack root: `environments/{plan.pack_id}/`
    - Working title: {plan.title}
    - Scenario focus: {plan.focus}

    ## Source Log
    {bullets(plan.sources)}
    """)


def child_issue_note() -> str:
    """Child issue note."""
    return clean("""\
    ## Child Issue Guidance
    This is a skeleton planning issue. The pack-design agent should edit this
    issue as the design becomes concrete and add child/slice issues for
    scenario-specific hosts, services, data sets, tooling, or proof gaps that
    are too large for one PR.
    """)


def contract_body(plan: PackPlan) -> str:
    """Contract body."""
    return clean(f"""\
    ## Goal
    Create the `{plan.pack_id}` scenario contract and pack skeleton under the current pack doctrine.

    {pack_block(plan)}
    {COMMON_ANCHORS}
    ## Deliverables
    - Set `pack.yaml.requirement` to your upstream requirement id if you track one, or `null`; do not synthesize a UID.
    - Scaffold `environments/{plan.pack_id}/` from the bundled template with `raes-new-pack`.
    - Fill `pack.yaml`, `pack.compatibility.yaml`, and `docs/provenance-ledger.yaml` with truthful initial metadata.
    - Replace template prose in `README.md`, `docs/concepts.md`, `docs/attack-path.md`, and `docs/lineage.md`.
    - Record source adaptation decisions: what is used, excluded, changed, or locally designed.

    ## Acceptance Criteria
    - The pack has the required minimum source shape: `pack.yaml`, `sdl/`, `docs/concepts.md`, `docs/attack-path.md`,
      and `docs/provenance-ledger.yaml`.
    - Participant-facing framing is offensive by default unless the pack and briefing explicitly declare otherwise.
    - `pack.yaml.status` remains `draft` until a real live build exists.

    {child_issue_note()}
    """)


def topology_body(plan: PackPlan) -> str:
    """Topology body."""
    return clean(f"""\
    ## Goal
    Define the real topology, assets, participant surface, and reference-triangle design for `{plan.pack_id}`.

    {pack_block(plan)}
    {COMMON_ANCHORS}
    ## Deliverables
    - `sdl/` start-state model naming every required host, identity, domain, application, service, share, dataset,
      route, credential, tool, dependency, and objective state.
    - `assets/` content for planted artifacts, briefing material, synthetic credentials, target data, and custom
      service/container source.
    - Reference-triangle design mapping the same path into `build/`, `tests/`, and `docs/walkthroughs/`.
    - Participant execution surface design: attacker host, browser terminal, seeded foothold, VPN/jump access, or
      equivalent.
    - Live-build isolation design: dedicated VPC/subnets or equivalent isolation, no default-VPC golden range, and no
      private-DNS endpoints in shared VPCs.

    ## Acceptance Criteria
    - Every referenced component has a real implementation plan.
    - Local/minimal profiles are marked as degraded aids and cannot replace the golden build.
    - The design shows how the golden build creates participant start state without hidden manual setup or required
      repo-root `.env`.

    {child_issue_note()}
    """)


def behavior_body(plan: PackPlan) -> str:
    """RAES participant-behavior body."""
    return clean(f"""\
    ## Goal
    Specify RAES participant behavior for the attacker in `{plan.pack_id}`.

    {pack_block(plan)}
    {COMMON_ANCHORS}
    ## Deliverables
    - RAES `agents`, `behavior_specifications`, and `action_contracts` that identify the attacker participant and the
      governed actions available to that participant.
    - RAES preconditions, effects, failure classes, observation boundaries, outcome interpretation rules, objectives,
      evidence requirements, and workflows needed to describe the intended behavior.
    - Pack-local explanatory design prose mapping clues, credentials, tools, planted artifacts, privileges, routes,
      services, and data to concrete RAES SDL and `assets/` references without defining a second semantic model.
    - Reference tests and walkthroughs that execute the declared behavior from the participant surface against the live
      golden build.

    ## Acceptance Criteria
    - The hydrated RAES SDL is the only machine-readable scenario specification; no pack-side behavior or reachability
      schema is introduced.
    - RAES validation accepts every participant-behavior reference and rejects unresolved semantic references.
    - Live rehearsal and the participant walkthrough demonstrate that the reference build realizes the declared RAES
      behavior and objectives from the intended participant privilege context.

    {child_issue_note()}
    """)


def flag_body(plan: PackPlan) -> str:
    """Flag body."""
    return clean(f"""\
    ## Goal
    Add the all-or-nothing flag, challenge, and reference CTFd layer for `{plan.pack_id}` when the scenario has flags.

    {pack_block(plan)}
    {COMMON_ANCHORS}
    ## Deliverables
    - `flags/placement.yaml` with one entry per flag and stable `flag_id`s.
    - `challenges/challenges.yaml` with participant-facing challenge text keyed by the same `flag_id`s.
    - `ctfd/` reference loader and tests.
    - Validator coverage reconciling flags to RAES objectives, topology assets, challenges, and CTFd output.

    ## Acceptance Criteria
    - `pack.yaml.contents.flag_layer: true` only when `flags/`, `challenges/`, and `ctfd/` all ship together.
    - A flag is proof of executing the path or reaching the gated objective context.
    - If this pack intentionally has no flag layer, close this issue as not planned only after pack metadata says so.

    {child_issue_note()}
    """)


def profile_body(plan: PackPlan) -> str:
    """Profile body."""
    return clean(f"""\
    ## Goal
    Add delivery/audience profile bundles for `{plan.pack_id}` when the pack has multiple audiences.

    {pack_block(plan)}
    {COMMON_ANCHORS}
    ## Deliverables
    - `profiles/bundles.yaml` with supported bundle rows and entrypoints.
    - Guided, unguided, purple-team, agent-benchmark, and demo content as applicable.
    - `profiles/validate_*.py` plus tests for manifest consistency, participant/operator split, leak scanning, and
      compatibility joins.
    - Matching `pack.yaml.contents.profile_bundles`, `profile_bundles:` index, and
      `pack.compatibility.yaml.delivery_bundles` rows.

    ## Acceptance Criteria
    - Selecting a profile changes content exposure only; it does not create a second scenario specification or a second
      golden proof.
    - Participant files do not disclose operator-only action ordering, raw evidence, answers, credentials, flags, or
      next-step hints.
    - If this pack intentionally has no profile layer, close this issue as not planned only after pack metadata says so.

    {child_issue_note()}
    """)


def build_body(plan: PackPlan) -> str:
    """Build body."""
    return clean(f"""\
    ## Goal
    Implement the `{plan.pack_id}` golden build in the declared live infrastructure.

    {pack_block(plan)}
    {COMMON_ANCHORS}
    ## Deliverables
    - `build/` implementation for the golden runtime profile.
    - Every referenced host, identity, domain, application, service, share, dataset, route, tool, credential, flag, and
      objective state created from committed pack source.
    - Participant entry surface provisioned by the build.
    - Reset, rebuild, cleanup, teardown, and operator diagnostics.
    - `pack.compatibility.yaml` runtime profile, platform feature, validation, and artifact-boundary
      references updated to point at actual build surfaces.

    ## Acceptance Criteria
    - A clean checkout can apply the golden build using committed pack content plus approved cloud/operator credentials
      only.
    - The build enters participant start state without hidden manual setup, rehearsal-only seeding, generated-password
      shortcuts, or operator-only management-plane actions.
    - The scenario may move to `built` only when it stands up; it remains short of `golden` until participant-equivalent
      proof and evidence complete.

    {child_issue_note()}
    """)


def rehearsal_body(plan: PackPlan) -> str:
    """Rehearsal body."""
    return clean(f"""\
    ## Goal
    Add automated live rehearsal for the `{plan.pack_id}` golden build.

    {pack_block(plan)}
    {COMMON_ANCHORS}
    ## Deliverables
    - `tests/` or build-local rehearsal tooling targeting the same declared golden runtime profile as the build issue.
    - Automated checks for setup health, participant start state, RAES objectives and behavior, flags when present,
      negative gates, reset/persistence behavior, and cleanup.
    - Durable rehearsal report committed under `docs/`.
    - Walkthrough alignment checks or explicit trace showing that automated steps and future human walkthroughs cover
      the same path.

    ## Acceptance Criteria
    - Rehearsal runs against the live golden build profile, not an abstraction or degraded local-only shortcut.
    - Operator transports are used only for provisioning, observation, diagnostics, reset, or teardown.
    - The rehearsal does not inject secrets, flags, users, data, or services that the golden build should have placed
      in-world.

    {child_issue_note()}
    """)


def manual_body(plan: PackPlan) -> str:
    """Manual body."""
    return clean(f"""\
    ## Goal
    Run the final manual participant walkthrough for `{plan.pack_id}` as its own golden-readiness slice.

    {pack_block(plan)}
    {COMMON_ANCHORS}
    ## Deliverables
    - Stand up the declared golden range from a clean checkout.
    - Enter only through the participant execution surface.
    - Work the intended happy path manually, command by command, from the intended participant privilege context.
    - Record commands, expected output, objective/flag proof, defects, fixes, reruns, and remaining limitations.
    - After the manual path works, run automated rehearsal, run static/unit checks, tear down the range, and verify
      cleanup.

    ## Acceptance Criteria
    - No SSM, cloud console, Terraform output, generated password, root/SYSTEM shell, database console, or test harness
      shortcut is used as proof of participant completion.
    - Every required RAES objective, flag, and success condition is reached from the intended participant role.
    - The copied golden-readiness checklist identifies exactly what was manually proven, what was automated, and what
      remains out of scope.

    {child_issue_note()}
    """)


def final_body(plan: PackPlan) -> str:
    """Final body."""
    return clean(f"""\
    ## Goal
    Reconcile final docs, status, evidence, release metadata, and teardown state for `{plan.pack_id}`.

    {pack_block(plan)}
    {COMMON_ANCHORS}
    ## Deliverables
    - Update `pack.yaml` status and `contents` only to match proven reality.
    - Update `pack.compatibility.yaml` runtime profiles, delivery bundles, artifact boundaries, operator surfaces,
      and validation gates.
    - Reconcile README, concepts, attack path, lineage, walkthroughs, golden-readiness checklist, provenance review
      gates, and evidence reports.
    - Remove stale TODOs, old emulation-plan-only language, misleading local-only claims, and references to superseded
      issues.
    - Run static content gates and pack release checks when artifact boundaries exist.
    - Verify teardown evidence and ensure no live range resources remain.

    ## Acceptance Criteria
    - Build, tests, walkthroughs, RAES SDL, flags, profiles, compatibility metadata, and provenance agree on declared
      behavior, objectives, and artifact boundaries.
    - Participant-visible exports are leak-scanned and do not include restricted operator state, answers, credentials,
      or other operator-only material.
    - Close this umbrella only after final evidence reconciliation is complete.

    {child_issue_note()}
    """)


ISSUE_TEMPLATES = (
    IssueTemplate(
        key="contract",
        suffix="create scenario contract and pack skeleton",
        labels=(
            LABEL_DOCUMENTATION,
            LABEL_AREA_CONTENT,
            LABEL_AREA_EMULATION,
            LABEL_TIER_RAES,
        ),
        renderer=contract_body,
    ),
    IssueTemplate(
        key="topology",
        suffix="design topology, assets, and reference triangle",
        labels=(
            LABEL_AREA_CONTENT,
            LABEL_AREA_INFRA,
            LABEL_AREA_VALIDATION,
            LABEL_AREA_EMULATION,
            LABEL_TIER_RAES,
        ),
        renderer=topology_body,
    ),
    IssueTemplate(
        key="behavior",
        suffix="specify participant attacker behavior in RAES",
        labels=(
            LABEL_AREA_CONTENT,
            LABEL_AREA_VALIDATION,
            LABEL_AREA_OPERATOR,
            LABEL_AREA_EMULATION,
            LABEL_TIER_RAES,
        ),
        renderer=behavior_body,
        legacy_suffixes=("define hidden path, oracle, and validation model",),
    ),
    IssueTemplate(
        key="flags",
        suffix="add flag, challenge, and reference CTFd layer",
        labels=(
            LABEL_AREA_CONTENT,
            LABEL_AREA_VALIDATION,
            LABEL_AREA_PRODUCT,
            LABEL_AREA_EMULATION,
            LABEL_TIER_RAES,
        ),
        renderer=flag_body,
    ),
    IssueTemplate(
        key="profiles",
        suffix="add delivery profile bundles",
        labels=(
            LABEL_AREA_CONTENT,
            LABEL_AREA_PRODUCT,
            LABEL_TIER_RAES,
            "profile:guided",
            "profile:unguided",
            "profile:purple",
            "profile:agent-benchmark",
            "profile:demo",
        ),
        renderer=profile_body,
    ),
    IssueTemplate(
        key="build",
        suffix="implement golden live-infrastructure build",
        labels=(
            LABEL_AREA_INFRA,
            LABEL_AREA_EMULATION,
            LABEL_TIER_RAES,
        ),
        renderer=build_body,
    ),
    IssueTemplate(
        key="rehearsal",
        suffix="add automated live rehearsal",
        labels=(
            LABEL_AREA_VALIDATION,
            LABEL_AREA_OPERATOR,
            LABEL_AREA_EMULATION,
            LABEL_TIER_RAES,
        ),
        renderer=rehearsal_body,
    ),
    IssueTemplate(
        key="manual",
        suffix="run final manual participant walkthrough",
        labels=(
            LABEL_AREA_VALIDATION,
            LABEL_AREA_OPERATOR,
            LABEL_DOCUMENTATION,
            LABEL_AREA_EMULATION,
            LABEL_TIER_RAES,
        ),
        renderer=manual_body,
    ),
    IssueTemplate(
        key="final",
        suffix="reconcile final docs, status, evidence, and teardown",
        labels=(
            LABEL_DOCUMENTATION,
            LABEL_AREA_VALIDATION,
            LABEL_AREA_OPERATOR,
            LABEL_AREA_EMULATION,
            LABEL_TIER_RAES,
        ),
        renderer=final_body,
    ),
)


def issue_title(plan: PackPlan, template: IssueTemplate) -> str:
    """Issue title."""
    return f"{plan.pack_id}: {template.suffix}"


def milestone_title(plan: PackPlan) -> str:
    """Milestone title."""
    return plan.milestone_title or f"Environment pack: {plan.title}"


def wanted_labels(plan: PackPlan, template: IssueTemplate,
                  available_labels: set[str] | None = None) -> tuple[str, ...]:
    """Wanted labels."""
    labels = set(template.labels).union(plan.labels)
    if available_labels is not None:
        labels = {label for label in labels if label in available_labels}
    return tuple(sorted(labels))


def matching_issue(existing_issues: list[dict[str, object]], title: str,
                   milestone_number: int | None) -> dict[str, object] | None:
    """Matching issue."""
    for issue in existing_issues:
        issue_milestone = (issue.get("milestone") or {}).get("number")
        if issue["title"] == title and (
                milestone_number is None or issue_milestone == milestone_number):
            return issue
    return None


def matching_template_issue(
    existing_issues: list[dict[str, object]],
    plan: PackPlan,
    template: IssueTemplate,
) -> dict[str, object] | None:
    """Match a template's current title or any legacy title."""
    suffixes = (template.suffix, *template.legacy_suffixes)
    for suffix in suffixes:
        found = matching_issue(
            existing_issues,
            f"{plan.pack_id}: {suffix}",
            plan.milestone_number,
        )
        if found is not None:
            return found
    return None


def build_operations(plan: PackPlan, existing_issues: list[dict[str, object]],
                     *, available_labels: set[str] | None = None,
                     refresh_existing: bool = False,
                     milestone_exists: bool = True) -> list[Operation]:
    """Build operations."""
    operations: list[Operation] = []
    if not milestone_exists:
        operations.append(Operation(
            action="create_milestone",
            title=milestone_title(plan),
            milestone_title=milestone_title(plan),
        ))

    for template in ISSUE_TEMPLATES:
        title = issue_title(plan, template)
        found = matching_template_issue(existing_issues, plan, template)
        labels = wanted_labels(plan, template, available_labels)
        if found and not refresh_existing:
            operations.append(Operation(
                action="skip_issue",
                issue_number=found["number"],
                title=title,
                milestone_number=plan.milestone_number,
            ))
        elif found:
            operations.append(Operation(
                action="update_issue",
                issue_number=found["number"],
                title=title,
                body=template.renderer(plan),
                labels=labels,
                milestone_number=plan.milestone_number,
            ))
        else:
            operations.append(Operation(
                action="create_issue",
                title=title,
                body=template.renderer(plan),
                labels=labels,
                milestone_number=plan.milestone_number,
                milestone_title=milestone_title(plan),
            ))
    return operations


class GhClient(object):
    """GhClient."""
    def __init__(self, repo: str) -> None:
        """Initialize the instance."""
        self.repo = repo

    @staticmethod
    def run(args: list[str], payload: dict[str, object] | None = None) -> object:
        """Run."""
        cmd = ["gh", *args]
        input_text = json.dumps(payload) if payload is not None else None
        if payload is not None:
            cmd.extend(["--input", "-"])
        proc = subprocess.run(cmd, input=input_text, text=True,
                              capture_output=True, check=False)
        if proc.returncode != 0:
            raise SystemExit(proc.stderr.strip() or proc.stdout.strip())
        if proc.stdout.strip():
            return json.loads(proc.stdout)
        return None

    def list_labels(self) -> set[str]:
        """List labels."""
        proc = subprocess.run(
            ["gh", "label", "list", "--repo", self.repo, "--limit", "500",
             "--json", "name"],
            text=True,
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            raise SystemExit(proc.stderr.strip() or proc.stdout.strip())
        return {row["name"] for row in json.loads(proc.stdout)}

    def list_issues(self) -> list[dict[str, object]]:
        """List issues."""
        proc = subprocess.run(
            ["gh", "issue", "list", "--repo", self.repo, "--state", "all",
             "--limit", "2000", "--json", "number,title,milestone,labels"],
            text=True,
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0:
            raise SystemExit(proc.stderr.strip() or proc.stdout.strip())
        return json.loads(proc.stdout)

    def list_milestones(self) -> list[dict[str, object]]:
        """List milestones."""
        return self.run(["api", f"repos/{self.repo}/milestones", "--paginate"]) or []

    def create_milestone(self, title: str) -> int:
        """Create milestone."""
        row = self.run(["api", "--method", "POST",
                        f"repos/{self.repo}/milestones"], {"title": title})
        if not isinstance(row, dict):
            raise SystemExit(f"unexpected milestone response for {title!r}")
        return int(row["number"])

    def create_issue(self, operation: Operation, milestone_number: int) -> None:
        """Create issue."""
        self.run(["api", "--method", "POST", f"repos/{self.repo}/issues"], {
            "title": operation.title,
            "body": operation.body,
            "labels": list(operation.labels),
            "milestone": milestone_number,
        })

    def update_issue(self, operation: Operation, milestone_number: int) -> None:
        """Update issue."""
        if operation.issue_number is None:
            raise SystemExit("update operation missing issue number")
        self.run(["api", "--method", "PATCH",
                  f"repos/{self.repo}/issues/{operation.issue_number}"], {
            "title": operation.title,
            "body": operation.body,
            "labels": list(operation.labels),
            "milestone": milestone_number,
        })


def resolve_milestone_number(plan: PackPlan, milestones: list[dict[str, object]]) -> tuple[int | None, bool]:
    """Resolve milestone number."""
    if plan.milestone_number is not None:
        return plan.milestone_number, True
    title = milestone_title(plan)
    for milestone in milestones:
        if milestone["title"] == title:
            return int(milestone["number"]), True
    return None, False


def print_operations(operations: list[Operation]) -> None:
    """Print operations."""
    for op in operations:
        if op.action == "create_milestone":
            print(f"CREATE milestone: {op.title}")
        elif op.action == "create_issue":
            where = op.milestone_number if op.milestone_number is not None else op.milestone_title
            print(f"CREATE issue in milestone {where}: {op.title}")
        elif op.action == "update_issue":
            print(f"UPDATE issue #{op.issue_number}: {op.title}")
        elif op.action == "skip_issue":
            print(f"SKIP existing issue #{op.issue_number}: {op.title}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse args."""
    parser = argparse.ArgumentParser(
        description="Create standard skeleton GitHub issues for an environment pack.")
    parser.add_argument("--repo", default=DEFAULT_REPO,
                        help=f"GitHub repository, default: {DEFAULT_REPO}")
    parser.add_argument("--pack-id", help="lowercase kebab-case environment pack id")
    parser.add_argument("--title", help="human-readable scenario title")
    parser.add_argument("--focus", default="TBD by the pack-design agent.",
                        help="one-sentence scenario focus")
    parser.add_argument("--source", action="append", default=[],
                        help="source-log entry; repeatable")
    parser.add_argument("--label", action="append", default=[],
                        help="extra issue label to apply if it exists; repeatable")
    parser.add_argument("--milestone-number", type=int,
                        help="existing GitHub milestone number")
    parser.add_argument("--milestone-title",
                        help="existing or new GitHub milestone title")
    parser.add_argument("--create-milestone", action="store_true",
                        help="create --milestone-title when it does not exist")
    parser.add_argument("--refresh-existing", action="store_true",
                        help="update existing skeleton issues instead of skipping them")
    parser.add_argument("--apply", action="store_true",
                        help="write changes to GitHub; default is dry-run")
    return parser.parse_args(argv)


def plan_from_args(args: argparse.Namespace) -> PackPlan:
    """Plan from args."""
    if not args.pack_id:
        raise SystemExit("--pack-id is required")
    validate_pack_id(args.pack_id)
    if not args.milestone_number and not args.milestone_title:
        raise SystemExit("pass --milestone-number or --milestone-title")
    return PackPlan(
        pack_id=args.pack_id,
        title=args.title or title_from_pack_id(args.pack_id),
        focus=args.focus,
        sources=tuple(args.source),
        labels=tuple(args.label),
        milestone_number=args.milestone_number,
        milestone_title=args.milestone_title,
    )


def prepare_operations(args: argparse.Namespace,
                       client: GhClient) -> tuple[list[Operation], int | None]:
    """Prepare operations."""
    plan = plan_from_args(args)
    milestone_number, milestone_exists = resolve_milestone_number(
        plan, client.list_milestones())
    if not milestone_exists and not (args.create_milestone or not args.apply):
        raise SystemExit(
            f"milestone not found: {milestone_title(plan)!r}; pass --create-milestone")
    plan = PackPlan(
        pack_id=plan.pack_id,
        title=plan.title,
        focus=plan.focus,
        sources=plan.sources,
        labels=plan.labels,
        milestone_number=milestone_number,
        milestone_title=plan.milestone_title,
    )
    operations = build_operations(
        plan,
        client.list_issues(),
        available_labels=client.list_labels(),
        refresh_existing=args.refresh_existing,
        milestone_exists=milestone_exists,
    )
    return operations, milestone_number


def require_milestone_number(milestone_number: int | None,
                             action: str) -> int:
    """Require milestone number."""
    if milestone_number is None:
        raise SystemExit(f"cannot {action} issue without a milestone number")
    return milestone_number


def _apply_issue_operation(client: GhClient, operation: Operation,
                           active_milestone: int | None) -> None:
    """Apply issue operation."""
    if operation.action == "create_issue":
        client.create_issue(operation, require_milestone_number(active_milestone, "create"))
        print(f"created issue: {operation.title}")
    elif operation.action == "update_issue":
        client.update_issue(operation, require_milestone_number(active_milestone, "update"))
        print(f"updated issue #{operation.issue_number}: {operation.title}")
    elif operation.action == "skip_issue":
        print(f"skipped issue #{operation.issue_number}: {operation.title}")


def apply_operation(client: GhClient, operation: Operation,
                    active_milestone: int | None) -> int | None:
    """Apply operation."""
    if operation.action == "create_milestone":
        milestone_number = client.create_milestone(operation.title)
        print(f"created milestone {milestone_number}: {operation.title}")
        return milestone_number
    _apply_issue_operation(client, operation, active_milestone)
    return active_milestone


def apply_operations(client: GhClient, operations: list[Operation],
                     milestone_number: int | None) -> None:
    """Apply operations."""
    active_milestone = milestone_number
    for operation in operations:
        active_milestone = apply_operation(client, operation, active_milestone)


def main(argv: list[str] | None = None) -> None:
    """Command-line entry point."""
    args = parse_args(argv or sys.argv[1:])
    client = GhClient(args.repo)
    operations, milestone_number = prepare_operations(args, client)
    if not args.apply:
        print("DRY RUN: no GitHub changes will be written. Pass --apply to write.")
        print_operations(operations)
        return

    apply_operations(client, operations, milestone_number)


if __name__ == "__main__":
    main()
