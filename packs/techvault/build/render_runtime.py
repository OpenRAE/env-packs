#!/usr/bin/env python3
"""Prepare generated runtime state for the TechVault Docker Compose build."""

from __future__ import annotations

import argparse
import os
import re
import secrets
import sys
import subprocess
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape


BUILD_ROOT = Path(__file__).resolve().parent
RUNTIME_ROOT = BUILD_ROOT / "aptl-runtime"
DEFAULT_ENV = BUILD_ROOT / "operator-defaults.env"
DEFAULT_PROJECT = "techvault_golden"
SURICATA_IMAGE = "jasonish/suricata:7.0"
PASSWORD_PATTERN = re.compile(r'(password:\s*)"[^"]*"')
KEY_PATTERN = re.compile(r"<key>[^<]*</key>")
SOC_CERTS = {
    "misp": ("aptl-misp", ("misp", "localhost", "127.0.0.1"), False),
    "thehive": ("aptl-thehive", ("thehive", "localhost", "127.0.0.1"), True),
    "cortex": ("aptl-cortex", ("cortex", "localhost", "127.0.0.1"), True),
    "shuffle-frontend": (
        "aptl-shuffle-frontend",
        ("shuffle-frontend", "localhost", "127.0.0.1"),
        False,
    ),
}

if str(BUILD_ROOT) not in sys.path:
    sys.path.insert(0, str(BUILD_ROOT))

from validate_build import resolve_operator_env, validate_compose_project  # noqa: E402


def _run(
    args: list[str],
    *,
    cwd: Path = RUNTIME_ROOT,
    timeout: int | None = None,
    input_text: str | None = None,
) -> None:
    kwargs: dict[str, object] = {"cwd": cwd, "check": True, "timeout": timeout}
    if input_text is not None:
        kwargs.update({"input": input_text, "text": True})
    subprocess.run(args, **kwargs)


def _load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _write(path: Path, text: str, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    path.chmod(mode)


def _render_configs(env: dict[str, str]) -> None:
    manager = RUNTIME_ROOT / "config" / "wazuh_cluster" / "wazuh_manager.conf"
    rendered_manager = RUNTIME_ROOT / ".aptl" / "config" / "wazuh_cluster" / "wazuh_manager.conf"
    cluster_key = xml_escape(env["WAZUH_CLUSTER_KEY"])
    source = manager.read_text(encoding="utf-8")
    pieces: list[str] = []
    count = 0
    pos = 0
    while True:
        start = source.find("<cluster>", pos)
        if start == -1:
            pieces.append(source[pos:])
            break
        end = source.find("</cluster>", start)
        if end == -1:
            pieces.append(source[pos:])
            break
        end += len("</cluster>")
        pieces.append(source[pos:start])
        block, n = KEY_PATTERN.subn(f"<key>{cluster_key}</key>", source[start:end])
        count += n
        pieces.append(block)
        pos = end
    if count == 0:
        raise RuntimeError("Wazuh manager cluster key placeholder not found")
    _write(rendered_manager, "".join(pieces))

    dashboard = RUNTIME_ROOT / "config" / "wazuh_dashboard" / "wazuh.yml"
    rendered_dashboard = RUNTIME_ROOT / ".aptl" / "config" / "wazuh_dashboard" / "wazuh.yml"
    password = env["API_PASSWORD"].replace("\\", "\\\\").replace('"', '\\"')
    rendered, count = PASSWORD_PATTERN.subn(
        lambda match: f'{match.group(1)}"{password}"',
        dashboard.read_text(encoding="utf-8"),
    )
    if count == 0:
        raise RuntimeError("Wazuh dashboard password placeholder not found")
    _write(rendered_dashboard, rendered)


def _ensure_ssh_key(private_key: Path, comment: str) -> None:
    if private_key.exists() and private_key.with_suffix(private_key.suffix + ".pub").exists():
        return
    private_key.parent.mkdir(parents=True, exist_ok=True)
    _run(["ssh-keygen", "-t", "ed25519", "-f", str(private_key), "-N", "", "-C", comment])


def _prepare_ssh_keys() -> None:
    operator_key = BUILD_ROOT / ".operator" / "ssh" / "aptl_lab_key"
    _ensure_ssh_key(operator_key, "techvault-operator")
    keys_dir = RUNTIME_ROOT / "keys"
    keys_dir.mkdir(parents=True, exist_ok=True)
    pub = operator_key.with_suffix(operator_key.suffix + ".pub").read_text(encoding="utf-8")
    _write(keys_dir / "aptl_lab_key.pub", pub)
    _write(keys_dir / "authorized_keys", pub)

    pivot_key = RUNTIME_ROOT / "config" / "lab-ssh" / "kali_pivot_key"
    _ensure_ssh_key(pivot_key, "techvault-kali-pivot")


def _generate_wazuh_certs() -> None:
    certs_dir = RUNTIME_ROOT / "config" / "wazuh_indexer_ssl_certs"
    if (certs_dir / "root-ca.pem").exists():
        if not (certs_dir / "root-ca-manager.pem").is_file():
            raise RuntimeError("Wazuh certificate set is incomplete: root-ca-manager.pem is missing")
        return
    certs_dir.mkdir(parents=True, exist_ok=True)
    _run(
        [
            "docker",
            "compose",
            "-p",
            "techvault-wazuh-certs",
            "-f",
            "generate-indexer-certs.yml",
            "run",
            "--rm",
            "generator",
        ],
        timeout=300,
    )
    _run(
        [
            "docker",
            "compose",
            "-p",
            "techvault-wazuh-certs",
            "-f",
            "generate-indexer-certs.yml",
            "down",
            "--remove-orphans",
        ],
        timeout=60,
    )
    for name in ("root-ca.pem", "root-ca-manager.pem"):
        if not (certs_dir / name).is_file():
            raise RuntimeError(f"Wazuh certificate generator did not create {name}")


def _openssl_san_args(sans: tuple[str, ...]) -> str:
    rendered = []
    for index, san in enumerate(sans, start=1):
        kind = "IP" if san.replace(".", "").isdigit() else "DNS"
        rendered.append(f"{kind}.{index} = {san}")
    return "\n".join(rendered)


def _generate_service_cert(ca_dir: Path, name: str, cn: str, sans: tuple[str, ...], keystore: bool) -> None:
    service_dir = ca_dir / name
    service_dir.mkdir(parents=True, exist_ok=True)
    cert = service_dir / "server.pem"
    key = service_dir / "server.key"
    if cert.exists() and key.exists() and (not keystore or (service_dir / "keystore.p12").exists()):
        return
    csr = service_dir / "server.csr"
    ext = service_dir / "server.ext"
    _run(["openssl", "genrsa", "-out", str(key), "2048"])
    _run(["openssl", "req", "-new", "-key", str(key), "-out", str(csr), "-subj", f"/CN={cn}"])
    _write(ext, "subjectAltName = @alt_names\n[alt_names]\n" + _openssl_san_args(sans) + "\n")
    _run(
        [
            "openssl",
            "x509",
            "-req",
            "-in",
            str(csr),
            "-CA",
            str(ca_dir / "lab-ca.pem"),
            "-CAkey",
            str(ca_dir / "lab-ca.key"),
            "-CAcreateserial",
            "-out",
            str(cert),
            "-days",
            "825",
            "-sha256",
            "-extfile",
            str(ext),
        ]
    )
    csr.unlink(missing_ok=True)
    ext.unlink(missing_ok=True)
    key.chmod(0o600)
    cert.chmod(0o644)
    if keystore:
        password = secrets.token_urlsafe(24)
        _write(service_dir / "keystore.p12.password", f"HTTPS_KEYSTORE_PASSWORD={password}\n", 0o600)
        _run(
            [
                "openssl",
                "pkcs12",
                "-export",
                "-out",
                str(service_dir / "keystore.p12"),
                "-inkey",
                str(key),
                "-in",
                str(cert),
                "-certfile",
                str(ca_dir / "lab-ca.pem"),
                "-passout",
                "stdin",
            ],
            input_text=f"{password}\n",
        )
        (service_dir / "keystore.p12").chmod(0o644)


def _generate_soc_certs() -> None:
    ca_dir = RUNTIME_ROOT / "config" / "soc_certs"
    ca_dir.mkdir(parents=True, exist_ok=True)
    ca_key = ca_dir / "lab-ca.key"
    ca_cert = ca_dir / "lab-ca.pem"
    if not ca_key.exists() or not ca_cert.exists():
        _run(["openssl", "genrsa", "-out", str(ca_key), "4096"])
        _run(
            [
                "openssl",
                "req",
                "-x509",
                "-new",
                "-nodes",
                "-key",
                str(ca_key),
                "-sha256",
                "-days",
                "3650",
                "-out",
                str(ca_cert),
                "-subj",
                "/CN=TechVault Lab CA",
            ]
        )
        ca_key.chmod(0o600)
        ca_cert.chmod(0o644)
    for name, (cn, sans, keystore) in SOC_CERTS.items():
        _generate_service_cert(ca_dir, name, cn, sans, keystore)


def _seed_volume(project: str, suffix: str, source: Path, files: tuple[tuple[str, str], ...]) -> None:
    volume = f"{project}_{suffix}"
    _run(["docker", "volume", "create", volume], timeout=60)
    commands = ["set -e"]
    for src, dest in files:
        dest_dir = Path(dest).parent.as_posix()
        if dest_dir not in ("", "."):
            commands.append(f"mkdir -p /dest/{dest_dir}")
        commands.append(f"cp -a /src/{src} /dest/{dest}")
    _run(
        [
            "docker",
            "run",
            "--rm",
            "--user",
            "0:0",
            "--entrypoint",
            "/bin/sh",
            "-v",
            f"{source}:/src:ro",
            "-v",
            f"{volume}:/dest",
            SURICATA_IMAGE,
            "-c",
            "; ".join(commands),
        ],
        timeout=600,
    )


def _seed_suricata(project: str) -> None:
    _seed_volume(
        project,
        "suricata_config_seed",
        RUNTIME_ROOT / "config" / "suricata",
        (("suricata.yaml", "suricata.yaml"), ("rules/local.rules", "rules/local.rules")),
    )
    _seed_volume(
        project,
        "suricata_misp_rules",
        RUNTIME_ROOT / "config" / "suricata" / "rules" / "misp",
        (
            ("misp-iocs.rules", "misp-iocs.rules"),
            ("misp-md5.list", "misp-md5.list"),
            ("misp-sha1.list", "misp-sha1.list"),
            ("misp-sha256.list", "misp-sha256.list"),
        ),
    )


def prepare(env_file: Path, project: str, *, skip_docker_materialization: bool = False) -> None:
    env_file = resolve_operator_env(env_file)
    project = validate_compose_project(project)
    env = _load_env(env_file)
    for name in ("API_PASSWORD", "WAZUH_CLUSTER_KEY"):
        if name not in env:
            raise RuntimeError(f"{name} is required in {env_file}")
    _render_configs(env)
    _prepare_ssh_keys()
    _generate_soc_certs()
    if skip_docker_materialization:
        return
    _generate_wazuh_certs()
    _seed_suricata(project)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare",), default="prepare")
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    parser.add_argument("--project", default=os.environ.get("TECHVAULT_COMPOSE_PROJECT", DEFAULT_PROJECT))
    parser.add_argument("--skip-docker-materialization", action="store_true")
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.env_file, args.project, skip_docker_materialization=args.skip_docker_materialization)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
