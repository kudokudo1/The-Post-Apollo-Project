.pragma library

// M28-N // Reversible SUBJECTS-first launch pilot.
// Pure decision contract: one root StationNavigator/Terminal/source owner.
// This policy does NOT change root collectors, persistent stores or displays.
// Set SUBJECTS_FIRST_PILOT=false to restore original CLASSIC-first open/close
// without deleting either presentation. The rail's CLASSIC toggle is a
// temporary per-open fallback even while this pilot is enabled.
var FORMAT = "post-apollo.weather.subject-default.m28n.v1";
var SUBJECTS_FIRST_PILOT = true;

function preferredView(pilotEnabled) {
    return pilotEnabled === true ? "subjects" : "classic";
}
function onOpen(pilotEnabled) {
    return preferredView(pilotEnabled) === "subjects";
}
function onClose(pilotEnabled) {
    // The station's PanelWindow remains visible with 0x0 geometry on close.
    // Always unload SUBJECTS while collapsed; the next open chooses again.
    // pilotEnabled stays a read-only preference, never a hidden active view.
    return false;
}
function escapeAction(subjectsOpen, indexOpen) {
    // INDEX is a nested route explorer: first Escape returns to its original
    // workspace route. Workspace and the CLASSIC fallback Escape both close.
    return subjectsOpen && indexOpen ? "workspace" : "close";
}
function canSwitch(menuOpen, contextTerminalRequested, terminalState) {
    return menuOpen === true && contextTerminalRequested !== true
        && terminalState === "IDLE";
}
function switchToClassic(subjectsOpen, allowed) {
    // No implicit switch may terminate an active Kitty instance. A manual
    // control can enter CLASSIC only when terminal state is confirmed IDLE.
    return allowed && subjectsOpen === true;
}
