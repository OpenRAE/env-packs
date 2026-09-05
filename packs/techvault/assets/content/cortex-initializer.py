#!/usr/bin/python3
"""Idempotently establish TechVault's bounded Cortex application state."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


class CortexError(RuntimeError):
    """A bounded initialization failure safe to report without response bodies."""


def _request(
    base_url: str,
    path: str,
    *,
    key: str | None = None,
    method: str = "GET",
    payload: object | None = None,
    accepted: tuple[int, ...] = (200,),
) -> object | None:
    headers = {"Accept": "application/json"}
    data = None
    if key:
        headers["Authorization"] = f"Bearer {key}"
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        base_url.rstrip("/") + path,
        data=data,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            status = response.status
            body = response.read()
    except urllib.error.HTTPError as error:
        status = error.code
        body = error.read(4096)
    except (OSError, urllib.error.URLError) as error:
        raise CortexError("Cortex API unavailable") from error
    if status not in accepted:
        detail = ""
        try:
            problem = json.loads(body)
            if isinstance(problem, dict):
                kind = str(problem.get("type", ""))[:80]
                detail = f" ({kind})" if kind else ""
        except (UnicodeDecodeError, json.JSONDecodeError):
            pass
        raise CortexError(
            f"Cortex API rejected {method} {path} with status {status}{detail}"
        )
    if not body:
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError as error:
        raise CortexError(f"Cortex API returned invalid JSON for {path}") from error


def _authenticated_user(base_url: str, key: str) -> dict[str, object] | None:
    try:
        user = _request(base_url, "/api/user/current", key=key)
    except CortexError as error:
        # A pristine Cortex 3.1.8 returns 404 because its synthetic `init`
        # principal is not a stored user; later invalid keys return 401.
        if "status 401" in str(error) or "status 404" in str(error):
            return None
        raise
    if not isinstance(user, dict):
        raise CortexError("Cortex current-user response has an invalid shape")
    return user


def _wait_ready(base_url: str, deadline_seconds: int) -> None:
    deadline = time.monotonic() + deadline_seconds
    while time.monotonic() < deadline:
        try:
            _request(base_url, "/api/status")
            return
        except CortexError:
            time.sleep(2)
    raise CortexError("Cortex API did not become ready before the deadline")


def _ensure_database(base_url: str, admin_key: str) -> None:
    try:
        _authenticated_user(base_url, admin_key)
        return
    except CortexError as error:
        if "status 520" not in str(error):
            raise
    _request(
        base_url,
        "/api/maintenance/migrate",
        method="POST",
        accepted=(204,),
    )
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            _authenticated_user(base_url, admin_key)
            return
        except CortexError as error:
            if "status 520" not in str(error):
                raise
            time.sleep(1)
    raise CortexError("Cortex database migration did not complete")


def _ensure_admin(base_url: str, admin_key: str, organization: str) -> None:
    if _authenticated_user(base_url, admin_key) is not None:
        return
    try:
        _request(
            base_url,
            "/api/organization",
            method="POST",
            payload={
                "name": organization,
                "description": "TechVault scenario organization",
            },
            accepted=(201,),
        )
    except CortexError as error:
        if "status 400" not in str(error) and "status 409" not in str(error):
            raise
    _request(
        base_url,
        "/api/user",
        method="POST",
        payload={
            "login": "techvault-admin@cortex.local",
            "name": "TechVault Cortex Initializer",
            "organization": organization,
            "roles": ["read", "analyze", "orgadmin"],
            "key": admin_key,
        },
        accepted=(201,),
    )
    if _authenticated_user(base_url, admin_key) is None:
        raise CortexError("Cortex initializer identity did not authenticate")


def _ensure_connector(
    base_url: str, admin_key: str, connector_key: str, organization: str
) -> None:
    expected_login = "thehive@cortex.local"
    user = _authenticated_user(base_url, connector_key)
    if user is None:
        encoded_login = urllib.parse.quote(expected_login, safe="")
        try:
            _request(base_url, f"/api/user/{encoded_login}", key=admin_key)
        except CortexError as error:
            if "status 404" not in str(error):
                raise
        else:
            raise CortexError("TheHive connector identity exists with another key")
        _request(
            base_url,
            "/api/user",
            key=admin_key,
            method="POST",
            payload={
                "login": expected_login,
                "name": "TechVault TheHive Connector",
                "organization": organization,
                "roles": ["read", "analyze"],
                "key": connector_key,
            },
            accepted=(201,),
        )
        user = _authenticated_user(base_url, connector_key)
    if user is None or user.get("_id") != expected_login:
        raise CortexError("TheHive connector identity did not authenticate")
    if sorted(user.get("roles", [])) != ["analyze", "read"]:
        raise CortexError("TheHive connector identity has unexpected roles")


def _ensure_analyzer(base_url: str, admin_key: str, definition_id: str) -> None:
    _request(
        base_url,
        "/api/analyzerdefinition/scan",
        key=admin_key,
        method="POST",
        accepted=(204,),
    )
    matches: list[dict[str, object]] = []
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline and not matches:
        definitions = _request(base_url, "/api/analyzerdefinition", key=admin_key)
        matches = [
            item
            for item in definitions or []
            if isinstance(item, dict) and item.get("id") == definition_id
        ] if isinstance(definitions, list) else []
        if not matches:
            time.sleep(1)
    if len(matches) != 1 or not isinstance(matches[0].get("name"), str):
        raise CortexError("Declared TechVault analyzer definition is unavailable")
    analyzers = _request(base_url, "/api/analyzer", key=admin_key)
    if not isinstance(analyzers, list):
        raise CortexError("Cortex analyzer inventory has an invalid shape")
    matching = [
        item
        for item in analyzers
        if isinstance(item, dict) and item.get("analyzerDefinitionId") == definition_id
    ]
    if not matching:
        _request(
            base_url,
            "/api/organization/analyzer/" + urllib.parse.quote(definition_id, safe=""),
            key=admin_key,
            method="POST",
            payload={"name": matches[0]["name"], "configuration": {}},
            accepted=(201,),
        )
        analyzers = _request(base_url, "/api/analyzer", key=admin_key)
        matching = [
            item
            for item in analyzers
            if isinstance(item, dict)
            and item.get("analyzerDefinitionId") == definition_id
        ]
    if len(matching) != 1:
        raise CortexError("Declared TechVault analyzer is not enabled exactly once")


def initialize(environment: dict[str, str]) -> None:
    required = (
        "CORTEX_URL",
        "CORTEX_ADMIN_KEY",
        "CORTEX_CONNECTOR_KEY",
        "CORTEX_ORGANIZATION",
        "CORTEX_ANALYZER_DEFINITION_ID",
    )
    missing = [name for name in required if not environment.get(name)]
    if missing:
        raise CortexError("Cortex initializer environment is incomplete")
    if environment["CORTEX_ADMIN_KEY"] == environment["CORTEX_CONNECTOR_KEY"]:
        raise CortexError("Cortex initializer and connector keys must differ")
    base_url = environment["CORTEX_URL"]
    _wait_ready(base_url, int(environment.get("CORTEX_READY_TIMEOUT", "300")))
    _ensure_database(base_url, environment["CORTEX_ADMIN_KEY"])
    _ensure_admin(
        base_url, environment["CORTEX_ADMIN_KEY"], environment["CORTEX_ORGANIZATION"]
    )
    _ensure_connector(
        base_url,
        environment["CORTEX_ADMIN_KEY"],
        environment["CORTEX_CONNECTOR_KEY"],
        environment["CORTEX_ORGANIZATION"],
    )
    _ensure_analyzer(
        base_url,
        environment["CORTEX_ADMIN_KEY"],
        environment["CORTEX_ANALYZER_DEFINITION_ID"],
    )


def main() -> int:
    try:
        initialize(dict(os.environ))
    except (CortexError, ValueError) as error:
        print(f"cortex-initializer: {error}", file=sys.stderr)
        return 1
    print("cortex-initializer: desired Cortex state is ready")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
