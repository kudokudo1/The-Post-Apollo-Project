#!/opt/postapollo-c2o-venv/bin/python3
"""C2o disposable Fedora-systemd fake status host. NOT a production binary.

Only copied into a short-lived CI container by the C2o Dockerfile.
Serves a single read-only D-Bus method. No secrets, network or authorizations.
"""
import asyncio
import json
import os
import signal
import sys
from dbus_next import BusType, NameFlag, RequestNameReply
from dbus_next.aio import MessageBus
from dbus_next.service import ServiceInterface, method

NAME = "org.postapollo.ConnectionsStatus1"
PATH = "/org/postapollo/ConnectionsStatus1"


class ReadOnlyStatus(ServiceInterface):
    def __init__(self):
        super().__init__(NAME)

    @method()
    def GetStatus(self) -> 's':
        return json.dumps({
            "schema": "post-apollo.connections.c2o.fedora-fixture.v1",
            "provider": "nasa-firms",
            "state": "IDLE",
            "readonly": True,
        }, separators=(",", ":"))


async def serve():
    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
    try:
        bus.export(PATH, ReadOnlyStatus())
        owned = await bus.request_name(NAME, flags=NameFlag.DO_NOT_QUEUE)
        if owned != RequestNameReply.PRIMARY_OWNER:
            print("C2O_REFUSED_NAME_NOT_OWNED", file=sys.stderr)
            return 2
        event = asyncio.Event()
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGTERM, event.set)
        loop.add_signal_handler(signal.SIGINT, event.set)
        print("C2O_CI_SERVICE_READY", flush=True)
        await event.wait()
        return 0
    finally:
        bus.disconnect()


def main():
    # Deliberately no alternative CLI, no auto-start or imported functions.
    if sys.argv[1:] != ["--read-only"]:
        print("C2O_REFUSED_NOT_READONLY", file=sys.stderr)
        return 2
    # Mode 0644 and traversable directory permit Unix DAC reading.
    # This dummy, non-secret file must be denied by the custom SELinux domain.
    probe = "/var/lib/postapollo-c2r-ci-denied"
    try:
        with open(probe, "r", encoding="utf-8") as handle:
            handle.read()
    except PermissionError:
        print("C2R_PASS // SELINUX_REFUSED_WORLD_READABLE_PROBE", flush=True)
    except OSError as exc:
        print("C2R_FAIL // INVALID_NEGATIVE_PROBE: " + type(exc).__name__, file=sys.stderr)
        return 2
    else:
        print("C2R_FAIL // CONFINED_SERVICE_COULD_READ_PROBE", file=sys.stderr)
        return 2
    try:
        return asyncio.run(serve())
    except Exception as exc:
        print("C2O_STATUS_ONLY_START_FAILED: " + type(exc).__name__, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
