#!/usr/bin/env python3

import argparse
import subprocess
from collections import OrderedDict
from pathlib import Path


SECTIONS = OrderedDict([
    ("Added", []),
    ("Changed", []),
    ("Fixed", []),
    ("Removed", []),
    ("Continuity / Provenance", []),
])


def git(*args):
    return subprocess.check_output(
        ["git", *args],
        text=True,
        stderr=subprocess.DEVNULL,
    ).strip()


def ref_exists(ref):
    try:
        git("rev-parse", "--verify", ref)
        return True
    except subprocess.CalledProcessError:
        return False


def auto_base(head):
    try:
        return git("describe", "--tags", "--abbrev=0", f"{head}^")
    except subprocess.CalledProcessError:
        return ""


def classify(subject, body):
    text = f"{subject}\n{body}".lower().strip()

    fixed = ("fix", "bug", "repair", "regression", "correct", "resolve")
    removed = ("remove", "delete", "retire", "deprecate", "drop")
    added = ("add", "feat", "feature", "introduce", "implement", "create", "new ")
    continuity = (
        "provenance", "continuity", "history", "archive", "migrate",
        "migration", "rename", "restore", "rebase", "cherry-pick",
        "cherry pick", "backfill", "lineage"
    )

    if any(word in text for word in fixed):
        return "Fixed"
    if any(word in text for word in removed):
        return "Removed"
    if any(word in text for word in continuity):
        return "Continuity / Provenance"
    if any(word in text for word in added):
        return "Added"
    return "Changed"


def collect_commits(base, head, limit):
    if base:
        revision = f"{base}..{head}"
    else:
        revision = head

    raw = git(
        "log",
        "--no-merges",
        f"--max-count={limit}",
        "--date=short",
        "--pretty=format:%H%x1f%ad%x1f%s%x1f%b%x1e",
        revision,
    )

    commits = []
    for record in raw.split("\x1e"):
        record = record.strip()
        if not record:
            continue

        parts = record.split("\x1f", 3)
        if len(parts) < 3:
            continue

        sha = parts[0].strip()
        date = parts[1].strip()
        subject = parts[2].strip()
        body = parts[3].strip() if len(parts) > 3 else ""

        commits.append({
            "sha": sha,
            "date": date,
            "subject": subject,
            "body": body,
        })

    return commits


def render(base, head, commits):
    for commit in commits:
        section = classify(commit["subject"], commit["body"])
        SECTIONS[section].append(commit)

    head_sha = git("rev-parse", "--short=10", head)
    if base:
        base_sha = git("rev-parse", "--short=10", base)
        range_text = f"{base} ({base_sha}) → {head} ({head_sha})"
    else:
        range_text = f"recent history ending at {head} ({head_sha})"

    lines = [
        "# PATCH NOTES // DRAFT",
        "",
        "> Generated from Git history as a **review draft**.",
        "> Nothing here is published automatically. Edit, reorder, combine, or delete entries before using them as release notes.",
        "",
        f"**Range:** {range_text}",
        f"**Commits inspected:** {len(commits)}",
        "",
    ]

    for title, rows in SECTIONS.items():
        lines.append(f"## {title}")
        lines.append("")

        if not rows:
            lines.append("_No draft entries._")
            lines.append("")
            continue

        for row in rows:
            lines.append(
                f"- {row['subject']} "
                f"(\`{row['sha'][:8]}\`, {row['date']})"
            )
        lines.append("")

    lines.extend([
        "## CURATION NOTES",
        "",
        "- Combine multiple implementation commits when they describe one meaningful user-facing transformation.",
        "- Rewrite commit-language into patch-note language where useful.",
        "- Move entries between sections when the heuristic guessed wrong.",
        "- Delete internal churn that does not matter to a person using or understanding the project.",
        "- Preserve continuity, provenance, and migration notes when they help explain how the project changed.",
        "",
        "**A patch note records the transformation that matters, not every motion required to produce it.**",
        "",
    ])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="")
    parser.add_argument("--head", default="main")
    parser.add_argument("--max-commits", type=int, default=150)
    parser.add_argument("--output", default="patch-notes-draft.md")
    args = parser.parse_args()

    head = args.head.strip() or "main"
    if not ref_exists(head):
        raise SystemExit(f"Head ref does not exist: {head}")

    base = args.base.strip()
    if base and not ref_exists(base):
        raise SystemExit(f"Base ref does not exist: {base}")

    if not base:
        base = auto_base(head)

    commits = collect_commits(base, head, max(1, args.max_commits))
    output = Path(args.output)
    output.write_text(render(base, head, commits), encoding="utf-8")

    print(f"PATCH NOTES DRAFT // {output}")
    print(f"BASE // {base or 'AUTO RECENT HISTORY'}")
    print(f"HEAD // {head}")
    print(f"COMMITS // {len(commits)}")


if __name__ == "__main__":
    main()
