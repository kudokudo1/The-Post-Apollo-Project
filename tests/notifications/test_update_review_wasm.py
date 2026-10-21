#!/usr/bin/env python3
"""Check the actual compiled Zellij header WASM exports a WASI command entry."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WASM = (ROOT / "scripts/updates/zellij/update-review-header/target"
        / "wasm32-wasip1/release/post_apollo_update_header.wasm")
data = WASM.read_bytes()
assert data[:8] == b"\0asm\x01\0\0\0", "Not a WebAssembly v1 binary"


def uleb(offset: int) -> tuple[int, int]:
    result = 0
    shift = 0
    while offset < len(data):
        byte = data[offset]
        offset += 1
        result |= (byte & 0x7f) << shift
        if not byte & 0x80:
            return result, offset
        shift += 7
        assert shift < 64, "Malformed unsigned LEB128"
    raise ValueError("Truncated WASM integer")


entry_found = False
offset = 8
while offset < len(data):
    section_id = data[offset]
    length, start = uleb(offset + 1)
    end = start + length
    assert end <= len(data), "Truncated WASM section"
    if section_id == 7:  # Export section
        count, cursor = uleb(start)
        for _ in range(count):
            size, cursor = uleb(cursor)
            name = data[cursor:cursor + size].decode("utf-8")
            cursor += size
            kind = data[cursor]
            cursor += 1
            _, cursor = uleb(cursor)  # Function/table/memory/global index
            if name == "_start" and kind == 0:
                entry_found = True
        assert cursor == end, "Malformed WASM exports"
    offset = end

assert entry_found, "Missing WASI _start function: build [[bin]], not cdylib"
print("Zellij header WASI _start export: PASS")
