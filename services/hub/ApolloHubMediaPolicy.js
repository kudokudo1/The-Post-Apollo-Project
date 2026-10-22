.pragma library

// Read-only small-screen projections. MPD session and MPRIS player identity
// are deliberately different. No action, raw object or playback handle escapes.
var MAX_MPD_AGE_MS = 15000;

function shortText(value, maxLen) {
    return typeof value === "string"
        ? value.replace(/[\x00-\x1f\x7f]/g, " ").trim().slice(0, maxLen)
        : "";
}

function knownAge(observedAtMs, nowMs) {
    var then = Number(observedAtMs);
    var now = Number(nowMs);
    if (!isFinite(then) || !isFinite(now) || then <= 0 || now < then)
        return -1;
    return Math.floor((now - then) / 1000);
}

function mpdSnapshot(attached, observation, errorText, observedAtMs, nowMs, dockObservation) {
    var connected = attached === true;
    var error = connected ? shortText(errorText, 120) : "";
    var age = knownAge(observedAtMs, nowMs);
    var fresh = connected && age >= 0
        && Number(nowMs) - Number(observedAtMs) <= MAX_MPD_AGE_MS;
    var payload = observation && typeof observation === "object"
        && !Array.isArray(observation) ? observation : null;
    var session = payload && payload.session && typeof payload.session === "object"
        ? payload.session : null;
    var loaded = payload && payload.loaded && typeof payload.loaded === "object"
        ? payload.loaded : null;
    var current = session && session.current && typeof session.current === "object"
        ? session.current : null;
    var currentTitle = current ? shortText(current.title, 160) : "";
    var loadedTitle = loaded && loaded.item && typeof loaded.item === "object"
        ? shortText(loaded.item.title, 160) : "";

    // Browser selection is *not* the loaded cassette and neither proves
    // actual playback. Controller ownership is evidence, not permission.
    var validStates = ["playing", "paused", "stopped", "unloaded"];
    var observedState = session && session.observed === true
        && validStates.indexOf(session.state) >= 0 ? session.state : "unavailable";
    var state = !connected ? "disconnected"
              : error ? "error"
              : !payload || age < 0 ? "unobserved"
              : !fresh ? "stale" : observedState;
    var usable = fresh && !error && observedState !== "unavailable";

    // The compact Media dock already observes MPD every two seconds even
    // while the full cassette deck is closed. Treat that as playback evidence,
    // NOT as controller ownership or proof of a loaded cassette.
    var dock = dockObservation && typeof dockObservation === "object"
        && !Array.isArray(dockObservation) ? dockObservation : null;
    var dockAge = dock ? knownAge(dock.observedAtMs, nowMs) : -1;
    var dockFresh = dockAge >= 0
        && Number(nowMs) - Number(dock.observedAtMs) <= MAX_MPD_AGE_MS;
    var dockState = dock && ["playing", "paused", "stopped"].indexOf(dock.state) >= 0
        ? dock.state : "unavailable";
    var dockUsable = dockFresh && dockState !== "unavailable";

    // Use the dock for actual MPD status, but preserve the controller's
    // distinct last-loaded cassette and ownership data when fresh.
    var displayFromDock = dockUsable;
    var displayedState = displayFromDock ? dockState
        : usable ? state : !connected && !dock ? "disconnected"
        : error && !dockUsable ? "error"
        : dock && dockFresh ? "unavailable"
        : !connected && dock && dockAge < 0 ? "unobserved"
        : state === "disconnected" || state === "unobserved"
          ? (dock && dockAge >= 0 ? "stale" : state) : state;
    var displayedFresh = dockUsable || usable;

    return {
        state: displayedState,
        source: "mpd",
        observationSource: displayFromDock ? "dock-mpc" : usable ? "controller" : "",
        connected: connected || dock !== null,
        fresh: displayedFresh,
        error: displayFromDock ? "" : error,
        ageSeconds: displayFromDock ? dockAge : usable ? age
                    : dock && dockAge >= 0 ? dockAge : age,
        // Loaded title is explicitly LAST KNOWN, including when stale.
        lastKnownLoadedTitle: loadedTitle,
        title: displayFromDock ? shortText(dock.title, 160)
             : usable ? currentTitle : "",
        // Dock provides a combined artist-title label, not separate tags.
        artist: displayFromDock ? ""
              : usable && current ? shortText(current.artist, 120) : "",
        loaded: usable && loaded !== null,
        ownedByController: usable && session.ownedByController === true,
        // No command capabilities or mutable controller/session references.
        audibleOutputVerified: false
    };
}

function mprisSnapshot(input) {
    var data = input && typeof input === "object" ? input : {};
    var count = typeof data.playerCount === "number"
        && isFinite(data.playerCount) && data.playerCount >= 0
        ? Math.floor(data.playerCount) : 0;
    var selected = typeof data.selectedBusName === "string"
        && data.selectedBusName.length > 0;
    var p = selected && data.player && typeof data.player === "object"
        ? data.player : null;
    var state = !selected ? (count > 0 ? "selection-required" : "unavailable")
              : !p ? "player-missing"
              : (["playing", "paused", "stopped"].indexOf(p.playbackState) >= 0
                 ? p.playbackState : "unknown");

    // Never select the first player, and never treat playerctld as a source.
    var valid = p !== null;
    return {
        state: state,
        source: "mpris",
        selected: valid,
        playerCount: count,
        playerName: valid ? shortText(p.identity, 100) : "",
        title: valid ? shortText(p.title, 160) : "",
        artist: valid ? shortText(p.artist, 120) : "",
        album: valid ? shortText(p.album, 120) : "",
        // These are observations, not transport permissions.
        audibleOutputVerified: false
    };
}
