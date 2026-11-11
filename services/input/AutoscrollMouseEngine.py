#!/usr/bin/env python3
"""Mouse-only autoscroll state machine, independent of Linux device access.

Events are passed in by one explicitly selected physical mouse. While active,
relative motion changes the Windows-style anchor displacement rather than moving
the real pointer. Tick output is Linux high-resolution wheel units (120 = one
wheel detent); the backend is responsible for device/focus/permission checks.
No keyboard reads, compositor commands, or file writes occur in this module.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Optional

BTN_LEFT = 272
BTN_RIGHT = 273
BTN_MIDDLE = 274
DEADZONE = 15.0
MAX_SPEED_PX_S = 2800.0
MAX_ACTIVE_S = 180.0
MAX_DELTA_MS = 100.0
PX_PER_NOTCH = 55.0


def speed(displacement: float) -> float:
    if not math.isfinite(displacement) or abs(displacement) <= DEADZONE:
        return 0.0
    distance = abs(displacement) - DEADZONE
    rate = 0.000008 * distance ** 2.2 * 1000.0
    return math.copysign(min(MAX_SPEED_PX_S, rate), displacement)


@dataclass
class MouseAutoscroll:
    active: bool = False
    anchor_target: Optional[str] = None
    start_time: float = 0.0
    dx: float = 0.0
    dy: float = 0.0
    wheel_remainder: float = 0.0
    hwheel_remainder: float = 0.0
    swallowed: set[int] = field(default_factory=set)
    generation: int = 0
    last_stop: str = "idle"

    def cancel(self, reason: str = "cancel") -> None:
        self.active = False
        self.anchor_target = None
        self.dx = self.dy = 0.0
        self.wheel_remainder = self.hwheel_remainder = 0.0
        self.generation += 1
        self.last_stop = reason

    def key_event(self, code: int, value: int, now: float,
                  target: Optional[str]) -> bool:
        """True means consume the mouse button, False means pass to uinput.

        Middle is reserved while the experimental service is explicitly
        running. Other clicks cancel and are consumed until button release,
        preventing a click at the still-anchored pointer from acting elsewhere.
        """
        if value not in (0, 1):
            return False
        if code == BTN_MIDDLE:
            if value == 1:
                if self.active:
                    self.cancel("middle_click")
                elif target:
                    self.active = True
                    self.anchor_target = target
                    self.start_time = now
                    self.dx = self.dy = 0.0
                    self.wheel_remainder = self.hwheel_remainder = 0.0
                    self.generation += 1
            return True
        if code in self.swallowed:
            if value == 0:
                self.swallowed.discard(code)
            return True
        if self.active and value == 1:
            self.cancel("other_button")
            self.swallowed.add(code)
            return True
        return False

    def motion(self, x: float, y: float) -> bool:
        """True means consume the physical pointer movement while active."""
        if not self.active:
            return False
        if not math.isfinite(x) or not math.isfinite(y):
            self.cancel("invalid_motion")
            return True
        self.dx = max(-1200.0, min(1200.0, self.dx + x))
        self.dy = max(-1200.0, min(1200.0, self.dy + y))
        return True

    def tick(self, now: float, dt_ms: float,
             target: Optional[str]) -> tuple[int, int]:
        """Return (vertical, horizontal) hi-res wheel units, or (0,0)."""
        if not self.active:
            return 0, 0
        if not target or target != self.anchor_target:
            self.cancel("focus_lost")
            return 0, 0
        if not math.isfinite(now) or now - self.start_time > MAX_ACTIVE_S:
            self.cancel("time_limit")
            return 0, 0
        if not math.isfinite(dt_ms) or not 0 < dt_ms <= MAX_DELTA_MS:
            self.cancel("stale_tick")
            return 0, 0
        self.wheel_remainder -= speed(self.dy) * dt_ms / 1000 * 120 / PX_PER_NOTCH
        self.hwheel_remainder += speed(self.dx) * dt_ms / 1000 * 120 / PX_PER_NOTCH
        vertical = math.trunc(self.wheel_remainder)
        horizontal = math.trunc(self.hwheel_remainder)
        self.wheel_remainder -= vertical
        self.hwheel_remainder -= horizontal
        return vertical, horizontal
