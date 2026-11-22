#!/usr/bin/env python3
"""Forest B0 // read-only Ollama inventory. No Tree runtime or UI ownership.

Explicit command invocation is the only network trigger. This helper never
loads a model, sends a prompt, reads personal data or operates Hospital/PX.
"""
from __future__ import annotations

import argparse
import http.client
import json
import re
import socket
import sys
from urllib.parse import urlsplit

SCHEMA_VERSION = 1
MAX_BODY_BYTES = 1024 * 1024
MAX_MODELS = 256
TIMEOUT_SECONDS = 2.5
DEFAULT_ENDPOINT = "http://127.0.0.1:11434"
VALID_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}$")


class InventoryFailure(Exception):
    """Static error reason. Do not expose OS/network exceptions to callers."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _target(endpoint: str) -> tuple[str, int]:
    """Pin all requests to literal loopback, never follow URL redirects."""
    if not isinstance(endpoint, str):
        raise InventoryFailure("INVALID_ENDPOINT")
    try:
        url = urlsplit(endpoint)
        host = url.hostname
        port = url.port if url.port is not None else 11434
    except ValueError as exc:
        raise InventoryFailure("INVALID_ENDPOINT") from exc
    if (url.scheme != "http" or not url.netloc
            or url.username is not None or url.password is not None
            or url.path not in ("", "/") or url.query or url.fragment
            or not 1 <= port <= 65535):
        raise InventoryFailure("INVALID_ENDPOINT")
    if host in ("localhost", "127.0.0.1"):
        return ("127.0.0.1", port)
    if host == "::1":
        return ("::1", port)
    raise InventoryFailure("NON_LOOPBACK_ENDPOINT")


def _read_json(host: str, port: int) -> object:
    connection = http.client.HTTPConnection(host, port, timeout=TIMEOUT_SECONDS)
    try:
        connection.request("GET", "/api/tags", headers={"Accept": "application/json"})
        response = connection.getresponse()
        if response.status != 200:
            raise InventoryFailure("OLLAMA_HTTP_ERROR")
        content_type = (response.getheader("Content-Type") or "").lower()
        if content_type.split(";", 1)[0].strip() != "application/json":
            raise InventoryFailure("OLLAMA_CONTENT_TYPE")
        body = response.read(MAX_BODY_BYTES + 1)
        if len(body) > MAX_BODY_BYTES:
            raise InventoryFailure("OLLAMA_RESPONSE_TOO_LARGE")
    except (socket.timeout, TimeoutError) as exc:
        raise InventoryFailure("OLLAMA_TIMEOUT") from exc
    except (OSError, http.client.HTTPException) as exc:
        raise InventoryFailure("OLLAMA_UNAVAILABLE") from exc
    finally:
        connection.close()
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise InventoryFailure("OLLAMA_INVALID_JSON") from exc


def _models(payload: object) -> list[dict[str, object]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("models"), list):
        raise InventoryFailure("OLLAMA_INVALID_SCHEMA")
    raw_models = payload["models"]
    if len(raw_models) > MAX_MODELS:
        raise InventoryFailure("OLLAMA_MODEL_LIMIT")
    models: list[dict[str, object]] = []
    seen: set[str] = set()
    for entry in raw_models:
        if not isinstance(entry, dict):
            raise InventoryFailure("OLLAMA_INVALID_SCHEMA")
        name = entry.get("name")
        size = entry.get("size")
        if (not isinstance(name, str) or not VALID_NAME.fullmatch(name)
                or isinstance(size, bool) or not isinstance(size, int)
                or size < 0 or size > 2**63 - 1 or name in seen):
            raise InventoryFailure("OLLAMA_INVALID_SCHEMA")
        seen.add(name)
        models.append({"name": name, "size_bytes": size})
    models.sort(key=lambda model: str(model["name"]))
    return models


def inventory(endpoint: str = DEFAULT_ENDPOINT) -> dict[str, object]:
    host, port = _target(endpoint)
    models = _models(_read_json(host, port))
    return {
        "schema_version": SCHEMA_VERSION,
        "provider": "ollama",
        "status": "REACHABLE",
        "models": models,
        "model_count": len(models),
        "capabilities": ["list_models"],
        "generation_enabled": False,
        "tools_enabled": False,
        "sessions_enabled": False,
    }


def unavailable(reason: str) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "provider": "ollama",
        "status": "UNAVAILABLE",
        "models": [],
        "model_count": 0,
        "capabilities": [],
        "generation_enabled": False,
        "tools_enabled": False,
        "sessions_enabled": False,
        "reason": reason,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Forest B0: read-only inventory of local Ollama models"
    )
    parser.add_argument("command", choices=["list-models"])
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT,
                        help="http://127.0.0.1:11434 (loopback only)")
    args = parser.parse_args(argv)
    try:
        output = inventory(args.endpoint)
        exit_code = 0
    except InventoryFailure as exc:
        output = unavailable(exc.reason)
        exit_code = 2
    print(json.dumps(output, separators=(",", ":"), ensure_ascii=True))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
