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

backend="$(find_backend || true)"
model="$(find_model || true)"

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

exec "$backend" \
    -m "$model" \
    -f "$audio" \
    -l en \
    -nt \
    -np
