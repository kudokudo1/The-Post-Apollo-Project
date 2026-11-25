"""Fixture witness barrier, then exec the real fixed one-shot helper."""
import fcntl
import os
from pathlib import Path
import sys
import time

if os.environ.get("POST_APOLLO_QUEUE_PIPE_SMOKE") != "CI_DISPOSABLE_ONLY":
    raise SystemExit("Disposable fixture only")
root=Path(__file__).resolve().parent
if len(sys.argv)!=3 or sys.argv[1] not in {"GEN_SAVE","GEN_LOAD","GEN_ADVANCE"}:
    raise SystemExit("Unexpected fixture helper command")
if Path(sys.argv[2]) != root/"checkpoint":
    raise SystemExit("Unexpected fixture checkpoint path")
if sys.argv[1]=="GEN_ADVANCE":
    until=time.monotonic()+5
    while not (root/"advance.ready").is_file():
        if time.monotonic()>=until:
            raise SystemExit("No exact owner exit witness")
        time.sleep(.01)
    # Independent check: actual old owner released DB lifetime custody.
    with open(root/"private"/"queue.db","rb") as db:
        fcntl.flock(db.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        fcntl.flock(db.fileno(),fcntl.LOCK_UN)
os.execv(sys.executable,[sys.executable,"-B",str(root/"memory"/"memory_queue_checkpoint_io.py"),*sys.argv[1:]])
