import fcntl
import os
from pathlib import Path
import sys

def locked(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: return True
        return False
    finally: os.close(fd)

old,new,want_old,want_new,*pids=sys.argv[1:]
assert locked(old)==(want_old=="1"),"old lock mismatch"
assert locked(new)==(want_new=="1"),"new lock mismatch"
for pid in pids:
    assert pid.isdecimal() and int(pid)>1
    values={}
    for line in (Path("/proc")/pid/"smaps_rollup").read_text().splitlines():
        key,_,rest=line.partition(":")
        if key in ("Rss","Pss","SwapPss"):
            values[key]=int(rest.split()[0])
    assert set(values)=={"Rss","Pss","SwapPss"},values
    print("CUSTODY_HELPER_MEMORY",pid,values,flush=True)
print("CUSTODY_LOCK_WITNESS",want_old,want_new,flush=True)
