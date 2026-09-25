#!/usr/bin/env python3
"""Pre-integration parity check for Team 5 donor-native scripts.

Run from the repository root:
    python3 services/tabs/validate_donor_parity.py

This test is intentionally temporary/pre-integration. While AppControl still
contains the donor-local TABS implementation, the four provider-native scripts
must remain byte-for-byte equivalent between donor and extracted provider.
Once the serialized host transplant removes the donor block, this test should
be retired or converted to fixture-based golden tests.
"""

from __future__ import annotations

import ast
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
DONOR = ROOT / "widgets" / "AppControlW.qml"
PROVIDER = ROOT / "services" / "tabs" / "TabSurfaceProvider.qml"

SCRIPT_FUNCTIONS = (
    "appTabBridgeScript",
    "appTabScanScript",
    "appTabActivateScript",
    "tabLifecycleScript",
)


def extract_returned_string(source: str, function_name: str) -> str:
    """Extract the one string literal returned by a donor/provider script fn."""
    pattern = re.compile(
        rf"function\s+{re.escape(function_name)}\s*\([^)]*\)\s*\{{\s*"
        rf"return\s+(?P<literal>"(?:\\.|[^"\\])*")\s*;\s*\}}",
        re.S,
    )
    match = pattern.search(source)
    if not match:
        raise ValueError(f"could not locate {function_name}()")

    # QML/JS uses JSON/Python-compatible escapes for these generated scripts.
    return ast.literal_eval(match.group("literal"))


def main() -> int:
    donor_text = DONOR.read_text(encoding="utf-8")
    provider_text = PROVIDER.read_text(encoding="utf-8")

    errors: list[str] = []

    for name in SCRIPT_FUNCTIONS:
        try:
            donor_script = extract_returned_string(donor_text, name)
            provider_script = extract_returned_string(provider_text, name)
        except Exception as exc:
            errors.append(f"{name}: extraction failed: {exc}")
            continue

        if donor_script != provider_script:
            errors.append(
                f"{name}: provider-native script drifted from donor"
            )

    if errors:
        print("TEAM 5 DONOR PARITY: FAIL")
        for error in errors:
            print(" -", error)
        return 1

    print("TEAM 5 DONOR PARITY: PASS")
    for name in SCRIPT_FUNCTIONS:
        print(" -", name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
