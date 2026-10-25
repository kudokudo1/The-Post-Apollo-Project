"""MACHINE M2d: fixture-only host/application session correlation prototype.

Pure data transformation: no live compositor, application, browser, terminal
or editor access. Correlation tokens are synthetic exercise inputs, NOT
authentication. Future production transports must establish provenance
independently; the result never authorizes an action or claims session equality.
"""
from __future__ import annotations

import uuid
from MachineAdapterRegistry import RegistryError, build_registry, find_declared_adapter
from MachineSessionIdentityV2 import SidecarError, validate_sidecar

MAX_WINDOWS = 512
MAX_INNER_ITEMS = 4096


class CorrelationError(ValueError):
    pass


def _fields(value, names):
    if not isinstance(value, dict) or set(value) != set(names):
        raise CorrelationError("INVALID OBSERVATION SHAPE")


def _uuid(value):
    if not isinstance(value, str):
        raise CorrelationError("INVALID OBSERVATION IDENTIFIER")
    try:
        canonical = str(uuid.UUID(value))
    except (ValueError, AttributeError) as exc:
        raise CorrelationError("INVALID OBSERVATION IDENTIFIER") from exc
    if canonical != value:
        raise CorrelationError("NONCANONICAL OBSERVATION IDENTIFIER")
    return canonical


def _app(value):
    if (not isinstance(value, str) or not 1 <= len(value) <= 128 or
            any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise CorrelationError("INVALID APPLICATION NAME")
    return value


def _workspace(value):
    return _app(value)


def _header(frame, *, kind, collection):
    _fields(frame, ("schema_version", "kind", "scope_id", collection))
    if type(frame["schema_version"]) is not int or frame["schema_version"] != 1:
        raise CorrelationError("UNSUPPORTED OBSERVATION VERSION")
    if frame["kind"] != kind:
        raise CorrelationError("INVALID OBSERVATION KIND")
    scope = _uuid(frame["scope_id"])
    records = frame[collection]
    if not isinstance(records, list) or len(records) > MAX_WINDOWS:
        raise CorrelationError("INVALID OBSERVATION COUNT")
    return scope, records


def inspect_fixture_correlations(saved_sidecar, host_frame, app_frame,
                                 *, adapter_manifests=()):
    """Correlate synthetic app claims through one unique shared challenge.

    Correlation is *descriptive* and does not grant identity verification,
    runtime support, exact session equality, launches, window moves, retries
    or restores. Never match by window order, titles, PID or app ID alone.
    """
    try:
        saved = validate_sidecar(saved_sidecar,
                                 adapter_manifests=adapter_manifests)
        registry = build_registry(adapter_manifests)
    except (SidecarError, RegistryError) as exc:
        raise CorrelationError("INVALID SAVED SESSION PROPOSAL") from exc
    host_scope, hosts = _header(
        host_frame, kind="synthetic-host-window-observations",
        collection="windows")
    app_scope, reports = _header(
        app_frame, kind="synthetic-app-session-observations",
        collection="observations")
    if host_scope != app_scope:
        raise CorrelationError("MISMATCHED OBSERVATION SCOPE")

    host_by_challenge = {}
    host_ids = set()
    for host in hosts:
        _fields(host, ("observation_id", "app_id", "workspace",
                       "floating", "challenge"))
        observation_id = _uuid(host["observation_id"])
        challenge = _uuid(host["challenge"])
        app_id = _app(host["app_id"])
        workspace = _workspace(host["workspace"])
        if type(host["floating"]) is not bool:
            raise CorrelationError("INVALID HOST PLACEMENT")
        if observation_id in host_ids or challenge in host_by_challenge:
            raise CorrelationError("DUPLICATE HOST OBSERVATION")
        host_ids.add(observation_id)
        host_by_challenge[challenge] = {
            "observation_id": observation_id, "app_id": app_id,
            "workspace": workspace, "floating": host["floating"],
        }

    correlated = {}
    observed_challenges = set()
    for observation in reports:
        _fields(observation, ("challenge", "adapter_id", "app_id",
                              "namespace_key", "instance_key",
                              "inner_item_count"))
        challenge = _uuid(observation["challenge"])
        if challenge in observed_challenges:
            raise CorrelationError("DUPLICATE APP OBSERVATION")
        observed_challenges.add(challenge)
        host = host_by_challenge.get(challenge)
        if host is None:
            raise CorrelationError("ORPHANED APP CHALLENGE")
        app_id = _app(observation["app_id"])
        if app_id != host["app_id"]:
            raise CorrelationError("CROSS-APPLICATION CORRELATION")
        adapter = observation["adapter_id"]
        try:
            find_declared_adapter(registry, adapter, app_id)
        except RegistryError as exc:
            raise CorrelationError("UNREGISTERED OR WRONG APP ADAPTER") from exc
        if adapter == "none":
            raise CorrelationError("GENERIC FALLBACK CANNOT ASSERT IDENTITY")
        namespace_key = (None if observation["namespace_key"] is None
                         else _uuid(observation["namespace_key"]))
        instance_key = _uuid(observation["instance_key"])
        count = observation["inner_item_count"]
        if type(count) is not int or not 0 <= count <= MAX_INNER_ITEMS:
            raise CorrelationError("INVALID INNER ITEM COUNT")
        identity = (adapter, namespace_key, instance_key)
        if identity in correlated:
            raise CorrelationError("DUPLICATE SESSION REFERENCE")
        correlated[identity] = (host, count)

    details = []
    used = set()
    for row in saved["windows"]:
        ident = row["identity"]
        identity = (ident["adapter"], ident["namespace_key"],
                    ident["instance_key"])
        # Even an adapter's reported token is untrusted until a separate
        # trusted transport binds it to a specific live application.
        if ident["status"] != "reported" or ident["instance_key"] is None:
            state = "identity_not_available"
            observed_id = None
            placement = "not_checked"
            inner = "not_checked"
        elif identity not in correlated:
            state = "no_fixture_correlation"
            observed_id = None
            placement = "not_checked"
            inner = "not_checked"
        else:
            host, observed_count = correlated[identity]
            if host["app_id"] != row["app_id"]:
                raise CorrelationError("SAVED INSTANCE APP MISMATCH")
            used.add(identity)
            state = "correlated_in_synthetic_fixture"
            observed_id = host["observation_id"]
            placement = ("placement_fields_match"
                         if host["workspace"] == row["workspace"]
                         and host["floating"] == row["floating"]
                         else "placement_fields_differ")
            inner = ("item_counts_match_contents_unverified"
                     if observed_count == len(row["items"])
                     else "item_counts_differ")
        details.append({
            "saved_window_key": row["window_key"],
            "synthetic_host_observation_id": observed_id,
            "state": state,
            "placement": placement,
            "inner_items": inner,
            "live_identity_verified": False,
            "safe_actions": [],
        })

    return {
        "kind": "machine-synthetic-session-correlation",
        "scope_id": host_scope,
        "read_only": True,
        "executable": False,
        "input_provenance": "synthetic_untrusted",
        "live_identity_verified": False,
        "exact_session_match": False,
        "checkpoint_id": saved["checkpoint_id"],
        "saved_windows": len(saved["windows"]),
        "fixture_correlations": len(used),
        "unresolved_saved_windows": len(saved["windows"]) - len(used),
        "unlinked_host_windows": len(hosts) - len(reports),
        "extra_reported_instances": len(correlated) - len(used),
        "windows": details,
        "safe_actions": [],
        "capture_enabled": False,
        "launch_enabled": False,
        "restore_enabled": False,
    }
