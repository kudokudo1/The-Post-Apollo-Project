#!/usr/bin/env python3
"""Independent elapsed-time witness for an explicit UI heartbeat capture.

No process inspection, system modification, background daemon or persistent state.
The witness does not assert that the QML event loop was responsive.
"""
import argparse
import json
import time


def observe(duration):
    if type(duration) is not int or not 5 <= duration <= 120:
        raise ValueError("invalid stall capture duration")
    started = time.monotonic_ns()
    wall_start = time.time_ns()
    time.sleep(duration)
    wall_end = time.time_ns()
    elapsed = (time.monotonic_ns() - started) // 1_000_000
    return {"schema":"post-apollo-stall-clock-v1",
            "durationSeconds":duration,
            "startWallMs":wall_start // 1_000_000,
            "endWallMs":wall_end // 1_000_000,
            "elapsedMs":elapsed}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration",required=True,type=int,choices=range(5,121))
    args=parser.parse_args()
    print(json.dumps(observe(args.duration),separators=(",",":")),flush=True)


if __name__=="__main__":
    main()
