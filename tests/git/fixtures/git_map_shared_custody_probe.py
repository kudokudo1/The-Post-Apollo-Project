#!/usr/bin/env python3
"""Independent lock and memory witness for disposable native host fixture."""
import fcntl
import os
from pathlib import Path
import signal
import sys

mode,directory,pid,snapshot,old=sys.argv[1:]
assert mode in ("held","overlap","kill")
assert pid.isdecimal() and int(pid)>1
pid=int(pid)
def locked(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: return True
        return False
    finally: os.close(fd)
assert locked(directory),"current generation not protected"
if old:
    assert locked(old)==(mode=="overlap"),"old generation lock incorrect"
proc=Path("/proc")/str(pid)
args=(proc/"cmdline").read_bytes().split(b"\0")
assert any(x.endswith(b"/scripts/git_map_reader_candidate.py") for x in args)
assert snapshot.encode() in args and Path(directory).name.encode() in args
values={}
for line in (proc/"smaps_rollup").read_text().splitlines():
    key,_,rest=line.partition(":")
    if key in ("Rss","Pss","SwapPss"):
        values[key]=int(rest.split()[0])
assert set(values)=={"Rss","Pss","SwapPss"}
print("SHARED_CUSTODY_KERNEL_MEMORY",mode,values,flush=True)
if mode=="kill":
    # pidfd binds the signal to this disposable helper rather than a reused PID.
    with_fd=os.pidfd_open(pid)
    try:
        assert (proc/"cmdline").read_bytes().split(b"\0")==args
        signal.pidfd_send_signal(with_fd,signal.SIGKILL)
    finally: os.close(with_fd)
print("SHARED_CUSTODY_KERNEL_WITNESS_PASS",mode,flush=True)
