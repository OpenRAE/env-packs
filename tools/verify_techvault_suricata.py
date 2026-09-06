#!/usr/bin/env python3
"""Run TechVault's native Suricata image/content verification.

This is an author-side live check, not a portable RAES evidence producer. It
uses the exact image and content identities already declared by the pack.
"""

from __future__ import annotations

import pathlib
import re
import subprocess
import sys
import tempfile
from collections.abc import Callable, Sequence

import yaml

from raes_env_packs import PackDigestError, resolve_pack_artifact


Runner = Callable[..., subprocess.CompletedProcess[str]]

_TRUSTED_IMAGE = (
    "jasonish/suricata@"
    "sha256:d64c491f6eb5d03b6562d873b3c5303e4c17d5dc1d75b3761a68319f11527dc3"
)
_TRUSTED_BUILT_IN_PATH = "/var/lib/suricata/rules/suricata.rules"
_CONTENT = {
    "suricata-config": (
        "techvault-suricata-config",
        "/etc/suricata/suricata.yaml",
    ),
    "suricata-local-rules": (
        "techvault-suricata-local-rules",
        "/etc/suricata/rules/local.rules",
    ),
    "suricata-misp-ioc-rules-seed": (
        "techvault-suricata-misp-ioc-rules-seed",
        "/var/lib/suricata/rules/misp/misp-iocs.rules",
    ),
    "suricata-misp-md5-seed": (
        "techvault-suricata-misp-md5-seed",
        "/var/lib/suricata/rules/misp/misp-md5.list",
    ),
    "suricata-misp-sha1-seed": (
        "techvault-suricata-misp-sha1-seed",
        "/var/lib/suricata/rules/misp/misp-sha1.list",
    ),
    "suricata-misp-sha256-seed": (
        "techvault-suricata-misp-sha256-seed",
        "/var/lib/suricata/rules/misp/misp-sha256.list",
    ),
}
_RULE_FILES_PROCESSED = re.compile(r"(?<!\d)(\d+)\s+rule files processed\b")
_RULES_FAILED = re.compile(r"(?<!\d)(\d+)\s+rules failed\b")


def _contract(pack_root: pathlib.Path) -> tuple[str, str, list[tuple[bytes, str]]]:
    sdl_path = next((pack_root / "sdl").glob("*.sdl.yaml"))
    sdl = yaml.safe_load(sdl_path.read_text(encoding="utf-8"))
    node = sdl["nodes"]["suricata"]
    exact_image = node["source"]["artifact_requirement"]["exact_artifact"]
    if exact_image["version"] != exact_image["digest"]:
        raise ValueError("Suricata image version and exact digest differ")
    image = f'{exact_image["artifact_id"]}@{exact_image["digest"]}'
    if image != _TRUSTED_IMAGE:
        raise ValueError("Suricata image differs from the verifier's trusted identity")

    (engine,) = node["runtime"]["network_detection_engines"]
    built_in = next(
        source for source in engine["rule_sources"] if source["kind"] == "built_in"
    )
    (built_in_path,) = built_in["file_refs"]
    if built_in_path != _TRUSTED_BUILT_IN_PATH:
        raise ValueError("Suricata built-in rules path differs from trusted policy")

    # Select only the fixed TechVault artifact ids and destinations. The
    # canonical resolver enforces bounded pack-local paths, regular files, the
    # complete manifest/set digest, and byte identity before Docker is invoked.
    mounts: list[tuple[bytes, str]] = []
    for content_id, (expected_artifact_id, expected_path) in _CONTENT.items():
        content = sdl["content"][content_id]
        exact = content["source"]["artifact_requirement"]["exact_artifact"]
        if (
            content["source"]["name"] != expected_artifact_id
            or exact["artifact_id"] != expected_artifact_id
            or content["path"] != expected_path
        ):
            raise ValueError(f"Suricata content declaration differs for {content_id}")
        resolved = resolve_pack_artifact(pack_root, expected_artifact_id)
        if (
            resolved.identity.version != exact["version"]
            or resolved.identity.digest != exact["digest"]
            or resolved.identity.media_type != exact["media_type"]
        ):
            raise ValueError(f"Suricata content identity differs for {content_id}")
        mounts.append((resolved.data, expected_path))
    return image, built_in_path, mounts


def native_commands(
    pack_root: pathlib.Path, staging_root: pathlib.Path
) -> tuple[list[str], list[str]]:
    """Stage verified bytes and return argv for both native checks.

    ``staging_root`` must be a caller-created empty directory. Docker receives
    only files materialized from immutable resolver output, never paths derived
    from pack-controlled URIs or symlinks.
    """

    image, built_in_path, mounts = _contract(pack_root)
    if not staging_root.is_dir() or any(staging_root.iterdir()):
        raise ValueError("native staging root must be an empty directory")
    image_check = [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "--cap-drop",
        "ALL",
        "--cap-add",
        "DAC_OVERRIDE",
        "--security-opt",
        "no-new-privileges",
        "--entrypoint",
        "test",
        image,
        "-s",
        built_in_path,
    ]
    config_check = [
        "docker",
        "run",
        "--rm",
        "--network",
        "none",
        "--cap-drop",
        "ALL",
        "--cap-add",
        "DAC_OVERRIDE",
        "--security-opt",
        "no-new-privileges",
        "--entrypoint",
        "suricata",
    ]
    for index, (data, destination) in enumerate(mounts):
        source = staging_root / f"artifact-{index}"
        source.write_bytes(data)
        config_check.extend(["-v", f"{source}:{destination}:ro"])
    config_check.extend([image, "-T", "-c", "/etc/suricata/suricata.yaml"])
    return image_check, config_check


def _has_exact_native_evidence(output: str) -> bool:
    processed = [int(value) for value in _RULE_FILES_PROCESSED.findall(output)]
    failed = [int(value) for value in _RULES_FAILED.findall(output)]
    return (
        bool(processed)
        and all(value == 3 for value in processed)
        and bool(failed)
        and all(value == 0 for value in failed)
        and "Configuration provided was successfully loaded" in output
    )


def verify(
    pack_root: pathlib.Path,
    *,
    runner: Runner = subprocess.run,
) -> list[str]:
    """Return bounded failures from the two native checks."""

    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="techvault-suricata-") as staging:
        try:
            image_check, config_check = native_commands(pack_root, pathlib.Path(staging))
        except (PackDigestError, KeyError, OSError, TypeError, ValueError, yaml.YAMLError):
            errors.append("suricata.native-content-invalid")
            return errors

        results: list[subprocess.CompletedProcess[str]] = []
        for label, command in (("built-in-rules", image_check), ("configuration", config_check)):
            try:
                result = runner(
                    command,
                    check=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=120,
                )
            except (OSError, subprocess.TimeoutExpired):
                errors.append(f"suricata.native-{label}-unavailable")
                continue
            results.append(result)
            if result.returncode != 0:
                errors.append(f"suricata.native-{label}-failed")

        if len(results) == 2 and results[1].returncode == 0:
            output = results[1].stdout[-16384:]
            if not _has_exact_native_evidence(output):
                errors.append("suricata.native-configuration-evidence-incomplete")
    return errors


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) > 1:
        print("usage: verify_techvault_suricata.py [PACK_ROOT]", file=sys.stderr)
        return 2
    pack_root = pathlib.Path(args[0] if args else "packs/techvault").resolve()
    failures = verify(pack_root)
    for failure in failures:
        print(failure)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
