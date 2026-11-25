#!/usr/bin/env python3
"""Explicit V2 manager process contract; production activation remains disabled."""
import argparse
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
import git_map_isolated_candidate as v2

def main(argv=None):
    os.umask(0o077)
    if os.environ.get("POST_APOLLO_GIT_MAP_SMOKE")!="CI_DISPOSABLE_ONLY":
        print("Disposable V2 manager only.",file=sys.stderr)
        return 1
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base",type=Path,required=True)
    parser.add_argument("action",choices=("lookup","build"))
    parser.add_argument("repo",type=Path)
    args=parser.parse_args(argv)
    try:
        if not args.repo.is_absolute() or args.repo.resolve(strict=True)!=args.repo:
            raise ValueError("canonical absolute repository required")
        v2.root_for(args.base)
        result=(v2.lookup if args.action=="lookup" else v2.build)(args.repo,args.base)
        if result["schema"]!=v2.PROTOCOL or result["reclamationAllowed"] is not False:
            raise ValueError("invalid manager disposition")
        if result["status"] not in ("READY","MISSING","CACHE LIMIT"):
            raise ValueError("invalid manager status")
        if args.action=="lookup" and result["status"]=="CACHE LIMIT":
            raise ValueError("invalid lookup disposition")
        print(json.dumps(result,ensure_ascii=True,separators=(",",":")),flush=True)
        return 0
    except (OSError,ValueError,TypeError,KeyError,sqlite3.Error,subprocess.SubprocessError):
        print("V2 manager unavailable; no fallback or automatic retry.",file=sys.stderr)
        return 1

if __name__=="__main__":
    sys.exit(main())
