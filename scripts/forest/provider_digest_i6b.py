#!/usr/bin/env python3
"""I6b: selected Ollama digest/residency observation, never process attribution."""
from __future__ import annotations

import argparse
import http.client
import json
import re
import sys

import ollama_inventory as inventory
import performance_snapshot_p0 as p0

SCHEMA = "post-apollo.forest.provider-digest.i6b"
_DIGEST = re.compile(r"(?:sha256:)?([0-9a-f]{64})\Z", re.ASCII)


class DigestRefusal(ValueError):
    pass


def _digest(value):
    match = _DIGEST.fullmatch(value) if type(value) is str else None
    if not match:
        raise DigestRefusal("INVALID_PROVIDER_DIGEST")
    return "sha256:" + match.group(1)


def _tags(host, port):
    # B0's public inventory deliberately discards digests. Use the same
    # fixed GET, bounds and literal-loopback target with P0 strict JSON.
    connection = http.client.HTTPConnection(host, port, timeout=p0.TIMEOUT_SECONDS)
    try:
        connection.request("GET", "/api/tags", headers={"Accept": "application/json"})
        response = connection.getresponse()
        if response.status != 200:
            raise DigestRefusal("TAGS_HTTP_ERROR")
        media = (response.getheader("Content-Type") or "").split(";", 1)[0]
        if media.strip().lower() != "application/json":
            raise DigestRefusal("TAGS_CONTENT_TYPE")
        body = response.read(p0.MAX_BODY_BYTES + 1)
        if len(body) > p0.MAX_BODY_BYTES:
            raise DigestRefusal("TAGS_RESPONSE_TOO_LARGE")
        return json.loads(body.decode("utf-8"), object_pairs_hook=p0._unique_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (OSError, http.client.HTTPException, UnicodeError, RecursionError) as exc:
        raise DigestRefusal("TAGS_UNAVAILABLE") from None
    except ValueError as exc:
        if type(exc) is DigestRefusal:
            raise
        raise DigestRefusal("TAGS_INVALID_JSON") from None
    finally:
        connection.close()


def _selected(payload, name, *, resident):
    # Reuse established inventory/residency validation, but retain the
    # selected raw digest. Do not emit arbitrary provider fields.
    if resident:
        normalized = p0._residency(payload)
        record = next((x for x in normalized if x["model"] == name), None)
    else:
        normalized = inventory._models(payload)
        record = next((x for x in normalized if x["name"] == name), None)
    if record is None:
        return None
    raw = next(x for x in payload["models"]
               if x.get("name", x.get("model")) == name)
    if raw.get("model", name) != name:
        raise DigestRefusal("MODEL_ALIAS_MISMATCH")
    return (_digest(raw.get("digest")), record)


def _base():
    return {
        "schema": SCHEMA,
        "measurement_scope": "UNAUTHENTICATED_LOCAL_PROVIDER_CLAIMS",
        "runtime_release_authenticated": False,
        "provider_runtime_instance_verified": False,
        "model_artifact_verified": False,
        "model_binding_verified": False,
        "runner_mapping_verified": False,
        "memory_attributed_to_model": False,
        "accelerator_mapping_verified": False,
        "resource_requirements_established": False,
        "resource_reserved": False,
        "generation_requested": False,
        "model_load_requested": False,
        "permission_granted": False,
        "production_authority": False,
        "safe_actions": [],
    }


def observe(model, *, expected_digest=None, endpoint=inventory.DEFAULT_ENDPOINT):
    if type(model) is not str or not inventory.VALID_NAME.fullmatch(model):
        raise DigestRefusal("INVALID_MODEL")
    expected = _digest(expected_digest) if expected_digest is not None else None
    try:
        host, port = inventory._target(endpoint)
        first = _selected(_tags(host, port), model, resident=False)
        resident = _selected(p0._read_json(host, port, "/api/ps"), model, resident=True)
        second = _selected(_tags(host, port), model, resident=False)
    except (inventory.InventoryFailure, p0.ProbeFailure):
        raise DigestRefusal("LOCAL_PROVIDER_OBSERVATION_UNAVAILABLE") from None
    if first != second:
        raise DigestRefusal("SELECTED_INVENTORY_CHANGED")
    if resident is not None and first is None:
        raise DigestRefusal("RESIDENT_WITHOUT_INSTALLED_REFERENCE")
    if resident is not None and resident[0] != first[0]:
        raise DigestRefusal("RESIDENT_DIGEST_MISMATCH")
    if expected is not None and first is not None and first[0] != expected:
        raise DigestRefusal("EXPECTED_DIGEST_MISMATCH")
    return {
        **_base(),
        "status": "OBSERVED",
        "installed_reported": first is not None,
        "resident_reported": resident is not None,
        "installed_resident_digest_match_reported": (
            True if resident is not None else None),
        "expected_digest_match_reported": (
            True if expected is not None and first is not None else None),
        "resident_memory_bytes_reported": (
            resident[1]["size_bytes_reported"] if resident else None),
        "resident_vram_bytes_reported": (
            resident[1]["vram_bytes_reported"] if resident else None),
        "context_length_reported": (
            resident[1]["context_length_reported"] if resident else None),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="I6b: read-only selected model digest comparison")
    parser.add_argument("command", choices=("observe",))
    parser.add_argument("--model", required=True)
    parser.add_argument("--expected-digest")
    parser.add_argument("--endpoint", default=inventory.DEFAULT_ENDPOINT)
    args = parser.parse_args(argv)
    try:
        data = observe(args.model, expected_digest=args.expected_digest,
                       endpoint=args.endpoint)
        code = 0
    except DigestRefusal as exc:
        data, code = {**_base(), "status": "UNAVAILABLE", "reason": str(exc)}, 2
    except KeyboardInterrupt:
        data, code = {**_base(), "status": "UNAVAILABLE", "reason": "CANCELLED"}, 2
    print(json.dumps(data, separators=(",", ":"), ensure_ascii=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
