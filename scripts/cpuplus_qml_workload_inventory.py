#!/usr/bin/env python3
"""Read-only static inventory of tracked QML workload markers (not a runtime profiler)."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import subprocess
import sys

OBJECTS = ("Timer", "Process", "FileView", "Connections", "Repeater",
           "Loader", "ListModel", "ListView", "Image", "ShaderEffect",
           "ShaderEffectSource", "NumberAnimation", "SequentialAnimation",
           "ParallelAnimation", "StdioCollector", "SplitParser")
OBJECT_RE = re.compile(r"^\s*(?:[A-Za-z_]\w*\.)?(" +
                       "|".join(OBJECTS) + r")\s*\{")
PROPERTY_RE = re.compile(r"^\s*(running|repeat|interval|active|watchChanges)\s*:\s*(.*)$")
COMPLETED_RE = re.compile(r"^\s*Component\.onCompleted\s*:")


def mask_source(source):
    """Mask comments and quoted strings while retaining line/column boundaries.

    This is intentionally a lexical heuristic, not a QML/JS parser. JS regex
    literals and template interpolation may be misclassified.
    """
    token = re.compile(r"//[^\n]*|/\*[\s\S]*?(?:\*/|\Z)|"
                       r""" "(?:\\[\s\S]|[^"\\])*"|'(?:\\[\s\S]|[^'\\])*'|`(?:\\[\s\S]|[^`\\])*` """,
                       re.VERBOSE)
    return token.sub(lambda m: "".join("\n" if c == "\n" else " "
                                        for c in m.group()), source)


def scan_source(source):
    markers = []
    for number, line in enumerate(mask_source(source).splitlines(), 1):
        match = OBJECT_RE.match(line)
        if match:
            markers.append({"line": number, "kind": match[1]})
        if COMPLETED_RE.match(line):
            markers.append({"line": number, "kind": "Component.onCompleted"})
        match = PROPERTY_RE.match(line)
        if match:
            name, value = match.groups()
            value = value.strip().rstrip(";").strip()
            # No raw expression, paths, literals or payload content in output.
            if name == "interval" and re.fullmatch(r"[0-9]+", value):
                marker = {"line": number, "kind": "interval.literal",
                          "milliseconds": int(value)}
            elif name != "interval" and value in ("true", "false"):
                marker = {"line": number, "kind": name + "." + value}
            else:
                marker = {"line": number, "kind": name + ".expression"}
            markers.append(marker)
    return markers


def tracked_qml(root):
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z", "--", "*.qml"],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    return sorted(set(p.decode("utf-8", errors="surrogateescape")
                      for p in result.stdout.split(b"\0") if p))


def inventory(root, paths):
    root = root.resolve()
    totals = Counter()
    groups = {}
    files = []
    skipped = []
    for name in paths:
        path = root / name
        try:
            if Path(name).is_absolute() or ".." in Path(name).parts:
                raise ValueError("invalid relative path")
            path.resolve().relative_to(root)
            if path.is_symlink() or not path.is_file():
                raise ValueError("not a regular source file")
            markers = scan_source(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError, RuntimeError):
            skipped.append(name)
            continue
        counts = Counter(m["kind"] for m in markers)
        totals.update(counts)
        parts = Path(name).parts
        group = "/".join(parts[:2]) if parts[0] == "services" and len(parts) > 2 else (
            parts[0] if len(parts) > 1 else "(root)")
        entry = groups.setdefault(group, {"files": 0, "counts": Counter()})
        entry["files"] += 1
        entry["counts"].update(counts)
        files.append({"path": name, "counts": dict(counts), "markers": markers})
    return {"trackedQml": len(paths), "scannedQml": len(files),
            "skipped": skipped, "totals": dict(totals), "groups": groups,
            "files": files}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--detail", action="store_true",
                        help="include source file and line marker inventory")
    args = parser.parse_args(argv)
    try:
        report = inventory(args.root, tracked_qml(args.root))
    except (OSError, subprocess.CalledProcessError):
        print("Cannot enumerate tracked QML in this checkout.", file=sys.stderr)
        return 2
    report["schema"] = "post-apollo-qml-workload-inventory-v1"
    report["limitations"] = ("Lexical source candidates only: no runtime counts, "
                             "no QML instantiation or binding evaluation, no "
                             "classification of timer ownership or actual frequency. "
                             "Inline declarations and JS lexical edge cases may be missed.")
    if not args.detail:
        del report["files"]
    print(json.dumps(report, sort_keys=True, indent=2, ensure_ascii=True))
    return 1 if report["skipped"] else 0


if __name__ == "__main__":
    sys.exit(main())
