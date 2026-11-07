#!/usr/bin/env python3
"""C2m disposable D-Bus transport pilot, never an authenticated production host.

All execution is opt-in AND gated to a private test bus. This prototype proves
only D-Bus method transport/name ownership/disconnect, not privileged service
installation, a protected system bus, user consent, or API authorization.
Do not import this module into Quickshell or any credential broker.
"""
import asyncio
import json
import os
import re
import signal
import sys

from dbus_next import NameFlag, RequestNameReply
from dbus_next.aio import MessageBus
from dbus_next.service import ServiceInterface, method

NAME = "org.postapollo.ConnectionsStatusPilot"
PATH = "/org/postapollo/ConnectionsStatusPilot"
IFACE = "org.postapollo.ConnectionsStatusPilot1"
SCHEMA = "post-apollo.connections.c2m.privatebus-status.v1"
FLAG = "POST_APOLLO_C2M_DISPOSABLE_TEST_ONLY"
SERVICE_ARG = "--ci-private-serve"
CLIENT_ARG = "--ci-private-inspect"

def denied(reason):
    return {
        "status": reason, "state": "",
        "hostAuthenticated": False,
        "credentialPresent": False,
        "grantActive": False,
        "canApprove": False,
        "canUseApi": False,
    }

def _payload():
    # No real C2f requests, credentials, service identity or permission grants.
    return json.dumps({
        "schema": SCHEMA, "provider": "nasa-firms",
        "state": "IDLE", "readonly": True,
    }, separators=(",", ":"))

def _project(data, owner_uid, client_uid):
    # The bus can report a Unix UID; the UID is NOT application attestation.
    if (type(owner_uid) is not int or type(client_uid) is not int
            or type(data) is not str or len(data) > 768):
        return denied("RESPONSE_INVALID")
    try:
        obj = json.loads(data)
    except (ValueError, TypeError):
        return denied("RESPONSE_INVALID")
    if (type(obj) is not dict or set(obj) != {
            "schema", "provider", "state", "readonly"}
            or obj.get("schema") != SCHEMA
            or obj.get("provider") != "nasa-firms"
            or obj.get("state") != "IDLE"
            or obj.get("readonly") is not True):
        return denied("RESPONSE_INVALID")
    # Even when ownerUid != clientUid someday, that alone cannot grant access.
    value = denied("OBSERVED_UNVERIFIED")
    value["state"] = "IDLE"
    return value

class ReadOnlyPilot(ServiceInterface):
    def __init__(self):
        super().__init__(IFACE)

    @method()
    def GetStatus(self) -> 's':
        return _payload()

async def _serve(address):
    bus = await MessageBus(bus_address=address).connect()
    try:
        bus.export(PATH, ReadOnlyPilot())
        # Do not replace another owner's name and do not queue for takeover.
        status = await bus.request_name(NAME, flags=NameFlag.DO_NOT_QUEUE)
        if status != RequestNameReply.PRIMARY_OWNER:
            print("C2M_NAME_ALREADY_OWNED", file=sys.stderr)
            return 2
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGTERM, stop.set)
        loop.add_signal_handler(signal.SIGINT, stop.set)
        await stop.wait()
        return 0
    finally:
        bus.disconnect()

async def _inspect(address):
    bus = await MessageBus(bus_address=address).connect()
    try:
        dbus_xml = await bus.introspect("org.freedesktop.DBus", "/org/freedesktop/DBus")
        dbus_object = bus.get_proxy_object(
            "org.freedesktop.DBus", "/org/freedesktop/DBus", dbus_xml)
        daemon = dbus_object.get_interface("org.freedesktop.DBus")
        try:
            owner = await daemon.call_get_name_owner(NAME)
        except Exception:
            return denied("HOST_NOT_FOUND")
        # Name ownership is a moving pointer. Bind the read to the unique
        # connection returned by the daemon, not the replaceable public name.
        if not isinstance(owner, str) or not re.fullmatch(
                r":[0-9]+(?:\\.[0-9]+)+", owner):
            return denied("RESPONSE_INVALID")
        try:
            # The UID comes from the daemon, not the service's JSON payload.
            # A bus-reported UID remains insufficient for app authentication.
            owner_uid = await daemon.call_get_connection_unix_user(owner)
            xml = await bus.introspect(owner, PATH)
            obj = bus.get_proxy_object(owner, PATH, xml)
            reply = await obj.get_interface(IFACE).call_get_status()
        except Exception:
            return denied("RESPONSE_INVALID")
        # An owner replacement during the exchange invalidates this snapshot.
        # Missing owner also fails closed; neither situation grants anything.
        try:
            if await daemon.call_get_name_owner(NAME) != owner:
                return denied("HOST_OWNER_CHANGED")
        except Exception:
            return denied("HOST_OWNER_CHANGED")
        return _project(reply, owner_uid, os.geteuid())
    finally:
        bus.disconnect()

def main(argv=None, env=None):
    args = sys.argv[1:] if argv is None else argv
    supplied = os.environ if env is None else env
    address = supplied.get("DBUS_SESSION_BUS_ADDRESS", "")
    # No system bus, fallback to desktop session, or arbitrary transport flags.
    if (len(args) != 1 or args[0] not in {SERVICE_ARG, CLIENT_ARG}
            or supplied.get(FLAG) != "1"
            or not address.startswith("unix:")):
        print("C2M_REFUSED_NOT_DISPOSABLE_PRIVATE_BUS", file=sys.stderr)
        return 2
    try:
        if args[0] == SERVICE_ARG:
            return asyncio.run(_serve(address))
        result = asyncio.run(_inspect(address))
        print(json.dumps(result, separators=(",", ":"), sort_keys=True))
        return 0
    except Exception:
        print("C2M_PRIVATE_BUS_UNAVAILABLE", file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
