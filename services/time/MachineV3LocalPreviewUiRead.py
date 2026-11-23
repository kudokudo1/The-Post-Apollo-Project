#!/usr/bin/env python3
"""TimeW M5: one-click read-only M4 preview for the local M3 data path.

Only an explicit STORED-view click starts this bridge. It reads one canonical
v4 checkpoint from the existing local M3 store. No captures, commands,
unscoped listing, authority promotion, C5 spending, or native window access.
"""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from MachineV3LocalExactCapturePreview import (
    PreviewRefused, _checkpoint_id, _encode_bounded, preview, unavailable,
)
from MachineV3LocalExactCaptureStore import (
    LocalCaptureRefused, LocalExactCaptureStore, suggested_path,
)


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    try:
        if len(args) != 2 or args[0] != "preview":
            raise PreviewRefused("UI READ ONLY PREVIEW REFUSED")
        checkpoint_id = _checkpoint_id(args[1])
        # A user click selects precisely this local XDG data path. The M4
        # developer CLI remains explicit-path only, never auto-discovers.
        # No read or directory creation occurs without an explicit click.
        local = LocalExactCaptureStore(suggested_path())
        result = preview(checkpoint_id, store=local)
        output = _encode_bounded(result)
    except (PreviewRefused, LocalCaptureRefused, ValueError, TypeError,
            AttributeError, OverflowError, OSError, sqlite3.Error):
        print(json.dumps(unavailable(), separators=(",", ":"), ensure_ascii=False))
        return 1
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
