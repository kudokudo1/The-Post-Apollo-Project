#!/usr/bin/env python3
"""Syntax-check Team 5's embedded Python provider scripts without executing them.

Run from the repository root:
    python3 services/tabs/validate_embedded_scripts.py

This is deliberately an offline/static gate. It verifies that extraction or later
provider maintenance has not damaged the Python sources embedded in QML.
"""

from __future__ import annotations

import ast
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
PROVIDER = ROOT / "services" / "tabs" / "TabSurfaceProvider.qml"

SCRIPT_FUNCTIONS = (
    "appTabBridgeScript",
    "appTabScanScript",
    "appTabActivateScript",
    "tabLifecycleScript",
)


def extract_returned_string(source: str, function_name: str) -> str:
    pattern = re.compile(
        rf"function\s+{re.escape(function_name)}\s*\([^)]*\)\s*\{{\s*"
        rf"return\s+(?P<literal>\"(?:\\\\.|[^\"\\\\])*\")\s*;\s*\}}",
        re.S,
    )
    match = pattern.search(source)
    if not match:
        raise ValueError(f"could not locate {function_name}()")
    return ast.literal_eval(match.group("literal"))


def main() -> int:
    qml = PROVIDER.read_text(encoding="utf-8")
    errors: list[str] = []

    for name in SCRIPT_FUNCTIONS:
        try:
            script = extract_returned_string(qml, name)
            ast.parse(script, filename=f"<{name}>", mode="exec")
        except Exception as exc:
            errors.append(f"{name}: {exc}")

    if errors:
        print("TEAM 5 EMBEDDED PYTHON: FAIL")
        for error in errors:
            print(" -", error)
        return 1

    print("TEAM 5 EMBEDDED PYTHON: PASS")
    for name in SCRIPT_FUNCTIONS:
        print(" -", name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
