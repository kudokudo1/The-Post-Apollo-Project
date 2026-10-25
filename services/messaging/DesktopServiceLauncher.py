#!/usr/bin/env python3
"""Explicit desktop-only service launcher used by Post-Apollo Social.

Signal/Viber/WeChat clients are independent, provider-owned desktop apps.
This launcher does not access their messages, login data or account sessions.
No package installation, account creation, window spoofing, scraping or
automatic login. It runs only after the operator clicks Open Desktop.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys

# Executables, not shell strings. Do not add unverified app IDs or commands.
DESKTOP_APPS = {
    "signal": ("signal-desktop",),
    "viber": ("viber", "Viber"),
    "wechat": ("wechat", "weixin"),
}


def installed_client(service: str) -> str | None:
    if service not in DESKTOP_APPS:
        raise ValueError("Unsupported desktop target")
    for name in DESKTOP_APPS[service]:
        candidate = shutil.which(name)
        if candidate:
            return candidate
    return None


def operation(action: str, service: str) -> dict:
    client = installed_client(service)
    result = {
        "serviceId": service,
        "backendMode": "UNSUPPORTED",
        "desktopInstalled": client is not None,
        "launched": False,
    }
    if action == "probe":
        result["detail"] = "Desktop application available" if client else "Install the provider's desktop application first"
        return result
    if action != "open":
        raise ValueError("Unknown desktop action")
    if client is None:
        result["detail"] = "No installed desktop executable was found"
        return result
    try:
        # Never set shell=True, invoke a provider protocol, or send credentials.
        subprocess.Popen(
            [client],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError:
        result["detail"] = "Desktop launch failed"
        return result
    result["launched"] = True
    result["detail"] = "Desktop launch requested; account connection not verified"
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Post-Apollo provider desktop launcher")
    parser.add_argument("action", choices=("probe", "open"))
    parser.add_argument("service", choices=tuple(DESKTOP_APPS))
    args = parser.parse_args(argv)
    try:
        print(json.dumps(operation(args.action, args.service), separators=(",", ":")))
        return 0
    except (ValueError, TypeError, OSError):
        print(json.dumps({"serviceId": args.service, "backendMode": "UNSUPPORTED",
                          "desktopInstalled": False, "launched": False,
                          "detail": "Desktop action unavailable"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
