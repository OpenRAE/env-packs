#!/usr/bin/env python3
"""Validate TechVault's pack-local live-build source against ACES."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import yaml


BUILD_ROOT = Path(__file__).resolve().parent
PACK_ROOT = BUILD_ROOT.parent
RUNTIME_DIR = "aptl-runtime"
RUNTIME_ROOT = BUILD_ROOT / RUNTIME_DIR
SDL_PATH = "sdl/techvault.sdl.yaml"
COMPOSE_PATH = f"{RUNTIME_DIR}/docker-compose.yml"
DEFAULT_ENV_FILE = "operator-defaults.env"
ACTIVE_PROFILES = frozenset(
    {"wazuh", "soc", "enterprise", "fileshare", "dns", "victim", "kali", "otel"}
)
NODE_SERVICE_ALIASES = {
    "wazuh-manager": "wazuh.manager",
    "wazuh-indexer": "wazuh.indexer",
    "wazuh-dashboard": "wazuh.dashboard",
}
NETWORK_ALIASES = {
    "security-net": "aptl-security",
    "dmz-net": "aptl-dmz",
    "internal-net": "aptl-internal",
    "redteam-net": "aptl-redteam",
}
GENERATED_RUNTIME_PATHS = frozenset(
    {
        f"{RUNTIME_DIR}/.aptl/config/wazuh_cluster/wazuh_manager.conf",
        f"{RUNTIME_DIR}/.aptl/config/wazuh_dashboard/wazuh.yml",
        f"{RUNTIME_DIR}/config/lab-ssh/kali_pivot_key",
        f"{RUNTIME_DIR}/config/lab-ssh/kali_pivot_key.pub",
        f"{RUNTIME_DIR}/config/soc_certs/lab-ca.key",
        f"{RUNTIME_DIR}/config/soc_certs/lab-ca.pem",
        f"{RUNTIME_DIR}/config/soc_certs/misp/server.key",
        f"{RUNTIME_DIR}/config/soc_certs/misp/server.pem",
        f"{RUNTIME_DIR}/config/soc_certs/thehive/keystore.p12",
        f"{RUNTIME_DIR}/config/soc_certs/thehive/keystore.p12.password",
        f"{RUNTIME_DIR}/config/soc_certs/thehive/server.key",
        f"{RUNTIME_DIR}/config/soc_certs/thehive/server.pem",
        f"{RUNTIME_DIR}/config/soc_certs/cortex/keystore.p12",
        f"{RUNTIME_DIR}/config/soc_certs/cortex/keystore.p12.password",
        f"{RUNTIME_DIR}/config/soc_certs/cortex/server.key",
        f"{RUNTIME_DIR}/config/soc_certs/cortex/server.pem",
        f"{RUNTIME_DIR}/config/soc_certs/shuffle-frontend/server.key",
        f"{RUNTIME_DIR}/config/soc_certs/shuffle-frontend/server.pem",
        f"{RUNTIME_DIR}/config/wazuh_indexer_ssl_certs/root-ca-manager.pem",
        f"{RUNTIME_DIR}/config/wazuh_indexer_ssl_certs/root-ca.pem",
        f"{RUNTIME_DIR}/config/wazuh_indexer_ssl_certs/wazuh.dashboard-key.pem",
        f"{RUNTIME_DIR}/config/wazuh_indexer_ssl_certs/wazuh.dashboard.pem",
        f"{RUNTIME_DIR}/config/wazuh_indexer_ssl_certs/wazuh.indexer-key.pem",
        f"{RUNTIME_DIR}/config/wazuh_indexer_ssl_certs/wazuh.indexer.pem",
        f"{RUNTIME_DIR}/config/wazuh_indexer_ssl_certs/wazuh.manager-key.pem",
        f"{RUNTIME_DIR}/config/wazuh_indexer_ssl_certs/wazuh.manager.pem",
        f"{RUNTIME_DIR}/keys/aptl_lab_key.pub",
        f"{RUNTIME_DIR}/keys/authorized_keys",
    }
)
ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?:(:?[-?])([^}]*))?\}")
ID_SEPARATORS = re.compile(r"[^a-z0-9]+")
COMPOSE_PROJECT_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


@dataclass(frozen=True)
class BuildContract:
    aces_nodes: tuple[str, ...]
    node_to_service: dict[str, str]
    generated_runtime_paths: frozenset[str]
    default_env_file: str
    default_env_names: frozenset[str]
    required_env_names: frozenset[str]
    gitignored_paths: frozenset[str]


def _issue(issues: list[str], obj: str, identifier: str, field: str, invariant: str) -> None:
    location = f"{obj}:{identifier}"
    if field:
        location += f".{field}"
    issues.append(f"{location}: {invariant}")


def _canonical_relative(value: str) -> PurePosixPath | None:
    if not value or "\\" in value:
        return None
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or str(path) != value:
        return None
    return path


def _pack_path(root: Path, relative: str) -> Path | None:
    canonical = _canonical_relative(relative)
    if canonical is None:
        return None
    candidate = root.joinpath(*canonical.parts)
    try:
        candidate.resolve(strict=False).relative_to(root.resolve(strict=True))
    except (OSError, ValueError):
        return None
    return candidate


def resolve_operator_env(value: str | Path, *, pack_root: Path = PACK_ROOT) -> Path:
    """Resolve a regular operator env file contained in the scenario pack."""
    raw = str(value)
    if not raw or raw.startswith("~"):
        raise ValueError("operator env path must be a pack-contained regular file")
    root = pack_root.resolve(strict=True)
    candidate = Path(raw)
    if not candidate.is_absolute():
        cwd_candidate = candidate.resolve(strict=False)
        try:
            cwd_candidate.relative_to(root)
            cwd_contained = True
        except ValueError:
            cwd_contained = False
        candidate = cwd_candidate if cwd_contained and cwd_candidate.exists() else root / candidate
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as exc:
        raise ValueError("operator env path must stay under the TechVault pack") from exc
    if candidate.is_symlink() or not resolved.is_file():
        raise ValueError("operator env path must be a regular non-symlink file")
    return resolved


def validate_compose_project(value: str) -> str:
    """Validate a Docker Compose project id before using it in Docker argv."""
    if not isinstance(value, str) or not COMPOSE_PROJECT_PATTERN.fullmatch(value):
        raise ValueError(
            "compose project must match "
            f"{COMPOSE_PROJECT_PATTERN.pattern!r}"
        )
    if ".." in value:
        raise ValueError("compose project must not contain '..'")
    return value


def _load_yaml(root: Path, relative: str, issues: list[str]) -> Any:
    path = _pack_path(root, relative)
    if path is None or not path.is_file() or path.is_symlink():
        _issue(issues, "file", relative, "", "regular contained file required")
        return None
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError):
        _issue(issues, "file", relative, "", "safe YAML parse required")
        return None


def _runtime_file(root: Path, relative: str) -> Path:
    return root / "build" / relative


def _normalize(value: str) -> str:
    return ID_SEPARATORS.sub("-", value.lower()).strip("-")


def _service_aliases(service_name: str, service: dict[str, Any]) -> set[str]:
    aliases = {service_name, _normalize(service_name)}
    for key in ("container_name", "hostname", "image"):
        raw = service.get(key)
        if isinstance(raw, str):
            terminal = raw.rsplit("/", 1)[-1].split(":", 1)[0]
            aliases.add(_normalize(raw))
            aliases.add(_normalize(terminal))
    build = service.get("build")
    if isinstance(build, dict) and isinstance(build.get("context"), str):
        aliases.add(_normalize(Path(build["context"]).name))
    return {alias for alias in aliases if alias}


def _vm_nodes(sdl: dict[str, Any]) -> tuple[str, ...]:
    nodes = sdl.get("nodes") if isinstance(sdl, dict) else {}
    if not isinstance(nodes, dict):
        return ()
    return tuple(
        sorted(
            name
            for name, row in nodes.items()
            if isinstance(row, dict) and row.get("type") != "switch"
        )
    )


def _compose_services(compose: dict[str, Any]) -> dict[str, dict[str, Any]]:
    services = compose.get("services") if isinstance(compose, dict) else {}
    if not isinstance(services, dict):
        return {}
    return {name: row for name, row in services.items() if isinstance(row, dict)}


def _active_service(service: dict[str, Any]) -> bool:
    profiles = service.get("profiles") or []
    return not profiles or bool(set(profiles) & ACTIVE_PROFILES)


def _map_nodes_to_services(nodes: tuple[str, ...], services: dict[str, dict[str, Any]]) -> dict[str, str]:
    alias_index: dict[str, str] = {}
    for service_name, service in services.items():
        for alias in _service_aliases(service_name, service):
            alias_index.setdefault(alias, service_name)
    mapped: dict[str, str] = {}
    for node in nodes:
        expected = NODE_SERVICE_ALIASES.get(node, node)
        candidates = {expected, _normalize(expected), _normalize(node)}
        match = next((alias_index[candidate] for candidate in candidates if candidate in alias_index), None)
        if match is not None:
            mapped[node] = match
    return mapped


def _env_names(path: Path) -> frozenset[str]:
    names: set[str] = set()
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            names.add(stripped.split("=", 1)[0].strip())
    except (OSError, UnicodeError):
        return frozenset()
    return frozenset(names)


def _env_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            values[key.strip()] = value.strip()
    except (OSError, UnicodeError):
        return {}
    return values


def _wazuh_api_password_strong(value: str) -> bool:
    """Match Wazuh API user policy before launch reaches create_user.py."""
    return (
        len(value) >= 8
        and any(char.islower() for char in value)
        and any(char.isupper() for char in value)
        and any(char.isdigit() for char in value)
        and any(not char.isalnum() for char in value)
    )


def _required_compose_env(compose_path: Path) -> frozenset[str]:
    try:
        text = "\n".join(
            line
            for line in compose_path.read_text(encoding="utf-8").splitlines()
            if not line.lstrip().startswith("#")
        )
    except (OSError, UnicodeError):
        return frozenset()
    required: set[str] = set()
    for name, operator, _default in ENV_PATTERN.findall(text):
        if operator != ":-":
            required.add(name)
    return frozenset(required)


def _gitignored_paths(root: Path) -> frozenset[str]:
    ignored: set[str] = set()
    path = root / "build" / ".gitignore"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return frozenset()
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            ignored.add(stripped)
    return frozenset(ignored)


def _contract(root: Path, issues: list[str]) -> BuildContract:
    sdl = _load_yaml(root, SDL_PATH, issues)
    compose = _load_yaml(root, f"build/{COMPOSE_PATH}", issues)
    nodes = _vm_nodes(sdl if isinstance(sdl, dict) else {})
    services = _compose_services(compose if isinstance(compose, dict) else {})
    return BuildContract(
        aces_nodes=nodes,
        node_to_service=_map_nodes_to_services(nodes, services),
        generated_runtime_paths=GENERATED_RUNTIME_PATHS,
        default_env_file=DEFAULT_ENV_FILE,
        default_env_names=_env_names(root / "build" / DEFAULT_ENV_FILE),
        required_env_names=_required_compose_env(root / "build" / COMPOSE_PATH),
        gitignored_paths=_gitignored_paths(root),
    )


def build_contract(root: Path = PACK_ROOT) -> BuildContract:
    issues: list[str] = []
    return _contract(root, issues)


def _check_static_files(root: Path, issues: list[str]) -> None:
    required = (
        "build/README.md",
        "build/launch.sh",
        "build/health-check.sh",
        "build/reset.sh",
        "build/cleanup.sh",
        "build/render_runtime.py",
        "build/operator-defaults.env",
        "build/aptl-runtime/aptl.json",
        "build/aptl-runtime/docker-compose.yml",
        "build/aptl-runtime/generate-indexer-certs.yml",
        "build/aptl-runtime/config/certs.yml",
        "build/aptl-runtime/config/wazuh_cluster/wazuh_manager.conf",
    )
    for relative in required:
        path = _pack_path(root, relative)
        if path is None or not path.exists() or path.is_symlink():
            _issue(issues, "file", relative, "", "committed build source required")


def _check_nodes(contract: BuildContract, issues: list[str]) -> None:
    for node in contract.aces_nodes:
        if node not in contract.node_to_service:
            _issue(issues, "node", node, "service", "compose realization required")


def _check_networks(root: Path, compose: dict[str, Any], sdl: dict[str, Any], issues: list[str]) -> None:
    del root
    networks = compose.get("networks") if isinstance(compose, dict) else {}
    infra = sdl.get("infrastructure") if isinstance(sdl, dict) else {}
    if not isinstance(networks, dict) or not isinstance(infra, dict):
        return
    for aces_name, compose_name in NETWORK_ALIASES.items():
        cnet = networks.get(compose_name)
        irow = infra.get(aces_name)
        if not isinstance(cnet, dict) or not isinstance(irow, dict):
            _issue(issues, "network", aces_name, "compose", "network realization required")
            continue
        props = irow.get("properties") if isinstance(irow.get("properties"), dict) else {}
        ipam_rows = cnet.get("ipam", {}).get("config", []) if isinstance(cnet.get("ipam"), dict) else []
        first = ipam_rows[0] if ipam_rows and isinstance(ipam_rows[0], dict) else {}
        if first.get("subnet") != props.get("cidr") or first.get("gateway") != props.get("gateway"):
            _issue(issues, "network", aces_name, "cidr", "ACES CIDR/gateway match required")
        if props.get("internal") is True and cnet.get("internal") is not True:
            _issue(issues, "network", aces_name, "internal", "internal network flag required")


def _bind_source(volume: str) -> str | None:
    if not volume.startswith("./"):
        return None
    return volume.split(":", 1)[0].removeprefix("./")


def _check_bind_mounts(root: Path, compose: dict[str, Any], issues: list[str]) -> None:
    services = _compose_services(compose)
    for service_name, service in services.items():
        if not _active_service(service):
            continue
        for volume in service.get("volumes", []) or []:
            if not isinstance(volume, str):
                continue
            source = _bind_source(volume)
            if source is None:
                continue
            build_relative = f"{RUNTIME_DIR}/{source}"
            if build_relative in GENERATED_RUNTIME_PATHS:
                continue
            if not _runtime_file(root, build_relative).exists():
                _issue(
                    issues,
                    "service",
                    service_name,
                    source,
                    "bind mount source must be committed or generated",
                )


def _uses_mutable_latest(image: str) -> bool:
    reference = image.rsplit("/", 1)[-1]
    tag = reference.split("@", 1)[0].rsplit(":", 1)
    return len(tag) == 2 and tag[1] == "latest"


def _environment_pairs(service: dict[str, Any]) -> dict[str, str]:
    environment = service.get("environment")
    if isinstance(environment, dict):
        return {str(key): str(value) for key, value in environment.items()}
    if isinstance(environment, list):
        pairs: dict[str, str] = {}
        for entry in environment:
            if isinstance(entry, str) and "=" in entry:
                key, value = entry.split("=", 1)
                pairs[key] = value
        return pairs
    return {}


def _check_image_pins(compose: dict[str, Any], issues: list[str]) -> None:
    services = _compose_services(compose)
    for service_name, service in services.items():
        if not _active_service(service):
            continue
        image = service.get("image")
        if isinstance(image, str) and _uses_mutable_latest(image):
            _issue(issues, "service", service_name, "image", "active profile image must not use latest")
        for key, value in _environment_pairs(service).items():
            if key.endswith("_IMAGE") and _uses_mutable_latest(value):
                _issue(
                    issues,
                    "service",
                    service_name,
                    f"environment.{key}",
                    "active profile image must not use latest",
                )


def _host_ip_for_port(port: Any) -> str | None:
    if isinstance(port, dict):
        host_ip = port.get("host_ip")
        return str(host_ip) if host_ip is not None else None
    if not isinstance(port, str):
        return None
    if port.startswith("127.0.0.1:"):
        return "127.0.0.1"
    pieces = port.split(":")
    if len(pieces) == 3:
        return pieces[0]
    return None


def _check_default_ingress(compose: dict[str, Any], issues: list[str]) -> None:
    services = _compose_services(compose)
    webapp = services.get("webapp", {})
    for port in webapp.get("ports", []) or []:
        host_ip = _host_ip_for_port(port)
        if host_ip != "127.0.0.1":
            _issue(issues, "service", "webapp", "ports", "host publish must bind loopback")


def _check_reverse_tools_source(root: Path, issues: list[str]) -> None:
    path = root / "build" / "aptl-runtime" / "containers" / "reverse" / "setup-reverse-tools.sh"
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        _issue(issues, "file", str(path.relative_to(root)), "", "reverse tools installer required")
        return
    required_snippets = (
        'RADARE2_COMMIT="4eb49d5ad8c99eaecc8850a2f10bad407067c898"',
        'RADARE2_TREE_SHA="5832bce065b40f209ece377b61d51aed7bdf052b"',
        'git fetch --depth=1 origin "${RADARE2_COMMIT}"',
        'actual_tree="$(git rev-parse \'HEAD^{tree}\')"',
    )
    for snippet in required_snippets:
        if snippet not in text:
            _issue(issues, "script", "reverse/setup-reverse-tools.sh", "radare2", "pinned verified source required")
    if "git clone https://github.com/radareorg/radare2" in text:
        _issue(issues, "script", "reverse/setup-reverse-tools.sh", "radare2", "mutable branch clone forbidden")


def _check_generated_state_gitignored(contract: BuildContract, issues: list[str]) -> None:
    for ignored in (
        "aptl-runtime/.aptl/",
        "aptl-runtime/config/lab-ssh/",
        "aptl-runtime/config/soc_certs/",
        "aptl-runtime/config/wazuh_indexer_ssl_certs/",
        "aptl-runtime/keys/",
        "aptl-runtime/runs/",
    ):
        if ignored not in contract.gitignored_paths:
            _issue(issues, "gitignore", ignored, "", "generated runtime path must be ignored")


def _check_env(root: Path, contract: BuildContract, issues: list[str]) -> None:
    if (root / ".env").exists():
        _issue(issues, "env", ".env", "", "repo-root env file forbidden for TechVault build")
    if not contract.required_env_names <= contract.default_env_names:
        missing = sorted(contract.required_env_names - contract.default_env_names)
        _issue(issues, "env", DEFAULT_ENV_FILE, ",".join(missing), "required compose env default missing")
    values = _env_values(root / "build" / DEFAULT_ENV_FILE)
    if not _wazuh_api_password_strong(values.get("API_PASSWORD", "")):
        _issue(issues, "env", DEFAULT_ENV_FILE, "API_PASSWORD", "Wazuh API password policy required")


def _check_aces_source_reuse(root: Path, issues: list[str]) -> None:
    pairs = (
        ("assets/runtime/wazuh/certs.yml", "build/aptl-runtime/config/certs.yml"),
        (
            "assets/runtime/wazuh/wazuh_manager.conf",
            "build/aptl-runtime/config/wazuh_cluster/wazuh_manager.conf",
        ),
    )
    for left, right in pairs:
        left_path = root / left
        right_path = root / right
        try:
            same = left_path.read_bytes() == right_path.read_bytes()
        except OSError:
            same = False
        if not same:
            _issue(issues, "source", right, "", "must match ACES provenance input")


def validate_pack(root: Path = PACK_ROOT) -> list[str]:
    root = root.resolve()
    issues: list[str] = []
    _check_static_files(root, issues)
    sdl = _load_yaml(root, SDL_PATH, issues)
    compose = _load_yaml(root, f"build/{COMPOSE_PATH}", issues)
    contract = _contract(root, issues)
    _check_nodes(contract, issues)
    if isinstance(compose, dict) and isinstance(sdl, dict):
        _check_networks(root, compose, sdl, issues)
        _check_bind_mounts(root, compose, issues)
        _check_image_pins(compose, issues)
        _check_default_ingress(compose, issues)
    _check_generated_state_gitignored(contract, issues)
    _check_env(root, contract, issues)
    _check_aces_source_reuse(root, issues)
    _check_reverse_tools_source(root, issues)
    return sorted(set(issues))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("validate")
    env_parser = subparsers.add_parser("resolve-operator-env")
    env_parser.add_argument("path")
    project_parser = subparsers.add_parser("validate-project")
    project_parser.add_argument("value")
    args = parser.parse_args()
    command = args.command or "validate"
    if command == "resolve-operator-env":
        try:
            print(resolve_operator_env(args.path))
        except ValueError as exc:
            print(f"FAIL: {exc}", file=sys.stderr)
            return 1
        return 0
    if command == "validate-project":
        try:
            print(validate_compose_project(args.value))
        except ValueError as exc:
            print(f"FAIL: {exc}", file=sys.stderr)
            return 1
        return 0
    failures = validate_pack()
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("TechVault build source contract: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
