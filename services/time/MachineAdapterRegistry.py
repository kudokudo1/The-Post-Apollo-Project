"""MACHINE M2c: data-only extensible application adapter *schema registry*.

Registry entries describe PROPOSED identity shapes, not executable plugins,
installed applications, read permissions, or supported live recovery.
No filesystem discovery, dynamic loading, process spawning, IPC or mutations.
"""
from __future__ import annotations

import re

MAX_ADAPTERS = 64
MAX_APP_IDS = 48
MAX_ITEM_KINDS = 32
MAX_TARGET_HOSTS = 8

SLUG = re.compile(r"[a-z][a-z0-9_]*(?:[.-][a-z0-9_]+)*\Z")
HOSTS = frozenset(("linux_wayland", "linux_x11", "windows", "macos"))


class RegistryError(ValueError):
    pass


# Compatibility with M2b fixture records. These declarations make NO claim
# that a Brave or Kitty adapter is installed, enabled or authenticated.
LEGACY = (
    {"adapter_id": "brave", "family": "browser",
     "app_ids": ["brave-browser"], "item_kinds": ["browser_tab"],
     "target_hosts": ["linux_wayland"], "state": "schema_only"},
    {"adapter_id": "kitty", "family": "terminal",
     "app_ids": ["kitty"],
     "item_kinds": ["terminal_tab", "terminal_split"],
     "target_hosts": ["linux_wayland"], "state": "schema_only"},
)


def _slug(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 64 or not SLUG.fullmatch(value):
        raise RegistryError("INVALID REGISTRY IDENTIFIER")
    return value


def _app(value):
    if (not isinstance(value, str) or not 1 <= len(value) <= 128
            or any(ord(ch) < 32 or ord(ch) == 127 for ch in value)):
        raise RegistryError("INVALID APPLICATION IDENTIFIER")
    return value


def _values(data, *, limit, cleaner, nonempty=True):
    if (not isinstance(data, list) or len(data) > limit
            or (nonempty and not data)):
        raise RegistryError("INVALID REGISTRY ARRAY")
    out = [cleaner(item) for item in data]
    if len(set(out)) != len(out):
        raise RegistryError("DUPLICATE REGISTRY ARRAY VALUE")
    return tuple(out)


def validate_manifest(manifest):
    """Strict schema declaration; never loads adapter code or grants access."""
    if (not isinstance(manifest, dict) or set(manifest) != {
            "adapter_id", "family", "app_ids", "item_kinds",
            "target_hosts", "state"}):
        raise RegistryError("INVALID ADAPTER DECLARATION")
    if manifest["state"] != "schema_only":
        raise RegistryError("ADAPTER IS NOT A LIVE CAPABILITY")
    adapter_id = _slug(manifest["adapter_id"])
    if adapter_id == "none":
        raise RegistryError("NONE IS FALLBACK ONLY")
    family = _slug(manifest["family"])
    apps = _values(manifest["app_ids"], limit=MAX_APP_IDS, cleaner=_app)
    kinds = _values(manifest["item_kinds"], limit=MAX_ITEM_KINDS,
                    cleaner=_slug, nonempty=False)
    hosts = _values(manifest["target_hosts"], limit=MAX_TARGET_HOSTS,
                    cleaner=_slug)
    if not set(hosts).issubset(HOSTS):
        raise RegistryError("UNKNOWN PLATFORM TARGET")
    return {
        "adapter_id": adapter_id, "family": family,
        "app_ids": apps, "item_kinds": kinds,
        "target_hosts": hosts, "state": "schema_only",
    }


def build_registry(additional_manifests=()):
    """Return validated data declarations; no code loading or autodetection.

    Callers must explicitly supply application-specific declarations. A
    registered shape never means the adapter exists in the running system.
    """
    if not isinstance(additional_manifests, (tuple, list)):
        raise RegistryError("INVALID ADAPTER CATALOG")
    if len(additional_manifests) + len(LEGACY) > MAX_ADAPTERS:
        raise RegistryError("TOO MANY ADAPTER DECLARATIONS")
    result = {}
    for raw in (*LEGACY, *additional_manifests):
        descriptor = validate_manifest(raw)
        key = descriptor["adapter_id"]
        if key in result:
            raise RegistryError("DUPLICATE ADAPTER DECLARATION")
        result[key] = descriptor
    return result


def find_declared_adapter(registry, adapter_id, app_id):
    """Fail closed for unknown adapter or mismatched app ID.

    'none' is a valid non-identifying fallback for any well-formed app_id.
    """
    _app(app_id)
    if adapter_id == "none":
        return {"adapter_id": "none", "family": "generic",
                "item_kinds": (), "state": "schema_only"}
    if not isinstance(adapter_id, str):
        raise RegistryError("INVALID ADAPTER IDENTIFIER")
    descriptor = registry.get(adapter_id)
    if descriptor is None or app_id not in descriptor["app_ids"]:
        raise RegistryError("UNKNOWN OR WRONG APPLICATION ADAPTER")
    return descriptor


def list_schema_capabilities(additional_manifests=()):
    """Safe descriptive catalog only. Never advertise tested live support."""
    registry = build_registry(additional_manifests)
    return {
        "kind": "machine-adapter-schema-catalog",
        "read_only": True, "executable": False,
        "installed_adapter_count": 0,
        "active_runtime_adapters": [],
        "live_capture_supported": False,
        "live_reopen_supported": False,
        "descriptors": [
            {"adapter_id": a["adapter_id"], "family": a["family"],
             "target_hosts": list(a["target_hosts"]),
             "item_kinds": list(a["item_kinds"]),
             "state": "schema_only"}
            for a in registry.values()
        ],
    }
