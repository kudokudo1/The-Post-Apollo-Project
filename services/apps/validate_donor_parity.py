#!/usr/bin/env python3
"""Pre-integration donor-parity guard for Team 8 APPS Core.

Run from the repository root:
    python3 services/apps/validate_donor_parity.py

Purpose:
- verify the still-live AppControl donor continues to expose the APPS semantics
  Team 8 extracted on the parallel floor;
- verify the isolated Team 8 files still preserve the corresponding behavior
  contracts;
- detect donor drift before a future serialized host-integration slot.

This is intentionally a semantic-anchor guard rather than byte-for-byte source
comparison because Team 8 has split donor behavior across multiple pure organs.

Once T3 authorizes APPS host integration and donor blocks are deliberately
removed, this guard must be retired or converted to fixture/golden tests.
"""

from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
DONOR = ROOT / "widgets" / "AppControlW.qml"
APP_DIR = ROOT / "services" / "apps"

EXTRACTED = {
    "core": APP_DIR / "AppCoreProvider.qml",
    "launch": APP_DIR / "AppLaunchPlanner.qml",
    "actions": APP_DIR / "AppActionCatalog.qml",
    "action_planner": APP_DIR / "AppActionPlanner.qml",
    "catalog": APP_DIR / "AppCatalogPolicy.qml",
    "hidden": APP_DIR / "AppHiddenAdapter.qml",
    "bottles": APP_DIR / "AppBottleProvider.qml",
}

errors: list[str] = []

if not DONOR.exists():
    print("TEAM 8 DONOR PARITY: SKIP/FAIL")
    print(" - AppControl donor is absent; retire/replace this pre-integration guard")
    sys.exit(1)

donor_text = DONOR.read_text(encoding="utf-8")
texts: dict[str, str] = {}

for key, path in EXTRACTED.items():
    if not path.exists():
        errors.append(f"missing extracted file: {path.relative_to(ROOT)}")
        continue
    texts[key] = path.read_text(encoding="utf-8")


def function_body(source: str, name: str) -> str:
    """Return one QML/JS function block using brace balancing."""
    match = re.search(
        rf"^\s*function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{",
        source,
        re.M,
    )
    if not match:
        raise ValueError(f"missing function {name}()")

    start = match.start()
    brace = source.find("{", match.start(), match.end())
    depth = 0
    in_string: str | None = None
    escaped = False

    for index in range(brace, len(source)):
        char = source[index]

        if in_string is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == in_string:
                in_string = None
            continue

        if char in ('"', "'", "`"):
            in_string = char
            continue

        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]

    raise ValueError(f"unterminated function {name}()")


def require_all(label: str, text: str, anchors: tuple[str, ...]) -> None:
    missing = [anchor for anchor in anchors if anchor not in text]
    if missing:
        errors.append(
            f"{label}: missing semantic anchors: "
            + ", ".join(repr(item) for item in missing)
        )


def require_function_anchors(
    label: str,
    source: str,
    function_name: str,
    anchors: tuple[str, ...],
) -> None:
    try:
        body = function_body(source, function_name)
    except Exception as exc:
        errors.append(f"{label}: {exc}")
        return
    require_all(label, body, anchors)


# ---------------------------------------------------------------------------
# Donor anchors
# ---------------------------------------------------------------------------

require_function_anchors(
    "donor Flatpak classification",
    donor_text,
    "appEntryIsFlatpak",
    ("flatpak run", "/flatpak ", "flatpak --"),
)

require_function_anchors(
    "donor source labels",
    donor_text,
    "appSourceLabel",
    ('"HIDDEN"', '"FLATPAK"', '"NORMAL"'),
)

require_function_anchors(
    "donor launch-command availability",
    donor_text,
    "appEntryHasLaunchCommand",
    ("Array.isArray(command)", "command[0]", ".trim().length > 0"),
)

require_function_anchors(
    "donor DesktopEntry argv cleanup",
    donor_text,
    "appToolboxCommandTokens",
    (
        r"/^%[fFuUdDnNickvm]$/",
        '"__APPCONTROL_SHELL__"',
        r"/\s+%[fFuUdDnNickvm]\b/g",
    ),
)

require_function_anchors(
    "donor browser classification",
    donor_text,
    "appEntryBrowserKind",
    ('"mullvad"', '"brave"', '"firefox"', "startupClass"),
)

require_function_anchors(
    "donor browser action catalog",
    donor_text,
    "appDesktopActions",
    (
        '"new-window"',
        '"new-private-window"',
        '"new-tab"',
        '"history"',
        '"downloads"',
        '"bookmarks"',
        '"extensions"',
        '"settings"',
        '"devtools"',
        '"clear-data"',
        '"restore"',
        '"task-manager"',
        '"passwords"',
        '"profile-manager"',
        '"firefox-view"',
    ),
)

require_function_anchors(
    "donor browser shortcuts",
    donor_text,
    "browserShortcutSequence",
    (
        '["ctrl", "h"]',
        '["ctrl", "shift", "h"]',
        '["ctrl", "j"]',
        '["ctrl", "shift", "o"]',
        '["ctrl", "shift", "Delete"]',
        '["ctrl", "shift", "t"]',
        '["shift", "Escape"]',
        '["F12"]',
    ),
)

require_function_anchors(
    "donor browser launch arguments",
    donor_text,
    "runBrowserLaunchAction",
    (
        '"--new-window"',
        '"brave://newtab/"',
        '"--incognito"',
        '"brave://extensions/"',
        '"brave://settings/"',
        '"about:newtab"',
        '"--private-window"',
        '"about:addons"',
        '"--preferences"',
        '"about:logins"',
        '"--ProfileManager"',
        '"about:firefoxview"',
    ),
)

require_function_anchors(
    "donor HIDDEN known icons",
    donor_text,
    "hiddenCommandIcon",
    (
        '"cava": "audio-card"',
        '"nvim": "nvim"',
        '"btop": "btop"',
        '"kitty": "kitty"',
        '"cmatrix": "utilities-terminal"',
    ),
)

require_function_anchors(
    "donor HIDDEN record shape",
    donor_text,
    "hiddenCommandRecord",
    (
        "_hiddenCommand: true",
        '"hidden:" + name',
        'genericName: "HIDDEN COMMAND"',
        'comment: "Command-line application from $PATH"',
        'keywords: "terminal cli hidden command"',
        "command: [name]",
    ),
)

require_function_anchors(
    "donor APPS local key",
    donor_text,
    "appEntryKey",
    ("entry.id", "entry.name"),
)

# filteredApps is a ScriptModel rather than a function, so guard the distinctive
# donor semantics directly in the containing source.
require_all(
    "donor APPS result policy",
    donor_text,
    (
        "id: filteredApps",
        "DesktopEntries.applications.values",
        "appControlWindow.runAllCommands",
        "appControlWindow.isFavorite(a)",
        "appControlWindow.isFavorite(b)",
        "appControlWindow.appEntryMatchesSelectedSource(a)",
        "appControlWindow.appEntryKey(a)",
    ),
)

# ---------------------------------------------------------------------------
# Extracted-side anchors
# ---------------------------------------------------------------------------

require_function_anchors(
    "extracted Flatpak classification",
    texts.get("core", ""),
    "entryIsFlatpak",
    ("flatpak run", "/flatpak ", "flatpak --"),
)

require_function_anchors(
    "extracted source labels",
    texts.get("core", ""),
    "sourceLabel",
    ('"HIDDEN"', '"FLATPAK"', '"NORMAL"'),
)

require_function_anchors(
    "extracted launch-command availability",
    texts.get("core", ""),
    "entryHasLaunchCommand",
    ("Array.isArray(command)", "command[0]", ".trim().length > 0"),
)

require_function_anchors(
    "extracted DesktopEntry argv cleanup",
    texts.get("launch", ""),
    "cleanedCommandTokens",
    (
        r"/^%[fFuUdDnNickvm]$/",
        '"__APPCONTROL_SHELL__"',
        r"/\s+%[fFuUdDnNickvm]\b/g",
    ),
)

require_function_anchors(
    "extracted browser classification",
    texts.get("actions", ""),
    "browserKind",
    ('"mullvad"', '"brave"', '"firefox"', "startupClass"),
)

require_function_anchors(
    "extracted browser action catalog",
    texts.get("actions", ""),
    "desktopActions",
    (
        '"new-window"',
        '"new-private-window"',
        '"new-tab"',
        '"history"',
        '"downloads"',
        '"bookmarks"',
        '"extensions"',
        '"settings"',
        '"devtools"',
        '"clear-data"',
        '"restore"',
        '"task-manager"',
        '"passwords"',
        '"profile-manager"',
        '"firefox-view"',
    ),
)

require_function_anchors(
    "extracted browser shortcuts",
    texts.get("actions", ""),
    "shortcutSequence",
    (
        '["ctrl", "h"]',
        '["ctrl", "shift", "h"]',
        '["ctrl", "j"]',
        '["ctrl", "shift", "o"]',
        '["ctrl", "shift", "Delete"]',
        '["ctrl", "shift", "t"]',
        '["shift", "Escape"]',
        '["F12"]',
    ),
)

require_function_anchors(
    "extracted browser launch arguments",
    texts.get("actions", ""),
    "launchArguments",
    (
        '"--new-window"',
        '"brave://newtab/"',
        '"--incognito"',
        '"brave://extensions/"',
        '"brave://settings/"',
        '"about:newtab"',
        '"--private-window"',
        '"about:addons"',
        '"--preferences"',
        '"about:logins"',
        '"--ProfileManager"',
        '"about:firefoxview"',
    ),
)

require_function_anchors(
    "extracted browser action precedence",
    texts.get("action_planner", ""),
    "browserBuiltinPlan",
    (
        "shortcutSequence",
        'id === "downloads"',
        '"about:downloads"',
        "launchArguments",
    ),
)

require_function_anchors(
    "extracted HIDDEN known icons",
    texts.get("hidden", ""),
    "knownIcon",
    (
        '"cava": "audio-card"',
        '"nvim": "nvim"',
        '"btop": "btop"',
        '"kitty": "kitty"',
        '"cmatrix": "utilities-terminal"',
    ),
)

require_function_anchors(
    "extracted HIDDEN record shape",
    texts.get("hidden", ""),
    "recordForCommand",
    (
        "_hiddenCommand: true",
        '"hidden:" + name',
        'genericName: "HIDDEN COMMAND"',
        'comment: "Command-line application from $PATH"',
        'keywords: "terminal cli hidden command"',
        "command: [name]",
    ),
)

# Intentional decoupling: extracted HIDDEN rows must not retain donor callback.
hidden_text = texts.get("hidden", "")
if re.search(r"\bexecute\s*:", hidden_text):
    errors.append("extracted HIDDEN adapter retained an execute callback")
if "appControlWindow" in hidden_text:
    errors.append("extracted HIDDEN adapter retained AppControl back-reference")

require_function_anchors(
    "extracted APPS local key",
    texts.get("catalog", ""),
    "entryKey",
    ("entry.id", "entry.name"),
)

require_function_anchors(
    "extracted APPS result ranking",
    texts.get("catalog", ""),
    "compareEntries",
    (
        "preferenceValue",
        "localeCompare",
        "entryMatchesSource",
        "entryKey",
    ),
)

require_function_anchors(
    "extracted external HIDDEN catalog",
    texts.get("catalog", ""),
    "rows",
    ("sourceHidden", "hiddenRows", "desktopRows"),
)

# The extracted policy must not pull provider implementations back into APPS.
for token in (
    "FavoritesStore",
    "favoriteStore",
    "runAllCommands",
    "TabSurfaceProvider",
    "ProcessControl",
    "appAudio",
    "swayWindows",
):
    for key, text in texts.items():
        if token in text:
            errors.append(
                f"extracted {key}: foreign implementation token present: "
                f"{token!r}"
            )

if errors:
    print("TEAM 8 DONOR PARITY: FAIL")
    for error in errors:
        print(" -", error)
    sys.exit(1)

print("TEAM 8 DONOR PARITY: PASS")
print(" donor:", DONOR.relative_to(ROOT))
for key, path in EXTRACTED.items():
    print(" -", key, path.relative_to(ROOT))
print(" donor callback intentionally removed from extracted HIDDEN records")
print(" foreign provider/store implementations: absent from APPS core")
