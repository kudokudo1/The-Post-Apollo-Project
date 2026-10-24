#!/usr/bin/env python3
"""Explicit, in-menu Telegram account pairing.

Run as a long-lived Quickshell Process only after the person clicks Connect.
One JSON event is printed per line; input events arrive on stdin (never argv).
No real credentials, phone numbers, codes or passwords are logged or echoed.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile

from bridge import BridgeError, _app_config_path, _credentials, _protect_session_file, _telegram_client

PHONE_RE = re.compile(r"^\+[1-9][0-9]{6,14}$")
APP_HASH_RE = re.compile(r"^[a-fA-F0-9]{32}$")


def emit(state: str, detail: str = "", **fields: str) -> None:
    print(json.dumps({"state": state, "detail": detail, **fields}, ensure_ascii=False), flush=True)


def read_event() -> dict:
    # Fixed max line limits messages and avoids accidentally reading unlimited data.
    line = sys.stdin.readline(8192)
    if not line or not line.endswith("\n"):
        raise BridgeError("CANCELLED", "Connection setup ended")
    try:
        item = json.loads(line)
    except (ValueError, TypeError) as exc:
        raise BridgeError("ERROR", "Invalid connection setup request") from exc
    if not isinstance(item, dict):
        raise BridgeError("ERROR", "Invalid connection setup request")
    return item


async def await_event(expected_action: str) -> str:
    item = await asyncio.to_thread(read_event)
    if item.get("action") != expected_action or not isinstance(item.get("value"), str):
        raise BridgeError("ERROR", "Unexpected connection setup step")
    return item["value"]


def save_app_keys() -> None:
    item = read_event()
    if item.get("action") != "configure":
        raise BridgeError("ERROR", "Expected application key configuration")
    api_id = str(item.get("apiId", "")).strip()
    api_hash = str(item.get("apiHash", "")).strip()
    if not api_id.isascii() or not api_id.isdigit() or int(api_id) <= 0 or not APP_HASH_RE.fullmatch(api_hash):
        raise BridgeError("ERROR", "Enter a valid Telegram API ID and 32-character API hash")
    path = _app_config_path()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.parent.is_symlink():
        raise BridgeError("ERROR", "Application key location is unsafe")
    path.parent.chmod(0o700)
    if path.is_symlink():
        raise BridgeError("ERROR", "Application key location is unsafe")
    # File remains private from creation. Atomic rename prevents partial values.
    payload = json.dumps({"apiId": api_id, "apiHash": api_hash}) + "\n"
    fd, temp = tempfile.mkstemp(prefix=".telegram-keys-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp, 0o600)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    emit("APP_SAVED", "Application configuration saved privately")


def qr_png_data(url: str) -> str:
    try:
        import qrcode
    except ImportError as exc:
        raise BridgeError("DEPENDENCY_MISSING",
                          "QR pairing requires Python qrcode with Pillow; phone sign-in remains available") from exc
    buffer = io.BytesIO()
    image = qrcode.make(url)
    image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


async def two_step_password(client) -> None:
    emit("PASSWORD_REQUIRED", "Enter your Telegram two-step verification password")
    password = await await_event("password")
    if not password:
        raise BridgeError("ERROR", "Two-step password cannot be empty")
    try:
        await client.sign_in(password=password)
    except Exception as exc:
        raise BridgeError("ERROR", "Two-step verification was not accepted") from exc
    finally:
        password = ""


async def qr_sign_in(client) -> None:
    try:
        from telethon.errors import SessionPasswordNeededError
    except ImportError as exc:
        raise BridgeError("DEPENDENCY_MISSING", "Telethon 1.x QR support is unavailable") from exc
    login = await client.qr_login()
    for _ in range(8):
        emit("QR_READY", "Scan this QR in Telegram Settings > Devices > Link Desktop Device",
             image=qr_png_data(login.url))
        try:
            await asyncio.wait_for(login.wait(), timeout=55)
            return
        except SessionPasswordNeededError:
            await two_step_password(client)
            return
        except asyncio.TimeoutError:
            await login.recreate()
    raise BridgeError("EXPIRED", "QR pairing expired. Select Connect again")


async def phone_sign_in(client) -> None:
    try:
        from telethon.errors import SessionPasswordNeededError
    except ImportError as exc:
        raise BridgeError("DEPENDENCY_MISSING", "Telethon 1.x phone sign-in is unavailable") from exc
    emit("PHONE_REQUIRED", "Enter your phone number with country code")
    phone = (await await_event("phone")).strip()
    if not PHONE_RE.fullmatch(phone):
        raise BridgeError("ERROR", "Use an international phone number such as +15551234567")
    try:
        sent = await client.send_code_request(phone)
    except Exception as exc:
        raise BridgeError("ERROR", "Telegram could not send a verification code") from exc
    phone_code_hash = sent.phone_code_hash
    for _ in range(3):
        emit("CODE_REQUIRED", "Enter the verification code sent by Telegram")
        code = (await await_event("code")).strip()
        if not code.isascii() or not code.isdigit() or not 3 <= len(code) <= 10:
            emit("INVALID_CODE", "Enter the numeric verification code")
            continue
        try:
            await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
            return
        except SessionPasswordNeededError:
            await two_step_password(client)
            return
        except Exception:
            emit("INVALID_CODE", "Code was not accepted; check Telegram and try again")
    raise BridgeError("ERROR", "Verification attempt limit reached; reconnect to retry")


async def connect(mode: str) -> None:
    try:
        _credentials()
    except BridgeError as exc:
        if exc.mode == "AUTH_REQUIRED":
            emit("APP_REQUIRED", "Telegram application keys are needed once for this installation")
            return
        raise
    if mode == "qr":
        # Detect missing QR support before touching the account session.
        qr_png_data("tg://login?token=preflight")
    # QR waits for an UpdateLoginToken event. Ordinary read/send bridges
    # deliberately disable updates, but QR authorization MUST enable them.
    client = _telegram_client(receive_updates=(mode == "qr"))
    try:
        await client.connect()
        if await client.is_user_authorized():
            emit("READY", "Telegram account is already connected")
            return
        if mode == "qr":
            await qr_sign_in(client)
        else:
            await phone_sign_in(client)
        if not await client.is_user_authorized():
            raise BridgeError("ERROR", "Telegram did not confirm this account")
        emit("READY", "Telegram account connected")
    finally:
        await client.disconnect()
        _protect_session_file()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Post-Apollo in-menu Telegram pairing bridge")
    parser.add_argument("mode", choices=("qr", "phone", "configure"))
    args = parser.parse_args(argv)
    try:
        if args.mode == "configure":
            save_app_keys()
        else:
            asyncio.run(connect(args.mode))
        return 0
    except BridgeError as exc:
        if exc.mode != "CANCELLED":
            emit(exc.mode, exc.detail)
        return 2
    except Exception:
        # Never echo Telethon exceptions, PII, or auth values to the UI/logs.
        emit("ERROR", "Telegram connection failed; retry or use phone sign-in")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
