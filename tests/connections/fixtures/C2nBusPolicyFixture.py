#!/usr/bin/env python3
"""CI ONLY: real D-Bus process fixture for C2n candidate policy.

Requires an explicitly injected disposable bus address. Never contacts the
machine system bus or handles provider secrets. Uses one GetStatus method.
"""
from __future__ import annotations
import asyncio
import json
import os
import signal
import sys

from dbus_next import Message, MessageType, NameFlag, RequestNameReply
from dbus_next.aio import MessageBus
from dbus_next.service import ServiceInterface, method

NAME = "org.postapollo.ConnectionsStatus1"
PATH = "/org/postapollo/ConnectionsStatus1"
IFACE = NAME
FLAG = "POST_APOLLO_C2N_TEST_BUS_ONLY"
ADDR = "C2N_TEST_BUS_ADDRESS"


class Status(ServiceInterface):
    def __init__(self):
        super().__init__(IFACE)

    @method()
    def GetStatus(self) -> 's':
        return json.dumps({
            "schema": "post-apollo.connections.c2n.policy-smoke.v1",
            "provider": "nasa-firms",
            "state": "IDLE",
            "readonly": True,
        }, separators=(",", ":"))


async def operation(kind: str, address: str) -> int:
    bus = await MessageBus(bus_address=address).connect()
    try:
        if kind == "serve":
            bus.export(PATH, Status())
            try:
                owned = await bus.request_name(NAME, flags=NameFlag.DO_NOT_QUEUE)
            except Exception:
                print("OWN_REFUSED", flush=True)
                return 2
            if owned != RequestNameReply.PRIMARY_OWNER:
                print("OWN_REFUSED", flush=True)
                return 2
            stopped = asyncio.Event()
            loop = asyncio.get_running_loop()
            loop.add_signal_handler(signal.SIGINT, stopped.set)
            loop.add_signal_handler(signal.SIGTERM, stopped.set)
            print("READY", flush=True)
            await stopped.wait()
            return 0

        if kind == "claim":
            try:
                owned = await bus.request_name(NAME, flags=NameFlag.DO_NOT_QUEUE)
                print("CLAIMED" if owned == RequestNameReply.PRIMARY_OWNER
                      else "OWN_REFUSED", flush=True)
                return 1 if owned == RequestNameReply.PRIMARY_OWNER else 0
            except Exception:
                print("OWN_REFUSED", flush=True)
                return 0

        if kind in {"status", "approve"}:
            msg = Message(
                destination=NAME, path=PATH, interface=IFACE,
                member="GetStatus" if kind == "status" else "Approve",
            )
            reply = await bus.call(msg)
            if reply.message_type == MessageType.ERROR:
                print("METHOD_REFUSED", flush=True)
                return 0
            if kind != "status" or reply.message_type != MessageType.METHOD_RETURN:
                print("UNEXPECTED_REPLY", flush=True)
                return 2
            if len(reply.body) != 1 or not isinstance(reply.body[0], str):
                print("BAD_REPLY", flush=True)
                return 2
            decoded = json.loads(reply.body[0])
            if (set(decoded) != {"schema", "provider", "state", "readonly"}
                    or decoded["schema"] != "post-apollo.connections.c2n.policy-smoke.v1"
                    or decoded["state"] != "IDLE"
                    or decoded["provider"] != "nasa-firms"
                    or decoded["readonly"] is not True):
                print("BAD_REPLY", flush=True)
                return 2
            print("STATUS_READONLY_UNVERIFIED", flush=True)
            return 0
    finally:
        bus.disconnect()
    return 2


def main() -> int:
    kind = sys.argv[1] if len(sys.argv) == 2 else ""
    address = os.environ.get(ADDR, "")
    if (kind not in {"serve", "claim", "status", "approve"}
            or os.environ.get(FLAG) != "1"
            or not address.startswith("unix:")):
        print("C2N_REFUSED_NOT_ISOLATED_CI", file=sys.stderr)
        return 2
    try:
        return asyncio.run(operation(kind, address))
    except Exception:
        print("C2N_DISPOSABLE_BUS_UNAVAILABLE", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
