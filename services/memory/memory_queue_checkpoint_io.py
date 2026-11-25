"""Bounded one-shot host checkpoint adapter; no queue or kernel operations.

Trusted wrapper supplies an explicit existing private directory and fixed
SAVE or LOAD command. SAVE reads one complete record from stdin to EOF.
Success receipt is emitted only after HostCheckpoint.save returns. Caller
must require exit status zero AND exact correlated receipt, never retry.
"""
import sys

from memory_adjustment_queue import QueueError
from memory_queue_host_checkpoint import HostCheckpoint, MAX_BYTES
from memory_queue_pipe import decode, encode


def main(argv):
    if len(argv)!=2 or argv[0] not in {"SAVE","LOAD"}:
        raise QueueError("INVALID_CHECKPOINT_COMMAND")
    command,directory=argv
    store=HostCheckpoint(directory)
    data=sys.stdin.buffer.read(MAX_BYTES+1)
    if command=="LOAD":
        if data:
            raise QueueError("INVALID_CHECKPOINT_INPUT")
        result={"version":1,"kind":"CHECKPOINT_LOADED","snapshot":store.load(),
                "can_execute":False}
    else:
        if len(data)>MAX_BYTES or not data.endswith(b"\n"):
            raise QueueError("INVALID_CHECKPOINT_INPUT")
        record=decode(data[:-1])
        result={"version":1,"kind":"CHECKPOINT_SAVED","record":store.save(record),
                "can_execute":False}
    sys.stdout.buffer.write(encode(result))
    sys.stdout.buffer.flush()


if __name__=="__main__":
    try:
        main(sys.argv[1:])
    except (QueueError,OSError,ValueError,TypeError,RecursionError):
        print("CHECKPOINT_UNAVAILABLE",file=sys.stderr)
        raise SystemExit(1)
