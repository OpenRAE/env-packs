#!/usr/bin/env python3
"""Pack-local static entrypoint used by the environment-pack content gate."""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys
from collections.abc import Mapping
from typing import Any

import yaml

from raes_env_packs import (
    PackDigestError,
    resolve_pack_artifact,
    validate_pack,
    validate_pack_content_manifest,
)


_EXPECTED_LOCAL_SIDS = (
    1000001,
    1000002,
    1000010,
    1000011,
    1000012,
    1000020,
    1000030,
    1000031,
    1000040,
    1000050,
    1000060,
    1000061,
    1000070,
    1000080,
    1000090,
    1000091,
)
_SURICATA_CONTENT = {
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
_LOCAL_SOURCE_REF = (
    "nodes.suricata.runtime.network_detection_engines.suricata-engine."
    "rule_sources.techvault-local"
)
_BUILTIN_SOURCE_REF = (
    "nodes.suricata.runtime.network_detection_engines.suricata-engine."
    "rule_sources.suricata-builtin"
)
_EVE_STREAM_REF = (
    "nodes.suricata.runtime.network_detection_engines.suricata-engine."
    "output_streams.eve-json"
)
_CONTROL_CHANNEL_REF = (
    "nodes.suricata.runtime.network_detection_engines.suricata-engine."
    "control_channels.command-socket"
)
_FORWARDER_REF = (
    "nodes.misp-suricata-sync.runtime.forwarding_agents.misp-ioc-to-suricata"
)
_LOGIN_ROUTE_REF = "nodes.webapp.runtime.applications.techvault-portal"
_LOGIN_ROUTE_SUBJECT = _LOGIN_ROUTE_REF + ".routes.login"
_LOGIN_WEAKNESS_CONCEPT = "CWE-89"
_BINDINGS_ARTIFACT = "techvault-pack-sdl-techvault-bindings-json"
_WAZUH_RULES_REF = (
    "nodes.wazuh-manager.runtime.security_monitoring_managers.wazuh-manager."
    "content_sets.suricata-rules"
)
_VARIABLE_REF = re.compile(r"\$([A-Z][A-Z0-9_]*)")
_SID = re.compile(r"(?:^|;)\s*sid\s*:\s*(\d+)\s*;")
_BUILD_MECHANISM = "materialization-specification"
_MISP_SID_NAMESPACE = "99000000"
_SYSTEMD_UNIT_DIRECTORIES = (
    pathlib.PurePosixPath("/etc/systemd/system"),
    pathlib.PurePosixPath("/lib/systemd/system"),
    pathlib.PurePosixPath("/usr/lib/systemd/system"),
)
_SYSTEMD_UNIT_SUFFIXES = frozenset(
    {
        ".automount",
        ".mount",
        ".path",
        ".service",
        ".slice",
        ".socket",
        ".target",
        ".timer",
    }
)
_FORBIDDEN_RUNTIME_FIELDS = {
    "container": "container-detail",
    "environment": "runtime-environment",
    "linux_capabilities": "linux-capabilities",
    "local_control_interfaces": "local-control-interface",
    "mounts": "backend-mount",
    "operational_policy": "operational-policy",
    "orchestration_authorities": "orchestration-authority",
}
_PORTABLE_RUNTIME_FIELD_EXCEPTIONS = {
    "shuffle-orborus": frozenset(
        {"local_control_interfaces", "orchestration_authorities"}
    ),
}
_SHUFFLE_ORBORUS_TEMPLATES = {
    "shuffle-worker": {
        "image_ref": (
            "ghcr.io/shuffle/shuffle-worker@sha256:"
            "fd0d420a5e0cd41f3979335e51912e8dd423e7ce540d1dfa24efdc98fb6071bd"
        ),
        "purpose": "workflow execution",
    },
    "shuffle-http-1-4-0": {
        "image_ref": (
            "frikky/shuffle:http_1.4.0@sha256:"
            "0f6f6a686205cdb1f589feb39b3ed7fb8ae715406ae4a626b2e7657e2551e00c"
        ),
        "purpose": "seeded HTTP workflow app execution",
    },
}
_FORBIDDEN_SENSOR_FIELDS = {
    "capture_interfaces": "packet-acquisition",
    "capture_mode": "packet-acquisition",
}

_WAZUH_ENDPOINT_OWNERS = frozenset(
    {"webapp", "ad", "dns", "fileshare", "victim", "workstation"}
)
_WAZUH_AGENT_SPECS = {
    "webapp": {
        "name": "techvault-webapp-agent",
        "state_volume": "wazuh-agent-webapp-state",
        "sources": {
            ("gunicorn-access", "/var/log/gunicorn/access.log", "syslog"),
        },
    },
    "ad": {
        "name": "techvault-ad-agent",
        "state_volume": "wazuh-agent-ad-state",
        "sources": {
            ("samba-log", "/var/log/samba/log.samba", "syslog"),
            ("smbd-log", "/var/log/samba/log.smbd", "syslog"),
            ("winbindd-log", "/var/log/samba/log.winbindd", "syslog"),
        },
    },
    "dns": {
        "name": "techvault-dns-agent",
        "state_volume": "wazuh-agent-dns-state",
        "sources": {
            ("dns-query-log", "/var/log/named/query.log", "syslog"),
            ("dns-default-log", "/var/log/named/default.log", "syslog"),
        },
    },
    "fileshare": {
        "name": "techvault-fileshare-agent",
        "state_volume": "wazuh-agent-fileshare-state",
        "sources": {
            ("fileshare-samba-log", "/var/log/samba/log.samba", "syslog"),
            ("fileshare-smbd-log", "/var/log/samba/log.smbd", "syslog"),
        },
    },
    "victim": {
        "name": "techvault-victim-agent",
        "state_volume": "wazuh-agent-victim-state",
        "sources": {
            ("victim-auth-log", "/var/log/secure", "syslog"),
            ("victim-system-log", "/var/log/messages", "syslog"),
        },
    },
    "workstation": {
        "name": "techvault-workstation-agent",
        "state_volume": "wazuh-agent-workstation-state",
        "sources": {
            ("workstation-auth-log", "/var/log/secure", "syslog"),
            ("workstation-system-log", "/var/log/messages", "syslog"),
        },
    },
    "db": {
        "name": "techvault-db-agent",
        "state_volume": "wazuh-agent-db-state",
        "sources": {
            ("postgres-log", "/var/log/postgresql/postgresql-15-main.log", "syslog"),
        },
    },
    "suricata": {
        "name": "techvault-suricata-agent",
        "state_volume": "wazuh-agent-suricata-state",
        "sources": {
            ("suricata-eve", "/var/log/suricata/eve.json", "eve_json"),
        },
    },
}


def _error(errors: list[str], code: str, detail: str) -> None:
    errors.append(f"suricata.{code}: {detail}")


def _cortex_error(errors: list[str], code: str, detail: str) -> None:
    errors.append(f"cortex.{code}: {detail}")


def _misp_error(errors: list[str], code: str, detail: str) -> None:
    errors.append(f"misp.{code}: {detail}")


def _wazuh_error(errors: list[str], code: str, detail: str) -> None:
    errors.append(f"wazuh.{code}: {detail}")


def _shuffle_orborus_error(errors: list[str], code: str, detail: str) -> None:
    errors.append(f"shuffle-orborus.{code}: {detail}")


def _as_mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _resolve_content(
    pack_root: pathlib.Path,
    sdl: Mapping[str, Any],
    content_id: str,
    errors: list[str],
    overrides: Mapping[str, bytes],
) -> bytes | None:
    expected_artifact, expected_path = _SURICATA_CONTENT[content_id]
    item = _as_mapping(_as_mapping(sdl.get("content")).get(content_id))
    source = _as_mapping(item.get("source"))
    requirement = _as_mapping(source.get("artifact_requirement"))
    exact = _as_mapping(requirement.get("exact_artifact"))
    if item.get("target") != "suricata" or item.get("path") != expected_path:
        _error(errors, "content-placement-mismatch", content_id)
    if source.get("name") != expected_artifact or exact.get("artifact_id") != expected_artifact:
        _error(errors, "content-identity-mismatch", content_id)
        return None
    if requirement.get("explicitness") != "exact":
        _error(errors, "content-identity-mismatch", content_id)
        return None
    try:
        resolved = resolve_pack_artifact(pack_root, expected_artifact)
    except (PackDigestError, OSError, ValueError):
        _error(errors, "content-identity-mismatch", content_id)
        return None
    expected_digest = str(exact.get("digest", ""))
    if (
        resolved.identity.version != exact.get("version")
        or resolved.identity.media_type != exact.get("media_type")
        or resolved.identity.digest != expected_digest
    ):
        _error(errors, "content-identity-mismatch", content_id)
    data = overrides.get(expected_artifact, resolved.data)
    if "sha256:" + hashlib.sha256(resolved.data).hexdigest() != expected_digest:
        _error(errors, "content-identity-mismatch", content_id)
    return data


def _normalized_rule_path(default_path: str, rule_file: object) -> str:
    value = str(rule_file)
    if value.startswith("/"):
        return str(pathlib.PurePosixPath(value))
    return str(pathlib.PurePosixPath(default_path, value))


def _validate_static_content(
    pack_root: pathlib.Path,
    sdl: Mapping[str, Any],
    errors: list[str],
    overrides: Mapping[str, bytes],
) -> tuple[Mapping[str, Any], bytes]:
    materialized: dict[str, bytes] = {}
    for content_id in _SURICATA_CONTENT:
        data = _resolve_content(pack_root, sdl, content_id, errors, overrides)
        if data is not None:
            materialized[content_id] = data

    config_bytes = materialized.get("suricata-config", b"")
    try:
        config = yaml.safe_load(config_bytes.decode("utf-8"))
    except (UnicodeDecodeError, yaml.YAMLError):
        _error(errors, "config-invalid", "suricata-config")
        config = {}
    if not isinstance(config, Mapping):
        _error(errors, "config-invalid", "suricata-config")
        config = {}

    local = materialized.get("suricata-local-rules", b"")
    if not local.strip():
        _error(errors, "local-rules-empty", "suricata-local-rules")
    try:
        local_text = local.decode("utf-8")
    except UnicodeDecodeError:
        _error(errors, "local-rules-invalid", "suricata-local-rules")
        local_text = ""
    active = [
        line.strip()
        for line in local_text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    effective = [line for line in active if line.startswith("alert ")]
    if not effective:
        _error(errors, "local-rules-zero-effective", "suricata-local-rules")
    if len(effective) != len(active):
        _error(errors, "local-rule-action-invalid", "all local rules must be alert rules")

    sids = tuple(int(match.group(1)) for line in effective if (match := _SID.search(line)))
    if sids != _EXPECTED_LOCAL_SIDS or len(sids) != len(set(sids)):
        _error(errors, "local-rule-sids-mismatch", "expected the authoritative 16-SID corpus")

    variables = _as_mapping(config.get("vars"))
    defined = set(_as_mapping(variables.get("address-groups"))) | set(
        _as_mapping(variables.get("port-groups"))
    )
    referenced = set(_VARIABLE_REF.findall("\n".join(effective)))
    for group in ("address-groups", "port-groups"):
        for value in _as_mapping(variables.get(group)).values():
            referenced.update(_VARIABLE_REF.findall(str(value)))
    missing = sorted(referenced - defined)
    if missing:
        _error(errors, "rule-variable-undefined", ",".join(missing))

    expected_variables = {
        "HOME_NET",
        "HTTP_SERVERS",
        "HTTP_PORTS",
        "INTERNAL_NET",
        "DMZ_NET",
    }
    if not expected_variables <= defined:
        _error(errors, "rule-variable-undefined", "authoritative TechVault variable set")

    if b"# ioc_count=0" not in materialized.get("suricata-misp-ioc-rules-seed", b""):
        _error(errors, "misp-seed-invalid", "the initial generated source must declare zero indicators")
    return config, local


def _validate_runtime_joins(
    sdl: Mapping[str, Any], config: Mapping[str, Any], local: bytes, errors: list[str]
) -> None:
    nodes = _as_mapping(sdl.get("nodes"))
    suricata_runtime = _as_mapping(_as_mapping(nodes.get("suricata")).get("runtime"))
    engines = suricata_runtime.get("network_detection_engines", [])
    engine = engines[0] if isinstance(engines, list) and len(engines) == 1 else {}
    engine = _as_mapping(engine)
    if engine.get("network_detection_engine_id") != "suricata-engine":
        _error(errors, "engine-missing", "suricata-engine")

    if engine.get("configuration_file_refs") != ["/etc/suricata/suricata.yaml"]:
        _error(errors, "configuration-ref-mismatch", "suricata-engine")
    if set(engine.get("log_file_refs", [])) != {
        "/var/log/suricata/eve.json",
        "/var/log/suricata/fast.log",
    }:
        _error(errors, "output-ref-mismatch", "suricata-engine")

    sources = {
        item.get("source_id"): item
        for item in engine.get("rule_sources", [])
        if isinstance(item, Mapping)
    }
    expected_source_paths = {
        "suricata-builtin": "/var/lib/suricata/rules/suricata.rules",
        "techvault-local": "/etc/suricata/rules/local.rules",
        "misp-iocs": "/var/lib/suricata/rules/misp/misp-iocs.rules",
    }
    for source_id, path in expected_source_paths.items():
        source = _as_mapping(sources.get(source_id))
        if source.get("file_refs") != [path] or source.get("loaded") is not True:
            _error(errors, "rule-source-mismatch", source_id)

    local_source = _as_mapping(sources.get("techvault-local"))
    actual_count = sum(
        1
        for line in local.decode("utf-8", errors="ignore").splitlines()
        if line.strip().startswith("alert ")
    )
    if local_source.get("rule_count") != actual_count or actual_count != len(
        _EXPECTED_LOCAL_SIDS
    ):
        _error(errors, "local-rule-count-mismatch", f"declared={local_source.get('rule_count')} actual={actual_count}")

    misp_source = _as_mapping(sources.get("misp-iocs"))
    if misp_source.get("generated_by") != _FORWARDER_REF:
        _error(errors, "generated-source-mismatch", "misp-iocs")

    default_path = str(config.get("default-rule-path", ""))
    rule_files = config.get("rule-files")
    if not isinstance(rule_files, list) or any(
        not isinstance(item, str) or not item.strip() for item in rule_files
    ):
        _error(errors, "rule-files-invalid", "rule-files must be a list of paths")
        rule_files = []
    configured = {
        _normalized_rule_path(default_path, item)
        for item in rule_files
    }
    expected_paths = set(expected_source_paths.values())
    for path in sorted(configured ^ expected_paths):
        _error(errors, "rule-file-unresolved", path)

    content_paths = {
        str(item.get("path"))
        for item in _as_mapping(sdl.get("content")).values()
        if isinstance(item, Mapping) and item.get("target") == "suricata"
    }
    built_in = expected_source_paths["suricata-builtin"]
    for path in sorted(configured - {built_in} - content_paths):
        _error(errors, "rule-file-unresolved", path)

    outputs = {
        item.get("stream_id"): item
        for item in engine.get("output_streams", [])
        if isinstance(item, Mapping)
    }
    if _as_mapping(outputs.get("eve-json")).get("path") != "/var/log/suricata/eve.json":
        _error(errors, "output-ref-mismatch", "eve-json")

    channels = {
        item.get("channel_id"): item
        for item in engine.get("control_channels", [])
        if isinstance(item, Mapping)
    }
    control = _as_mapping(channels.get("command-socket"))
    default_run_dir = str(config.get("default-run-dir", ""))
    configured_socket = _normalized_rule_path(
        default_run_dir, _as_mapping(config.get("unix-command")).get("filename", "")
    )
    if (
        control.get("path") != configured_socket
        or control.get("kind") != "unix_socket"
        or "rule_reload" not in control.get("capabilities", [])
    ):
        _error(errors, "control-channel-mismatch", "command-socket")

    sync_runtime = _as_mapping(_as_mapping(nodes.get("misp-suricata-sync")).get("runtime"))
    forwarders = sync_runtime.get("forwarding_agents", [])
    forwarder = forwarders[0] if isinstance(forwarders, list) and len(forwarders) == 1 else {}
    forwarder = _as_mapping(forwarder)
    transforms = forwarder.get("transforms", [])
    transform = transforms[0] if isinstance(transforms, list) and len(transforms) == 1 else {}
    reloads = forwarder.get("reload_channels", [])
    reload = reloads[0] if isinstance(reloads, list) and len(reloads) == 1 else {}
    if _as_mapping(transform).get("sid_namespace") != _MISP_SID_NAMESPACE:
        _error(errors, "sid-namespace-mismatch", "ioc-to-suricata-rules")
    if _as_mapping(reload).get("target_ref") != _CONTROL_CHANNEL_REF:
        _error(errors, "reload-target-mismatch", "suricata-command-socket")

    volume_sources = {"suricata_command_socket", "suricata_misp_rules"}
    for runtime, owner in ((suricata_runtime, "suricata"), (sync_runtime, "misp-suricata-sync")):
        if any(
            item.get("source") in volume_sources
            for item in runtime.get("mounts", [])
            if isinstance(item, Mapping)
        ):
            _error(errors, "shared-volume-mismatch", f"duplicate runtime mount on {owner}")

    volumes = _as_mapping(sdl.get("persistent_volumes"))
    if "suricata_config_seed" in volumes:
        _error(errors, "stale-config-seed", "suricata_config_seed")
    expected_consumers = {
        "suricata_command_socket": {
            ("suricata", "/var/run/suricata", "read_write"),
            ("misp-suricata-sync", "/var/run/suricata", "read_write"),
        },
        "suricata_misp_rules": {
            ("suricata", "/var/lib/suricata/rules/misp", "read_only"),
            (
                "misp-suricata-sync",
                "/var/lib/suricata/rules/misp",
                "read_write",
            ),
        },
    }
    for name, expected in expected_consumers.items():
        volume = _as_mapping(volumes.get(name))
        consumers = {
            (
                item.get("node"),
                item.get("mount_destination"),
                item.get("access_mode"),
            )
            for item in volume.get("consumers", [])
            if isinstance(item, Mapping)
        }
        if (
            volume.get("lifecycle") != "ephemeral"
            or volume.get("access_mode") != "read_write_many"
            or consumers != expected
        ):
            _error(errors, "shared-volume-mismatch", name)


def _login_route_is_sql_injectable(
    pack_root: pathlib.Path, overrides: Mapping[str, bytes]
) -> bool:
    """The detection path needs its CWE-89 binding on the portal login route."""

    try:
        data = resolve_pack_artifact(pack_root, _BINDINGS_ARTIFACT).data
    except (PackDigestError, OSError, ValueError):
        data = b""
    try:
        document = json.loads(overrides.get(_BINDINGS_ARTIFACT, data))
    except ValueError:
        return False
    return any(
        _as_mapping(_as_mapping(binding).get("subject")).get("canonical_ref")
        == _LOGIN_ROUTE_SUBJECT
        and _as_mapping(_as_mapping(binding).get("scheme")).get("concept_id")
        == _LOGIN_WEAKNESS_CONCEPT
        for binding in _as_mapping(_as_mapping(document).get("bindings")).values()
    )


def _validate_evidence_contract(
    pack_root: pathlib.Path,
    sdl: Mapping[str, Any],
    errors: list[str],
    overrides: Mapping[str, bytes],
) -> None:
    propositions = _as_mapping(sdl.get("propositions"))
    assertions = _as_mapping(sdl.get("assertions"))
    evidence = _as_mapping(sdl.get("evidence_requirements"))

    readiness = _as_mapping(propositions.get("suricata-local-rules-ready"))
    if readiness.get("subjects") != [_LOCAL_SOURCE_REF] or readiness.get(
        "evidence_requirements"
    ) != ["suricata-local-rule-readiness"]:
        _error(errors, "readiness-evidence-mismatch", "suricata-local-rules-ready")
    detection = _as_mapping(propositions.get("suricata-login-sqli-detected"))
    if detection.get("subjects") != [_LOCAL_SOURCE_REF] or detection.get(
        "evidence_requirements"
    ) != ["suricata-login-sqli-alert"]:
        _error(errors, "detection-evidence-mismatch", "suricata-login-sqli-detected")
    for assertion_id in ("suricata-local-rules-ready", "suricata-login-sqli-detected"):
        assertion = _as_mapping(assertions.get(assertion_id))
        if assertion.get("proposition") != assertion_id or assertion.get("role") != "postcondition":
            _error(errors, "detection-evidence-mismatch", assertion_id)

    readiness_evidence = _as_mapping(evidence.get("suricata-local-rule-readiness"))
    if set(readiness_evidence.get("source_refs", [])) != {
        _BUILTIN_SOURCE_REF,
        _LOCAL_SOURCE_REF,
    } or set(readiness_evidence.get("scope_refs", [])) != {
        "nodes.suricata",
        "content.suricata-config",
        "content.suricata-local-rules",
    }:
        _error(errors, "readiness-evidence-mismatch", "suricata-local-rule-readiness")
    alert_evidence = _as_mapping(evidence.get("suricata-login-sqli-alert"))
    if set(alert_evidence.get("source_refs", [])) != {_EVE_STREAM_REF, _WAZUH_RULES_REF}:
        _error(errors, "detection-evidence-mismatch", "suricata-login-sqli-alert sources")
    if alert_evidence.get("trigger_ref") != _LOGIN_ROUTE_REF or not {
        _LOGIN_ROUTE_REF,
        _LOCAL_SOURCE_REF,
    } <= set(alert_evidence.get("scope_refs", [])):
        _error(errors, "detection-evidence-mismatch", "suricata-login-sqli-alert path")
    scope = str(alert_evidence.get("scope", ""))
    if "1000010" not in scope or "303020" not in scope:
        _error(errors, "detection-evidence-mismatch", "expected alert identities")

    if not _login_route_is_sql_injectable(pack_root, overrides):
        _error(errors, "detection-path-mismatch", "webapp login weakness")
    try:
        wazuh_rules = resolve_pack_artifact(pack_root, "techvault-wazuh-suricata-rules").data
    except (PackDigestError, OSError, ValueError):
        wazuh_rules = b""
    wazuh_rules = overrides.get("techvault-wazuh-suricata-rules", wazuh_rules)
    if b'<rule id="303020"' not in wazuh_rules or b"web-application-attack" not in wazuh_rules:
        _error(errors, "detection-path-mismatch", "Wazuh rule 303020")


def _wazuh_forwarders_by_owner(
    nodes: Mapping[str, Any], errors: list[str]
) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for owner, raw_node in nodes.items():
        runtime = _as_mapping(_as_mapping(raw_node).get("runtime"))
        agents = [
            _as_mapping(agent)
            for agent in runtime.get("forwarding_agents", [])
            if isinstance(agent, Mapping)
            and agent.get("implementation") == "wazuh_agent"
        ]
        if not agents:
            continue
        if len(agents) != 1:
            _wazuh_error(errors, "forwarder-owner-set-mismatch", str(owner))
        result[str(owner)] = agents[0]
    if set(result) != set(_WAZUH_AGENT_SPECS):
        _wazuh_error(
            errors,
            "forwarder-owner-set-mismatch",
            ",".join(sorted(set(result) ^ set(_WAZUH_AGENT_SPECS))),
        )
    return result


def _validate_wazuh_manager_membership(
    nodes: Mapping[str, Any],
    forwarders: Mapping[str, Mapping[str, Any]],
    errors: list[str],
) -> None:
    manager_runtime = _as_mapping(_as_mapping(nodes.get("wazuh-manager")).get("runtime"))
    managers = [
        _as_mapping(manager)
        for manager in manager_runtime.get("security_monitoring_managers", [])
        if isinstance(manager, Mapping)
        and manager.get("security_monitoring_manager_id") == "wazuh-manager"
    ]
    if len(managers) != 1:
        _wazuh_error(errors, "manager-membership-mismatch", "wazuh-manager")
        return

    agents = [
        _as_mapping(agent)
        for agent in managers[0].get("agents", [])
        if isinstance(agent, Mapping)
    ]
    actual_pairs = {(agent.get("node_ref"), agent.get("name")) for agent in agents}
    expected_pairs = {
        (owner, spec["name"]) for owner, spec in _WAZUH_AGENT_SPECS.items()
    }
    if actual_pairs != expected_pairs or len(agents) != len(expected_pairs):
        _wazuh_error(errors, "manager-membership-mismatch", "owner/name bijection")
    agent_ids = [agent.get("agent_id") for agent in agents]
    names = [agent.get("name") for agent in agents]
    if len(agent_ids) != len(set(agent_ids)) or len(names) != len(set(names)):
        _wazuh_error(errors, "manager-membership-mismatch", "duplicate identity")
    for agent in agents:
        if agent.get("status") != "active":
            _wazuh_error(
                errors,
                "manager-membership-mismatch",
                str(agent.get("agent_id", "unknown")),
            )
    for owner, forwarder in forwarders.items():
        if (owner, forwarder.get("name")) not in actual_pairs:
            _wazuh_error(errors, "manager-membership-mismatch", owner)


def _validate_wazuh_targets(
    manager_node: Mapping[str, Any],
    owner: str,
    agent: Mapping[str, Any],
    errors: list[str],
) -> None:
    services = {
        service.get("name"): _as_mapping(service)
        for service in manager_node.get("services", [])
        if isinstance(service, Mapping)
    }
    runtime = _as_mapping(manager_node.get("runtime"))
    managers = runtime.get("security_monitoring_managers", [])
    manager = _as_mapping(managers[0]) if isinstance(managers, list) and managers else {}
    listeners = {
        listener.get("service"): _as_mapping(listener)
        for listener in manager.get("listeners", [])
        if isinstance(listener, Mapping)
    }
    targets = {
        target.get("target_service_ref"): _as_mapping(target)
        for target in agent.get("ship_targets", [])
        if isinstance(target, Mapping)
    }
    expected = {
        "agent-events": ("agent_event_ingestion", "ingestion_port", 1514),
        "agent-enrollment": ("agent_enrollment", "enrollment_port", 1515),
    }
    if set(targets) != set(expected) or len(agent.get("ship_targets", [])) != 2:
        _wazuh_error(errors, "target-contract-mismatch", owner)
        return
    for service_name, (role, port_field, expected_port) in expected.items():
        target = targets[service_name]
        service = services.get(service_name, {})
        listener = listeners.get(service_name, {})
        other_port = "enrollment_port" if port_field == "ingestion_port" else "ingestion_port"
        if (
            target.get("target_node_ref") != "wazuh-manager"
            or target.get(port_field) != expected_port
            or target.get(other_port) is not None
            or target.get("protocol") != "tcp"
            or service.get("port") != expected_port
            or service.get("protocol") != "tcp"
            or listener.get("role") != role
            or listener.get("protocol") != "tcp"
        ):
            _wazuh_error(errors, "target-contract-mismatch", f"{owner}:{service_name}")
        if service_name == "agent-enrollment" and target.get(
            "enrollment_identity_classification"
        ) != "operator_secret":
            _wazuh_error(errors, "target-contract-mismatch", f"{owner}:enrollment")


def _validate_wazuh_realization(
    sdl: Mapping[str, Any],
    owner: str,
    spec: Mapping[str, Any],
    agent: Mapping[str, Any],
    errors: list[str],
) -> None:
    nodes = _as_mapping(sdl.get("nodes"))
    node = _as_mapping(nodes.get(owner))
    runtime = _as_mapping(node.get("runtime"))
    actual_sources = {
        (
            source.get("source_id"),
            source.get("location"),
            source.get("parse_format"),
        )
        for source in agent.get("sources", [])
        if isinstance(source, Mapping)
        and source.get("kind") == "tailed_path"
        and str(source.get("location", "")).strip()
    }
    if actual_sources != spec["sources"] or len(agent.get("sources", [])) != len(spec["sources"]):
        _wazuh_error(errors, "source-contract-mismatch", owner)
    if owner in _WAZUH_ENDPOINT_OWNERS and any(
        source[2] == "eve_json" for source in actual_sources
    ):
        _wazuh_error(errors, "source-contract-mismatch", f"{owner}:network-evidence")
    transforms = [
        transform
        for transform in agent.get("transforms", [])
        if isinstance(transform, Mapping) and transform.get("kind") == "parse"
    ]
    buffer = _as_mapping(agent.get("buffer_policy"))
    if len(transforms) != 1 or buffer.get("crypto") != "aes":
        _wazuh_error(errors, "source-contract-mismatch", f"{owner}:processing")

    inventory = {
        item.get("path")
        for item in runtime.get("filesystem_inventory", [])
        if isinstance(item, Mapping) and item.get("entry_type") == "file"
    }
    # Suricata already owns its EVE source through the typed output stream.
    inventory.update(
        stream.get("path")
        for engine in runtime.get("network_detection_engines", [])
        if isinstance(engine, Mapping)
        for stream in engine.get("output_streams", [])
        if isinstance(stream, Mapping)
    )
    if any(location not in inventory for _, location, _ in spec["sources"]):
        _wazuh_error(errors, "source-contract-mismatch", f"{owner}:unrealized-path")

    volumes = _as_mapping(sdl.get("persistent_volumes"))
    state_volume = _as_mapping(volumes.get(str(spec["state_volume"])))
    expected_consumer = {
        "node": owner,
        "mount_destination": "/var/ossec/etc",
        "access_mode": "read_write",
    }
    if (
        state_volume.get("lifecycle") != "retain"
        or state_volume.get("access_mode") != "read_write_once"
        or state_volume.get("consumers") != [expected_consumer]
    ):
        _wazuh_error(errors, "persistence-mismatch", owner)

    infrastructure = _as_mapping(_as_mapping(sdl.get("infrastructure")).get(owner))
    if "wazuh-manager" not in infrastructure.get("dependencies", []):
        _wazuh_error(errors, "lifecycle-mismatch", f"{owner}:dependency")

    components = [
        item for item in runtime.get("software_components", [])
        if isinstance(item, Mapping) and item.get("component_id") == "wazuh-agent"
    ]
    if len(components) != 1 or (
        components[0].get("name") != "Wazuh agent"
        or components[0].get("component_type") != "application"
        or components[0].get("presence", "required") != "required"
        or components[0].get("version") != "4.12.0"
        or agent.get("version") != "4.12.0"
    ):
        _wazuh_error(errors, "software-mismatch", owner)


def _validate_wazuh_readiness(
    sdl: Mapping[str, Any],
    forwarders: Mapping[str, Mapping[str, Any]],
    errors: list[str],
) -> None:
    proposition = _as_mapping(_as_mapping(sdl.get("propositions")).get("wazuh-agents-ready"))
    assertion = _as_mapping(_as_mapping(sdl.get("assertions")).get("wazuh-agents-ready"))
    evidence = _as_mapping(_as_mapping(sdl.get("evidence_requirements")).get("wazuh-agent-readiness"))
    predicate = _as_mapping(proposition.get("predicate"))
    subjects = {f"nodes.{owner}" for owner in _WAZUH_AGENT_SPECS}
    manager_ref = "nodes.wazuh-manager.runtime.security_monitoring_managers.wazuh-manager"
    sources = {manager_ref} | {
        f"nodes.{owner}.runtime.forwarding_agents.{agent.get('forwarding_agent_id')}"
        for owner, agent in forwarders.items()
    }
    if (
        proposition.get("basis") != "observed_state"
        or proposition.get("quantifier", "all") != "all"
        or set(proposition.get("subjects", [])) != subjects
        or proposition.get("evidence_requirements") != ["wazuh-agent-readiness"]
        or predicate.get("kind") != "boolean"
        or predicate.get("property") != "wazuh-agent-ready"
        or predicate.get("semantic_ref") != "urn:techvault:observable:wazuh-agent-ready"
        or predicate.get("operator", "equals") != "equals"
        or predicate.get("expected") is not True
        or assertion.get("proposition") != "wazuh-agents-ready"
        or assertion.get("role") != "precondition"
        or assertion.get("polarity", "positive") != "positive"
        or set(evidence.get("source_refs", [])) != sources
        or set(evidence.get("scope_refs", [])) != subjects | {"nodes.wazuh-manager"}
        or evidence.get("channel") != "file_artifact"
        or evidence.get("redaction") != "redact_secrets"
        or evidence.get("loss_disclosure") != "required"
    ):
        _wazuh_error(errors, "readiness-mismatch", "wazuh-agents-ready")


def validate_wazuh_agent_contract(sdl: Mapping[str, Any]) -> list[str]:
    """Validate TechVault's closed joins around RAES-owned Wazuh models."""

    errors: list[str] = []
    nodes = _as_mapping(sdl.get("nodes"))
    forwarders = _wazuh_forwarders_by_owner(nodes, errors)
    names = [agent.get("name") for agent in forwarders.values()]
    if len(names) != len(set(names)):
        _wazuh_error(errors, "enrollment-name-duplicate", "forwarding agents")
    manager_node = _as_mapping(nodes.get("wazuh-manager"))
    for owner, spec in _WAZUH_AGENT_SPECS.items():
        agent = forwarders.get(owner)
        if agent is None:
            continue
        if agent.get("name") != spec["name"] or agent.get("agent_kind") != "log_forwarder":
            _wazuh_error(errors, "identity-mismatch", owner)
        _validate_wazuh_targets(manager_node, owner, agent, errors)
        _validate_wazuh_realization(sdl, owner, spec, agent, errors)
    _validate_wazuh_manager_membership(nodes, forwarders, errors)
    _validate_wazuh_readiness(sdl, forwarders, errors)
    return errors


def validate_suricata_contract(
    pack_root: pathlib.Path,
    sdl: Mapping[str, Any],
    *,
    artifact_overrides: Mapping[str, bytes] | None = None,
) -> list[str]:
    """Validate TechVault's joins around RAES-owned Suricata declarations.

    This deliberately checks only this pack's closed contract. Suricata remains
    the authority for configuration/rule syntax and RAES remains the semantic
    authority for the declaration models.
    """

    errors: list[str] = []
    config, local = _validate_static_content(
        pack_root, sdl, errors, artifact_overrides or {}
    )
    _validate_runtime_joins(sdl, config, local, errors)
    _validate_evidence_contract(pack_root, sdl, errors, artifact_overrides or {})
    return errors


def validate_misp_contract(sdl: Mapping[str, Any]) -> list[str]:
    """Validate TechVault's closed, provider-neutral MISP contract."""

    errors: list[str] = []
    nodes = _as_mapping(sdl.get("nodes"))
    misp_runtime = _as_mapping(_as_mapping(nodes.get("misp")).get("runtime"))

    applications = misp_runtime.get("platform_applications", [])
    application = _as_mapping(
        applications[0]
        if isinstance(applications, list) and len(applications) == 1
        else {}
    )
    expected_bindings = {
        "misp-relational-store": ("data_source", "misp-db", "mysql"),
        "misp-cache-store": ("data_source", "misp-redis", "redis"),
    }
    bindings = application.get("upstream_bindings", [])
    actual_bindings = {
        str(item.get("binding_id")): (
            item.get("role"),
            item.get("target_node_ref"),
            item.get("target_service_ref"),
        )
        for item in bindings
        if isinstance(item, Mapping)
    }
    if (
        len(bindings) != len(expected_bindings)
        or actual_bindings != expected_bindings
    ):
        _misp_error(errors, "binding-invalid", "platform upstream bindings")

    settings = application.get("settings", [])
    if not isinstance(settings, list) or len(settings) != 1:
        _misp_error(errors, "setting-invalid", "canonical URL inventory")
    else:
        setting = _as_mapping(settings[0])
        if {
            "setting_id": setting.get("setting_id"),
            "name": setting.get("name"),
            "value": setting.get("value"),
            "provenance": setting.get("provenance"),
            "classification": setting.get("classification"),
        } != {
            "setting_id": "misp-canonical-url",
            "name": "Canonical MISP URL",
            "value": "https://misp.techvault.local",
            "provenance": "runtime",
            "classification": "plain",
        }:
            _misp_error(errors, "setting-invalid", "canonical URL state")

    listeners = misp_runtime.get("service_listeners", [])
    listener = _as_mapping(
        listeners[0]
        if isinstance(listeners, list) and len(listeners) == 1
        else {}
    )
    readiness = _as_mapping(listener.get("readiness"))
    if (
        listener.get("service_listener_id") != "misp-https-listener"
        or readiness.get("probe") != "misp-authenticated-api-operation"
        or readiness.get("evidence_refs")
        != ["misp-authenticated-api-readiness"]
        or readiness.get("criteria")
        != (
            "A certificate-verified, authenticated MISP API write and read "
            "succeeds through the declared MariaDB and Redis services."
        )
    ):
        _misp_error(errors, "readiness-invalid", "authenticated API readiness")

    authorizations = misp_runtime.get("app_authorizations", [])
    authorization = _as_mapping(
        authorizations[0]
        if isinstance(authorizations, list) and len(authorizations) == 1
        else {}
    )
    principal_shape = {
        str(item.get("principal_id")): (
            item.get("kind"),
            item.get("name", ""),
            item.get("credential_classification"),
        )
        for item in authorization.get("principals", [])
        if isinstance(item, Mapping)
    }
    expected_principals = {
        "misp-administrator": ("user", "admin@admin.test", "operator_secret"),
        "misp-suricata-sync-api-key": ("api_key", "", "operator_secret"),
    }
    authorization_shape = {
        "roles": {
            str(item.get("role_id")): item.get("name")
            for item in authorization.get("roles", [])
            if isinstance(item, Mapping)
        },
        "permission_grants": {
            str(item.get("grant_id")): (
                item.get("role_ref"),
                item.get("resource_kind"),
                item.get("actions"),
                item.get("resource_patterns"),
                item.get("effect"),
            )
            for item in authorization.get("permission_grants", [])
            if isinstance(item, Mapping)
        },
        "role_mappings": {
            str(item.get("mapping_id")): (
                item.get("role_ref"),
                item.get("users"),
            )
            for item in authorization.get("role_mappings", [])
            if isinstance(item, Mapping)
        },
    }
    expected_authorization_shape = {
        "roles": {
            "misp-administrator-role": "MISP administrator",
            "misp-sync-reader-role": "MISP synchronization reader",
        },
        "permission_grants": {
            "misp-administrator-access": (
                "misp-administrator-role",
                "app_resource",
                ["manage"],
                ["*"],
                "allow",
            ),
            "misp-sync-read-access": (
                "misp-sync-reader-role",
                "app_resource",
                ["read"],
                ["attributes/*", "events/*"],
                "allow",
            ),
        },
        "role_mappings": {
            "misp-administrator-mapping": (
                "misp-administrator-role",
                ["misp-administrator"],
            ),
            "misp-sync-reader-mapping": (
                "misp-sync-reader-role",
                ["misp-suricata-sync-api-key"],
            ),
        },
    }
    if (
        authorization.get("app_authorization_id") != "misp-api-authorization"
        or authorization.get("resource_vocabulary") != "app_resource"
        or authorization.get("auth_enabled") is not True
        or principal_shape != expected_principals
        or authorization_shape != expected_authorization_shape
        or len(authorization.get("principals", [])) != len(expected_principals)
        or any(
            len(authorization.get(field, [])) != len(expected)
            for field, expected in expected_authorization_shape.items()
        )
    ):
        _misp_error(errors, "principal-invalid", "MISP authorization inventory")

    db_runtime = _as_mapping(_as_mapping(nodes.get("misp-db")).get("runtime"))
    database_services = db_runtime.get("database_services", [])
    database = _as_mapping(
        database_services[0]
        if isinstance(database_services, list) and len(database_services) == 1
        else {}
    )
    databases = database.get("databases", [])
    roles = database.get("roles", [])
    grants = database.get("grants", [])
    logical_database = _as_mapping(
        databases[0] if isinstance(databases, list) and len(databases) == 1 else {}
    )
    role = _as_mapping(roles[0] if isinstance(roles, list) and len(roles) == 1 else {})
    grant = _as_mapping(
        grants[0] if isinstance(grants, list) and len(grants) == 1 else {}
    )
    if (
        database.get("database_service_id") != "misp-db"
        or database.get("service") != "mysql"
        or database.get("engine") != "mariadb"
        or database.get("protocol") != "mysql"
        or {
            "database_id": logical_database.get("database_id"),
            "name": logical_database.get("name"),
            "origin": logical_database.get("origin"),
        }
        != {"database_id": "misp", "name": "misp", "origin": "scenario"}
        or {
            "role_id": role.get("role_id"),
            "name": role.get("name"),
            "role_type": role.get("role_type"),
            "origin": role.get("origin"),
            "can_login": role.get("can_login"),
        }
        != {
            "role_id": "misp-application-role",
            "name": "misp",
            "role_type": "application",
            "origin": "scenario",
            "can_login": True,
        }
        or {
            "grantee_role_ref": grant.get("grantee_role_ref"),
            "object_type": grant.get("object_type"),
            "object_ref": grant.get("object_ref"),
            "privileges": grant.get("privileges"),
            "with_grant_option": grant.get("with_grant_option"),
        }
        != {
            "grantee_role_ref": "misp-application-role",
            "object_type": "database",
            "object_ref": "misp",
            "privileges": ["ALL"],
            "with_grant_option": False,
        }
    ):
        _misp_error(errors, "database-invalid", "MariaDB logical state")

    relationships = _as_mapping(sdl.get("relationships"))
    database_relationship = _as_mapping(relationships.get("misp-uses-database"))
    database_access = _as_mapping(database_relationship.get("database_access"))
    if {
        "type": database_relationship.get("type"),
        "source": database_relationship.get("source"),
        "target": database_relationship.get("target"),
        "role_ref": database_access.get("role_ref"),
        "auth_method": database_access.get("auth_method"),
    } != {
        "type": "connects_to",
        "source": "nodes.misp.runtime.applications.misp-web",
        "target": "nodes.misp-db.runtime.database_services.misp-db",
        "role_ref": "misp-application-role",
        "auth_method": "password",
    }:
        _misp_error(errors, "database-access-invalid", "MISP database access")

    redis_runtime = _as_mapping(
        _as_mapping(nodes.get("misp-redis")).get("runtime")
    )
    datastores = redis_runtime.get("datastore_services", [])
    datastore = _as_mapping(
        datastores[0]
        if isinstance(datastores, list) and len(datastores) == 1
        else {}
    )
    redis_authorizations = redis_runtime.get("app_authorizations", [])
    redis_authorization = _as_mapping(
        redis_authorizations[0]
        if isinstance(redis_authorizations, list)
        and len(redis_authorizations) == 1
        else {}
    )
    redis_principals = redis_authorization.get("principals", [])
    redis_principal = _as_mapping(
        redis_principals[0]
        if isinstance(redis_principals, list) and len(redis_principals) == 1
        else {}
    )
    redis_authorization_shape = {
        "roles": {
            str(item.get("role_id")): item.get("name")
            for item in redis_authorization.get("roles", [])
            if isinstance(item, Mapping)
        },
        "permission_grants": {
            str(item.get("grant_id")): (
                item.get("role_ref"),
                item.get("resource_kind"),
                item.get("actions"),
                item.get("resource_patterns"),
                item.get("effect"),
            )
            for item in redis_authorization.get("permission_grants", [])
            if isinstance(item, Mapping)
        },
        "role_mappings": {
            str(item.get("mapping_id")): (
                item.get("role_ref"),
                item.get("users"),
            )
            for item in redis_authorization.get("role_mappings", [])
            if isinstance(item, Mapping)
        },
    }
    if (
        datastore.get("authorization_ref") != "misp-redis-authorization"
        or redis_authorization.get("app_authorization_id")
        != "misp-redis-authorization"
        or redis_authorization.get("resource_vocabulary") != "redis_acl"
        or redis_authorization.get("auth_enabled") is not True
        or {
            "principal_id": redis_principal.get("principal_id"),
            "kind": redis_principal.get("kind"),
            "credential_classification": redis_principal.get(
                "credential_classification"
            ),
        }
        != {
            "principal_id": "misp-cache-client",
            "kind": "service_account",
            "credential_classification": "redacted",
        }
        or redis_authorization_shape
        != {
            "roles": {"misp-cache-role": "MISP cache read/write"},
            "permission_grants": {
                "misp-cache-access": (
                    "misp-cache-role",
                    "redis_acl",
                    ["read", "write"],
                    ["*"],
                    "allow",
                )
            },
            "role_mappings": {
                "misp-cache-client-mapping": (
                    "misp-cache-role",
                    ["misp-cache-client"],
                )
            },
        }
    ):
        _misp_error(
            errors,
            "redis-authorization-invalid",
            "Redis authorization inventory",
        )

    generated = _as_mapping(sdl.get("generated_artifacts"))
    certificates = _as_mapping(generated.get("techvault-soc-certificates"))
    outputs = {
        str(item.get("name")): (
            item.get("path"),
            item.get("sensitivity"),
            item.get("disposition", ""),
        )
        for item in certificates.get("outputs", [])
        if isinstance(item, Mapping)
    }
    consumers = [
        item
        for item in certificates.get("consumers", [])
        if isinstance(item, Mapping) and item.get("node") == "misp"
    ]
    certificate_consumer = _as_mapping(consumers[0] if len(consumers) == 1 else {})
    if (
        any(
            outputs.get(name) != expected
            for name, expected in {
                "ca-private-key": ("lab-ca.key", "secret", "producer_private"),
                "ca-certificate": ("lab-ca.pem", "public", ""),
                "misp-certificate": ("misp/server.pem", "public", ""),
                "misp-private-key": ("misp/server.key", "secret", ""),
            }.items()
        )
        or len(consumers) != 1
        or certificate_consumer.get("access_mode") != "read_only"
        or set(certificate_consumer.get("selected_outputs", []))
        != {"ca-certificate", "misp-certificate", "misp-private-key"}
    ):
        _misp_error(
            errors,
            "certificate-selection-invalid",
            "MISP certificate outputs",
        )

    requirements = _as_mapping(sdl.get("evidence_requirements"))
    evidence = _as_mapping(requirements.get("misp-authenticated-api-readiness"))
    expected_sources = {
        "nodes.misp.runtime.platform_applications.misp-threat-intelligence",
        "nodes.misp-db.runtime.database_services.misp-db",
        "nodes.misp-redis.runtime.datastore_services.misp-redis",
    }
    if (
        evidence.get("channel") != "api_response"
        or evidence.get("redaction") != "redact_secrets"
        or evidence.get("boundary_kind") != "system_under_test"
        or set(evidence.get("source_refs", [])) != expected_sources
        or len(evidence.get("source_refs", [])) != len(expected_sources)
    ):
        _misp_error(errors, "evidence-invalid", "authenticated readiness evidence")

    propositions = _as_mapping(sdl.get("propositions"))
    proposition = _as_mapping(propositions.get("misp-authenticated-api-ready"))
    assertions = _as_mapping(sdl.get("assertions"))
    assertion = _as_mapping(assertions.get("misp-authenticated-api-ready"))
    if (
        proposition.get("evidence_requirements")
        != ["misp-authenticated-api-readiness"]
        or assertion.get("proposition") != "misp-authenticated-api-ready"
        or assertion.get("role") != "postcondition"
    ):
        _misp_error(errors, "readiness-invalid", "readiness proposition")

    sync_runtime = _as_mapping(
        _as_mapping(nodes.get("misp-suricata-sync")).get("runtime")
    )
    forwarding_agents = sync_runtime.get("forwarding_agents", [])
    forwarding_agent = _as_mapping(
        forwarding_agents[0]
        if isinstance(forwarding_agents, list) and len(forwarding_agents) == 1
        else {}
    )
    sources = forwarding_agent.get("sources", [])
    sync_source = _as_mapping(
        sources[0] if isinstance(sources, list) and len(sources) == 1 else {}
    )
    if sync_source.get("location") != "https://misp.techvault.local":
        _misp_error(errors, "setting-invalid", "sync canonical URL")

    return errors


def validate_cortex_contract(
    pack_root: pathlib.Path, sdl: Mapping[str, Any]
) -> list[str]:
    """Validate the closed joins that make TechVault's Cortex useful."""

    errors: list[str] = []
    nodes = _as_mapping(sdl.get("nodes"))
    content = _as_mapping(sdl.get("content"))
    cortex = _as_mapping(nodes.get("cortex"))
    thehive = _as_mapping(nodes.get("thehive"))

    cortex_runtime = _as_mapping(cortex.get("runtime"))
    applications = cortex_runtime.get("platform_applications", [])
    application = applications[0] if isinstance(applications, list) and applications else {}
    application = _as_mapping(application)
    if application.get("platform_application_id") != "cortex-enrichment":
        _cortex_error(errors, "application-missing", "cortex-enrichment")
    capabilities = {
        item.get("kind")
        for item in application.get("capabilities", [])
        if isinstance(item, Mapping)
    }
    if "analysis_execution" not in capabilities:
        _cortex_error(errors, "capability-missing", "analysis_execution")

    thehive_runtime = _as_mapping(thehive.get("runtime"))
    thehive_applications = thehive_runtime.get("platform_applications", [])
    thehive_application = _as_mapping(
        thehive_applications[0]
        if isinstance(thehive_applications, list) and thehive_applications
        else {}
    )
    cortex_bindings = [
        item
        for item in thehive_application.get("upstream_bindings", [])
        if isinstance(item, Mapping)
        and item.get("target_node_ref") == "cortex"
        and item.get("target_service_ref") == "cortex-api"
        and item.get("role") == "backend_api"
    ]
    connectors = [
        item
        for item in thehive_application.get("connectors", [])
        if isinstance(item, Mapping) and item.get("kind") == "analyzer_engine"
    ]
    if len(cortex_bindings) != 1 or len(connectors) != 1:
        _cortex_error(errors, "connector-binding-invalid", "TheHive connector")
    elif connectors[0].get("credential_classification") != "redacted":
        _cortex_error(errors, "connector-key-mismatch", "TheHive connector")

    authorizations = cortex_runtime.get("app_authorizations", [])
    authorization = (
        authorizations[0]
        if isinstance(authorizations, list) and authorizations
        else {}
    )
    principals = {
        item.get("principal_id"): item
        for item in _as_mapping(authorization).get("principals", [])
        if isinstance(item, Mapping)
    }
    principal = _as_mapping(principals.get("thehive-cortex-connector"))
    if (
        principal.get("kind") != "service_account"
        or principal.get("credential_classification") != "redacted"
        or principal.get("backend_roles") != ["read", "analyze"]
    ):
        _cortex_error(errors, "connector-principal-invalid", "least privilege")
    if set(principals) != {"thehive-cortex-connector"}:
        _cortex_error(errors, "unexpected-principal", "Cortex authorization")
    if "cortex-job-index-schema" in content:
        _cortex_error(errors, "native-schema-leaked", "Cortex owns its index mapping")

    expected_content = {
        "cortex-analyzer-definition": (
            "techvault-cortex-analyzer-definition",
            "/opt/techvault/cortex-analyzers/TechVaultScenarioContext/analyzer.json",
        ),
        "cortex-analyzer-executable": (
            "techvault-cortex-analyzer-executable",
            "/opt/techvault/cortex-analyzers/TechVaultScenarioContext/techvault_scenario_context.py",
        ),
    }
    resolved: dict[str, bytes] = {}
    for content_id, (artifact_id, path) in expected_content.items():
        item = _as_mapping(content.get(content_id))
        source = _as_mapping(item.get("source"))
        exact = _as_mapping(_as_mapping(source.get("artifact_requirement")).get("exact_artifact"))
        if item.get("path") != path or source.get("name") != artifact_id:
            _cortex_error(errors, "content-placement-mismatch", content_id)
            continue
        try:
            artifact = resolve_pack_artifact(pack_root, artifact_id)
        except (PackDigestError, OSError, ValueError):
            _cortex_error(errors, "content-identity-mismatch", content_id)
            continue
        if artifact.identity.digest != exact.get("digest"):
            _cortex_error(errors, "content-identity-mismatch", content_id)
        resolved[content_id] = artifact.data

    try:
        definition = json.loads(resolved.get("cortex-analyzer-definition", b"{}"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        definition = {}
    if (
        definition.get("name") != "TechVaultScenarioContext"
        or definition.get("version") != "1.0"
        or definition.get("dataTypeList") != ["ip"]
        or not definition.get("command")
    ):
        _cortex_error(errors, "analyzer-definition-invalid", "TechVaultScenarioContext_1_0")
    return errors


def _is_build_recipe(requirement: Mapping[str, Any]) -> bool:
    if requirement.get("materialization_specifications"):
        return True
    routes = requirement.get("permitted_routes")
    return any(
        _as_mapping(_as_mapping(route).get("mechanism")).get("mechanism")
        == _BUILD_MECHANISM
        for route in (routes if isinstance(routes, list) else [])
    )


def _is_installed_service_manager_unit(value: Mapping[str, Any]) -> bool:
    """Return whether content places units or drop-ins in a systemd load path."""

    content_type = value.get("type")
    location_field = "destination" if content_type == "directory" else "path"
    location = value.get(location_field)
    if content_type not in {"file", "directory"} or not isinstance(location, str):
        return False
    path = pathlib.PurePosixPath(location)
    for directory in _SYSTEMD_UNIT_DIRECTORIES:
        if path != directory and not path.is_relative_to(directory):
            continue
        if content_type == "directory":
            return True
        relative = path.relative_to(directory)
        for part in relative.parts:
            candidate = pathlib.PurePosixPath(part)
            if candidate.suffix in _SYSTEMD_UNIT_SUFFIXES:
                return True
            if candidate.suffix == ".d" and pathlib.PurePosixPath(
                candidate.stem
            ).suffix in _SYSTEMD_UNIT_SUFFIXES:
                return True
    return False


def validate_shuffle_orborus_contract(sdl: Mapping[str, Any]) -> list[str]:
    """Validate Orborus's portable authority without prescribing realization."""

    errors: list[str] = []
    runtime = _as_mapping(
        _as_mapping(_as_mapping(sdl.get("nodes")).get("shuffle-orborus")).get(
            "runtime"
        )
    )
    interfaces = runtime.get("local_control_interfaces")
    interface_values = interfaces if isinstance(interfaces, list) else []
    interface = _as_mapping(
        interface_values[0] if len(interface_values) == 1 else None
    )
    if (
        len(interface_values) != 1
        or interface.get("control_interface_id") != "docker-sock"
        or interface.get("path") != "/var/run/docker.sock"
        or interface.get("kind") != "unix_socket"
        or interface.get("access") != "read_write"
    ):
        _shuffle_orborus_error(
            errors,
            "interface-invalid",
            "/nodes/shuffle-orborus/runtime/local_control_interfaces",
        )
    for field in ("bind_source", "bind_source_sensitivity", "protocol"):
        if field in interface:
            _shuffle_orborus_error(
                errors,
                "backend-field",
                "/nodes/shuffle-orborus/runtime/"
                f"local_control_interfaces/0/{field}",
            )

    authorities = runtime.get("orchestration_authorities")
    authority_values = authorities if isinstance(authorities, list) else []
    authority = _as_mapping(
        authority_values[0] if len(authority_values) == 1 else None
    )
    scope = _as_mapping(authority.get("scope"))
    if (
        len(authority_values) != 1
        or authority.get("orchestration_authority_id") != "shuffle-orborus"
        or authority.get("control_interface_ref") != "docker-sock"
        or authority.get("engine") != "docker"
        or authority.get("privilege_class") != "host_root_equivalent"
        or scope.get("environment_name") != "Shuffle"
    ):
        _shuffle_orborus_error(
            errors,
            "authority-invalid",
            "/nodes/shuffle-orborus/runtime/orchestration_authorities",
        )
    for field in ("engine_api_version", "realized_children"):
        if field in authority:
            _shuffle_orborus_error(
                errors,
                "backend-field",
                "/nodes/shuffle-orborus/runtime/"
                f"orchestration_authorities/0/{field}",
            )

    templates = authority.get("spawn_templates")
    template_values = templates if isinstance(templates, list) else []
    actual_templates = {
        template.get("template_id"): {
            "image_ref": template.get("image_ref"),
            "purpose": template.get("purpose"),
        }
        for value in template_values
        if (template := _as_mapping(value)).get("template_id")
    }
    if (
        len(template_values) != len(_SHUFFLE_ORBORUS_TEMPLATES)
        or actual_templates != _SHUFFLE_ORBORUS_TEMPLATES
    ):
        _shuffle_orborus_error(
            errors,
            "spawn-template-invalid",
            "/nodes/shuffle-orborus/runtime/orchestration_authorities/0/"
            "spawn_templates",
        )

    lifecycle = _as_mapping(authority.get("lifecycle_policy"))
    if (
        lifecycle.get("execution_timeout") != "600"
        or lifecycle.get("cleanup") != "false"
    ):
        _shuffle_orborus_error(
            errors,
            "lifecycle-invalid",
            "/nodes/shuffle-orborus/runtime/orchestration_authorities/0/"
            "lifecycle_policy",
        )
    return errors


def validate_realization_method_contract(sdl: Mapping[str, Any]) -> list[str]:
    """Reject structurally explicit realization choices from TechVault."""

    errors: list[str] = []

    realization = _as_mapping(sdl.get("realization"))
    if realization.get("default") != "open":
        errors.append("realization.default-not-open: /realization/default")
    constraints = realization.get("constraints")
    for index, _constraint in enumerate(
        constraints if isinstance(constraints, list) else []
    ):
        errors.append(f"realization.constraint: /realization/constraints/{index}")

    nodes = _as_mapping(sdl.get("nodes"))
    for node_id, value in nodes.items():
        node = _as_mapping(value)
        base = f"/nodes/{node_id}"

        source = _as_mapping(node.get("source"))
        if source:
            requirement = _as_mapping(source.get("artifact_requirement"))
            if _is_build_recipe(requirement):
                errors.append(
                    f"realization.build-recipe: {base}/source/artifact_requirement"
                )
            else:
                errors.append(f"realization.node-source: {base}/source")

        runtime = _as_mapping(node.get("runtime"))
        portable_exceptions = _PORTABLE_RUNTIME_FIELD_EXCEPTIONS.get(
            str(node_id), frozenset()
        )
        for field, code in _FORBIDDEN_RUNTIME_FIELDS.items():
            if field in runtime and field not in portable_exceptions:
                errors.append(f"realization.{code}: {base}/runtime/{field}")

        network = _as_mapping(runtime.get("network"))
        if "published_ports" in network:
            errors.append(
                f"realization.host-publication: {base}/runtime/network/published_ports"
            )

        listeners = runtime.get("service_listeners")
        for index, listener_value in enumerate(
            listeners if isinstance(listeners, list) else []
        ):
            listener = _as_mapping(listener_value)
            if "published_port_refs" in listener:
                errors.append(
                    "realization.listener-publication-ref: "
                    f"{base}/runtime/service_listeners/{index}/published_port_refs"
                )

        sensors = runtime.get("network_sensors")
        for index, sensor_value in enumerate(
            sensors if isinstance(sensors, list) else []
        ):
            sensor = _as_mapping(sensor_value)
            for field, code in _FORBIDDEN_SENSOR_FIELDS.items():
                if field in sensor:
                    errors.append(
                        f"realization.{code}: "
                        f"{base}/runtime/network_sensors/{index}/{field}"
                    )

    for feature_id, value in _as_mapping(sdl.get("features")).items():
        source = _as_mapping(_as_mapping(value).get("source"))
        if not source:
            continue
        requirement = _as_mapping(source.get("artifact_requirement"))
        if _is_build_recipe(requirement):
            errors.append(
                "realization.build-recipe: "
                f"/features/{feature_id}/source/artifact_requirement"
            )
        else:
            errors.append(f"realization.feature-source: /features/{feature_id}/source")

    for content_id, value in _as_mapping(sdl.get("content")).items():
        content = _as_mapping(value)
        if _is_installed_service_manager_unit(content):
            errors.append(
                f"realization.service-unit-content: /content/{content_id}"
            )
        source = _as_mapping(content.get("source"))
        requirement = _as_mapping(source.get("artifact_requirement"))
        if _is_build_recipe(requirement):
            errors.append(
                "realization.build-recipe: "
                f"/content/{content_id}/source/artifact_requirement"
            )
    return errors


def validate() -> list[str]:
    root = pathlib.Path(__file__).resolve().parents[1]
    result = validate_pack(root)
    errors = list(result.errors)
    if not errors:
        try:
            validate_pack_content_manifest(root)
        except ValueError as exc:
            errors.append(str(exc))
    if not errors:
        sdl_path = next((root / "sdl").glob("*.sdl.yaml"))
        sdl = yaml.safe_load(sdl_path.read_text(encoding="utf-8"))
        errors.extend(validate_realization_method_contract(sdl))
        errors.extend(validate_shuffle_orborus_contract(sdl))
        errors.extend(validate_misp_contract(sdl))
        errors.extend(validate_suricata_contract(root, sdl))
        errors.extend(validate_cortex_contract(root, sdl))
        errors.extend(validate_wazuh_agent_contract(sdl))
    return errors


if __name__ == "__main__":
    if sys.argv[1:] != ["validate"]:
        raise SystemExit("usage: validate_techvault.py validate")
    failures = validate()
    for failure in failures:
        print(failure)
    raise SystemExit(1 if failures else 0)
