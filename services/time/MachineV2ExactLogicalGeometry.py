"""TimeW Scope A: exact native logical-geometry VALUES, not native evidence.

Pure import-only, additive candidate. This module does not capture a SwayPX
window, read/write a checkpoint, speak any cross-process wire protocol, bind
a selection, check C3e/C4b, spend C5 consent, or authorize Restore.

The four coordinate bits are *in-process Python integer values*. They are
not approved serialized packet fields, signed evidence or stable database
schema. SwayPX #173 is a value-only draft; source/receipt semantics and a
canonical byte order remain separate owner decisions.

Existing V1/V2 saved geometry and the operation journal retain their
integer-only validators. Do not replace those validators with this module.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import struct

VALUE_VERSION = 1
PHASE_PENDING = 1
PHASE_CURRENT = 2
MIN_LAYOUT_COORD = -(2**31)
MAX_LAYOUT_COORD = (2**31) - 1
MAX_BITS = (2**64) - 1
PHASES = frozenset((PHASE_PENDING, PHASE_CURRENT))


class ExactGeometryRefused(ValueError):
    pass


def _refuse():
    raise ExactGeometryRefused("TIMEW EXACT GEOMETRY VALUE REFUSED")


@dataclass(frozen=True, slots=True)
class ExactLogicalRect:
    """Immutable untrusted binary64 value snapshot, never an authority token."""

    version: int
    phase: int
    x_bits: int
    y_bits: int
    width_bits: int
    height_bits: int


def _as_float(value):
    if type(value) not in (int, float):
        _refuse()
    try:
        number = float(value)
    except (ValueError, TypeError, OverflowError):
        _refuse()
    if not math.isfinite(number):
        _refuse()
    return number


def _bits(value):
    # '=' means native in-memory IEEE-754 bit-pattern reinterpretation,
    # as in C memcpy(double -> uint64_t). No byte stream is emitted.
    return struct.unpack("=Q", struct.pack("=d", value))[0]


def _number(bits):
    if type(bits) is not int or not 0 <= bits <= MAX_BITS:
        _refuse()
    return struct.unpack("=d", struct.pack("=Q", bits))[0]


def _values(x, y, width, height, *, from_bits):
    # All validation precedes any return: an invalid rectangle cannot be
    # partially consumed by a caller.
    if from_bits:
        dx, dy = _number(x), _number(y)
        dw, dh = _number(width), _number(height)
    else:
        dx, dy = _as_float(x), _as_float(y)
        dw, dh = _as_float(width), _as_float(height)

    if (not all(math.isfinite(v) for v in (dx, dy, dw, dh))
            or not MIN_LAYOUT_COORD <= dx <= MAX_LAYOUT_COORD
            or not MIN_LAYOUT_COORD <= dy <= MAX_LAYOUT_COORD
            or not 1.0 <= dw <= MAX_LAYOUT_COORD
            or not 1.0 <= dh <= MAX_LAYOUT_COORD):
        _refuse()

    if from_bits:
        # The bit representation must be unique. A forged -0.0 is not valid.
        if ((dx == 0.0 and math.copysign(1.0, dx) < 0)
                or (dy == 0.0 and math.copysign(1.0, dy) < 0)):
            _refuse()
    else:
        # Normalize -0.0 to +0.0 before capturing bits.
        if dx == 0.0:
            dx = 0.0
        if dy == 0.0:
            dy = 0.0

    return dx, dy, dw, dh


def capture_value(phase, *, x, y, width, height):
    """Capture a finite value with no implicit rounding or authority."""
    if type(phase) is not int or phase not in PHASES:
        _refuse()
    dx, dy, dw, dh = _values(x, y, width, height, from_bits=False)
    return ExactLogicalRect(
        version=VALUE_VERSION,
        phase=phase,
        x_bits=_bits(dx),
        y_bits=_bits(dy),
        width_bits=_bits(dw),
        height_bits=_bits(dh),
    )


def read_value(value):
    """Validate and return exact floats in (x, y, width, height) order.

    A caller-created or dataclasses.replace()-forged object is revalidated;
    merely possessing an ExactLogicalRect never means the compositor made it.
    """
    if (type(value) is not ExactLogicalRect
            or type(value.version) is not int
            or value.version != VALUE_VERSION
            or type(value.phase) is not int
            or value.phase not in PHASES):
        _refuse()
    return _values(
        value.x_bits, value.y_bits, value.width_bits, value.height_bits,
        from_bits=True,
    )


def exact_value_equal(left, right):
    """Strict version + phase + four-bit-pattern equality, not evidence."""
    read_value(left)
    read_value(right)
    return left == right
