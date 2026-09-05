#!/usr/bin/env python3
"""Prove TechVault Cortex enrichment with the exact declared native images."""

from __future__ import annotations

import base64
import contextlib
import json
import pathlib
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid

import yaml


ROOT = pathlib.Path(__file__).resolve().parents[1]
PACK = ROOT / "packs" / "techvault"
SDL_PATH = PACK / "sdl" / "techvault.sdl.yaml"
CONTENT = PACK / "assets" / "content"
ATTACKER_IP = "172.20.1.30"
ANALYZER_DEFINITION_ID = "TechVaultScenarioContext_1_0"


class VerificationError(RuntimeError):
    """A bounded native verification failure."""


def _image(sdl: dict, node: str) -> str:
    source = sdl["nodes"][node]["source"]
    return f'{source["name"]}@{source["version"]}'


def _environment(sdl: dict, node: str) -> dict[str, str]:
    return {
        item["name"]: str(item.get("value", ""))
        for item in sdl["nodes"][node]["runtime"].get("environment", [])
    }


def _free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def _run(compose: pathlib.Path, project: str, *args: str, timeout: int = 900) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["docker", "compose", "-p", project, "-f", str(compose), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout).strip().splitlines()
        raise VerificationError(
            f'docker compose {" ".join(args)} failed: '
            + (detail[-1] if detail else f"exit {result.returncode}")
        )
    return result


def _request(
    url: str,
    *,
    key: str | None = None,
    basic: tuple[str, str] | None = None,
    method: str = "GET",
    payload: object | None = None,
    timeout: int = 15,
) -> object | None:
    headers = {"Accept": "application/json"}
    data = None
    if key:
        headers["Authorization"] = f"Bearer {key}"
    elif basic:
        credential = base64.b64encode(f"{basic[0]}:{basic[1]}".encode()).decode()
        headers["Authorization"] = f"Basic {credential}"
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read()
    except urllib.error.HTTPError as error:
        raise VerificationError(f"native API request returned status {error.code}") from error
    except OSError as error:
        raise VerificationError("native API request failed") from error
    return json.loads(body) if body else None


def _wait_json(url: str, *, timeout: int) -> object:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            value = _request(url)
            if value is not None:
                return value
        except VerificationError:
            pass
        time.sleep(2)
    raise VerificationError("native service did not become ready before the deadline")


def _cortex_connector_is_ok(value: object, *, cortex_context: bool = False) -> bool:
    if isinstance(value, dict):
        name = str(value.get("name", value.get("service", ""))).lower()
        status = str(value.get("status", "")).upper()
        local_context = cortex_context or "cortex" in name
        if local_context and status == "OK":
            return True
        return any(
            _cortex_connector_is_ok(
                item,
                cortex_context=local_context or "cortex" in str(key).lower(),
            )
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(
            _cortex_connector_is_ok(item, cortex_context=cortex_context)
            for item in value
        )
    return False


def _wait_cortex_connector_ok(
    url: str, *, basic: tuple[str, str], timeout: int, requester=_request
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            status = requester(url, basic=basic)
            if _cortex_connector_is_ok(status):
                return
        except VerificationError:
            pass
        time.sleep(3)
    raise VerificationError("TheHive Cortex connector is not OK")


def _verify_analyzer_execution(requester, cortex_url: str, connector_key: str) -> None:
    analyzers = requester(cortex_url + "/api/analyzer", key=connector_key)
    if not isinstance(analyzers, list):
        raise VerificationError("Cortex returned an invalid analyzer inventory")
    selected = [
        item
        for item in analyzers
        if isinstance(item, dict)
        and item.get("analyzerDefinitionId") == ANALYZER_DEFINITION_ID
    ]
    if len(selected) != 1 or not selected[0].get("id"):
        raise VerificationError("exact TechVault analyzer is not enabled")
    job = requester(
        cortex_url + f'/api/analyzer/{selected[0]["id"]}/run',
        key=connector_key,
        method="POST",
        payload={"data": ATTACKER_IP, "dataType": "ip", "tlp": 2, "pap": 2},
    )
    if not isinstance(job, dict) or not job.get("id"):
        raise VerificationError("Cortex did not create an analyzer job")
    report = requester(
        cortex_url + f'/api/job/{job["id"]}/waitreport?atMost=2minute',
        key=connector_key,
    )
    if not isinstance(report, dict) or report.get("status") != "Success":
        status = report.get("status") if isinstance(report, dict) else "invalid"
        raise VerificationError(
            f"TechVault analyzer job did not succeed (status {status})"
        )
    full = report.get("report", {}).get("full", {})
    if isinstance(full, str):
        full = json.loads(full)
    if not isinstance(full, dict) or full.get("scenario_role") != "attacker":
        raise VerificationError("TechVault analyzer report lacks attacker context")


def verify() -> dict[str, object]:
    if subprocess.run(
        ["docker", "info"], capture_output=True, timeout=20, check=False
    ).returncode:
        raise VerificationError("Docker is unavailable")

    sdl = yaml.safe_load(SDL_PATH.read_text(encoding="utf-8"))
    cortex_port, thehive_port = _free_port(), _free_port()
    initializer_environment = _environment(sdl, "cortex-initializer")
    admin_key = secrets.token_urlsafe(32)
    connector_key = secrets.token_urlsafe(32)
    initializer_environment.update(
        CORTEX_ADMIN_KEY=admin_key,
        CORTEX_CONNECTOR_KEY=connector_key,
    )

    project = "techvault-cortex-" + uuid.uuid4().hex[:10]
    with tempfile.TemporaryDirectory(prefix="techvault-cortex-") as directory:
        temporary = pathlib.Path(directory)
        config = temporary / "application.conf"
        config.write_text(sdl["content"]["cortex-app-config"]["text"], encoding="utf-8")
        compose = temporary / "compose.yaml"
        document = {
            "services": {
                "thehive-es": {
                    "image": _image(sdl, "thehive-es"),
                    "environment": {
                        "discovery.type": "single-node",
                        "xpack.security.enabled": "false",
                        "cluster.routing.allocation.disk.threshold_enabled": "false",
                        "ES_JAVA_OPTS": "-Xms512m -Xmx512m",
                    },
                    "healthcheck": {
                        "test": ["CMD-SHELL", "curl -sf http://localhost:9200 >/dev/null"],
                        "interval": "5s",
                        "timeout": "5s",
                        "retries": 60,
                    },
                    "volumes": ["es-data:/usr/share/elasticsearch/data"],
                },
                "cortex": {
                    "image": _image(sdl, "cortex"),
                    "environment": _environment(sdl, "cortex"),
                    "ports": [f"127.0.0.1:{cortex_port}:9001"],
                    "volumes": [
                        "cortex-jobs:/opt/cortex/jobs",
                        f"{config}:/etc/cortex/application.conf:ro",
                        f"{CONTENT / 'cortex-techvault-analyzer.json'}:/opt/techvault/cortex-analyzers/TechVaultScenarioContext/analyzer.json:ro",
                        f"{CONTENT / 'cortex-techvault-analyzer.py'}:/opt/techvault/cortex-analyzers/TechVaultScenarioContext/techvault_scenario_context.py:ro",
                    ],
                    "healthcheck": {
                        "test": ["CMD-SHELL", "curl -sf http://localhost:9001/api/status >/dev/null"],
                        "interval": "5s",
                        "timeout": "5s",
                        "retries": 60,
                        "start_period": "20s",
                    },
                    "depends_on": {"thehive-es": {"condition": "service_healthy"}},
                },
                "cortex-initializer": {
                    "image": _image(sdl, "cortex-initializer"),
                    "entrypoint": ["python3", "/opt/techvault/cortex-initializer.py"],
                    "environment": initializer_environment,
                    "volumes": [
                        f"{CONTENT / 'cortex-initializer.py'}:/opt/techvault/cortex-initializer.py:ro"
                    ],
                    "depends_on": {"cortex": {"condition": "service_healthy"}},
                },
                "thehive-cassandra": {
                    "image": _image(sdl, "thehive-cassandra"),
                    "environment": {
                        "CASSANDRA_CLUSTER_NAME": "thehive",
                        "MAX_HEAP_SIZE": "512M",
                        "HEAP_NEWSIZE": "128M",
                    },
                    "healthcheck": {
                        "test": ["CMD-SHELL", "cqlsh -e 'describe cluster' >/dev/null"],
                        "interval": "10s",
                        "timeout": "10s",
                        "retries": 60,
                        "start_period": "30s",
                    },
                    "volumes": ["cassandra-data:/var/lib/cassandra"],
                },
                "thehive": {
                    "image": _image(sdl, "thehive"),
                    "ports": [f"127.0.0.1:{thehive_port}:9000"],
                    "environment": {
                        "JVM_OPTS": "-Xms512m -Xmx512m",
                        "TH_CORTEX_KEYS": connector_key,
                    },
                    "command": sdl["nodes"]["thehive"]["runtime"]["container"]["command"],
                    "depends_on": {
                        "thehive-cassandra": {"condition": "service_healthy"},
                        "thehive-es": {"condition": "service_healthy"},
                        "cortex-initializer": {"condition": "service_completed_successfully"},
                    },
                    "volumes": [
                        "thehive-data:/opt/thp/thehive/data",
                        "thehive-index:/opt/thp/thehive/index",
                    ],
                },
            },
            "volumes": {
                "es-data": {},
                "cortex-jobs": {},
                "cassandra-data": {},
                "thehive-data": {},
                "thehive-index": {},
            },
        }
        compose.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")

        try:
            _run(compose, project, "up", "-d", "--wait", "thehive-es")
            _run(compose, project, "up", "-d", "--wait", "cortex")
            _run(compose, project, "run", "--rm", "--no-deps", "cortex-initializer")
            cortex_url = f"http://127.0.0.1:{cortex_port}"
            _verify_analyzer_execution(_request, cortex_url, connector_key)

            _run(compose, project, "up", "-d", "thehive")
            _wait_cortex_connector_ok(
                f"http://127.0.0.1:{thehive_port}/api/v1/status",
                basic=("admin@thehive.local", "secret"),
                timeout=600,
            )
            return {
                "analyzer_definition_id": ANALYZER_DEFINITION_ID,
                "observable": ATTACKER_IP,
                "scenario_role": "attacker",
                "job_status": "Success",
                "thehive_cortex_status": "OK",
                "admin_and_connector_keys_distinct": admin_key != connector_key,
            }
        finally:
            with contextlib.suppress(Exception):
                _run(compose, project, "down", "--volumes", "--remove-orphans", timeout=180)


def main() -> int:
    try:
        result = verify()
    except (VerificationError, subprocess.TimeoutExpired, json.JSONDecodeError) as error:
        print(f"TechVault Cortex native verification failed: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
