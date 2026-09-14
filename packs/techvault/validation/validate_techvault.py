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
_FORBIDDEN_SENSOR_FIELDS = {
    "capture_interfaces": "packet-acquisition",
    "capture_mode": "packet-acquisition",
}


def _error(errors: list[str], code: str, detail: str) -> None:
    errors.append(f"suricata.{code}: {detail}")


def _cortex_error(errors: list[str], code: str, detail: str) -> None:
    errors.append(f"cortex.{code}: {detail}")


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
        for field, code in _FORBIDDEN_RUNTIME_FIELDS.items():
            if field in runtime:
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
        errors.extend(validate_suricata_contract(root, sdl))
        errors.extend(validate_cortex_contract(root, sdl))
    return errors


if __name__ == "__main__":
    if sys.argv[1:] != ["validate"]:
        raise SystemExit("usage: validate_techvault.py validate")
    failures = validate()
    for failure in failures:
        print(failure)
    raise SystemExit(1 if failures else 0)
