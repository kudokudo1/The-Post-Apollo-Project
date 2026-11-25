#!/usr/bin/env python3
"""Offline candidate: reuse a verified unchanged suffix in a new Git map.

No integration into the automatic cache manager until proof and timings pass.
Git still supplies the complete ordered stream. No guess based only on HEAD.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parent))
import git_map_history_index as index

MAX_PREFIX = 512


class ReuseRefused(ValueError):
    pass


class VerifiedSuffix:
    """Use the existing fill algorithm as the authority for every row/edge.

    Intercept only its exact insert statements. Prefix records and boundaries
    are written normally; the immutable suffix is copied in two SQL statements
    and every would-be insert is compared with the prior ordered record.
    A mismatch aborts the candidate transaction, never the old generation.
    """
    COMMIT = "INSERT INTO commits VALUES (?,?,?,?,?,?)"
    EDGE = "INSERT INTO edges VALUES (?,?,?,?)"

    def __init__(self, conn, prior, repo_id):
        self.conn = conn
        self.offset = None
        self.verified = False
        prior = Path(prior)
        with index.open_index(prior) as old:
            m = index.manifest_for(old)
        old.close()
        if m.get("repoId") != repo_id or m.get("shallow") is not False or not m["total"]:
            raise ReuseRefused("prior identity or shallow state not eligible")
        conn.execute("ATTACH DATABASE ? AS prior", ((prior / index.NAME).resolve().as_uri()+"?mode=ro&immutable=1",))
        docs = conn.execute("SELECT document FROM prior.manifest LIMIT 2").fetchall()
        if len(docs) != 1 or json.loads(docs[0][0]) != m:
            raise ReuseRefused("prior manifest changed")
        self.total = m["total"]
        first = conn.execute("SELECT sha FROM prior.commits WHERE ordinal=0").fetchone()
        if first is None or not index.valid_sha(first[0]):
            raise ReuseRefused("prior head unavailable")
        self.first = first[0]
        self.commits = None
        self.edges = None

    def executescript(self, sql):
        return self.conn.executescript(sql)

    def begin_suffix(self, ordinal):
        if not 1 <= ordinal <= MAX_PREFIX:
            raise ReuseRefused("prefix length not eligible")
        self.offset = ordinal
        self.commits = iter(self.conn.execute(
            "SELECT ordinal,sha,lane,timestamp,author,subject FROM prior.commits ORDER BY ordinal"))
        self.edges = iter(self.conn.execute(
            "SELECT child,position,parent_sha,parent_lane FROM prior.edges ORDER BY child,position"))
        self.conn.execute("""INSERT INTO commits SELECT ordinal+?,sha,lane,timestamp,author,subject
                          FROM prior.commits ORDER BY ordinal""", (ordinal,))
        self.conn.execute("""INSERT INTO edges SELECT child+?,position,parent_sha,parent_lane
                          FROM prior.edges ORDER BY child,position""", (ordinal,))

    def compare(self, cursor, params):
        expected = next(cursor, None)
        if expected is None or (expected[0]+self.offset, *expected[1:]) != tuple(params):
            raise ReuseRefused("existing ordered commit metadata or lane/edge changed")

    def complete_proof(self):
        if self.offset is None or next(self.commits, None) is not None or next(self.edges, None) is not None:
            raise ReuseRefused("old suffix not completely verified")
        if self.conn.execute("SELECT count(*) FROM commits").fetchone()[0] != self.offset+self.total:
            raise ReuseRefused("old suffix count mismatch")
        self.verified = True

    def execute(self, sql, params=()):
        if sql == self.COMMIT:
            ordinal, sha = params[:2]
            if self.offset is None:
                if sha == self.first:
                    self.begin_suffix(ordinal)
                elif ordinal >= MAX_PREFIX:
                    raise ReuseRefused("old suffix not reached within prefix limit")
            if self.offset is not None:
                self.compare(self.commits, params)
                return
        elif sql == self.EDGE and self.offset is not None:
            self.compare(self.edges, params)
            return
        elif sql.lstrip().startswith("SELECT 1 FROM edges e LEFT JOIN commits"):
            self.complete_proof()
        return self.conn.execute(sql, params)

    def commit(self):
        if not self.verified:
            raise ReuseRefused("fill contract did not complete suffix proof")
        self.conn.commit()


def build(repo, prior, destination):
    repo = Path(repo).resolve(strict=True)
    repo_id = hashlib.sha256(index.git_output(repo, "rev-parse", "--path-format=absolute",
                                               "--git-common-dir").strip()).hexdigest()
    if index.shallow_for(repo):
        raise ReuseRefused("shallow repository requires full rebuild")
    roots = index.roots_for(repo)
    digest = hashlib.sha256("\n".join(roots).encode("ascii")).hexdigest()
    destination = Path(destination)
    destination.mkdir(mode=0o700, exist_ok=False)
    pending = destination / ".building.sqlite3"
    final = destination / index.NAME
    conn = sqlite3.connect(pending, uri=True)
    try:
        conn.execute("PRAGMA journal_mode=DELETE")
        conn.execute("PRAGMA synchronous=FULL")
        conn.execute("PRAGMA trusted_schema=OFF")
        sink = VerifiedSuffix(conn, prior, repo_id)
        rows = index.log_rows(repo, roots)
        try:
            manifest = index.fill(sink, rows, snapshot=uuid.uuid4().hex, repo_id=repo_id,
                                  roots_digest=digest, shallow=False)
        finally:
            rows.close()
        prefix = sink.offset
    finally:
        conn.close()
    if index.roots_for(repo) != roots or index.shallow_for(repo):
        raise ReuseRefused("repository changed during proof")
    os.chmod(pending, 0o600)
    with pending.open("rb") as handle:
        os.fsync(handle.fileno())
    os.link(pending, final)
    pending.unlink()
    fd = os.open(destination, os.O_DIRECTORY | os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return {"manifest": manifest, "prefixRows": prefix, "reusedRows": manifest["total"]-prefix}


def main(argv=None):
    os.umask(0o077)
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("repo", type=Path)
    p.add_argument("prior", type=Path)
    p.add_argument("destination", type=Path)
    args = p.parse_args(argv)
    try:
        print(json.dumps(build(args.repo, args.prior, args.destination), separators=(",",":")))
        return 0
    except ReuseRefused:
        print("Incremental proof refused; full rebuild required.", file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError, KeyError, sqlite3.Error, subprocess.SubprocessError):
        print("Incremental candidate unavailable; prior history preserved.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
