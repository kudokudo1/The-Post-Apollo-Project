.pragma library

// Camera Cleanup Hunt M3b. This module performs visual movement ONLY.
// It never reads a filesystem path, executes a command, or marks Trash.
var PROFILES = ["bird", "frog", "deer", "ox", "fox"];

function clamp(value, low, high) {
    return Math.max(low, Math.min(high, value));
}

function randomUnit(random) {
    var value = typeof random === "function" ? random() : Math.random();
    return clamp(Number(value) || 0, 0, 0.999999);
}

function pickSpeed(base, spread, random) {
    return base + spread * randomUnit(random);
}

function randomDirection(random) {
    return randomUnit(random) < 0.5 ? -1 : 1;
}

function reflect(position, velocity) {
    var x = position + velocity;
    var v = velocity;
    if (x < 0) {
        x = -x;
        v = Math.abs(v);
    } else if (x > 1) {
        x = 2 - x;
        v = -Math.abs(v);
    }
    return {position: clamp(x, 0, 1), velocity: v};
}

function createTarget(record, profile, random) {
    if (PROFILES.indexOf(profile) < 0)
        throw new Error("INVALID_HUNT_PROFILE");
    var yBase = 0.60 + 0.23 * randomUnit(random);
    var target = {
        path: record.path, name: String(record.name || ""),
        mediaType: String(record.mediaType || ""),
        profile: profile,
        // Position is normalized against the usable arena area AFTER
        // the actual target width/height are reserved.
        xNorm: 0.15 + 0.70 * randomUnit(random),
        yNorm: yBase,
        baseY: yBase,
        vx: randomDirection(random) * 0.009,
        vy: randomDirection(random) * 0.006,
        sizeScale: 1,
        phase: randomUnit(random) * Math.PI * 2,
        state: "move",
        age: 0,
        stateTicks: 0
    };
    if (profile === "bird") {
        target.sizeScale = 0.92;
        target.vx = randomDirection(random) * pickSpeed(0.010, 0.006, random);
        target.vy = randomDirection(random) * pickSpeed(0.007, 0.004, random);
        target.yNorm = 0.12 + 0.64 * randomUnit(random);
        target.state = "fly";
    } else if (profile === "frog") {
        target.sizeScale = 0.91;
        target.vx = 0;
        target.vy = 0;
        target.state = "idle";
        target.stateTicks = 4 + Math.floor(9 * randomUnit(random));
    } else if (profile === "deer") {
        target.sizeScale = 0.85;
        target.vx = randomDirection(random) * pickSpeed(0.020, 0.009, random);
        target.vy = 0;
        target.state = "run";
        target.stateTicks = 9 + Math.floor(18 * randomUnit(random));
    } else if (profile === "ox") {
        target.sizeScale = 1.30;
        target.vx = randomDirection(random) * pickSpeed(0.0025, 0.0020, random);
        target.vy = randomDirection(random) * pickSpeed(0.0018, 0.0015, random);
        target.state = "trudge";
    } else if (profile === "fox") {
        target.sizeScale = 0.77;
        target.vx = randomDirection(random) * pickSpeed(0.010, 0.006, random);
        target.vy = randomDirection(random) * pickSpeed(0.007, 0.004, random);
        target.state = "dart";
    }
    return target;
}

function advanceTarget(current, pointer) {
    // Immutable snapshot: existing shot/undo history is not mutated by
    // subsequent clock ticks.
    var t = Object.assign({}, current);
    t.age += 1;

    if (t.profile === "bird") {
        // Unsteady diagonal flight, with mild altitude wobble.
        t.vy = clamp(t.vy + Math.sin(t.age * 0.19 + t.phase) * 0.00055,
                     -0.014, 0.014);
    } else if (t.profile === "frog") {
        if (t.state === "idle") {
            t.stateTicks -= 1;
            if (t.stateTicks <= 0) {
                t.state = "hop";
                t.vx = Math.sin(t.phase + t.age * 1.3) >= 0 ? 0.011 : -0.011;
                t.vy = -0.040;
            }
        } else {
            // Ballistic hop: starts upward, falls back to a personal
            // landing level, then rests before the next jump.
            t.vy += 0.0035;
            t.yNorm += t.vy;
            if (t.yNorm <= 0) {
                t.yNorm = 0;
                t.vy = Math.abs(t.vy);
            }
            if (t.yNorm >= t.baseY) {
                t.yNorm = t.baseY;
                t.vx = 0;
                t.vy = 0;
                t.state = "idle";
                t.stateTicks = 8 + (t.age % 11);
            }
        }
    } else if (t.profile === "deer") {
        if (t.state === "run") {
            t.stateTicks -= 1;
            t.yNorm = clamp(t.baseY + 0.018 * Math.sin(t.age * 0.85), 0, 1);
            if (t.stateTicks <= 0) {
                t.state = "leap";
                t.vy = -0.036;
            }
        } else {
            t.vy += 0.0038;
            t.yNorm += t.vy;
            if (t.yNorm < 0) {
                t.yNorm = 0;
                t.vy = Math.abs(t.vy);
            }
            if (t.yNorm >= t.baseY) {
                t.yNorm = t.baseY;
                t.vy = 0;
                t.state = "run";
                t.stateTicks = 18 + (t.age % 20);
            }
        }
    } else if (t.profile === "fox") {
        if (t.age % 35 === 0) {
            // Occasional feint; no teleport, just a new direction.
            t.vx = -t.vx * 0.88;
            t.vy += Math.sin(t.phase + t.age) * 0.004;
        }
        if (pointer && pointer.active) {
            var dx = t.xNorm - pointer.x;
            var dy = t.yNorm - pointer.y;
            var d = Math.sqrt(dx * dx + dy * dy);
            if (d < 0.28 && d > 0.01) {
                // Small, bounded evasive acceleration away from cursor.
                // Fox reacts, but cannot become impossible to click.
                var boost = 0.0019 * (1 - d / 0.28);
                t.vx += boost * dx / d;
                t.vy += boost * dy / d;
            }
        }
        t.vx = clamp(t.vx, -0.022, 0.022);
        t.vy = clamp(t.vy, -0.018, 0.018);
    }

    var x = reflect(t.xNorm, t.vx);
    t.xNorm = x.position;
    t.vx = x.velocity;
    if (t.profile !== "frog" && t.profile !== "deer") {
        var y = reflect(t.yNorm, t.vy);
        t.yNorm = y.position;
        t.vy = y.velocity;
    }
    t.xNorm = clamp(t.xNorm, 0, 1);
    t.yNorm = clamp(t.yNorm, 0, 1);
    return t;
}
