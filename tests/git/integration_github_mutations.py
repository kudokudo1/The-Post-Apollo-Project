#!/usr/bin/env python3
"""Opt-in live GitHub mutation integration harness.

This script intentionally does nothing unless all safety gates are supplied.
Use a disposable/scratch repository only. It refuses the production
Taskbars // Post-Apollo repository by name.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import time

ENABLE = os.environ.get("POST_APOLLO_GITHUB_MUTATION_TESTS", "") == "1"
TARGET = os.environ.get("POST_APOLLO_GITHUB_MUTATION_TEST_REPO", "").strip()
CONFIRM = os.environ.get("POST_APOLLO_GITHUB_MUTATION_CONFIRM", "")
TEST_QUEUE = os.environ.get("POST_APOLLO_TEST_MERGE_QUEUE", "") == "1"
EXPECTED_CONFIRM = "I_UNDERSTAND_THIS_MUTATES_THE_SCRATCH_REPO"

PRODUCTION_REPOS = {
    "kudokudo1/taskbars-post-apollo",
}


def die(message: str) -> None:
    print("POST-APOLLO GITHUB MUTATION INTEGRATION // FAIL")
    print(message)
    raise SystemExit(1)


def run(*args: str, input_text: str | None = None) -> str:
    command = [str(arg) for arg in args]
    proc = subprocess.run(
        command,
        input=input_text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        rendered = " ".join(shlex.quote(part) for part in command)
        die(
            f"command failed ({proc.returncode}): {rendered}\n"
            f"{proc.stderr.strip() or proc.stdout.strip()}"
        )
    return proc.stdout.strip()


def api(path: str, method: str = "GET", fields: dict[str, str] | None = None) -> dict:
    args = ["gh", "api"]
    if method != "GET":
        args += ["--method", method]
    args.append(path)
    for key, value in (fields or {}).items():
        args += ["-f", f"{key}={value}"]
    output = run(*args)
    return json.loads(output or "{}")


def graphql(query: str, variables: dict[str, str | int]) -> dict:
    args = ["gh", "api", "graphql", "-f", f"query={query}"]
    for key, value in variables.items():
        flag = "-F" if isinstance(value, int) else "-f"
        args += [flag, f"{key}={value}"]
    return json.loads(run(*args) or "{}")


def number_from_url(url: str) -> int:
    try:
        return int(url.rstrip("/").split("/")[-1])
    except Exception as exc:
        die(f"could not recover number from {url!r}: {exc}")


def issue_readback(number: int) -> dict:
    return json.loads(
        run(
            "gh",
            "issue",
            "view",
            str(number),
            "--repo",
            TARGET,
            "--json",
            "number,title,body,state,url,labels,assignees,milestone,comments",
        )
    )


def pr_readback(number: int) -> dict:
    return json.loads(
        run(
            "gh",
            "pr",
            "view",
            str(number),
            "--repo",
            TARGET,
            "--json",
            "number,title,body,state,url,isDraft,headRefOid,headRefName,baseRefName,mergeable,mergeStateStatus,reviewDecision",
        )
    )


if not ENABLE:
    print(
        "POST-APOLLO GITHUB MUTATION INTEGRATION // SKIP // "
        "set POST_APOLLO_GITHUB_MUTATION_TESTS=1"
    )
    raise SystemExit(0)

if not TARGET or "/" not in TARGET:
    die("POST_APOLLO_GITHUB_MUTATION_TEST_REPO=owner/repo is required")

if TARGET.lower() in PRODUCTION_REPOS:
    die("refusing to mutate the production taskbars-post-apollo repository")

if CONFIRM != EXPECTED_CONFIRM:
    die(
        "explicit confirmation missing; set "
        f"POST_APOLLO_GITHUB_MUTATION_CONFIRM={EXPECTED_CONFIRM!r}"
    )

viewer = api("user").get("login", "")
if not viewer:
    die("could not resolve authenticated GitHub viewer")

repo_info = api(f"repos/{TARGET}")
default_branch = str(repo_info.get("default_branch") or "")
if not default_branch:
    die("target repository has no default branch")

stamp = str(int(time.time()))
branch = f"post-apollo-integration-{stamp}"
test_path = f".post-apollo-integration/{stamp}.txt"
issue_number = 0
pr_number = 0

print(f"TARGET // {TARGET}")
print(f"VIEWER // @{viewer}")
print(f"DEFAULT BRANCH // {default_branch}")

try:
    # ISSUE LIFECYCLE
    issue_url = run(
        "gh",
        "issue",
        "create",
        "--repo",
        TARGET,
        "--title",
        f"[integration] issue {stamp}",
        "--body",
        "Post-Apollo controlled Issue lifecycle integration test.",
    )
    issue_number = number_from_url(issue_url)

    run(
        "gh",
        "issue",
        "edit",
        str(issue_number),
        "--repo",
        TARGET,
        "--title",
        f"[integration] issue edited {stamp}",
        "--body",
        "Issue mutation readback body.",
    )
    run(
        "gh",
        "issue",
        "comment",
        str(issue_number),
        "--repo",
        TARGET,
        "--body",
        "Issue integration comment.",
    )
    issue = issue_readback(issue_number)
    assert issue["title"] == f"[integration] issue edited {stamp}"
    assert issue["body"] == "Issue mutation readback body."

    run(
        "gh",
        "issue",
        "close",
        str(issue_number),
        "--repo",
        TARGET,
        "--reason",
        "completed",
    )
    assert issue_readback(issue_number)["state"] == "CLOSED"

    run(
        "gh",
        "issue",
        "reopen",
        str(issue_number),
        "--repo",
        TARGET,
    )
    assert issue_readback(issue_number)["state"] == "OPEN"
    print("ISSUE LIFECYCLE // PASS")

    # PR LIFECYCLE: build a disposable branch directly through GitHub.
    base_ref = api(
        f"repos/{TARGET}/git/ref/heads/{default_branch}"
    )
    base_sha = str((base_ref.get("object") or {}).get("sha") or "")
    if not base_sha:
        die("could not resolve default-branch head")

    api(
        f"repos/{TARGET}/git/refs",
        "POST",
        {
            "ref": f"refs/heads/{branch}",
            "sha": base_sha,
        },
    )
    api(
        f"repos/{TARGET}/contents/{test_path}",
        "PUT",
        {
            "message": f"integration fixture {stamp}",
            "content": "cG9zdC1hcG9sbG8taW50ZWdyYXRpb24KbGluZS0yCg==",
            "branch": branch,
        },
    )

    pr_url = run(
        "gh",
        "pr",
        "create",
        "--repo",
        TARGET,
        "--draft",
        "--head",
        branch,
        "--base",
        default_branch,
        "--title",
        f"[integration] PR {stamp}",
        "--body",
        "Post-Apollo controlled PR lifecycle integration test.",
    )
    pr_number = number_from_url(pr_url)
    assert pr_readback(pr_number)["isDraft"] is True

    run("gh", "pr", "ready", str(pr_number), "--repo", TARGET)
    run(
        "gh",
        "pr",
        "edit",
        str(pr_number),
        "--repo",
        TARGET,
        "--title",
        f"[integration] PR edited {stamp}",
        "--body",
        "PR mutation readback body.",
    )
    run(
        "gh",
        "pr",
        "comment",
        str(pr_number),
        "--repo",
        TARGET,
        "--body",
        "PR integration comment.",
    )
    pr = pr_readback(pr_number)
    assert pr["title"] == f"[integration] PR edited {stamp}"
    assert pr["body"] == "PR mutation readback body."
    assert pr["isDraft"] is False
    print("PR LIFECYCLE // PASS")

    # REVIEW THREAD: create an inline top-level comment on the added file.
    comment = api(
        f"repos/{TARGET}/pulls/{pr_number}/comments",
        "POST",
        {
            "body": "Inline review-thread integration fixture.",
            "commit_id": str(pr["headRefOid"]),
            "path": test_path,
            "line": "1",
            "side": "RIGHT",
        },
    )
    top_comment_id = str(comment.get("id") or "")
    top_comment_node = str(comment.get("node_id") or "")
    if not top_comment_id or not top_comment_node:
        die("review comment did not return stable identities")

    owner, name = TARGET.split("/", 1)
    thread_query = (
        "query($owner:String!,$name:String!,$number:Int!){"
        "repository(owner:$owner,name:$name){"
        "pullRequest(number:$number){reviewThreads(first:100){nodes{"
        "id isResolved viewerCanReply viewerCanResolve viewerCanUnresolve "
        "comments(first:100){totalCount nodes{id fullDatabaseId body}}"
        "}}}}}"
    )
    thread_payload = graphql(
        thread_query,
        {"owner": owner, "name": name, "number": pr_number},
    )
    nodes = (
        thread_payload.get("data", {})
        .get("repository", {})
        .get("pullRequest", {})
        .get("reviewThreads", {})
        .get("nodes", [])
    )
    thread = None
    for candidate in nodes:
        comments = (candidate.get("comments") or {}).get("nodes") or []
        if any(str(row.get("id") or "") == top_comment_node for row in comments):
            thread = candidate
            break
    if not thread:
        die("fresh GraphQL readback could not locate created review thread")

    thread_id = str(thread.get("id") or "")
    api(
        f"repos/{TARGET}/pulls/{pr_number}/comments/{top_comment_id}/replies",
        "POST",
        {"body": "Inline review-thread reply integration fixture."},
    )

    resolve_mutation = (
        "mutation($threadId:ID!){"
        "resolveReviewThread(input:{threadId:$threadId}){"
        "thread{id isResolved}}}"
    )
    resolved = graphql(resolve_mutation, {"threadId": thread_id})
    assert (
        resolved.get("data", {})
        .get("resolveReviewThread", {})
        .get("thread", {})
        .get("isResolved")
        is True
    )

    unresolve_mutation = (
        "mutation($threadId:ID!){"
        "unresolveReviewThread(input:{threadId:$threadId}){"
        "thread{id isResolved}}}"
    )
    unresolved = graphql(unresolve_mutation, {"threadId": thread_id})
    assert (
        unresolved.get("data", {})
        .get("unresolveReviewThread", {})
        .get("thread", {})
        .get("isResolved")
        is False
    )
    print("REVIEW THREAD LIFECYCLE // PASS")

    # MERGE QUEUE is optional because a scratch repository may not have one.
    queue_query = (
        "query($owner:String!,$name:String!,$branch:String!){"
        "repository(owner:$owner,name:$name){"
        "mergeQueue(branch:$branch){id url}}}"
    )
    queue_payload = graphql(
        queue_query,
        {"owner": owner, "name": name, "branch": default_branch},
    )
    queue = (
        queue_payload.get("data", {})
        .get("repository", {})
        .get("mergeQueue")
    )

    if queue and TEST_QUEUE:
        current = pr_readback(pr_number)
        enqueue = (
            "mutation($pullRequestId:ID!,$expectedHeadOid:GitObjectID!){"
            "enqueuePullRequest(input:{pullRequestId:$pullRequestId,"
            "expectedHeadOid:$expectedHeadOid,jump:false}){"
            "mergeQueueEntry{id state pullRequest{number}}}}"
        )
        pr_node = graphql(
            "query($owner:String!,$name:String!,$number:Int!){"
            "repository(owner:$owner,name:$name){pullRequest(number:$number){id}}}",
            {"owner": owner, "name": name, "number": pr_number},
        )
        pr_id = (
            pr_node.get("data", {})
            .get("repository", {})
            .get("pullRequest", {})
            .get("id", "")
        )
        queued = graphql(
            enqueue,
            {
                "pullRequestId": pr_id,
                "expectedHeadOid": str(current["headRefOid"]),
            },
        )
        entry = (
            queued.get("data", {})
            .get("enqueuePullRequest", {})
            .get("mergeQueueEntry")
        )
        if not entry:
            die("merge queue enqueue did not return an entry")

        dequeue = (
            "mutation($id:ID!){"
            "dequeuePullRequest(input:{id:$id}){"
            "mergeQueueEntry{id state}}}"
        )
        graphql(dequeue, {"id": pr_id})
        print("MERGE QUEUE ENQUEUE/DEQUEUE // PASS")
    elif queue:
        print(
            "MERGE QUEUE // SKIP MUTATION // "
            "set POST_APOLLO_TEST_MERGE_QUEUE=1 to enable"
        )
    else:
        print("MERGE QUEUE // SKIP // target branch has no native queue")

    print("POST-APOLLO GITHUB MUTATION INTEGRATION // PASS")

finally:
    # Leave durable evidence but close active work and remove disposable ref.
    if pr_number:
        subprocess.run(
            ["gh", "pr", "close", str(pr_number), "--repo", TARGET],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    if issue_number:
        subprocess.run(
            ["gh", "issue", "close", str(issue_number), "--repo", TARGET],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    subprocess.run(
        [
            "gh",
            "api",
            "--method",
            "DELETE",
            f"repos/{TARGET}/git/refs/heads/{branch}",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
