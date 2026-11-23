#!/usr/bin/env python3
"""Source-only TimeW exact-value checks, including real SwayPX fraction 92.5.

No SwayPX runtime, local database, C5 grant, window movement or native restore.
"""
from dataclasses import replace
import math
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "services" / "time"))

import MachineGeometryV2 as capture_v2
import MachineGeometryStoreV2 as store_v2
import MachineV2GeometryJournal as journal_v2
from MachineV2ExactLogicalGeometry import (
    ExactGeometryRefused, ExactLogicalRect, VALUE_VERSION,
    PHASE_PENDING, PHASE_CURRENT, MIN_LAYOUT_COORD, MAX_LAYOUT_COORD,
    capture_value, read_value, exact_value_equal,
)

checks = 0


def check(ok, label):
    global checks
    assert ok, label
    checks += 1


def rejected(fn, label, expected=ExactGeometryRefused):
    global checks
    try:
        fn()
    except expected:
        checks += 1
    else:
        raise AssertionError(label + " incorrectly accepted")


def bits(number):
    return struct.unpack("=Q", struct.pack("=d", number))[0]


def make(phase=PHASE_PENDING, **values):
    original = dict(x=259.0, y=92.5, width=1402.0, height=872.0)
    original.update(values)
    return capture_value(phase, **original)


# Real mapped-XDG SwayPX #172 pending example; unlike an integer journal,
# a native value may have a half-unit logical coordinate.
pending = make()
check(type(pending) is ExactLogicalRect, "must be immutable typed value")
check(pending.version == VALUE_VERSION and pending.phase == PHASE_PENDING,
      "version and pending are kept")
check((pending.x_bits, pending.y_bits, pending.width_bits, pending.height_bits)
      == tuple(bits(v) for v in (259.0, 92.5, 1402.0, 872.0)),
      "all four IEEE754 value bit patterns preserved")
check(read_value(pending) == (259.0, 92.5, 1402.0, 872.0),
      "exact fractional readback")
check(exact_value_equal(pending, make()), "same-phase exact replay")
check(not exact_value_equal(pending, make(PHASE_CURRENT)),
      "pending is not current even if coordinates match")

# One ULP means unequal even if a rounded decimal UI would look identical.
one_ulp = math.nextafter(92.5, math.inf)
check(one_ulp != 92.5, "distinct binary64 fraction")
check(not exact_value_equal(pending, make(y=one_ulp)),
      "one ULP is not silently rounded")
check(pending.y_bits != make(y=one_ulp).y_bits,
      "single-ULP difference retained in bits")

# 256 deterministic half/eighth/fractional samples across all four fields.
for i in range(256):
    x = -900.0 + i / 8.0
    y = 0.25 + i / 16.0
    width = 100.0 + i / 4.0
    height = 300.0 + i / 2.0
    v = capture_value(PHASE_CURRENT, x=x, y=y,
                      width=width, height=height)
    check(tuple(bits(n) for n in read_value(v))
          == tuple(bits(n) for n in (x, y, width, height)),
          "exact fractional sample " + str(i))
    check(not exact_value_equal(v, replace(v, phase=PHASE_PENDING)),
          "phase differs for sample " + str(i))

# Coordinates allow fractions and signed 32-bit layout range, not physical px.
edge = capture_value(PHASE_CURRENT,
                     x=MIN_LAYOUT_COORD, y=MAX_LAYOUT_COORD,
                     width=MAX_LAYOUT_COORD, height=1.0)
check(read_value(edge) == (float(MIN_LAYOUT_COORD),
                           float(MAX_LAYOUT_COORD),
                           float(MAX_LAYOUT_COORD), 1.0),
      "finite boundary values supported")
fraction_size = make(x=-0.5, y=0.125, width=1.5, height=2.5)
check(read_value(fraction_size) == (-0.5, 0.125, 1.5, 2.5),
      "positive fractional dimensions are supported")

zero = make(x=-0.0, y=0.0)
check(zero.x_bits == 0 and zero.y_bits == 0,
      "negative zero canonicalizes to positive zero")
check(read_value(zero)[:2] == (0.0, 0.0), "canonical zero roundtrip")
rejected(lambda: read_value(replace(zero, x_bits=bits(-0.0))),
         "forged negative-zero x")
rejected(lambda: read_value(replace(zero, y_bits=bits(-0.0))),
         "forged negative-zero y")

# Both new input and raw forged immutable records reject invalid values.
for phase in (False, True, 0, 3, "PENDING", None):
    rejected(lambda p=phase: make(p), "invalid phase")
for name in ("x", "y", "width", "height"):
    for invalid in (float("nan"), math.inf, -math.inf, None, True, "92.5"):
        rejected(lambda k=name, value=invalid: make(**{k: value}),
                 "invalid raw value for " + name)
for name, invalid in (
    ("x", MIN_LAYOUT_COORD - 1),
    ("x", MAX_LAYOUT_COORD + 0.5),
    ("y", MIN_LAYOUT_COORD - 0.5),
    ("y", MAX_LAYOUT_COORD + 1),
    ("width", -1),
    ("width", 0),
    ("width", 0.5),
    ("width", MAX_LAYOUT_COORD + 1),
    ("height", -1),
    ("height", 0),
    ("height", 0.75),
    ("height", MAX_LAYOUT_COORD + 0.5),
):
    rejected(lambda k=name, v=invalid: make(**{k: v}),
             "out-of-range " + name)
rejected(lambda: make(x=10**1000), "huge integer overflow")

for bad in (
    replace(pending, version=2),
    replace(pending, version=True),
    replace(pending, phase=0),
    replace(pending, phase=True),
    replace(pending, y_bits=bits(float("nan"))),
    replace(pending, y_bits=bits(math.inf)),
    replace(pending, x_bits=bits(MAX_LAYOUT_COORD + 1.0)),
    replace(pending, width_bits=bits(-1.0)),
    replace(pending, height_bits=bits(0.5)),
    replace(pending, x_bits=-1),
    replace(pending, y_bits=2**64),
    replace(pending, width_bits=True),
    replace(pending, x_bits="not a bit pattern"),
):
    rejected(lambda value=bad: read_value(value),
             "malformed or forged value must refuse")
rejected(lambda: read_value({"version": 1}), "untyped dictionary refuse")
rejected(lambda: exact_value_equal(pending, replace(pending, phase=3)),
         "invalid comparison refuses")

# Legacy paths are intentionally NOT widened by this new additive module.
# It is safer to reject the live fractional native value than to truncate it.
legacy_rect = {"x": 259, "y": 92.5, "width": 1402, "height": 872}
rejected(lambda: capture_v2._rectangle(legacy_rect),
         "V2 projection still fail-closed", capture_v2.GeometryError)
rejected(lambda: store_v2._rect(legacy_rect),
         "V2 checkpoint store still fail-closed",
         store_v2.GeometryStoreError)
rejected(lambda: journal_v2._rect(legacy_rect),
         "V2 local journal still fail-closed",
         journal_v2.GeometryJournalError)

# No privileged machinery exists in this file and existing callers do not
# depend on or import the new module. This is deliberately only source values.
code = (ROOT / "services" / "time" / "MachineV2ExactLogicalGeometry.py").read_text()
for forbidden in (
    "import socket", "import subprocess", "import sqlite3",
    "swaymsg", "os.system", "execve", "if __name__",
    "Ed25519PrivateKey", "native_restore(", "command_runner",
    "from MachineV2FloatingPilot", "from MachineV2GeometryJournal",
):
    check(forbidden not in code, "privileged symbol forbidden: " + forbidden)
for old_path in (
    "MachineGeometryV2.py", "MachineGeometryStoreV2.py",
    "MachineV2GeometryJournal.py", "MachineV2SelectedSurfaceReview.py",
    "MachineV2FloatingPilot.py",
):
    old = (ROOT / "services" / "time" / old_path).read_text()
    check("MachineV2ExactLogicalGeometry" not in old,
          "no production or fixture consumer may load this lane yet")

print("TIMEW EXACT NATIVE GEOMETRY VALUES // "
      + str(checks) + " source-only checks PASS; native authority NOT TESTED")
