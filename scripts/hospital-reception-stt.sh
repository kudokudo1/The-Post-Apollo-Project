#!/usr/bin/env bash
set -euo pipefail

find_model() {
    if [[ -n "${POST_APOLLO_STT_MODEL:-}" && -f "${POST_APOLLO_STT_MODEL}" ]]; then
        printf '%s\n' "${POST_APOLLO_STT_MODEL}"
        return 0
    fi

    local candidates=(
        "$HOME/.local/share/post-apollo-speech/ggml-base.en.bin"
        "$HOME/.local/share/post-apollo-speech/ggml-tiny.en.bin"
        "$HOME/.local/share/whisper.cpp/models/ggml-base.en.bin"
        "$HOME/.local/share/whisper.cpp/models/ggml-tiny.en.bin"
        "$HOME/Projects/whisper.cpp/models/ggml-base.en.bin"
        "$HOME/Projects/whisper.cpp/models/ggml-tiny.en.bin"
    )

    local candidate
    for candidate in "${candidates[@]}"; do
        if [[ -f "$candidate" ]]; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done

    return 1
}

find_backend() {
    if [[ -n "${POST_APOLLO_STT_BIN:-}" ]]; then
        command -v "${POST_APOLLO_STT_BIN}" 2>/dev/null || {
            [[ -x "${POST_APOLLO_STT_BIN}" ]] && printf '%s\n' "${POST_APOLLO_STT_BIN}"
        }
        return
    fi

    local detected
    detected="$(command -v whisper-cli 2>/dev/null || true)"

    if [[ -n "$detected" ]]; then
        printf '%s\n' "$detected"
        return 0
    fi

    local candidates=(
        "$HOME/.local/bin/whisper-cli"
        "$HOME/Projects/whisper.cpp/build/bin/whisper-cli"
        "/usr/local/bin/whisper-cli"
        "/usr/bin/whisper-cli"
    )

    local candidate
    for candidate in "${candidates[@]}"; do
        if [[ -x "$candidate" ]]; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done

    return 1
}

# The server is optional. Its model is loaded once per active mic session,
# using a Unix-domain socket in a private 0700 directory (no TCP port).
find_server() {
    if [[ -n "${POST_APOLLO_STT_SERVER_BIN:-}" ]]; then
        command -v "${POST_APOLLO_STT_SERVER_BIN}" 2>/dev/null || {
            [[ -x "${POST_APOLLO_STT_SERVER_BIN}" ]] && printf '%s\n' "${POST_APOLLO_STT_SERVER_BIN}"
        }
        return
    fi

    local detected
    detected="$(command -v whisper-server 2>/dev/null || true)"
    if [[ -n "$detected" ]]; then
        printf '%s\n' "$detected"
        return 0
    fi

    local candidate
    for candidate in \
        "$HOME/.local/bin/whisper-server" \
        "$HOME/Projects/whisper.cpp/build/bin/whisper-server" \
        "/usr/local/bin/whisper-server" \
        "/usr/bin/whisper-server"; do
        if [[ -x "$candidate" ]]; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done
    return 1
}

backend="$(find_backend || true)"
model="$(find_model || true)"
server="$(find_server || true)"

# Read-only capability/model profile; never starts a model or microphone.
if [[ "${1:-}" == "--profile" ]]; then
    printf 'MODEL // %s\n' "$(basename "${model:-none}")"
    [[ -n "$backend" ]] && printf 'CLI // AVAILABLE\n' || printf 'CLI // UNAVAILABLE\n'
    [[ -n "$server" ]] && printf 'SESSION // AVAILABLE\n' || printf 'SESSION // UNAVAILABLE\n'
    exit 0
fi

if [[ "${1:-}" == "--session-check" ]]; then
    [[ -n "$model" && -n "$server" ]] || exit 2
    # Do not attempt to start an unknown server version without Unix socket
    # support. --help neither initializes a model nor opens a listener.
    help_text="$("$server" --help 2>&1 || true)"
    [[ "$help_text" == *"--host"* && "$help_text" == *"socket"* ]] || exit 3
    exit 0
fi

if [[ "${1:-}" == "--session" ]]; then
    socket_path="${2:-}"
    [[ "${POST_APOLLO_STT_SAFE_MODE:-}" == "1" ]] || exit 70
    [[ -n "$model" && -n "$server" ]] || exit 2
    [[ "$socket_path" == /*.sock ]] || exit 64
    [[ -d "$(dirname "$socket_path")" ]] || exit 66
    # Local-only server, GPU disabled, one server process/worker. No ffmpeg
    # conversion and no network-facing TCP listener, even on localhost.
    exec "$server" -m "$model" --host "$socket_path" \
        -ng -t 2 -p 1 -l en -nt -np -nc
fi

if [[ "${1:-}" == "--check" ]]; then
    if [[ -z "$backend" ]]; then
        printf '%s\n' "WHISPER-CLI NOT FOUND" >&2
        exit 127
    fi

    if [[ -z "$model" ]]; then
        printf '%s\n' "WHISPER MODEL NOT FOUND" >&2
        exit 2
    fi

    printf '%s\n' "READY"
    exit 0
fi

audio="${1:-}"

if [[ -z "$audio" || ! -f "$audio" ]]; then
    printf '%s\n' "VOICE AUDIO NOT FOUND" >&2
    exit 3
fi

if [[ -z "$backend" ]]; then
    printf '%s\n' "WHISPER-CLI NOT FOUND" >&2
    exit 127
fi

if [[ -z "$model" ]]; then
    printf '%s\n' "WHISPER MODEL NOT FOUND" >&2
    exit 2
fi

# Limit Whisper CPU worker threads and avoid GPU driver paths for the
# incident-isolated live microphone process. The guard sets this flag.
safe_args=()
if [[ "${POST_APOLLO_STT_SAFE_MODE:-}" == "1" ]]; then
    safe_args=(-ng -t 2)
fi

exec "$backend" "${safe_args[@]}" \
    -m "$model" \
    -f "$audio" \
    -l en \
    -nt \
    -np
