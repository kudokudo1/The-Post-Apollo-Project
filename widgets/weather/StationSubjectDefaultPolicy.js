.pragma library

// M28-V // SUBJECTS-only navigation lifecycle, no Classic fallback.
// Pure policy; the single root owns services, stores and terminal.
var FORMAT = "post-apollo.weather.subject-lifecycle.m28v.v1";

function escapeAction(indexOpen) {
    return indexOpen === true ? "workspace" : "close";
}
