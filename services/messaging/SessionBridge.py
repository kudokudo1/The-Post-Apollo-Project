#!/usr/bin/env python3
"""Compatibility bridge between Quickshell Social and Session Desktop.

Read operations prefer the existing session-cli installation. If that CLI is
missing, times out, or no longer understands Session's private SQL schema, the
bridge falls back to a schema-tolerant read-only SQLCipher reader.

Writes still go through session-cli/CDP. The bridge never writes to Session's
database directly.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable


DEFAULT_READ_TIMEOUT = 8.0
DEFAULT_SEND_TIMEOUT = 20.0


class BridgeError(RuntimeError):
    pass


def _timeout(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default

    try:
        value = float(raw)
    except ValueError:
        return default

    return max(1.0, value)


def _compact(value: str, limit: int = 700) -> str:
    lines = [line.strip() for line in str(value or "").splitlines() if line.strip()]
    text = " // ".join(lines[-4:]) if lines else ""
    return text[-limit:]


def _unique(values: Iterable[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []

    for value in values:
        if not value:
            continue

        item = str(value)
        if item in seen:
            continue

        seen.add(item)
        result.append(item)

    return result


def _cli_candidates() -> list[str]:
    home = Path.home()
    configured = os.environ.get("SESSION_CLI", "").strip()

    return _unique(
        [
            configured,
            str(home / ".local" / "share" / "session-cli-venv" / "bin" / "session-cli"),
            str(home / ".local" / "bin" / "session-cli"),
            shutil.which("session-cli"),
            "/usr/local/bin/session-cli",
            "/usr/bin/session-cli",
        ]
    )


def _find_cli() -> str | None:
    for candidate in _cli_candidates():
        path = Path(candidate).expanduser()

        if path.is_file() and os.access(path, os.X_OK):
            return str(path)

    return None


def _run_process(command: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as error:
        raise BridgeError(
            "timed out after %.1fs: %s"
            % (timeout, " ".join(command[:2]))
        ) from error
    except OSError as error:
        raise BridgeError(str(error)) from error


def _run_cli(arguments: list[str], timeout: float) -> subprocess.CompletedProcess[str]:
    cli = _find_cli()

    if not cli:
        raise BridgeError(
            "session-cli not found; checked SESSION_CLI, "
            "~/.local/share/session-cli-venv/bin/session-cli, ~/.local/bin and PATH"
        )

    result = _run_process([cli, *arguments], timeout)

    if result.returncode != 0:
        detail = _compact(result.stderr) or _compact(result.stdout)
        raise BridgeError(
            "session-cli exited %d%s"
            % (
                result.returncode,
                ": " + detail if detail else "",
            )
        )

    return result


def _parse_json_array(text: str, context: str) -> list[dict[str, Any]]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        raise BridgeError("%s returned invalid JSON: %s" % (context, error)) from error

    if not isinstance(payload, list):
        raise BridgeError("%s returned %s, expected array" % (context, type(payload).__name__))

    return [item for item in payload if isinstance(item, dict)]


def _normalize_conversation(item: dict[str, Any]) -> dict[str, Any]:
    row = dict(item)

    row.setdefault("id", "")
    row.setdefault("type", "private")
    row.setdefault("active_at", 0)
    row.setdefault("displayNameInProfile", None)
    row.setdefault("nickname", None)
    row.setdefault("lastMessage", None)
    row.setdefault("unreadCount", 0)
    row.setdefault("members", None)
    row.setdefault("groupAdmins", None)
    row.setdefault("isApproved", None)
    row.setdefault("didApproveMe", None)
    row.setdefault("avatarInProfile", None)

    return row


def _normalize_message(item: dict[str, Any]) -> dict[str, Any]:
    row = dict(item)

    direction = str(row.get("direction") or "").lower()
    message_type = str(row.get("type") or "").lower()

    if direction not in ("incoming", "outgoing"):
        if message_type in ("incoming", "outgoing"):
            direction = message_type
        elif row.get("isOutgoing") is True:
            direction = "outgoing"
        elif row.get("isIncoming") is True:
            direction = "incoming"
        else:
            direction = "incoming"

    row["direction"] = direction

    if not row.get("type"):
        row["type"] = direction

    if "sent_at" not in row and "timestamp" in row:
        row["sent_at"] = row.get("timestamp")

    row.setdefault("body", "")

    return row


def _cli_list() -> list[dict[str, Any]]:
    result = _run_cli(
        ["--json", "list"],
        _timeout("SESSION_BRIDGE_READ_TIMEOUT", DEFAULT_READ_TIMEOUT),
    )
    return [_normalize_conversation(item) for item in _parse_json_array(result.stdout, "session-cli list")]


def _cli_messages(conversation_id: str, limit: int) -> list[dict[str, Any]]:
    result = _run_cli(
        ["--json", "messages", "--limit", str(limit), conversation_id],
        _timeout("SESSION_BRIDGE_READ_TIMEOUT", DEFAULT_READ_TIMEOUT),
    )
    return [_normalize_message(item) for item in _parse_json_array(result.stdout, "session-cli messages")]


def _session_data_candidates() -> list[Path]:
    home = Path.home()
    configured = os.environ.get("SESSION_DATA_DIR", "").strip()

    values = [
        Path(configured).expanduser() if configured else None,
        home / ".config" / "Session",
        home / ".var" / "app" / "network.loki.Session" / "config" / "Session",
        home / ".var" / "app" / "io.oxen.Session" / "config" / "Session",
        home / ".var" / "app" / "com.getsession.Session" / "config" / "Session",
    ]

    result: list[Path] = []
    seen: set[str] = set()

    for value in values:
        if value is None:
            continue

        key = str(value)
        if key in seen:
            continue

        seen.add(key)
        result.append(value)

    return result


def _find_session_data_dir() -> Path:
    checked: list[str] = []

    for candidate in _session_data_candidates():
        checked.append(str(candidate))

        if (candidate / "config.json").is_file() and (candidate / "sql" / "db.sqlite").is_file():
            return candidate

    raise BridgeError(
        "Session data directory not found; checked " + ", ".join(checked)
    )


def _load_sqlcipher():
    try:
        from sqlcipher3 import dbapi2 as sqlite  # type: ignore

        return sqlite
    except ImportError:
        try:
            from pysqlcipher3 import dbapi2 as sqlite  # type: ignore

            return sqlite
        except ImportError as error:
            raise BridgeError("sqlcipher3/pysqlcipher3 is not installed in this Python environment") from error


def _open_database():
    sqlite = _load_sqlcipher()
    data_dir = _find_session_data_dir()
    config_path = data_dir / "config.json"

    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise BridgeError("cannot read Session config.json: %s" % error) from error

    if bool(config.get("dbHasPassword")):
        raise BridgeError(
            "Session database uses a user password; direct read fallback cannot unlock it"
        )

    key = str(config.get("key") or "").strip()
    if not key:
        raise BridgeError("Session config.json does not contain a database key")

    database_path = data_dir / "sql" / "db.sqlite"

    try:
        connection = sqlite.connect(str(database_path))
        connection.execute('PRAGMA key = "x\'%s\'"' % key)
        connection.execute("SELECT count(*) FROM sqlite_master").fetchone()
    except Exception as error:
        try:
            connection.close()
        except Exception:
            pass

        raise BridgeError("Session SQLCipher open failed: %s" % error) from error

    return connection


def _columns(connection, table: str) -> set[str]:
    try:
        rows = connection.execute("PRAGMA table_info(%s)" % table).fetchall()
    except Exception as error:
        raise BridgeError("cannot inspect Session table %s: %s" % (table, error)) from error

    return {str(row[1]) for row in rows}


def _select_expression(columns: set[str], name: str) -> str:
    if name in columns:
        return '"%s"' % name

    return "NULL AS \"%s\"" % name


def _direct_list() -> list[dict[str, Any]]:
    connection = _open_database()

    try:
        conversation_columns = _columns(connection, "conversations")
        message_columns = _columns(connection, "messages")

        fields = [
            "id",
            "type",
            "active_at",
            "displayNameInProfile",
            "nickname",
            "lastMessage",
            "unreadCount",
            "members",
            "groupAdmins",
            "isApproved",
            "didApproveMe",
            "avatarInProfile",
        ]

        expressions = [_select_expression(conversation_columns, field) for field in fields]

        where = ' WHERE COALESCE("active_at", 0) > 0' if "active_at" in conversation_columns else ""
        order = ' ORDER BY "active_at" DESC' if "active_at" in conversation_columns else ""

        rows = connection.execute(
            "SELECT %s FROM conversations%s%s"
            % (", ".join(expressions), where, order)
        ).fetchall()

        unread_by_conversation: dict[str, int] = {}

        if "unreadCount" not in conversation_columns and {
            "conversationId",
            "unread",
        }.issubset(message_columns):
            for conversation_id, count in connection.execute(
                'SELECT "conversationId", count(*) FROM messages '
                'WHERE "unread" = 1 GROUP BY "conversationId"'
            ).fetchall():
                unread_by_conversation[str(conversation_id)] = int(count or 0)

        result: list[dict[str, Any]] = []

        for row in rows:
            item = dict(zip(fields, row))

            if "unreadCount" not in conversation_columns:
                item["unreadCount"] = unread_by_conversation.get(str(item.get("id") or ""), 0)

            result.append(_normalize_conversation(item))

        return result
    except BridgeError:
        raise
    except Exception as error:
        raise BridgeError("Session conversation fallback query failed: %s" % error) from error
    finally:
        connection.close()


def _message_rows_without_json(
    connection,
    columns: set[str],
    conversation_id: str,
    limit: int,
) -> list[dict[str, Any]]:
    fields = [
        "id",
        "conversationId",
        "source",
        "body",
        "sent_at",
        "received_at",
        "type",
    ]

    expressions = [_select_expression(columns, field) for field in fields]

    if "sent_at" in columns:
        order_column = '"sent_at"'
    elif "received_at" in columns:
        order_column = '"received_at"'
    else:
        order_column = "rowid"

    rows = connection.execute(
        "SELECT %s FROM messages WHERE \"conversationId\" = ? "
        "ORDER BY %s DESC LIMIT ?"
        % (", ".join(expressions), order_column),
        (conversation_id, limit),
    ).fetchall()

    return [_normalize_message(dict(zip(fields, row))) for row in rows]


def _direct_messages(conversation_id: str, limit: int) -> list[dict[str, Any]]:
    connection = _open_database()

    try:
        columns = _columns(connection, "messages")

        if "conversationId" not in columns:
            raise BridgeError("Session messages table no longer exposes conversationId")

        if "json" not in columns:
            return _message_rows_without_json(connection, columns, conversation_id, limit)

        if "sent_at" in columns:
            order_column = '"sent_at"'
        elif "received_at" in columns:
            order_column = '"received_at"'
        else:
            order_column = "rowid"

        rows = connection.execute(
            'SELECT "json" FROM messages WHERE "conversationId" = ? '
            "ORDER BY %s DESC LIMIT ?" % order_column,
            (conversation_id, limit),
        ).fetchall()

        result: list[dict[str, Any]] = []

        for row in rows:
            raw = row[0]

            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", errors="replace")

            try:
                parsed = json.loads(raw or "{}")
            except json.JSONDecodeError:
                continue

            if isinstance(parsed, dict):
                result.append(_normalize_message(parsed))

        return result
    except BridgeError:
        raise
    except Exception as error:
        raise BridgeError("Session message fallback query failed: %s" % error) from error
    finally:
        connection.close()


def _venv_python_candidates() -> list[str]:
    cli = _find_cli()
    if not cli:
        return []

    directory = Path(cli).parent
    return _unique(
        [
            str(directory / "python3"),
            str(directory / "python"),
        ]
    )


def _direct_child(arguments: list[str]) -> str:
    errors: list[str] = []

    for candidate in _venv_python_candidates():
        path = Path(candidate)

        if not path.is_file() or not os.access(path, os.X_OK):
            continue

        try:
            if path.resolve() == Path(sys.executable).resolve():
                continue
        except OSError:
            pass

        result = _run_process(
            [str(path), str(Path(__file__).resolve()), "--direct", *arguments],
            _timeout("SESSION_BRIDGE_READ_TIMEOUT", DEFAULT_READ_TIMEOUT),
        )

        if result.returncode == 0:
            return result.stdout

        errors.append(_compact(result.stderr) or _compact(result.stdout))

    detail = " // ".join(error for error in errors if error)
    raise BridgeError(
        "direct database fallback needs sqlcipher3"
        + (": " + detail if detail else "")
    )


def _direct_json(command: str, conversation_id: str | None, limit: int) -> list[dict[str, Any]]:
    try:
        if command == "list":
            return _direct_list()

        if command == "messages":
            if not conversation_id:
                raise BridgeError("messages requires a conversation id")
            return _direct_messages(conversation_id, limit)

        raise BridgeError("unsupported direct command: %s" % command)
    except BridgeError as error:
        if "sqlcipher3/pysqlcipher3 is not installed" not in str(error):
            raise

        arguments = ["--json", command]

        if command == "messages":
            arguments.extend(["--limit", str(limit), str(conversation_id or "")])

        child_output = _direct_child(arguments)
        return _parse_json_array(child_output, "Session direct fallback")


def _read_with_fallback(command: str, conversation_id: str | None, limit: int) -> tuple[list[dict[str, Any]], str]:
    cli_error = ""

    try:
        if command == "list":
            return _cli_list(), "SESSION_CLI"

        return _cli_messages(str(conversation_id or ""), limit), "SESSION_CLI"
    except BridgeError as error:
        cli_error = str(error)

    try:
        return _direct_json(command, conversation_id, limit), "DATABASE_FALLBACK"
    except BridgeError as direct_error:
        raise BridgeError(
            "session-cli read failed: %s; direct fallback failed: %s"
            % (cli_error, direct_error)
        ) from direct_error


def _send(conversation_id: str, message: str) -> str:
    result = _run_cli(
        ["send", conversation_id, message],
        _timeout("SESSION_BRIDGE_SEND_TIMEOUT", DEFAULT_SEND_TIMEOUT),
    )
    return result.stdout.strip()


def _health() -> dict[str, Any]:
    cli = _find_cli()
    cli_detail = cli or "not found"

    try:
        _cli_list()
        return {
            "status": "ready",
            "mode": "SESSION_CLI",
            "detail": cli_detail,
        }
    except BridgeError as cli_error:
        try:
            _direct_json("list", None, 1)
            return {
                "status": "ready",
                "mode": "DATABASE_FALLBACK",
                "detail": "session-cli unavailable/incompatible; read fallback ready",
            }
        except BridgeError as direct_error:
            raise BridgeError(
                "session-cli: %s; direct fallback: %s"
                % (cli_error, direct_error)
            ) from direct_error


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Post-Apollo Session compatibility bridge")
    parser.add_argument("--json", action="store_true", dest="json_output")
    parser.add_argument("--direct", action="store_true", help=argparse.SUPPRESS)

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("health")
    subparsers.add_parser("list")

    messages = subparsers.add_parser("messages")
    messages.add_argument("--limit", type=int, default=100)
    messages.add_argument("conversation_id")

    send = subparsers.add_parser("send")
    send.add_argument("conversation_id")
    send.add_argument("message")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "health":
            payload = _health()
            print(json.dumps(payload))
            return 0

        if args.command == "send":
            output = _send(args.conversation_id, args.message)
            if output:
                print(output)
            return 0

        if args.direct:
            payload = _direct_json(
                args.command,
                getattr(args, "conversation_id", None),
                max(1, int(getattr(args, "limit", 100))),
            )
        else:
            payload, _mode = _read_with_fallback(
                args.command,
                getattr(args, "conversation_id", None),
                max(1, int(getattr(args, "limit", 100))),
            )

        print(json.dumps(payload))
        return 0
    except BridgeError as error:
        print("SESSION BRIDGE // %s" % error, file=sys.stderr)
        return 2
    except Exception as error:
        print(
            "SESSION BRIDGE // unexpected %s: %s"
            % (type(error).__name__, error),
            file=sys.stderr,
        )
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
