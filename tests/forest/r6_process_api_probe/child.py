#!/usr/bin/env python3
"""CI-only fixed byte-stream probe; no Runtime, model, DB or external input."""
import os
import signal
import sys
import time

if len(sys.argv) != 2 or os.environ.get("FOREST_PROBE_ONLY") != "1":
    sys.exit(2)
if "FOREST_PROBE_PARENT_SENTINEL" in os.environ:
    sys.exit(3)
if os.getcwd() != os.environ.get("HOME") or os.getcwd() != os.environ.get("TMPDIR"):
    sys.exit(4)
mode = sys.argv[1]
if mode == "terminate":
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
# Independent finite fallback even if parent fails to reap.
signal.alarm(8)
if sys.stdin.buffer.read(3) != b"GO\n":
    sys.exit(5)
if mode == "fragments":
    os.write(1, b"FRAG")
    # Second write cannot occur until parent observes first bytes.
    if sys.stdin.buffer.read(5) != b"CONT\n":
        sys.exit(6)
    os.write(1, b"MENT\nPAIR1\nPAIR2\n")
elif mode == "boundary":
    os.write(1, b"A" * 16383 + b"\n")
elif mode == "overflow":
    os.write(1, b"A" * 16384)
elif mode == "trailing":
    os.write(1, b"CLOSE\nEXTRA\n")
elif mode == "partial":
    os.write(1, b"PARTIAL")
elif mode == "nonascii":
    os.write(1, b"A\xc3\xa9\n")
elif mode == "stderr":
    os.write(2, b"FIXED TEST ERROR\n")
elif mode == "terminate":
    os.write(1, b"READY\n")
    time.sleep(7)
    sys.exit(7)
else:
    sys.exit(8)
