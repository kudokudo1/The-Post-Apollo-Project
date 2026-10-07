#!/usr/bin/env python3

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "").strip()
TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()

LABELS = [
    ("type: bug", "D16041", "Something is broken or behaving incorrectly."),
    ("type: feature", "C74EC7", "A new capability or meaningful extension."),
    ("type: design", "F2BE4E", "Architecture, interaction, visual, or system design work."),
    ("type: docs", "55CFCA", "Documentation or explanatory material."),
    ("type: security", "D16041", "A security or expected-trust relationship concern."),
    ("type: experiment", "5B5FD4", "Exploratory work where the outcome is intentionally uncertain."),

    ("concept: relationship", "55CFCA", "Primarily concerns a relationship between people, tools, systems, or environments."),
    ("concept: continuity", "5B5FD4", "Primarily concerns preserving useful state, context, place, or capability through change."),
    ("concept: provenance", "F2BE4E", "Primarily concerns origin, history, attribution, evidence, or lineage."),
    ("concept: spirit", "C74EC7", "Primarily concerns what should remain recognizable through transformation."),

    ("state: needs-evidence", "F2BE4E", "Needs reproduction, logs, examples, measurements, or other supporting evidence."),
    ("state: blocked", "D16041", "Cannot currently proceed because a dependency or decision is unresolved."),
    ("state: ready", "55CFCA", "Ready for the next intended action."),
    ("state: needs-review", "C74EC7", "Ready for human review or judgment."),
    ("state: help-wanted", "5B5FD4", "Additional community help would be useful."),

    ("scope: upstream", "5B5FD4", "Primarily belongs to or depends on an upstream project."),
    ("scope: family", "C74EC7", "Affects multiple projects across the Post-Apollo family."),
    ("scope: local", "55CFCA", "Specific to this repository or its local implementation."),
]


def request(method, path, payload=None):
    url = f"https://api.github.com{path}"
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {TOKEN}",
        "User-Agent": "post-apollo-label-sync",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req) as response:
        raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else None


def all_labels():
    labels = []
    page = 1

    while True:
        batch = request(
            "GET",
            f"/repos/{REPOSITORY}/labels?per_page=100&page={page}",
        )
        labels.extend(batch)

        if len(batch) < 100:
            return labels
        page += 1


def main():
    if not REPOSITORY:
        raise SystemExit("GITHUB_REPOSITORY is required.")
    if not TOKEN:
        raise SystemExit("GITHUB_TOKEN is required.")

    current = all_labels()
    by_lower = {str(row.get("name", "")).lower(): row for row in current}

    created = 0
    updated = 0
    unchanged = 0

    for name, color, description in LABELS:
        existing = by_lower.get(name.lower())

        if existing is None:
            request(
                "POST",
                f"/repos/{REPOSITORY}/labels",
                {
                    "name": name,
                    "color": color,
                    "description": description,
                },
            )
            print(f"CREATE // {name}")
            created += 1
            continue

        same_name = str(existing.get("name", "")) == name
        same_color = str(existing.get("color", "")).lower() == color.lower()
        same_description = str(existing.get("description") or "") == description

        if same_name and same_color and same_description:
            print(f"KEEP // {name}")
            unchanged += 1
            continue

        old_name = str(existing.get("name", ""))
        encoded = urllib.parse.quote(old_name, safe="")
        request(
            "PATCH",
            f"/repos/{REPOSITORY}/labels/{encoded}",
            {
                "new_name": name,
                "color": color,
                "description": description,
            },
        )
        print(f"UPDATE // {old_name} -> {name}")
        updated += 1

    print(
        f"COMPLETE // {REPOSITORY} // "
        f"{created} CREATED // {updated} UPDATED // {unchanged} UNCHANGED"
    )


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        print(f"GITHUB API ERROR // {error.code} // {body}", file=sys.stderr)
        raise
