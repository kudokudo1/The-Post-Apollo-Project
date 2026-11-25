#!/usr/bin/env python3
"""Disposable/offline Git map candidate. No live GitW integration or Git writes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import subprocess
import sys
import tempfile
import uuid

SCHEMA = "post-apollo-git-map-index-v1"
PAGE = 128
MAX_ROWS = 1_000_000
MAX_LANES = 512
MAX_PARENTS = 64
MAX_FIELD = 65536
MAX_ROOTS = 10000
SHA = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")
SNAPSHOT = re.compile(r"[0-9a-f]{32}")
NAME = "history.sqlite3"


def valid_sha(value):
    return isinstance(value, str) and SHA.fullmatch(value) is not None


def git_env():
    # Do not accidentally inherit another worktree, injected Git config,
    # alternate object directory, or a request to fetch promised objects.
    env = {key: val for key, val in os.environ.items() if not key.startswith("GIT_")}
    env.update(GIT_OPTIONAL_LOCKS="0", GIT_NO_LAZY_FETCH="1",
               GIT_TERMINAL_PROMPT="0", GIT_NO_REPLACE_OBJECTS="1",
               LC_ALL="C")
    return env


def command(repo, *args):
    return ["/usr/bin/git", "-C", str(repo), "--no-replace-objects", *args]


def git_output(repo, *args, allow_missing=False):
    result = subprocess.run(command(repo, *args), env=git_env(),
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            timeout=30, check=False)
    if allow_missing and result.returncode == 1:
        return b""
    if result.returncode or len(result.stdout) > 2_000_000:
        raise ValueError("Git metadata unavailable")
    return result.stdout


def roots_for(repo):
    # Includes locally reachable refs, plus detached HEAD where applicable.
    roots = set(git_output(repo, "rev-list", "--all", "--no-walk").decode("ascii").split())
    head = git_output(repo, "rev-parse", "--verify", "--quiet", "HEAD^{commit}",
                      allow_missing=True).decode("ascii").strip()
    if head:
        roots.add(head)
    if len(roots) > MAX_ROOTS or any(not valid_sha(x) for x in roots):
        raise ValueError("unsupported tip set")
    return sorted(roots)


def shallow_for(repo):
    value = git_output(repo, "rev-parse", "--is-shallow-repository").strip()
    if value not in (b"true", b"false"):
        raise ValueError("shallow state unavailable")
    return value == b"true"


def fields(stream):
    """Read NUL-delimited fields without buffering the whole log."""
    pending = b""
    while True:
        block = stream.read(65536)
        if not block:
            if pending:
                raise ValueError("incomplete Git log framing")
            return
        pieces = (pending + block).split(b"\0")
        pending = pieces.pop()
        if len(pending) > MAX_FIELD:
            raise ValueError("Git metadata field exceeds bound")
        for piece in pieces:
            if len(piece) > MAX_FIELD:
                raise ValueError("Git metadata field exceeds bound")
            yield piece


def log_rows(repo, roots):
    if not roots:
        return
    with tempfile.TemporaryFile() as tips:
        tips.write(("\n".join(roots) + "\n").encode("ascii"))
        tips.seek(0)
        worker = subprocess.Popen(command(repo, "log", "--stdin", "--topo-order",
                                  "--no-decorate", "--no-show-signature", "--no-notes",
                                  "--no-color", "--no-patch", "-z",
                                  "--format=%H%x00%P%x00%ct%x00%an%x00%s"),
                                  stdin=tips, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, env=git_env())
        try:
            group = []
            for value in fields(worker.stdout):
                group.append(value)
                if len(group) != 5:
                    continue
                sha, parents, timestamp, author, subject = group
                group = []
                yield (sha.decode("ascii"), parents.decode("ascii").split(),
                       int(timestamp), author.decode("utf-8", "replace"),
                       subject.decode("utf-8", "replace"))
            if group or worker.wait(timeout=10):
                raise ValueError("Git log incomplete")
        finally:
            worker.stdout.close()
            if worker.poll() is None:
                worker.kill()
                worker.wait()


def schema(conn):
    conn.executescript("""
    CREATE TABLE manifest (document TEXT NOT NULL);
    CREATE TABLE commits (
        ordinal INTEGER PRIMARY KEY, sha TEXT NOT NULL UNIQUE,
        lane INTEGER NOT NULL, timestamp INTEGER NOT NULL,
        author TEXT NOT NULL, subject TEXT NOT NULL
    );
    CREATE TABLE edges (
        child INTEGER NOT NULL, position INTEGER NOT NULL,
        parent_sha TEXT NOT NULL, parent_lane INTEGER NOT NULL,
        PRIMARY KEY(child, position)
    );
    CREATE TABLE boundaries (
        ordinal INTEGER PRIMARY KEY, frontier TEXT NOT NULL
    );
    """)


def allocate(frontier, preferred=None):
    used = set(frontier.values())
    if preferred is not None and preferred not in used:
        return preferred
    for lane in range(MAX_LANES):
        if lane not in used:
            return lane
    raise ValueError("graph lane limit reached; index not published")


def fill(conn, rows, *, snapshot, repo_id, roots_digest, shallow):
    """Immutable ordinal order and lane assignment for one frozen snapshot."""
    schema(conn)
    frontier = {}
    total = 0
    max_lane = 0
    for sha, parents, timestamp, author, subject in rows:
        if (total >= MAX_ROWS or not valid_sha(sha)
                or not isinstance(parents, list) or len(parents) > MAX_PARENTS
                or len(set(parents)) != len(parents)
                or any(not valid_sha(p) or p == sha for p in parents)
                or not isinstance(timestamp, int) or timestamp < 0
                or not isinstance(author, str) or not isinstance(subject, str)):
            raise ValueError("unsupported commit record")
        if total % PAGE == 0:
            conn.execute("INSERT INTO boundaries VALUES (?,?)",
                         (total, json.dumps([{"sha": k, "lane": v}
                          for k, v in sorted(frontier.items(), key=lambda x:x[1])])))
        if sha in frontier:
            lane = frontier.pop(sha)
        else:
            lane = allocate(frontier)
        max_lane = max(max_lane, lane)
        # Display summaries only; no diffs, bodies, paths or recovery data.
        conn.execute("INSERT INTO commits VALUES (?,?,?,?,?,?)",
                     (total, sha, lane, timestamp, author[:256], subject[:1024]))
        # When the first parent is new, prefer continuity in the current lane.
        # An already-open parent keeps its original lane.
        for position, parent in enumerate(parents):
            if parent not in frontier:
                frontier[parent] = allocate(frontier, lane if position == 0 else None)
            parent_lane = frontier[parent]
            max_lane = max(max_lane, parent_lane)
            conn.execute("INSERT INTO edges VALUES (?,?,?,?)",
                         (total, position, parent, parent_lane))
        total += 1
    if frontier:
        raise ValueError("unresolved ancestry")
    invalid = conn.execute("""
        SELECT 1 FROM edges e LEFT JOIN commits p ON p.sha=e.parent_sha
        WHERE p.sha IS NULL OR p.ordinal<=e.child OR p.lane!=e.parent_lane LIMIT 1
        """).fetchone()
    if invalid:
        raise ValueError("invalid ancestry order or lane continuity")
    manifest = {"schema":SCHEMA, "snapshot":snapshot, "repoId":repo_id,
                "rootsDigest":roots_digest, "total":total, "pageSize":PAGE,
                "shallow":shallow, "maxLane":max_lane,
                "scope":"captured-local-ref-tips-and-head"}
    conn.execute("INSERT INTO manifest VALUES (?)", (json.dumps(manifest),))
    conn.commit()
    return manifest


def build(repo, destination):
    # Fresh, caller-selected candidate directory only. Never replace a live
    # database or another index. No repository configuration or refs change.
    repo = Path(repo).resolve(strict=True)
    common = git_output(repo, "rev-parse", "--path-format=absolute",
                        "--git-common-dir").strip()
    repo_id = hashlib.sha256(common).hexdigest()
    shallow = shallow_for(repo)
    roots = roots_for(repo)
    digest = hashlib.sha256("\n".join(roots).encode("ascii")).hexdigest()
    destination = Path(destination)
    destination.mkdir(mode=0o700, exist_ok=False)
    pending = destination / ".building.sqlite3"
    final = destination / NAME
    try:
        with sqlite3.connect(pending) as conn:
            conn.execute("PRAGMA journal_mode=DELETE")
            conn.execute("PRAGMA synchronous=FULL")
            result = fill(conn, log_rows(repo, roots), snapshot=uuid.uuid4().hex,
                          repo_id=repo_id, roots_digest=digest, shallow=shallow)
        conn.close()
        if roots_for(repo) != roots or shallow_for(repo) != shallow:
            raise ValueError("repository changed during build; retry explicit build")
        # Make completed candidate immutable by convention. Only new
        # generations are built; never append to a published generation.
        os.chmod(pending, 0o600)
        with pending.open("rb") as handle:
            os.fsync(handle.fileno())
        os.link(pending, final)  # no overwrite, even if a target appears late
        pending.unlink()
        fd = os.open(destination, os.O_DIRECTORY | os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
        return result
    except BaseException:
        # No destructive repair. The isolated incomplete directory is not
        # eligible for use; a subsequent build must use a fresh directory.
        raise


def open_index(directory):
    path = Path(directory) / NAME
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
            or info.st_mode & 0o077 or info.st_nlink != 1):
        raise ValueError("unsafe candidate index")
    conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")
    conn.execute("PRAGMA trusted_schema=OFF")
    return conn


def manifest_for(conn, snapshot=None):
    rows = conn.execute("SELECT document FROM manifest LIMIT 2").fetchall()
    if len(rows) != 1:
        raise ValueError("invalid manifest")
    m = json.loads(rows[0][0])
    if (m.get("schema") != SCHEMA or m.get("pageSize") != PAGE
            or not isinstance(m.get("total"), int) or not 0 <= m["total"] <= MAX_ROWS
            or not isinstance(m.get("snapshot"), str) or not SNAPSHOT.fullmatch(m["snapshot"])
            or (snapshot is not None and m["snapshot"] != snapshot)):
        raise ValueError("snapshot unavailable or mismatched")
    return m


def page(conn, snapshot, start):
    m = manifest_for(conn, snapshot)
    if type(start) is not int or start < 0 or start % PAGE or start >= m["total"]:
        raise ValueError("page outside indexed range")
    stop = min(start + PAGE, m["total"])
    rows = [dict(row) for row in conn.execute(
        "SELECT * FROM commits WHERE ordinal>=? AND ordinal<? ORDER BY ordinal",
        (start,stop))]
    if len(rows) != stop-start or any(row["ordinal"] != start+i for i,row in enumerate(rows)):
        raise ValueError("incomplete page")
    for row in rows:
        row["parents"] = [dict(edge) for edge in conn.execute("""
            SELECT e.position, e.parent_sha AS sha, p.ordinal, e.parent_lane AS lane
            FROM edges e JOIN commits p ON p.sha=e.parent_sha
            WHERE e.child=? ORDER BY e.position LIMIT ?
            """, (row["ordinal"], MAX_PARENTS+1))]
        if len(row["parents"]) > MAX_PARENTS:
            raise ValueError("invalid edge count")
    boundary = conn.execute("SELECT frontier FROM boundaries WHERE ordinal=?", (start,)).fetchone()
    if boundary is None:
        raise ValueError("missing boundary")
    return {"schema":SCHEMA, "snapshot":snapshot, "repoId":m["repoId"],
            "start":start, "total":m["total"], "rows":rows,
            "frontier":json.loads(boundary[0]), "end":stop==m["total"]}


def locate(conn, snapshot, sha):
    m = manifest_for(conn, snapshot)
    if not valid_sha(sha):
        raise ValueError("full SHA required")
    row = conn.execute("SELECT ordinal FROM commits WHERE sha=?", (sha,)).fetchone()
    return {"schema":SCHEMA,"snapshot":snapshot,"repoId":m["repoId"],
            "sha":sha,"ordinal":row[0] if row else None}


def search(conn, snapshot, query, start):
    """One literal match in frozen ordinal order; no history materialization."""
    m = manifest_for(conn, snapshot)
    if (not isinstance(query, str) or not query.strip() or len(query) > 128
            or len(query.encode("utf-8")) > 512 or any(ord(c) < 32 or ord(c) == 127 for c in query)
            or type(start) is not int or not 0 <= start <= m["total"]):
        raise ValueError("invalid search request")
    # SQLite lower() is ASCII-case-insensitive, otherwise literal. No LIKE
    # wildcards, regexp, shell or query-language interpretation.
    row = conn.execute("""
        SELECT ordinal, sha FROM commits
        WHERE ordinal>=? AND (instr(lower(sha),lower(?))>0
            OR instr(lower(author),lower(?))>0 OR instr(lower(subject),lower(?))>0)
        ORDER BY ordinal LIMIT 1
        """, (start,query,query,query)).fetchone()
    return {"schema":SCHEMA,"snapshot":snapshot,"repoId":m["repoId"],
            "query":query,"start":start,"match":dict(row) if row else None}


def main(argv=None):
    os.umask(0o077)
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="action", required=True)
    b = sub.add_parser("build")
    b.add_argument("repo")
    b.add_argument("directory")
    for action in ("info","page","locate","search"):
        sp = sub.add_parser(action)
        sp.add_argument("directory")
        if action != "info":
            sp.add_argument("snapshot")
        if action == "page":
            sp.add_argument("start",type=int)
        if action == "locate":
            sp.add_argument("sha")
        if action == "search":
            sp.add_argument("query")
            sp.add_argument("start",type=int)
    args = p.parse_args(argv)
    try:
        if args.action == "build":
            result = build(args.repo,args.directory)
        else:
            with open_index(args.directory) as conn:
                if args.action == "info":
                    result = manifest_for(conn)
                elif args.action == "page":
                    result = page(conn,args.snapshot,args.start)
                elif args.action == "locate":
                    result = locate(conn,args.snapshot,args.sha)
                else:
                    result = search(conn,args.snapshot,args.query,args.start)
            conn.close()
        print(json.dumps(result,ensure_ascii=True,separators=(",",":")))
        return 0
    except (OSError, ValueError, TypeError, KeyError, sqlite3.Error, subprocess.SubprocessError):
        print("Git map candidate unavailable; no live index changed.",file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
