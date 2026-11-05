#!/usr/bin/env python3
"""C2o client for the throwaway Fedora container ONLY. No credential actions."""
import asyncio
import json
import sys
from dbus_next import BusType, Message, MessageType, NameFlag, RequestNameReply
from dbus_next.aio import MessageBus

NAME = "org.postapollo.ConnectionsStatus1"
PATH = "/org/postapollo/ConnectionsStatus1"

async def run(mode):
    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
    try:
        if mode == "claim":
            try:
                r = await asyncio.wait_for(
                    bus.request_name(NAME, flags=NameFlag.DO_NOT_QUEUE), 3)
                return "CLAIMED" if r == RequestNameReply.PRIMARY_OWNER else "OWN_REFUSED"
            except Exception:
                return "OWN_REFUSED"
        if mode not in {"status", "approve"}:
            return "BAD_MODE"
        msg = Message(destination=NAME, path=PATH, interface=NAME,
                      member="GetStatus" if mode == "status" else "Approve")
        reply = await asyncio.wait_for(bus.call(msg), 3)
        if reply.message_type == MessageType.ERROR:
            return "METHOD_REFUSED"
        if mode != "status" or reply.message_type != MessageType.METHOD_RETURN:
            return "INVALID_REPLY"
        if len(reply.body) != 1 or type(reply.body[0]) is not str:
            return "INVALID_REPLY"
        try:
            val = json.loads(reply.body[0])
        except ValueError:
            return "INVALID_REPLY"
        if (type(val) is not dict
                or set(val) != {"schema", "provider", "state", "readonly"}
                or val["schema"] != "post-apollo.connections.c2o.fedora-fixture.v1"
                or val["state"] != "IDLE"
                or val["provider"] != "nasa-firms"
                or val["readonly"] is not True):
            return "INVALID_REPLY"
        return "OBSERVED_UNVERIFIED"
    finally:
        bus.disconnect()


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in {"claim", "status", "approve"}:
        print("C2O_REFUSED_UNSUPPORTED_CLIENT_ACTION", file=sys.stderr)
        return 2
    try:
        outcome = asyncio.run(run(sys.argv[1]))
    except Exception as exc:
        outcome = "TRANSPORT_UNAVAILABLE"
    print(outcome)
    return 0 if outcome in {"OWN_REFUSED", "METHOD_REFUSED", "OBSERVED_UNVERIFIED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
