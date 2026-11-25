"""Bounded one-shot host checkpoint adapter; no queue or kernel operations.

Trusted wrapper supplies an explicit existing private directory and fixed
SAVE or LOAD command. SAVE reads one complete record from stdin to EOF.
Success receipt is emitted only after HostCheckpoint.save returns. Caller
must require exit status zero AND exact correlated receipt, never retry.
"""
import sys
import fcntl
import os

from memory_adjustment_queue import QueueError
from memory_queue_host_checkpoint import HostCheckpoint, MAX_BYTES, SLOTS
from memory_queue_checkpoint_generations import CheckpointGenerations
from memory_queue_pipe import decode, encode


def main(argv):
    if len(argv)!=2 or argv[0] not in {"SAVE","LOAD","GEN_LOAD","GEN_SAVE","GEN_ADVANCE"}:
        raise QueueError("INVALID_CHECKPOINT_COMMAND")
    command,directory=argv
    data=sys.stdin.buffer.read(MAX_BYTES+1)
    if len(data)>MAX_BYTES:
        raise QueueError("INVALID_CHECKPOINT_INPUT")
    if command.startswith("GEN_"):
        store=CheckpointGenerations(directory)
        if command=="GEN_LOAD":
            if data:
                raise QueueError("INVALID_CHECKPOINT_INPUT")
            result={"version":1,"kind":"CHECKPOINT_GENERATION_LOADED","snapshot":store.load(),
                    "can_execute":False}
        else:
            if not data.endswith(b"\n"):
                raise QueueError("INVALID_CHECKPOINT_INPUT")
            value=decode(data[:-1])
            field="record" if command=="GEN_SAVE" else "receipt"
            if set(value)!={"version","generation",field} or type(value["generation"]) is not int:
                raise QueueError("INVALID_CHECKPOINT_INPUT")
            generation=value["generation"]
            if command=="GEN_SAVE":
                result={"version":1,"kind":"CHECKPOINT_GENERATION_SAVED","generation":generation,
                        "record":store.save(generation,value["record"]),"can_execute":False}
            else:
                # Receipt provenance is the trusted wrapper's responsibility.
                # This helper is not a backend identity or authority check.
                next_generation=store.advance(generation,value["receipt"])
                result={"version":1,"kind":"CHECKPOINT_GENERATION_ADVANCED",
                        "generation":next_generation,"action_id":value["receipt"]["review"]["action_id"],
                        "startup_unlock":False,"can_execute":False}
    else:
        store=HostCheckpoint(directory)
        # Updated legacy helper refuses retained storage and shares the
        # cooperating root lock. Older installed writers must be retired.
        with store._directory() as fd:
            fcntl.flock(fd,fcntl.LOCK_EX)
            if set(os.listdir(fd))-set(SLOTS.values()):
                raise QueueError("CHECKPOINT_GENERATION_MODE_REQUIRED")
            if command=="LOAD":
                if data:
                    raise QueueError("INVALID_CHECKPOINT_INPUT")
                result={"version":1,"kind":"CHECKPOINT_LOADED","snapshot":store.load(),
                        "can_execute":False}
            else:
                if not data.endswith(b"\n"):
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
