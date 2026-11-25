#!/usr/bin/env python3
"""Explicit disposable V2 reader process interface. No production activation."""
import argparse
import json
import os
from pathlib import Path
import sqlite3
import stat
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import git_map_isolated_candidate as v2
import git_map_history_index as index

SCHEMA="post-apollo-git-map-reader-v2-candidate"

def emit(result):
    print(json.dumps(result,ensure_ascii=True,separators=(",",":")),flush=True)

def main(argv=None):
    os.umask(0o077)
    if os.environ.get("POST_APOLLO_GIT_MAP_SMOKE")!="CI_DISPOSABLE_ONLY":
        print("Disposable candidate only.",file=sys.stderr)
        return 1
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base",type=Path,required=True)
    sub=parser.add_subparsers(dest="action",required=True)
    for action in ("info","page","locate","search","hold"):
        sp=sub.add_parser(action)
        sp.add_argument("repo_id")
        sp.add_argument("key")
        sp.add_argument("snapshot")
        if action=="page": sp.add_argument("start",type=int)
        if action=="locate": sp.add_argument("sha")
        if action=="search":
            sp.add_argument("query")
            sp.add_argument("start",type=int)
    args=parser.parse_args(argv)
    try:
        if args.action=="hold" and not stat.S_ISFIFO(os.fstat(sys.stdin.fileno()).st_mode):
            raise ValueError("lifetime pipe required")
        with v2.read(args.base,args.repo_id,args.key,args.snapshot) as (conn,m):
            if args.action=="hold":
                # The directory descriptor remains held by read() even after
                # the SQLite connection closes. No heartbeat, no open DB.
                conn.close()
                emit({"schema":SCHEMA,"status":"HELD","repoId":args.repo_id,
                      "key":args.key,"snapshot":m["snapshot"],"reclamationAllowed":False})
                if sys.stdin.buffer.read(1):
                    raise ValueError("unexpected lifetime channel data")
                return 0
            if args.action=="info": result=m
            elif args.action=="page": result=index.page(conn,args.snapshot,args.start)
            elif args.action=="locate": result=index.locate(conn,args.snapshot,args.sha)
            else: result=index.search(conn,args.snapshot,args.query,args.start)
            # Serialize and flush before relinquishing the finite shared lock.
            emit({"schema":SCHEMA,"status":"READY","repoId":args.repo_id,
                  "key":args.key,"snapshot":m["snapshot"],"reclamationAllowed":False,
                  "result":result})
        return 0
    except (OSError,ValueError,TypeError,KeyError,sqlite3.Error,subprocess.SubprocessError):
        print("V2 candidate reader unavailable; no generation changed.",file=sys.stderr)
        return 1

if __name__=="__main__":
    sys.exit(main())
