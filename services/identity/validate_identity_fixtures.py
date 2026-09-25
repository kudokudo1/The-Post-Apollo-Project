#!/usr/bin/env python3
"""Validate Team 7 cross-provider identity fixture bundles.

This is a fixture contract validator, not an identity resolver. It verifies that
captured evidence preserves provenance and does not smuggle a canonical identity
decision into provider observations.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ALLOWED_LIFETIMES = {
    "persistent",
    "session",
    "application-instance",
    "ephemeral",
}

FORBIDDEN_IDENTITY_FIELDS = {
    "canonicalId",
    "canonical_id",
    "semanticKey",
    "semantic_key",
    "applicationEntity",
    "application_entity",
}

REQUIRED_OBSERVATION_FIELDS = {
    "provider",
    "providerKey",
    "lifetimeClass",
    "raw",
    "aliases",
    "relationships",
}


def fail(errors: list[str], where: str, message: str) -> None:
    errors.append(f"{where}: {message}")


def as_object(
    value: Any,
    errors: list[str],
    where: str,
) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        fail(errors, where, "expected object")
        return None
    return value


def as_list(
    value: Any,
    errors: list[str],
    where: str,
) -> list[Any] | None:
    if not isinstance(value, list):
        fail(errors, where, "expected array")
        return None
    return value


def check_forbidden_fields(
    value: dict[str, Any],
    errors: list[str],
    where: str,
) -> None:
    for field in sorted(FORBIDDEN_IDENTITY_FIELDS):
        if field in value:
            fail(
                errors,
                where,
                f"forbidden semantic-identity field {field!r}",
            )


def validate_alias(
    alias: Any,
    errors: list[str],
    where: str,
) -> None:
    obj = as_object(alias, errors, where)
    if obj is None:
        return

    check_forbidden_fields(obj, errors, where)

    for field in ("kind", "value"):
        if not isinstance(obj.get(field), str) or not obj[field]:
            fail(errors, where, f"{field} must be a non-empty string")

    if "normalized" in obj and not isinstance(obj["normalized"], str):
        fail(errors, where, "normalized must be a string when present")

    if "provider" in obj and not isinstance(obj["provider"], str):
        fail(errors, where, "provider must be a string when present")


def validate_relationship(
    relationship: Any,
    errors: list[str],
    where: str,
) -> None:
    obj = as_object(relationship, errors, where)
    if obj is None:
        return

    check_forbidden_fields(obj, errors, where)

    for field in ("kind", "targetProvider", "targetKey", "strength"):
        if not isinstance(obj.get(field), str) or not obj[field]:
            fail(errors, where, f"{field} must be a non-empty string")

    strength = obj.get("strength")
    if isinstance(strength, str) and strength not in {"exact", "heuristic"}:
        fail(
            errors,
            where,
            "strength must be 'exact' or 'heuristic'",
        )

    if "sourceField" in obj and not isinstance(obj["sourceField"], str):
        fail(errors, where, "sourceField must be a string when present")


def validate_observation(
    observation: Any,
    errors: list[str],
    where: str,
) -> tuple[str, str] | None:
    obj = as_object(observation, errors, where)
    if obj is None:
        return None

    check_forbidden_fields(obj, errors, where)

    missing = sorted(REQUIRED_OBSERVATION_FIELDS - set(obj))
    if missing:
        fail(
            errors,
            where,
            "missing fields: " + ", ".join(missing),
        )

    provider = obj.get("provider")
    provider_key = obj.get("providerKey")
    lifetime = obj.get("lifetimeClass")

    if not isinstance(provider, str) or not provider:
        fail(errors, where, "provider must be a non-empty string")

    if not isinstance(provider_key, str):
        fail(errors, where, "providerKey must be a string")

    if lifetime not in ALLOWED_LIFETIMES:
        fail(
            errors,
            where,
            "lifetimeClass must be one of "
            + ", ".join(sorted(ALLOWED_LIFETIMES)),
        )

    raw = obj.get("raw")
    if not isinstance(raw, dict):
        fail(errors, where, "raw must be an object")
    else:
        check_forbidden_fields(raw, errors, where + ".raw")

    aliases = as_list(obj.get("aliases"), errors, where + ".aliases")
    if aliases is not None:
        for index, alias in enumerate(aliases):
            validate_alias(
                alias,
                errors,
                f"{where}.aliases[{index}]",
            )

    relationships = as_list(
        obj.get("relationships"),
        errors,
        where + ".relationships",
    )
    if relationships is not None:
        for index, relationship in enumerate(relationships):
            validate_relationship(
                relationship,
                errors,
                f"{where}.relationships[{index}]",
            )

    if "generation" in obj:
        generation = obj["generation"]
        if (
            generation is not None
            and not isinstance(generation, (int, float, str))
        ):
            fail(
                errors,
                where,
                "generation must be null, number, or string",
            )

    if (
        isinstance(provider, str)
        and provider
        and isinstance(provider_key, str)
        and provider_key
    ):
        return provider, provider_key

    return None


def validate_ground_truth(
    ground_truth: Any,
    errors: list[str],
    where: str,
) -> None:
    obj = as_object(ground_truth, errors, where)
    if obj is None:
        return

    check_forbidden_fields(obj, errors, where)

    for field in (
        "knownSameApplication",
        "knownDifferentApplication",
        "unknown",
    ):
        if field not in obj:
            fail(errors, where, f"missing {field}")
            continue

        values = as_list(obj[field], errors, f"{where}.{field}")
        if values is None:
            continue

        for index, value in enumerate(values):
            if not isinstance(value, (str, list, dict)):
                fail(
                    errors,
                    f"{where}.{field}[{index}]",
                    "annotation must be a string, array, or object",
                )


def validate_fixture(data: Any, source: str) -> list[str]:
    errors: list[str] = []
    root = as_object(data, errors, source)
    if root is None:
        return errors

    check_forbidden_fields(root, errors, source)

    if root.get("fixtureVersion") != 1:
        fail(errors, source, "fixtureVersion must equal 1")

    label = root.get("label")
    if not isinstance(label, str) or not label.strip():
        fail(errors, source, "label must be a non-empty string")

    context = root.get("captureContext")
    if context is not None and not isinstance(context, dict):
        fail(errors, source, "captureContext must be an object when present")

    observations = as_list(
        root.get("observations"),
        errors,
        source + ".observations",
    )

    seen_coordinates: set[tuple[str, str]] = set()

    if observations is not None:
        for index, observation in enumerate(observations):
            coordinate = validate_observation(
                observation,
                errors,
                f"{source}.observations[{index}]",
            )

            if coordinate is None:
                continue

            if coordinate in seen_coordinates:
                fail(
                    errors,
                    f"{source}.observations[{index}]",
                    "duplicate provider/providerKey coordinate "
                    f"{coordinate[0]}|{coordinate[1]}",
                )
            else:
                seen_coordinates.add(coordinate)

    if "groundTruth" not in root:
        fail(errors, source, "missing groundTruth")
    else:
        validate_ground_truth(
            root["groundTruth"],
            errors,
            source + ".groundTruth",
        )

    return errors


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def fixture_paths(explicit: list[str]) -> list[Path]:
    if explicit:
        return [Path(item) for item in explicit]

    root = Path(__file__).resolve().parents[2]
    fixture_dir = root / "tests" / "identity" / "fixtures"

    return sorted(
        path
        for path in fixture_dir.glob("*.json")
        if not path.name.endswith(".synthetic.json")
    )


def run_self_test() -> int:
    valid = {
        "fixtureVersion": 1,
        "label": "synthetic-valid",
        "captureContext": {},
        "observations": [
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
                "provider": "PROCFS",
                "providerKey": "pid:100",
                "lifetimeClass": "ephemeral",
                "generation": 1,
                "raw": {"pid": 100},
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

    invalid = json.loads(json.dumps(valid))
    invalid["observations"][0]["canonicalId"] = "forbidden"

    valid_errors = validate_fixture(valid, "<self-test-valid>")
    invalid_errors = validate_fixture(invalid, "<self-test-invalid>")

    if valid_errors:
        print("SELF TEST FAIL: valid fixture rejected", file=sys.stderr)
        for error in valid_errors:
            print("  " + error, file=sys.stderr)
        return 1

    if not any("canonicalId" in error for error in invalid_errors):
        print(
            "SELF TEST FAIL: canonicalId was not rejected",
            file=sys.stderr,
        )
        return 1

    print("Team 7 identity fixture validator SELF TEST PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "fixtures",
        nargs="*",
        help="fixture JSON paths; defaults to tests/identity/fixtures/*.json",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="run embedded validator checks without runtime fixtures",
    )
    args = parser.parse_args()

    if args.self_test:
        return run_self_test()

    paths = fixture_paths(args.fixtures)

    if not paths:
        print(
            "No runtime identity fixture JSON files found; "
            "contract validator has nothing to validate."
        )
        return 0

    failed = False

    for path in paths:
        try:
            data = load_json(path)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"FAIL {path}: {exc}", file=sys.stderr)
            failed = True
            continue

        errors = validate_fixture(data, str(path))

        if errors:
            failed = True
            print(f"FAIL {path}", file=sys.stderr)
            for error in errors:
                print("  " + error, file=sys.stderr)
        else:
            print(f"PASS {path}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
