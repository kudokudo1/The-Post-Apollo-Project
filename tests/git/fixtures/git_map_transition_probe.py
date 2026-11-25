#!/usr/bin/env python3
"""Disposable witness; never changes a cache or a Git repository."""
import fcntl
import os
from pathlib import Path
import sys
import time

control=Path(os.environ["MAP_TRANSITION_CONTROL"])
mode,*paths=sys.argv[1:]
def locked(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: return True
        return False
    finally: os.close(fd)

if mode=="started":
    deadline=time.monotonic()+2
    while not (control/"started").exists():
        assert time.monotonic()<deadline,"finite reader did not reach locked function"
        time.sleep(.01)
    assert locked(paths[0])
elif mode=="pair-release":
    assert len(paths)==2 and paths[0]!=paths[1]
    assert all(locked(p) for p in paths),"transition lock missing"
    print("GIT_MAP_TRANSITION_KERNEL_PAIR_PASS",flush=True)
    (control/"release").touch()
elif mode=="final":
    assert locked(paths[0]) and not any(locked(p) for p in paths[1:]),"old generation still held"
    print("GIT_MAP_TRANSITION_KERNEL_FINAL_PASS",flush=True)
else:
    raise ValueError("unknown fixture command")
