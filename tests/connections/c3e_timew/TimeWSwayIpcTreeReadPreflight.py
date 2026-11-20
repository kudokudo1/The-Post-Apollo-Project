#!/usr/bin/env python3
"""C3e / TimeW: strictly diagnostic Sway GET_TREE wire preflight.

The connected stream is a CI-controlled *fake* Sway peer. Correct IPC framing
and a plausible tree do not authenticate the compositor, active seat, Brave
window reference, or a Wayland surface. Never authorizes restoration.
"""
from __future__ import annotations

import json
import socket
import struct

MAGIC = b"i3-ipc"
GET_TREE = 4
HEADER = struct.Struct("<6sII")
MAX_REPLY = 262144
MAX_NODES = 2048
MAX_CHILDREN = 256
MAX_DEPTH = 48
BRAVE_APPS = frozenset(("brave-browser", "Brave-browser", "com.brave.Browser", "brave"))
DENIED = {
    "independentlyAuthenticatedCompositorPeer": False,
    "installedSignedCompositorReleaseVerified": False,
    "braveRendererAndWindowReferenceAuthenticated": False,
    "browserWindowToWaylandSurfaceBound": False,
    "sameSessionIndependentIdentityVerified": False,
    "independentC5TimeWConsentVerified": False,
    "canSignTimeWPairing": False,
    "canMoveWindow": False,
    "canRestoreBrave": False,
    "productionAuthority": False,
}


class Refused(ValueError):
    pass


def _deny(reason: str):
    raise Refused("C3E_TIMEW_SWAY_IPC_HOLD // " + reason)


def _unique_pairs(pairs):
    item = {}
    for key, value in pairs:
        if key in item:
            _deny("DUPLICATE_JSON_FIELD")
        item[key] = value
    return item


def _read_exact(connection: socket.socket, count: int) -> bytes:
    chunks = []
    while count:
        try:
            part = connection.recv(count)
        except (OSError, TimeoutError) as exc:
            raise Refused("C3E_TIMEW_SWAY_IPC_HOLD // INCOMPLETE_RESPONSE") from exc
        if not part:
            _deny("INCOMPLETE_RESPONSE")
        chunks.append(part)
        count -= len(part)
    return b"".join(chunks)


def _find_brave_leaves(root: dict) -> tuple[int, bool]:
    if type(root) is not dict or root.get("type") != "root":
        _deny("INVALID_TREE_ROOT")
    count = 0
    ids = set()
    brave_pids = []
    stack = [(root, 0, None, None)]
    while stack:
        node, depth, output, workspace = stack.pop()
        count += 1
        if count > MAX_NODES or depth > MAX_DEPTH or type(node) is not dict:
            _deny("UNBOUNDED_TREE")
        ident = node.get("id")
        if type(ident) is not int or ident <= 0 or ident in ids:
            _deny("DUPLICATE_OR_INVALID_CONTAINER_ID")
        ids.add(ident)
        kind = node.get("type")
        if type(kind) is not str:
            _deny("INVALID_NODE_TYPE")
        if kind in ("output", "workspace"):
            name = node.get("name")
            if type(name) is not str or not 0 < len(name) <= 128:
                _deny("INVALID_OUTPUT_OR_WORKSPACE")
            if kind == "output":
                output = name
            else:
                workspace = name
        app = node.get("app_id")
        if app is None and type(node.get("window_properties")) is dict:
            app = node["window_properties"].get("class")
        if kind == "con" and app in BRAVE_APPS:
            pid = node.get("pid")
            if (type(pid) is not int or pid <= 1
                    or not output or not workspace):
                _deny("UNATTRIBUTABLE_BRAVE_LEAF")
            brave_pids.append(pid)
        for field in ("nodes", "floating_nodes"):
            children = node.get(field, [])
            if type(children) is not list or len(children) > MAX_CHILDREN:
                _deny("INVALID_TREE_CHILDREN")
            for child in reversed(children):
                stack.append((child, depth + 1, output, workspace))
    return len(brave_pids), len(brave_pids) != len(set(brave_pids))


def inspect_fake_sway_ipc_ci_only(*, connection: socket.socket) -> dict:
    """Send only IPC_GET_TREE to an ALREADY CONNECTED disposable CI socket.

    No path lookup, socket connection, external command, compositor install,
    release enrollment, signer or privileged action is available here.
    The caller supplies the socket: even a valid response is not trusted.
    """
    if type(connection) is not socket.socket:
        _deny("CONNECTED_SOCKET_REQUIRED")
    try:
        if (connection.family != socket.AF_UNIX
                or connection.type & 15 != socket.SOCK_STREAM):
            _deny("UNSUPPORTED_SOCKET_TYPE")
        timeout = connection.gettimeout()
        if type(timeout) not in (int, float) or not 0 < timeout <= 2:
            _deny("BOUNDED_TIMEOUT_REQUIRED")
        connection.sendall(HEADER.pack(MAGIC, 0, GET_TREE))
        magic, length, msg_type = HEADER.unpack(_read_exact(connection, HEADER.size))
        if magic != MAGIC or msg_type != GET_TREE:
            _deny("WRONG_IPC_RESPONSE_TYPE")
        if not 1 <= length <= MAX_REPLY:
            _deny("UNBOUNDED_IPC_PAYLOAD")
        raw = _read_exact(connection, length)
    except (OSError, TimeoutError, struct.error) as exc:
        raise Refused("C3E_TIMEW_SWAY_IPC_HOLD // IPC_UNAVAILABLE") from exc
    try:
        tree = json.loads(raw.decode("utf-8"), object_pairs_hook=_unique_pairs)
    except (UnicodeError, ValueError, TypeError) as exc:
        raise Refused("C3E_TIMEW_SWAY_IPC_HOLD // INVALID_TREE_JSON") from exc
    leaves, ambiguous = _find_brave_leaves(tree)
    return {
        "schema": "postapollo.connections.c3e-timew-sway-ipc-observation.ci-v1",
        "status": "DISPOSABLE_SWAY_WIRE_OBSERVED_NO_WINDOW_IDENTITY",
        "onlyReadOnlyGetTreeSentInCi": True,
        "ciFakeCompositorTreeParsed": True,
        "braveLeafCountInCi": leaves,
        "braveLeavesSharePidInCi": ambiguous,
        "browserWindowReferenceInSwayIpc": None,
        **DENIED,
    }


def run_native_sway_window_identity_issuer(*_args, **_kwargs):
    _deny("NATIVE_BRAVE_WAYLAND_TRUST_NOT_IMPLEMENTED")
