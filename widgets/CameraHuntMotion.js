.pragma library

// Camera Cleanup Hunt M3e. Visual animal pursuit + bounded progression only.
// It never reads a filesystem path, executes a command, or marks Trash.
var PROFILES = ["bird", "frog", "deer", "ox", "fox"];

// The next round is 1-based: base difficulty applies through round N.
// Tier 1 begins at round N+1 (e.g., rounds 1-5 are base, round 6 grows).
// The progression math has no filesystem or Trash authority.
function spawnForRound(base, add, every, round) {
    var initial = clamp(Math.round(Number(base) || 1), 1, 10);
    var gain = clamp(Math.round(Number(add) || 0), 0, 5);
    var interval = clamp(Math.round(Number(every) || 1), 1, 50);
    var tier = Math.floor(Math.max(0, Math.round(Number(round) || 1) - 1) / interval);
    return clamp(initial + gain * tier, 1, 10);
}

function speedForRound(gainPercent, every, round) {
    var gain = clamp(Math.round(Number(gainPercent) || 0), 0, 50);
    var interval = clamp(Math.round(Number(every) || 1), 1, 50);
    var tier = Math.floor(Math.max(0, Math.round(Number(round) || 1) - 1) / interval);
    // Compounding is intentionally bounded, even after many rounds.
    return clamp(Math.pow(1 + gain / 100, tier), 1, 2.5);
}

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

function shieldingPrey(ox, targets) {
    // Frog is the shield's preferred companion; if absent, the ox
    // chooses the nearest other smaller animal. Pure read-only lookup.
    if (!Array.isArray(targets) || targets.length === 0)
        return null;
    var choice = null;
    var best = Infinity;
    for (var i = 0; i < targets.length; i++) {
        var other = targets[i];
        if (!other || other.profile === "ox" || other.path === ox.path)
            continue;
        var dx = other.xNorm - ox.xNorm;
        var dy = other.yNorm - ox.yNorm;
        var distance2 = dx * dx + dy * dy;
        var frogBonus = other.profile === "frog" ? 0 : 10;
        var rank = frogBonus + distance2;
        if (rank < best) {
            choice = other;
            best = rank;
        }
    }
    return choice;
}

// Explicit gallery classifications, not filename heuristics, decide the
// very light media wash. The backend owns recognition of screen recordings.
function mediaKind(record) {
    var kind = String(record && record.mediaType || "");
    if (kind === "screen-video") return "screen-video";
    if (kind === "webcam-video") return "webcam-video";
    if (kind === "other-video") return "video";
    if (kind === "screenshot" || (record && record.screenshotLikely === true))
        return "screenshot";
    return "photo";
}

function protectedHuntMedia(record) {
    // Operator policy: recognized screen recordings are safe in HUNT.
    // Do not apply this rule to Batch or Swipe without their own approval.
    return mediaKind(record) === "screen-video";
}

function createTarget(record, profile, random) {
    if (PROFILES.indexOf(profile) < 0)
        throw new Error("INVALID_HUNT_PROFILE");
    var yBase = 0.60 + 0.23 * randomUnit(random);
    var target = {
        path: record.path, name: String(record.name || ""),
        mediaType: String(record.mediaType || ""),
        screenshotLikely: record.screenshotLikely === true,
        mediaKind: mediaKind(record),
        protected: protectedHuntMedia(record),
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
        // Heavy targets vary in size rather than always spawning identical.
        // Ox remains larger than the deer, bird, fox or frog.
        target.sizeScale = 1.5 + 0.75 * randomUnit(random);
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

function advanceTarget(current, pointer, speedTier, herd) {
    // Immutable snapshot: existing shot/undo history is not mutated by
    // subsequent clock ticks. Scale position deltas, not stored velocities,
    // to avoid compounding speed every 100ms.
    var speed = clamp(Number(speedTier) || 1, 1, 2.5);
    var originalY = current.yNorm;
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
    } else if (t.profile === "ox") {
        // The slower, oversized ox drifts toward smaller targets to
        // occlude them. It favors Frog, but never teleports, and stays
        // slower than Fox/Deer/Bird even at higher difficulty tiers.
        var prey = shieldingPrey(t, herd);
        if (prey) {
            var pX = clamp(prey.xNorm + (prey.vx || 0) * 2, 0, 1);
            var pY = clamp(prey.yNorm, 0, 1);
            var seekX = pX - t.xNorm;
            var seekY = pY - t.yNorm;
            var distance = Math.sqrt(seekX * seekX + seekY * seekY);
            if (distance > 0.04) {
                var nudge = prey.profile === "frog" ? 0.00058 : 0.00038;
                t.vx = clamp(t.vx * 0.985 + nudge * seekX / distance,
                             -0.0075, 0.0075);
                t.vy = clamp(t.vy * 0.985 + nudge * seekY / distance,
                             -0.0060, 0.0060);
                t.state = "shield";
            } else {
                t.vx *= 0.88;
                t.vy *= 0.88;
                t.state = "cover";
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

    var x = reflect(t.xNorm, t.vx * speed);
    t.xNorm = x.position;
    t.vx = x.velocity / speed;
    if (t.profile !== "frog" && t.profile !== "deer") {
        var y = reflect(t.yNorm, t.vy * speed);
        t.yNorm = y.position;
        t.vy = y.velocity / speed;
    } else if (t.state === "hop" || t.state === "leap") {
        // The frog/deer integrates its own vertical ballistic jump before
        // this point. Speed its visual climb/fall without amplifying the
        // persistent gravity velocity or moving beyond the arena.
        t.yNorm = clamp(originalY + (t.yNorm - originalY) * speed,
                        0, t.baseY);
    }
    t.xNorm = clamp(t.xNorm, 0, 1);
    t.yNorm = clamp(t.yNorm, 0, 1);
    return t;
}
