"""Forest Heart I6c: offline legacy Ollama manifest-to-weight reference.

No IO, private-store discovery, model loading, process mapping or trust.
Caller-supplied bytes and expected digest are not authenticated evidence.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re

from performance_snapshot_p0 import _unique_pairs

SCHEMA = "post-apollo.forest.manifest-reference.i6c"
MAX_BYTES = 1024 * 1024
MAX_LAYERS = 128
MAX_SIZE = 2**63 - 1
MANIFEST = "application/vnd.docker.distribution.manifest.v2+json"
CONFIG = "application/vnd.docker.container.image.v1+json"
WEIGHT = "application/vnd.ollama.image.model"
_METADATA = frozenset("application/vnd.ollama.image." + kind for kind in
                      ("template", "system", "license", "params", "messages"))
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z", re.ASCII)
_EXPECTED = re.compile(r"(?:sha256:)?([0-9a-f]{64})\Z", re.ASCII)


class ManifestRefusal(ValueError):
    """Static refusal codes, no content, file paths or provider identifiers."""


@dataclass(frozen=True, slots=True)
class ManifestReference:
    manifest_digest: str
    weight_digest: str
    weight_size_bytes_declared: int
    layer_count: int


def _descriptor(item):
    if (type(item) is not dict or set(item) != {"mediaType", "digest", "size"}
            or type(item["mediaType"]) is not str
            or type(item["digest"]) is not str
            or not _DIGEST.fullmatch(item["digest"])
            or type(item["size"]) is not int
            or not 0 <= item["size"] <= MAX_SIZE):
        raise ManifestRefusal("INVALID_LAYER_DESCRIPTOR")
    return item["mediaType"], item["digest"], item["size"]


def inspect_manifest(raw, expected_digest):
    """Return a content-reference relationship, not installed artifact proof."""
    if type(raw) is not bytes or not 1 <= len(raw) <= MAX_BYTES:
        raise ManifestRefusal("INVALID_MANIFEST_BYTES")
    match = _EXPECTED.fullmatch(expected_digest) if type(expected_digest) is str else None
    if match is None:
        raise ManifestRefusal("INVALID_EXPECTED_DIGEST")
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    if digest != "sha256:" + match.group(1):
        raise ManifestRefusal("MANIFEST_DIGEST_MISMATCH")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (UnicodeError, ValueError, RecursionError):
        raise ManifestRefusal("INVALID_MANIFEST_JSON") from None
    # Deliberately narrow: no recursive lists, selected runner manifests,
    # tensors, draft/adapter/projector layers or other unmodelled layouts.
    if (type(value) is not dict
            or set(value) != {"schemaVersion", "mediaType", "config", "layers"}
            or type(value["schemaVersion"]) is not int
            or value["schemaVersion"] != 2
            or value["mediaType"] != MANIFEST
            or type(value["layers"]) is not list
            or not 1 <= len(value["layers"]) <= MAX_LAYERS):
        raise ManifestRefusal("UNSUPPORTED_MANIFEST_LAYOUT")
    kind, config_digest, config_size = _descriptor(value["config"])
    if kind != CONFIG or config_size == 0:
        raise ManifestRefusal("INVALID_CONFIG_REFERENCE")
    weights = []
    seen = {config_digest}
    for item in value["layers"]:
        kind, layer_digest, size = _descriptor(item)
        if layer_digest in seen:
            raise ManifestRefusal("AMBIGUOUS_LAYER_REFERENCE")
        seen.add(layer_digest)
        if kind == WEIGHT:
            if size == 0:
                raise ManifestRefusal("INVALID_WEIGHT_REFERENCE")
            weights.append((layer_digest, size))
        elif kind not in _METADATA:
            raise ManifestRefusal("UNSUPPORTED_LAYER_TYPE")
    if len(weights) != 1:
        raise ManifestRefusal("SINGLE_WEIGHT_REFERENCE_REQUIRED")
    weight_digest, size = weights[0]
    return ManifestReference(digest, weight_digest, size, len(value["layers"]))


def public_status(raw, expected_digest):
    """Recompute from bytes, never accept caller-constructed positive receipts."""
    base = {
        "schema": SCHEMA,
        "measurement_scope": "CALLER_SUPPLIED_OFFLINE_MANIFEST_BYTES",
        "source_authenticated": False,
        "installed_artifact_verified": False,
        "weight_bytes_verified": False,
        "provider_runtime_instance_verified": False,
        "runner_mapping_verified": False,
        "model_binding_verified": False,
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
    try:
        ref = inspect_manifest(raw, expected_digest)
    except ManifestRefusal as exc:
        return {**base, "status": "UNAVAILABLE", "reason": str(exc),
                "manifest_digest_matches_supplied_reference": False,
                "single_weight_reference_observed": False,
                "layer_count": None, "weight_size_bytes_declared": None}
    return {**base, "status": "REFERENCE_MATCH",
            "manifest_digest_matches_supplied_reference": True,
            "single_weight_reference_observed": True,
            "layer_count": ref.layer_count,
            "weight_size_bytes_declared": ref.weight_size_bytes_declared}
