.pragma library

// Camera Cleanup Hunt M3c. This module performs visual movement ONLY.
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
        stateTicks: 0,
        // Additional profile-specific timers are gameplay state only.
        fatigueAt: 0,
        hopGravity: 0.0035,
        perchVX: 0,
        perchVY: 0
    };
    if (profile === "bird") {
        target.sizeScale = 0.89;
        // Quicker than M3b, but occasionally holds still on a "perch".
        target.vx = randomDirection(random) * pickSpeed(0.015, 0.009, random);
        target.vy = randomDirection(random) * pickSpeed(0.010, 0.007, random);
        target.yNorm = 0.12 + 0.64 * randomUnit(random);
        target.state = "fly";
        target.stateTicks = 43 + Math.floor(34 * randomUnit(random));
    } else if (profile === "frog") {
        target.sizeScale = 0.68;
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
        // Most 25-second rounds end before fatigue. A rare long run
        // gets a brief rest; it never stays asleep permanently.
        target.fatigueAt = 215 + Math.floor(430 * randomUnit(random));
    } else if (profile === "ox") {
        target.sizeScale = 1.72;
        target.vx = randomDirection(random) * pickSpeed(0.0025, 0.0020, random);
        target.vy = randomDirection(random) * pickSpeed(0.0018, 0.0015, random);
        target.state = "trudge";
    } else if (profile === "fox") {
        target.sizeScale = 0.75;
        target.vx = randomDirection(random) * pickSpeed(0.019, 0.011, random);
        target.vy = randomDirection(random) * pickSpeed(0.013, 0.009, random);
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
        if (t.state === "perch") {
            // Pause flight for 0.7-1.2 seconds, then resume original
            // velocity. No random per-tick teleports or lost bounce state.
            t.stateTicks -= 1;
            if (t.stateTicks <= 0) {
                t.state = "fly";
                t.vx = t.perchVX;
                t.vy = t.perchVY;
                t.stateTicks = 42 + (t.age % 41);
            } else {
                return t;
            }
        } else {
            t.stateTicks -= 1;
            if (t.stateTicks <= 0) {
                t.state = "perch";
                t.perchVX = t.vx;
                t.perchVY = t.vy;
                t.vx = 0;
                t.vy = 0;
                t.stateTicks = 7 + (t.age % 6);
                return t;
            }
        }
        // Faster 2D flight with soft up/down wobble.
        t.vy = clamp(t.vy + Math.sin(t.age * 0.23 + t.phase) * 0.00070,
                     -0.022, 0.022);
    } else if (t.profile === "frog") {
        if (t.state === "idle") {
            t.stateTicks -= 1;
            if (t.stateTicks <= 0) {
                // Distinct hop speed, height and gravity on EVERY jump.
                // Deterministic variation keeps Undo snapshots recoverable.
                var cycle = Math.abs(Math.sin(t.phase * 4.3 + t.age * 1.71));
                var lift = Math.abs(Math.cos(t.phase * 2.9 + t.age * 0.97));
                t.state = "hop";
                t.vx = (Math.sin(t.phase + t.age * 1.3) >= 0 ? 1 : -1)
                       * (0.008 + 0.016 * cycle);
                t.vy = -(0.026 + 0.032 * lift);
                t.hopGravity = 0.0030 + 0.0024 * cycle;
            }
        } else {
            t.vy += t.hopGravity;
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
                t.stateTicks = 5 + (t.age % 12);
            }
        }
    } else if (t.profile === "deer") {
        if (t.state === "rest") {
            t.stateTicks -= 1;
            if (t.stateTicks <= 0) {
                t.state = "run";
                t.stateTicks = 15 + (t.age % 19);
                t.fatigueAt = t.age + 240 + (t.age % 130);
            }
            return t;
        }
        if (t.age >= t.fatigueAt && t.state === "run") {
            t.state = "rest";
            t.stateTicks = 8 + (t.age % 12);
            t.yNorm = t.baseY;
            return t;
        }
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
        // The fox is curious when the pointer is still, but slips around
        // a moving pointer. Its orbit direction changes occasionally,
        // making jukes and counter-circles without teleporting.
        if (t.age % 31 === 0) {
            t.vx = -t.vx * 0.90;
            t.vy += Math.sin(t.phase + t.age) * 0.005;
        }
        if (pointer && pointer.active) {
            var dx = t.xNorm - pointer.x;
            var dy = t.yNorm - pointer.y;
            var dist = Math.sqrt(dx * dx + dy * dy);
            if (dist > 0.012) {
                var ux = dx / dist;
                var uy = dy / dist;
                if (pointer.moving && dist < 0.58) {
                    // Close chase = dodge outward while sliding around the
                    // pointer's sides. The occasional sign flip is a juke.
                    var orbitSign = Math.sin(t.phase + Math.floor(t.age / 22))
                                    >= 0 ? 1 : -1;
                    var pressure = 1 - dist / 0.58;
                    var tangential = 0.0028 + 0.0029 * pressure;
                    var dodge = 0.0022 * pressure;
                    t.vx += (-uy * orbitSign) * tangential + ux * dodge;
                    t.vy += (ux * orbitSign) * tangential + uy * dodge;
                    t.state = "juke";
                } else if (!pointer.moving && dist < 0.72) {
                    // Tease stationary cursor: gently approach at range,
                    // then circle close to it rather than covering it.
                    var curiosity = dist > 0.15 ? 0.00145 : -0.00070;
                    t.vx += -ux * curiosity - uy * 0.00075;
                    t.vy += -uy * curiosity + ux * 0.00075;
                    t.state = "taunt";
                }
            }
        }
        t.vx = clamp(t.vx, -0.041, 0.041);
        t.vy = clamp(t.vy, -0.034, 0.034);
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
