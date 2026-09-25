#!/usr/bin/env python3
"""Analyze Team 7 identity fixtures without resolving semantic identity.

The report keeps evidence families separate. It is intentionally incapable of
choosing a canonical application, assigning a semantic key, or scoring a winner.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from validate_identity_fixtures import validate_fixture


def text(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def coordinate(observation: dict[str, Any]) -> str:
    provider = text(observation.get("provider"))
    provider_key = text(observation.get("providerKey"))
    return f"{provider}|{provider_key}" if provider and provider_key else ""


def normalize_token(value: Any) -> str:
    raw = text(value).lower()
    raw = re.sub(r"\.desktop$", "", raw)
    return re.sub(r"[^a-z0-9]+", "", raw)


def positive_pid(value: Any) -> int:
    try:
        pid = int(value)
    except (TypeError, ValueError):
        return 0
    return pid if pid > 1 else 0


def pid_attachments(
    observation: dict[str, Any],
) -> list[dict[str, Any]]:
    raw = observation.get("raw") or {}
    result: list[dict[str, Any]] = []
    seen: set[tuple[int, str]] = set()

    def add(value: Any, source_field: str) -> None:
        pid = positive_pid(value)
        key = (pid, source_field)
        if pid <= 1 or key in seen:
            return
        seen.add(key)
        result.append({"pid": pid, "sourceField": source_field})

    add(raw.get("pid"), "raw.pid")
    add(
        raw.get("applicationProcessId"),
        "raw.applicationProcessId",
    )

    process_pids = raw.get("processPids")
    if isinstance(process_pids, list):
        for value in process_pids:
            add(value, "raw.processPids")

    relationships = observation.get("relationships")
    if isinstance(relationships, list):
        for relationship in relationships:
            if not isinstance(relationship, dict):
                continue
            if text(relationship.get("targetProvider")) != "PROCFS":
                continue
            target_key = text(relationship.get("targetKey"))
            if not target_key.startswith("pid:"):
                continue
            add(
                target_key[4:],
                "relationship:" + text(relationship.get("kind")),
            )

    return result


def pid_groups(
    observations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    groups: dict[int, dict[str, Any]] = {}

    for observation in observations:
        obs_coordinate = coordinate(observation)
        if not obs_coordinate:
            continue

        for attachment in pid_attachments(observation):
            pid = attachment["pid"]
            group = groups.setdefault(
                pid,
                {
                    "pid": pid,
                    "evidenceFamily": "pid",
                    "members": {},
                },
            )
            member = group["members"].setdefault(
                obs_coordinate,
                {
                    "coordinate": obs_coordinate,
                    "provider": text(observation.get("provider")),
                    "providerKey": text(observation.get("providerKey")),
                    "sourceFields": [],
                },
            )
            if attachment["sourceField"] not in member["sourceFields"]:
                member["sourceFields"].append(attachment["sourceField"])

    result: list[dict[str, Any]] = []
    for pid in sorted(groups):
        group = groups[pid]
        members = list(group["members"].values())
        if len(members) < 2:
            continue
        result.append(
            {
                "pid": pid,
                "evidenceFamily": "pid",
                "members": members,
            }
        )

    return result


def process_owns_debug_port(
    observation: dict[str, Any],
    port: int,
) -> bool:
    if text(observation.get("provider")) != "PROCFS" or port <= 0:
        return False

    raw = observation.get("raw") or {}
    args = text(raw.get("args"))
    tokens = args.split()

    equal_form = f"--remote-debugging-port={port}"
    for index, token in enumerate(tokens):
        if token == equal_form:
            return True
        if (
            token == "--remote-debugging-port"
            and index + 1 < len(tokens)
        ):
            try:
                if int(tokens[index + 1]) == port:
                    return True
            except ValueError:
                pass

    return False


def debug_port_edges(
    observations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str, int]] = set()

    for left in observations:
        left_raw = left.get("raw") or {}
        try:
            port = int(left_raw.get("debugPort") or 0)
        except (TypeError, ValueError):
            port = 0

        if port <= 0:
            continue

        for process in observations:
            if not process_owns_debug_port(process, port):
                continue

            key = (coordinate(left), coordinate(process), port)
            if not all(key[:2]) or key in seen:
                continue
            seen.add(key)

            result.append(
                {
                    "kind": "EXACT_DEBUG_PORT_OWNER",
                    "strength": "exact",
                    "left": key[0],
                    "right": key[1],
                    "debugPort": port,
                    "evidenceFamily": "debug-port",
                }
            )

    return result


def kitty_endpoint_edges(
    observations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    launches = [
        item
        for item in observations
        if text(item.get("provider")) == "SURFACE_LAUNCH"
    ]
    surfaces = [
        item
        for item in observations
        if text(item.get("provider")) == "KITTY"
    ]

    for launch in launches:
        listen_on = text(
            (launch.get("raw") or {}).get("kittyListenOn")
        ).strip()
        if not listen_on:
            continue

        for surface in surfaces:
            address = text(
                (surface.get("raw") or {}).get("kittyAddress")
            ).strip()
            if address != listen_on:
                continue

            key = (
                coordinate(launch),
                coordinate(surface),
                address,
            )
            if not all(key[:2]) or key in seen:
                continue
            seen.add(key)

            result.append(
                {
                    "kind": "EXACT_KITTY_ENDPOINT",
                    "strength": "exact",
                    "left": key[0],
                    "right": key[1],
                    "kittyAddress": address,
                    "evidenceFamily": "kitty-endpoint",
                }
            )

    return result


def alias_records(
    observation: dict[str, Any],
) -> list[dict[str, str]]:
    aliases = observation.get("aliases")
    if not isinstance(aliases, list):
        return []

    result: list[dict[str, str]] = []
    for alias in aliases:
        if not isinstance(alias, dict):
            continue

        value = text(alias.get("value"))
        if not value:
            continue

        result.append(
            {
                "kind": text(alias.get("kind")),
                "value": value,
                "rawComparable": value.strip().lower(),
                "normalized": text(alias.get("normalized"))
                or normalize_token(value),
            }
        )

    return result


def alias_edges(
    observations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str, str]] = set()

    for left_index, left in enumerate(observations):
        left_coord = coordinate(left)
        if not left_coord:
            continue

        for right in observations[left_index + 1 :]:
            right_coord = coordinate(right)
            if (
                not right_coord
                or text(left.get("provider"))
                == text(right.get("provider"))
            ):
                continue

            for left_alias in alias_records(left):
                for right_alias in alias_records(right):
                    kind = ""
                    strength = ""

                    if (
                        left_alias["rawComparable"]
                        == right_alias["rawComparable"]
                    ):
                        kind = "ALIAS_EXACT"
                        strength = "exact"
                    else:
                        left_token = left_alias["normalized"]
                        right_token = right_alias["normalized"]

                        if (
                            left_token
                            and right_token
                            and left_token == right_token
                            and len(left_token) >= 4
                        ):
                            kind = "TOKEN_NORMALIZED_MATCH"
                            strength = "heuristic"
                        elif (
                            left_token
                            and right_token
                            and min(
                                len(left_token),
                                len(right_token),
                            )
                            >= 4
                            and (
                                left_token.endswith(right_token)
                                or right_token.endswith(left_token)
                            )
                        ):
                            kind = "TOKEN_SUFFIX_HEURISTIC"
                            strength = "heuristic"

                    if not kind:
                        continue

                    key = (
                        left_coord,
                        right_coord,
                        kind,
                        left_alias["kind"],
                        right_alias["kind"],
                    )
                    if key in seen:
                        continue
                    seen.add(key)

                    result.append(
                        {
                            "kind": kind,
                            "strength": strength,
                            "left": left_coord,
                            "right": right_coord,
                            "leftAliasKind": left_alias["kind"],
                            "leftValue": left_alias["value"],
                            "rightAliasKind": right_alias["kind"],
                            "rightValue": right_alias["value"],
                            "evidenceFamily": "alias",
                        }
                    )

    return result


def alias_collision_groups(
    observations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}

    for observation in observations:
        obs_coordinate = coordinate(observation)
        if not obs_coordinate:
            continue

        for alias in alias_records(observation):
            token = alias["normalized"]
            if len(token) < 4:
                continue

            group = groups.setdefault(
                token,
                {
                    "normalized": token,
                    "members": {},
                },
            )
            member = group["members"].setdefault(
                obs_coordinate,
                {
                    "coordinate": obs_coordinate,
                    "provider": text(observation.get("provider")),
                    "providerKey": text(observation.get("providerKey")),
                    "aliasKinds": [],
                    "rawValues": [],
                },
            )

            if alias["kind"] not in member["aliasKinds"]:
                member["aliasKinds"].append(alias["kind"])
            if alias["value"] not in member["rawValues"]:
                member["rawValues"].append(alias["value"])

    result: list[dict[str, Any]] = []
    for token in sorted(groups):
        members = list(groups[token]["members"].values())
        providers = {member["provider"] for member in members}
        if len(members) < 2 or len(providers) < 2:
            continue

        desktop_candidates = [
            member
            for member in members
            if member["provider"] == "DESKTOP_ENTRY"
        ]
        non_desktop = [
            member
            for member in members
            if member["provider"] != "DESKTOP_ENTRY"
        ]

        result.append(
            {
                "normalized": token,
                "members": members,
                "desktopCandidateCount": len(desktop_candidates),
                "hasNonDesktopEvidence": bool(non_desktop),
                "desktopAmbiguitySignal": (
                    len(desktop_candidates) > 1
                    and bool(non_desktop)
                ),
            }
        )

    return result


def provider_summary(
    observations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    counts: dict[str, int] = defaultdict(int)
    lifetimes: dict[str, set[str]] = defaultdict(set)

    for observation in observations:
        provider = text(observation.get("provider"))
        counts[provider] += 1
        lifetimes[provider].add(
            text(observation.get("lifetimeClass"))
        )

    return [
        {
            "provider": provider,
            "count": counts[provider],
            "lifetimes": sorted(lifetimes[provider]),
        }
        for provider in sorted(counts)
    ]


def analyze_fixture(data: dict[str, Any]) -> dict[str, Any]:
    observations = data.get("observations") or []

    return {
        "fixtureVersion": data.get("fixtureVersion"),
        "label": data.get("label"),
        "observationCount": len(observations),
        "providers": provider_summary(observations),
        "pidGroups": pid_groups(observations),
        "debugPortEdges": debug_port_edges(observations),
        "kittyEndpointEdges": kitty_endpoint_edges(observations),
        "aliasEdges": alias_edges(observations),
        "aliasCollisionGroups": alias_collision_groups(observations),
        "groundTruth": data.get("groundTruth") or {},
        "resolverVerdict": None,
    }


def print_human(report: dict[str, Any]) -> None:
    print(f"=== FIXTURE {report['label']} ===")
    print(f"observations: {report['observationCount']}")

    print("\nPROVIDERS")
    for item in report["providers"]:
        lifetimes = ",".join(item["lifetimes"])
        print(
            f"  {item['provider']}: "
            f"{item['count']} [{lifetimes}]"
        )

    print("\nPID GROUPS")
    if not report["pidGroups"]:
        print("  none")
    for group in report["pidGroups"]:
        members = ", ".join(
            member["coordinate"]
            for member in group["members"]
        )
        print(f"  pid {group['pid']}: {members}")

    print("\nDEBUG PORT EDGES")
    if not report["debugPortEdges"]:
        print("  none")
    for edge in report["debugPortEdges"]:
        print(
            f"  {edge['left']} -> {edge['right']} "
            f"port={edge['debugPort']}"
        )

    print("\nKITTY ENDPOINT EDGES")
    if not report["kittyEndpointEdges"]:
        print("  none")
    for edge in report["kittyEndpointEdges"]:
        print(
            f"  {edge['left']} -> {edge['right']} "
            f"endpoint={edge['kittyAddress']}"
        )

    print("\nALIAS COLLISION GROUPS")
    if not report["aliasCollisionGroups"]:
        print("  none")
    for group in report["aliasCollisionGroups"]:
        flag = (
            " DESKTOP_AMBIGUITY"
            if group["desktopAmbiguitySignal"]
            else ""
        )
        members = ", ".join(
            member["coordinate"]
            for member in group["members"]
        )
        print(
            f"  {group['normalized']}: "
            f"{members}{flag}"
        )

    print("\nRESOLVER")
    print("  none — diagnostic evidence only")


def synthetic_fixture() -> dict[str, Any]:
    return {
        "fixtureVersion": 1,
        "label": "synthetic-browser-ambiguity",
        "captureContext": {"notes": "analyzer self-test"},
        "observations": [
            {
                "provider": "DESKTOP_ENTRY",
                "providerKey": "desktop-entry:firefox.desktop",
                "lifetimeClass": "persistent",
                "generation": None,
                "raw": {"id": "firefox.desktop"},
                "aliases": [
                    {
                        "kind": "desktop-entry.id",
                        "value": "firefox.desktop",
                        "normalized": "firefox",
                        "provider": "DESKTOP_ENTRY",
                    }
                ],
                "relationships": [],
            },
            {
                "provider": "DESKTOP_ENTRY",
                "providerKey": (
                    "desktop-entry:org.mozilla.firefox.desktop"
                ),
                "lifetimeClass": "persistent",
                "generation": None,
                "raw": {"id": "org.mozilla.firefox.desktop"},
                "aliases": [
                    {
                        "kind": "desktop-entry.id-leaf",
                        "value": "firefox",
                        "normalized": "firefox",
                        "provider": "DESKTOP_ENTRY",
                    }
                ],
                "relationships": [],
            },
            {
                "provider": "SURFACE_LAUNCH",
                "providerKey": "surface-launch:demo",
                "lifetimeClass": "application-instance",
                "generation": 1,
                "raw": {
                    "correlationId": "demo",
                    "debugPort": 9222,
                },
                "aliases": [],
                "relationships": [],
            },
            {
                "provider": "SWAY",
                "providerKey": "sway-con:42",
                "lifetimeClass": "ephemeral",
                "generation": 1,
                "raw": {"pid": 5000, "appId": "firefox"},
                "aliases": [
                    {
                        "kind": "sway.app-id",
                        "value": "firefox",
                        "normalized": "firefox",
                        "provider": "SWAY",
                    }
                ],
                "relationships": [
                    {
                        "kind": "EXACT_PID",
                        "targetProvider": "PROCFS",
                        "targetKey": "pid:5000",
                        "strength": "exact",
                        "sourceField": "pid",
                    }
                ],
            },
            {
                "provider": "PROCFS",
                "providerKey": "pid:5000",
                "lifetimeClass": "ephemeral",
                "generation": 1,
                "raw": {
                    "pid": 5000,
                    "args": (
                        "/usr/bin/firefox "
                        "--remote-debugging-port=9222"
                    ),
                },
                "aliases": [],
                "relationships": [],
            },
            {
                "provider": "PIPEWIRE",
                "providerKey": "sink-input:9",
                "lifetimeClass": "ephemeral",
                "generation": 1,
                "raw": {"applicationProcessId": "5000"},
                "aliases": [],
                "relationships": [],
            },
        ],
        "groundTruth": {
            "knownSameApplication": [],
            "knownDifferentApplication": [],
            "unknown": [],
        },
    }


def run_self_test() -> int:
    fixture = synthetic_fixture()
    validation_errors = validate_fixture(
        fixture,
        "<analyzer-self-test>",
    )
    if validation_errors:
        print(
            "SELF TEST FAIL: synthetic fixture invalid",
            file=sys.stderr,
        )
        for error in validation_errors:
            print("  " + error, file=sys.stderr)
        return 1

    report = analyze_fixture(fixture)

    if len(report["pidGroups"]) != 1:
        print(
            "SELF TEST FAIL: expected one correlated PID group",
            file=sys.stderr,
        )
        return 1

    if len(report["debugPortEdges"]) != 1:
        print(
            "SELF TEST FAIL: expected one debug-port edge",
            file=sys.stderr,
        )
        return 1

    ambiguous = [
        group
        for group in report["aliasCollisionGroups"]
        if group["desktopAmbiguitySignal"]
    ]
    if len(ambiguous) != 1:
        print(
            "SELF TEST FAIL: expected one DesktopEntry ambiguity signal",
            file=sys.stderr,
        )
        return 1

    if report["resolverVerdict"] is not None:
        print(
            "SELF TEST FAIL: analyzer emitted a resolver verdict",
            file=sys.stderr,
        )
        return 1

    print("Team 7 identity fixture analyzer SELF TEST PASS")
    return 0


def load_fixture(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("fixture root must be an object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("fixtures", nargs="*")
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable diagnostic reports",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="run analyzer contract checks without runtime fixtures",
    )
    args = parser.parse_args()

    if args.self_test:
        return run_self_test()

    if not args.fixtures:
        print(
            "No fixture paths supplied. T0 owns runtime fixture packaging; "
            "pass one or more validated fixture JSON files."
        )
        return 0

    reports: list[dict[str, Any]] = []

    for value in args.fixtures:
        path = Path(value)

        try:
            fixture = load_fixture(path)
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            print(f"FAIL {path}: {exc}", file=sys.stderr)
            return 1

        errors = validate_fixture(fixture, str(path))
        if errors:
            print(
                f"FAIL {path}: fixture contract validation failed",
                file=sys.stderr,
            )
            for error in errors:
                print("  " + error, file=sys.stderr)
            return 1

        reports.append(analyze_fixture(fixture))

    if args.json:
        print(json.dumps(reports, indent=2, sort_keys=True))
    else:
        for index, report in enumerate(reports):
            if index:
                print()
            print_human(report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
