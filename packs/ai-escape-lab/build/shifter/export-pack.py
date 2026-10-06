#!/usr/bin/env python3
"""Build the upload archive accepted by the current Shifter RAES boundary."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import os
import pathlib
import shutil
import tarfile
import tempfile

import yaml
from raes_env_packs import derive_pack_content_manifest, validate_pack


_PACK_NAME = "ai-escape-lab"
_SDL = pathlib.Path("sdl/ai-escape-lab.sdl.yaml")
_CAMPAIGN_COMPUTE_NODES = {
    "eval-sandbox",
    "registry-cache",
    "cybergym",
    "request-capture",
    "pastebin",
    "hf-api",
    "dataset-worker",
    "k8s-api",
    "internal-db",
    "mesh-gateway",
    "source-control",
}
_CAMPAIGN_SWITCH_NODES = {
    "participant-net",
    "eval-net",
    "internet-net",
    "hf-prod-net",
    "hf-cluster-net",
    "corp-net",
    "model-egress-net",
}


def adapt_sdl_for_raes_3_5(pack_root: pathlib.Path) -> None:
    """Project the canonical campaign onto Shifter's one-host RAES 3.5 plan."""

    path = pack_root / _SDL
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    nodes = payload["nodes"]
    if set(nodes) != _CAMPAIGN_COMPUTE_NODES | _CAMPAIGN_SWITCH_NODES:
        raise ValueError("unexpected canonical campaign topology")

    # Shifter provisions the golden image as one GCE resource. The eleven
    # canonical compute nodes describe containers already baked into that image;
    # leaving them in the upload projection would incorrectly request eleven VMs.
    participant_node = nodes["eval-sandbox"]
    participant_node.pop("runtime", None)
    payload["nodes"] = {
        "participant-net": nodes["participant-net"],
        "eval-sandbox": participant_node,
    }
    payload["infrastructure"] = {
        "participant-net": payload["infrastructure"]["participant-net"],
        "eval-sandbox": {"links": ["participant-net"]},
    }

    participant = payload["agents"]["participant"]
    if participant.get("affiliations") != ["participant-team"] or "entity" in participant:
        raise ValueError("unexpected participant identity declaration")
    participant["entity"] = participant.pop("affiliations")[0]
    participant.pop("actions", None)
    participant["operating_scope"] = ["nodes.eval-sandbox"]

    # These sections retain the portable container campaign semantics in the
    # source pack. The current Shifter compiler deploys the physical projection
    # and CTFd imports the challenge progression separately.
    for section in (
        "action_contracts",
        "behavior_specifications",
        "propositions",
        "assertions",
        "evidence_requirements",
        "objectives",
    ):
        payload.pop(section, None)
    payload["description"] += " Current Shifter compatibility projection: one golden-image GCE host."
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _copy_pack(source: pathlib.Path, destination: pathlib.Path) -> None:
    def ignored(_directory: str, names: list[str]) -> set[str]:
        return {name for name in names if name == "__pycache__" or name.endswith(".pyc")}

    # Preserve source links so staged pack validation can reject them. Following
    # a link here could copy bytes from outside the pack into the upload archive.
    shutil.copytree(source, destination, symlinks=True, ignore=ignored)


def _write_manifest(pack_root: pathlib.Path) -> None:
    manifest = derive_pack_content_manifest(pack_root)
    (pack_root / "associated-artifacts.json").write_text(
        manifest.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    result = validate_pack(pack_root)
    if not result.ok:
        codes = ", ".join(item.code for item in result.diagnostics)
        raise ValueError(f"Shifter upload pack validation failed: {codes}")


def _write_archive(pack_root: pathlib.Path, output: pathlib.Path) -> None:
    with output.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w", format=tarfile.GNU_FORMAT) as archive:
                paths = [pack_root, *sorted(pack_root.rglob("*"), key=lambda item: item.as_posix())]
                for path in paths:
                    relative = pathlib.Path(_PACK_NAME) / path.relative_to(pack_root)
                    info = archive.gettarinfo(str(path), arcname=relative.as_posix())
                    info.uid = 0
                    info.gid = 0
                    info.uname = ""
                    info.gname = ""
                    info.mtime = 0
                    if path.is_dir():
                        info.mode = 0o755
                        archive.addfile(info)
                    elif path.is_file():
                        info.mode = 0o755 if os.access(path, os.X_OK) else 0o644
                        with path.open("rb") as member:
                            archive.addfile(info, member)
                    else:
                        raise ValueError(f"unsupported pack member: {path.relative_to(pack_root)}")
    output.chmod(0o600)


def export(pack_root: pathlib.Path, output: pathlib.Path) -> str:
    source = pack_root.resolve()
    target = output.resolve()
    if source == target or source in target.parents:
        raise ValueError("output must be outside the source pack")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise FileExistsError(target)

    with tempfile.TemporaryDirectory(prefix="ai-escape-lab-shifter-") as directory:
        staged = pathlib.Path(directory) / _PACK_NAME
        _copy_pack(source, staged)
        adapt_sdl_for_raes_3_5(staged)
        _write_manifest(staged)
        _write_archive(staged, target)
    return hashlib.sha256(target.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack-root", type=pathlib.Path, required=True)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    digest = export(args.pack_root, args.output)
    print(f"{args.output}: sha256:{digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
