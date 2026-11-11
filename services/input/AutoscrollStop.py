#!/usr/bin/env python3
"""Explicit same-user emergency STOP request; no input device access."""
from __future__ import annotations
import json
import sys
from AutoscrollStopChannel import send_stop, StopChannelError


def main(args=None):
    args = list(sys.argv[1:] if args is None else args)
    if args != ["--stop"]:
        print(json.dumps({"status": "unavailable", "code": "INVALID_ACTION"}))
        return 2
    try:
        result = send_stop()
    except StopChannelError as exc:
        print(json.dumps({"status": "unavailable", "code": str(exc)}))
        return 2
    print(json.dumps(result, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
