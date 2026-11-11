.pragma library

// Keep all CLI requests in ONE already-configured Fedora Toolbox session when
// the operator's gh executable is precisely the known single-command wrapper.
// Without that wrapper, preserve the normal host bash/gh execution path.
// Does not alter ~/bin/gh, host configuration, credentials or Git state.
function wrap(script, label, values) {
    const args = Array.isArray(values) ? values : [];
    const runner = [
        'batch="$1"',
        'shift',
        'gh_wrapper="$HOME/.local/bin/gh"',
        'if [ "$(command -v gh 2>/dev/null)" = "$gh_wrapper" ]',
        '    && [ -r "$gh_wrapper" ]',
        '    && grep -Fxq \'exec toolbox run -c fedora-toolbox-44 /usr/bin/gh "$@"\' "$gh_wrapper"',
        '    && command -v toolbox >/dev/null 2>&1; then',
        '  # Run the complete read-only batch inside one Toolbox invocation.',
        '  # A shell function calls the container-native gh, never the host',
        '  # wrapper again. Preserve the original script $0/$1/$@ interface.',
        '  exec toolbox run -c fedora-toolbox-44 /usr/bin/bash -c',
        '    \'batch="$1"; shift; gh() { /usr/bin/gh "$@"; }; eval "$batch"\'',
        '    "$0" "$batch" "$@"',
        'fi',
        '# For ordinary installations (or changed wrappers), keep host mode.',
        'eval "$batch"'
    ].join("\n");

    const command = ["bash", "-lc", runner, String(label || "pa-github-read"),
                     String(script || "")];
    for (let i = 0; i < args.length; ++i)
        command.push(String(args[i]));
    return command;
}
