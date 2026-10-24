#!/usr/bin/env python3
"""Post-Apollo Telegram personal-client bridge (Telethon 1.x / official MTProto API).

Requires an operator-created Telegram API ID/hash and opt-in CLI login.
Never prompts during GUI health/read/send operations. Does not use Telegram Bot API.
Send bodies arrive on stdin as a single JSON line, not process arguments.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
import json
import os
from pathlib import Path
import sys
from typing import Any

SERVICE = "telegram"
MAX_TEXT_LENGTH = 4096


class BridgeError(Exception):
    def __init__(self, mode: str, detail: str):
        super().__init__(detail)
        self.mode = mode
        self.detail = detail


def _session_path() -> Path:
    root = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local/share"))
    return root / "post-apollo" / "telegram" / "personal.session"


def _app_config_path() -> Path:
    root = Path(os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config"))
    return root / "post-apollo" / "telegram" / "client.json"


def _app_credentials_from_private_file() -> dict[str, str]:
    path = _app_config_path()
    if not path.exists():
        return {}
    if path.is_symlink() or (path.stat().st_mode & 0o077):
        raise BridgeError("AUTH_REQUIRED", "Telegram application key file permissions are unsafe")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise BridgeError("AUTH_REQUIRED", "Telegram application key file is unreadable")
    return data if isinstance(data, dict) else {}


def _credentials() -> tuple[int, str]:
    id_text = os.environ.get("POST_APOLLO_TELEGRAM_API_ID", "").strip()
    api_hash = os.environ.get("POST_APOLLO_TELEGRAM_API_HASH", "").strip()
    if not id_text or not api_hash:
        config = _app_credentials_from_private_file()
        id_text = id_text or str(config.get("apiId", "")).strip()
        api_hash = api_hash or str(config.get("apiHash", "")).strip()
    if not id_text or not api_hash:
        raise BridgeError("AUTH_REQUIRED", "Configure Telegram API ID/hash, then run explicit login")
    try:
        api_id = int(id_text)
    except ValueError as exc:
        raise BridgeError("AUTH_REQUIRED", "Telegram API ID must be numeric") from exc
    if api_id <= 0:
        raise BridgeError("AUTH_REQUIRED", "Telegram API ID must be positive")
    return api_id, api_hash


def _telegram_client(*, receive_updates: bool = False):
    api_id, api_hash = _credentials()
    try:
        from telethon import TelegramClient
    except ImportError as exc:
        raise BridgeError("UNSUPPORTED", "Install the supported Telethon 1.x Python library") from exc
    session = _session_path()
    session.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    session.parent.chmod(0o700)
    if session.exists():
        session.chmod(0o600)
    # SQLite session creation can happen inside TelegramClient's constructor.
    # Ensure it is private *from creation*, not merely after disconnect.
    prior_umask = os.umask(0o077)
    try:
        return TelegramClient(str(session), api_id, api_hash, receive_updates=receive_updates)
    finally:
        os.umask(prior_umask)


def _protect_session_file() -> None:
    path = _session_path()
    if path.exists():
        path.chmod(0o600)


def _seconds(value: Any) -> int:
    """Native Telethon UTC datetime converted to integer Unix seconds.

    v1.0 universal timestamp unit is awaiting integration-owner freeze;
    this provider retains its native unit and declares it in the handoff.
    """
    if isinstance(value, datetime):
        return int(value.timestamp())
    return int(value or 0)


def normalize_dialog(dialog: Any) -> dict[str, Any]:
    msg = getattr(dialog, "message", None)
    last = getattr(msg, "message", None)
    return {
        "id": str(dialog.id),
        "serviceId": SERVICE,
        "type": "group" if getattr(dialog, "is_group", False) else "channel" if getattr(dialog, "is_channel", False) else "private",
        "displayNameInProfile": str(getattr(dialog, "name", "") or str(dialog.id)),
        "lastMessage": str(last or ""),
        "unreadCount": max(0, int(getattr(dialog, "unread_count", 0) or 0)),
        "active_at": _seconds(getattr(msg, "date", None)),
    }


def normalize_message(message: Any, conversation_id: str) -> dict[str, Any]:
    return {
        "id": str(message.id),
        "conversationId": conversation_id,
        "body": str(getattr(message, "message", "") or ""),
        "direction": "outgoing" if bool(getattr(message, "out", False)) else "incoming",
        "sent_at": _seconds(getattr(message, "date", None)),
    }


async def _dialogs(client: Any) -> list[Any]:
    # Fetch all dialogs so IDs are resolved from this authenticated account,
    # without constructing peers from an arbitrary user-provided identifier.
    return list(await client.get_dialogs(limit=None))


async def list_conversations(client: Any) -> list[dict[str, Any]]:
    return [normalize_dialog(row) for row in await _dialogs(client)]


async def _resolve_dialog(client: Any, conversation_id: str) -> Any:
    if not conversation_id:
        raise BridgeError("ERROR", "Select a Telegram conversation")
    for dialog in await _dialogs(client):
        if str(dialog.id) == conversation_id:
            return dialog
    raise BridgeError("ERROR", "Telegram conversation not found in this account")


async def list_messages(client: Any, conversation_id: str, limit: int = 100) -> list[dict[str, Any]]:
    dialog = await _resolve_dialog(client, conversation_id)
    rows = await client.get_messages(dialog.entity, limit=max(1, min(limit, 100)))
    messages = [normalize_message(row, conversation_id) for row in rows]
    return sorted(messages, key=lambda row: (row["sent_at"], int(row["id"])))


async def send_text(client: Any, conversation_id: str, body: str) -> dict[str, Any]:
    if not isinstance(body, str) or not body.strip():
        raise BridgeError("ERROR", "Cannot send an empty Telegram message")
    if len(body) > MAX_TEXT_LENGTH:
        raise BridgeError("ERROR", "Telegram text exceeds the 4096-character limit")
    dialog = await _resolve_dialog(client, conversation_id)
    # Disable Telethon's default Markdown parser: the shared composer is plain text.
    result = await client.send_message(dialog.entity, body, parse_mode=None)
    if not result or not getattr(result, "id", None):
        raise BridgeError("ERROR", "Telegram did not confirm the send")
    return {"sent": True, "messageId": str(result.id)}


def _read_send_body() -> str:
    line = sys.stdin.readline(30000)
    try:
        envelope = json.loads(line)
    except (ValueError, TypeError) as exc:
        raise BridgeError("ERROR", "Malformed Telegram send request") from exc
    if not isinstance(envelope, dict) or not isinstance(envelope.get("text"), str):
        raise BridgeError("ERROR", "Telegram send request requires text")
    return envelope["text"]


async def _run(args: argparse.Namespace) -> Any:
    if args.command == "login" and not sys.stdin.isatty():
        raise BridgeError("AUTH_REQUIRED", "Telegram login requires an interactive terminal")
    # Don't touch a profile without credentials and the provider dependency.
    client = _telegram_client()
    if args.command == "login":
        try:
            await client.start()
            if not await client.is_user_authorized():
                raise BridgeError("AUTH_REQUIRED", "Telegram login was not completed")
            return {"mode": "READY", "detail": "Telegram account linked"}
        finally:
            await client.disconnect()
            _protect_session_file()
    try:
        await client.connect()
        if not await client.is_user_authorized():
            raise BridgeError("AUTH_REQUIRED", "Telegram account not linked; run explicit login")
        if args.command == "health":
            return {"mode": "READY", "detail": "Telegram account authorized"}
        if args.command == "list":
            return await list_conversations(client)
        if args.command == "messages":
            return await list_messages(client, args.conversation_id, args.limit)
        if args.command == "send":
            return await send_text(client, args.conversation_id, _read_send_body())
        raise BridgeError("ERROR", "Unknown Telegram bridge command")
    finally:
        await client.disconnect()
        _protect_session_file()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Post-Apollo personal Telegram bridge")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("health")
    sub.add_parser("login")
    sub.add_parser("list")
    messages = sub.add_parser("messages")
    messages.add_argument("conversation_id")
    messages.add_argument("--limit", type=int, default=100)
    send = sub.add_parser("send")
    send.add_argument("conversation_id")
    args = parser.parse_args(argv)
    try:
        payload = asyncio.run(_run(args))
        print(json.dumps(payload, ensure_ascii=False))
        return 0
    except BridgeError as exc:
        if args.command == "health":
            print(json.dumps({"mode": exc.mode, "detail": exc.detail}))
            return 0
        print(f"TELEGRAM {exc.mode}: {exc.detail}", file=sys.stderr)
        return 2
    except (OSError, RuntimeError, ValueError, TimeoutError):
        # Avoid echoing library exceptions: they may contain account information.
        if args.command == "health":
            print(json.dumps({"mode": "ERROR", "detail": "Telegram connection unavailable"}))
            return 0
        print("TELEGRAM ERROR: connection or provider operation failed", file=sys.stderr)
        return 2
    except Exception:
        if args.command == "health":
            print(json.dumps({"mode": "ERROR", "detail": "Telegram provider error"}))
            return 0
        print("TELEGRAM ERROR: provider operation failed", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
