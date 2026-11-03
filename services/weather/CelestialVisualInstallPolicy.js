.pragma library

// MAGICK // Resolve an existing user-local installation without changing the
// Quickshell launch command. This policy only constructs paths. It does not
// read files, install Python, download JPL kernels, or create processes.
//
// Existing one-time setup:
//   $HOME/.local/share/post-apollo/magick/de440s.bsp
//   $HOME/.local/share/post-apollo/magick/venv/bin/python
// Explicit developer environment overrides continue to take precedence.

function clean(value) {
    return typeof value === "string" ? value.trim() : "";
}

function installRoot(home) {
    var h = clean(home);
    if (h.length < 2 || h[0] !== "/" || /[\r\n]/.test(h))
        return "";
    h = h.replace(/\/+$/, "");
    return h + "/.local/share/post-apollo/magick";
}

function resolveKernel(kernelOverride, home) {
    var override = clean(kernelOverride);
    if (override !== "") return override;
    var root = installRoot(home);
    return root !== "" ? root + "/de440s.bsp" : "";
}

function resolvePython(pythonOverride, home) {
    var override = clean(pythonOverride);
    if (override !== "") return override;
    var root = installRoot(home);
    return root !== "" ? root + "/venv/bin/python" : "python3";
}

function pathSource(kernelOverride, pythonOverride, home) {
    if (clean(kernelOverride) !== "" || clean(pythonOverride) !== "")
        return "environment-override";
    return installRoot(home) !== "" ? "home-installation" : "unconfigured";
}
