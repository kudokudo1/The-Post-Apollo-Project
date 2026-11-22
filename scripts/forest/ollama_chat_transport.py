#!/usr/bin/env python3
"""Forest Core B2 // opt-in, local-only Ollama chat streaming.

Transport ONLY: no session database, tool execution, memory access, provider
credentials, model pulls, process start, or connection to Hospital/PX.
Nothing happens on import. Calls must be deliberate. Streaming deltas are
PROVISIONAL until a COMPLETE event; they must not be persisted on failure.
"""
from __future__ import annotations

import argparse
import http.client
import json
import socket
import sys
import time
from collections.abc import Iterator
from typing import Any

from ollama_inventory import InventoryFailure, VALID_NAME, _target

MAX_HISTORY = 16
MAX_MESSAGE_BYTES = 4096
MAX_TOTAL_PROMPT_BYTES = 16384
MAX_CHUNK_BYTES = 65536
MAX_STREAM_BYTES = 1024 * 1024
MAX_OUTPUT_BYTES = 32768
MAX_OUTPUT_TOKENS = 512
MIN_CONTEXT = 512
MAX_CONTEXT = 8192
CONNECT_TIMEOUT = 6
TOTAL_SECONDS = 120


class ChatRefusal(Exception):
    """Do not surface prompt, host exception or server response in errors."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _model_name(model: object) -> str:
    if type(model) is not str or not VALID_NAME.fullmatch(model):
        raise ChatRefusal("INVALID_MODEL")
    return model


def _messages(value: object) -> list[dict[str, str]]:
    if type(value) is not list or not 1 <= len(value) <= MAX_HISTORY:
        raise ChatRefusal("INVALID_HISTORY")
    result: list[dict[str, str]] = []
    total = 0
    for message in value:
        if type(message) is not dict or set(message) != {"role", "content"}:
            raise ChatRefusal("INVALID_HISTORY")
        role = message["role"]
        content = message["content"]
        if type(role) is not str or role not in ("user", "assistant"):
            raise ChatRefusal("INVALID_ROLE")
        if type(content) is not str or not content or "\x00" in content:
            raise ChatRefusal("INVALID_PROMPT")
        try:
            size = len(content.encode("utf-8"))
        except UnicodeError as exc:
            raise ChatRefusal("INVALID_PROMPT") from exc
        if size > MAX_MESSAGE_BYTES:
            raise ChatRefusal("PROMPT_TOO_LARGE")
        total += size
        if total > MAX_TOTAL_PROMPT_BYTES:
            raise ChatRefusal("PROMPT_TOO_LARGE")
        result.append({"role": role, "content": content})
    if result[-1]["role"] != "user":
        raise ChatRefusal("LAST_MESSAGE_NOT_USER")
    return result


def _number(value: object, *, lower: int, upper: int, code: str) -> int:
    if type(value) is not int or not lower <= value <= upper:
        raise ChatRefusal(code)
    return value


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict:
    obj: dict = {}
    for key, value in pairs:
        if key in obj:
            raise ChatRefusal("INVALID_STREAM_JSON")
        obj[key] = value
    return obj


def _strict_json(data: bytes) -> object:
    try:
        return json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_no_duplicate_keys,
            parse_constant=lambda _: (_ for _ in ()).throw(
                ChatRefusal("INVALID_STREAM_JSON")),
        )
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ChatRefusal("INVALID_STREAM_JSON") from exc


def stream_chat(
    *,
    model: str,
    messages: list[dict[str, str]],
    endpoint: str = "http://127.0.0.1:11434",
    max_predict: int = 256,
    num_ctx: int = 4096,
) -> Iterator[dict[str, object]]:
    """Yields STARTED, DELTA*, COMPLETE. Raises ChatRefusal on any failure.

    COMPLETE is the only signal suitable for later durable journal commit.
    Close the generator to close the socket; no autonomous retries occur.
    """
    model = _model_name(model)
    messages = _messages(messages)
    max_predict = _number(max_predict, lower=1, upper=MAX_OUTPUT_TOKENS,
                          code="INVALID_PREDICT_LIMIT")
    num_ctx = _number(num_ctx, lower=MIN_CONTEXT, upper=MAX_CONTEXT,
                      code="INVALID_CONTEXT")
    try:
        host, port = _target(endpoint)
    except InventoryFailure as exc:
        raise ChatRefusal(exc.reason) from exc
    payload = json.dumps({
        "model": model,
        "messages": messages,
        "stream": True,
        # No tools, format, think, or auto-specified system persona.
        # Default modest context/prediction limits avoid huge cold starts.
        "options": {"num_predict": max_predict, "num_ctx": num_ctx},
    }, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    connection = http.client.HTTPConnection(host, port, timeout=CONNECT_TIMEOUT)
    start = time.monotonic()
    received = 0
    output_bytes = 0
    fragments: list[str] = []
    complete = False
    try:
        try:
            connection.request("POST", "/api/chat", body=payload, headers={
                "Content-Type": "application/json", "Accept": "application/x-ndjson"
            })
            response = connection.getresponse()
            if response.status != 200:
                raise ChatRefusal("OLLAMA_HTTP_ERROR")
            media_type = (response.getheader("Content-Type") or "").lower()
            media_type = media_type.split(";", 1)[0].strip()
            if media_type not in ("application/x-ndjson", "application/json"):
                raise ChatRefusal("OLLAMA_STREAM_CONTENT_TYPE")
            yield {"event": "STARTED", "model": model, "provider": "ollama"}
            while True:
                if time.monotonic() - start > TOTAL_SECONDS:
                    raise ChatRefusal("OLLAMA_STREAM_DEADLINE")
                data = response.readline(MAX_CHUNK_BYTES + 1)
                received += len(data)
                if received > MAX_STREAM_BYTES:
                    raise ChatRefusal("OLLAMA_STREAM_TOO_LARGE")
                if not data:
                    break
                if len(data) > MAX_CHUNK_BYTES or not data.endswith(b"\n"):
                    raise ChatRefusal("OLLAMA_STREAM_LINE_LIMIT")
                packet = _strict_json(data)
                if type(packet) is not dict or type(packet.get("done")) is not bool:
                    raise ChatRefusal("OLLAMA_STREAM_SCHEMA")
                if packet.get("error"):
                    raise ChatRefusal("OLLAMA_STREAM_ERROR")
                message = packet.get("message", {})
                if type(message) is not dict:
                    raise ChatRefusal("OLLAMA_STREAM_SCHEMA")
                if message.get("tool_calls"):
                    raise ChatRefusal("OLLAMA_TOOLS_UNAUTHORIZED")
                if "role" in message and message["role"] != "assistant":
                    raise ChatRefusal("OLLAMA_STREAM_SCHEMA")
                content = message.get("content", "")
                if type(content) is not str:
                    raise ChatRefusal("OLLAMA_STREAM_SCHEMA")
                try:
                    content_bytes = len(content.encode("utf-8"))
                except UnicodeError as exc:
                    raise ChatRefusal("OLLAMA_STREAM_SCHEMA") from exc
                output_bytes += content_bytes
                if output_bytes > MAX_OUTPUT_BYTES:
                    raise ChatRefusal("OLLAMA_OUTPUT_TOO_LARGE")
                if content:
                    fragments.append(content)
                    yield {"event": "DELTA", "text": content}
                if packet["done"]:
                    if not fragments:
                        raise ChatRefusal("OLLAMA_EMPTY_RESPONSE")
                    complete = True
                    yield {
                        "event": "COMPLETE",
                        "provider": "ollama",
                        "model": model,
                        "text": "".join(fragments),
                    }
                    break
            if not complete:
                raise ChatRefusal("OLLAMA_STREAM_TRUNCATED")
        except socket.timeout as exc:
            raise ChatRefusal("OLLAMA_TIMEOUT") from exc
        except (OSError, http.client.HTTPException) as exc:
            raise ChatRefusal("OLLAMA_UNAVAILABLE") from exc
    finally:
        connection.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Forest B2 local chat transport, explicitly invoked"
    )
    parser.add_argument("command", choices=["chat"])
    parser.add_argument("--model", required=True)
    parser.add_argument("--prompt-stdin", action="store_true", required=True,
                        help="read a prompt from standard input, not shell history")
    parser.add_argument("--endpoint", default="http://127.0.0.1:11434")
    parser.add_argument("--max-predict", type=int, default=256)
    parser.add_argument("--num-ctx", type=int, default=4096)
    args = parser.parse_args(argv)
    prompt = sys.stdin.read(MAX_MESSAGE_BYTES + 1)
    try:
        events = stream_chat(
            model=args.model,
            messages=[{"role": "user", "content": prompt}],
            endpoint=args.endpoint, max_predict=args.max_predict,
            num_ctx=args.num_ctx,
        )
        for event in events:
            print(json.dumps(event, separators=(",", ":"), ensure_ascii=True),
                  flush=True)
        return 0
    except ChatRefusal as exc:
        print(json.dumps({"event": "REFUSED", "reason": exc.code},
                         separators=(",", ":")), flush=True)
        return 2


if __name__ == "__main__":
    sys.exit(main())
