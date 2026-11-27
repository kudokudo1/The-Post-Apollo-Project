"""Offline, read-only classification of exact pinned public manifest bytes.

No CLI, network adapter, acquisition, file I/O or policy change. Output is
bounded fixed categories and aggregate integers, not raw descriptor data.
"""
import json

import first_light_stage1 as stage

REQUIRED = frozenset(("mediaType", "digest", "size"))
OPTIONAL = frozenset(("from", "name"))
ROLES = {
    "application/vnd.docker.container.image.v1+json": "CONFIG",
    "application/vnd.ollama.image.model": "MODEL",
    "application/vnd.ollama.image.template": "TEMPLATE",
    "application/vnd.ollama.image.system": "SYSTEM",
    "application/vnd.ollama.image.params": "PARAMS",
    "application/vnd.ollama.image.license": "LICENSE",
    "application/vnd.ollama.image.messages": "MESSAGES",
    "application/vnd.ollama.image.adapter": "ADAPTER",
    "application/vnd.ollama.image.projector": "PROJECTOR",
}
REFUSALS = frozenset((
    "MANIFEST_SHAPE", "BLOB_DESCRIPTOR_TYPE", "BLOB_DESCRIPTOR_KEYS",
    "BLOB_MEDIA_TYPE", "BLOB_DIGEST_FORMAT", "BLOB_SIZE",
    "DUPLICATE_BLOB", "MODEL_BYTE_LIMIT",
))


def _reject_constant(_):
    raise stage.Hold("MANIFEST_JSON")


def _metadata_kind(entry, key):
    if key not in entry:
        return "ABSENT"
    value = entry[key]
    if type(value) is not str:
        return "NONSTRING"
    if not value:
        return "EMPTY_STRING"
    return "BOUNDED_STRING" if len(value) <= 512 else "LONG_STRING"


def classify(raw):
    """Classify only the unchanged pinned manifest; never accept a descriptor."""
    stage.require(type(raw) is bytes and 0 < len(raw) <= stage.MANIFEST_LIMIT
                  and stage.digest_bytes(raw) == stage.MANIFEST_SHA,
                  "MANIFEST_DIGEST")
    try:
        obj = json.loads(raw, object_pairs_hook=stage.unique_pairs,
                         parse_constant=_reject_constant)
    except stage.Hold as exc:
        if str(exc) == "DUPLICATE_JSON_KEY":
            raise stage.Hold("DUPLICATE_JSON_KEY") from None
        raise stage.Hold("MANIFEST_JSON") from None
    except (ValueError, RecursionError):
        raise stage.Hold("MANIFEST_JSON") from None
    try:
        stage.parse_manifest(raw)
        refusal = "NONE"
    except stage.Hold as exc:
        refusal = str(exc) if str(exc) in REFUSALS else "OTHER_REFUSAL"
    except (ValueError, RecursionError):
        refusal = "OTHER_REFUSAL"

    report = {"kind": "PINNED_MANIFEST_METADATA_ONLY", "raw_bytes": len(raw),
              "original_refusal": refusal, "descriptor_count": 0,
              "descriptors": [], "bounded_size_sum": None,
              "duplicate_valid_digest": False, "config_size_within_cap": False,
              "aggregate_within_cap": False}
    if (type(obj) is not dict or obj.get("schemaVersion") != 2
            or type(obj.get("layers")) is not list
            or not 1 <= len(obj["layers"]) <= 16):
        return report

    entries = [obj.get("config")] + obj["layers"]
    report["descriptor_count"] = len(entries)
    seen = set()
    sizes = []
    for i, entry in enumerate(entries):
        item = {"position": "CONFIG" if i == 0 else "LAYER", "role": "UNKNOWN",
                "object": type(entry) is dict}
        if type(entry) is dict:
            keys = set(entry)
            media = entry.get("mediaType")
            digest = entry.get("digest")
            size = entry.get("size")
            valid_digest = type(digest) is str and stage.DIGEST.fullmatch(digest) is not None
            valid_size = type(size) is int and 0 < size <= stage.MODEL_LIMIT
            item.update({
                "role": ROLES.get(media, "UNKNOWN") if type(media) is str else "INVALID_TYPE",
                "required_keys_present": REQUIRED <= keys,
                "unknown_key_count": len(keys - REQUIRED - OPTIONAL),
                "from_kind": _metadata_kind(entry, "from"),
                "name_kind": _metadata_kind(entry, "name"),
                "digest_format_valid": valid_digest,
                "size_kind": ("VALID" if valid_size else "NONINTEGER" if type(size) is not int
                              else "ZERO" if size == 0 else "NEGATIVE" if size < 0 else "OVER_CAP"),
            })
            if valid_digest:
                if digest in seen:
                    report["duplicate_valid_digest"] = True
                seen.add(digest)
            if valid_size:
                sizes.append(size)
            if i == 0:
                report["config_size_within_cap"] = valid_size and size <= stage.CHUNK
        report["descriptors"].append(item)
    if len(sizes) == len(entries):
        report["bounded_size_sum"] = sum(sizes)
        report["aggregate_within_cap"] = report["bounded_size_sum"] <= stage.MODEL_LIMIT
    return report
