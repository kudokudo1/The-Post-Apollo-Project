#!/usr/bin/env python3
"""Stage the compact holder in an explicit disposable scripts directory.

No system installation, replacement, shell reload, or production activation.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile

def main():
    if os.environ.get("POST_APOLLO_GIT_MAP_SMOKE")!="CI_DISPOSABLE_ONLY":
        raise SystemExit("Disposable staging only")
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage",type=Path)
    args=parser.parse_args()
    stage=args.stage
    if not stage.is_absolute() or stage.resolve(strict=True)!=stage:
        raise SystemExit("Canonical existing stage required")
    info=stage.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.getuid() or info.st_mode&0o022:
        raise SystemExit("Unsafe stage directory")
    source=Path(__file__).resolve().with_name("git_map_compact_holder.c")
    target=stage/"git_map_compact_holder"
    if os.path.lexists(target):
        raise SystemExit("Existing holder preserved")
    # Stage on the same filesystem; publish with atomic no-replace link.
    with tempfile.TemporaryDirectory(prefix=".compact-build-",dir=stage) as tmp:
        binary=Path(tmp)/"holder"
        subprocess.run(["cc","-std=c11","-O2","-Wall","-Wextra","-Werror",
                        str(source),"-o",str(binary)],check=True)
        binary.chmod(0o755)
        digest=hashlib.sha256(binary.read_bytes()).hexdigest()
        with binary.open("rb") as f: os.fsync(f.fileno())
        os.link(binary,target,follow_symlinks=False)
    fd=os.open(stage,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try: os.fsync(fd)
    finally: os.close(fd)
    print(json.dumps({"status":"STAGED","path":str(target),"sha256":digest,
                      "productionActivation":False},separators=(",",":")))

if __name__=="__main__":
    main()
