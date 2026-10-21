#!/usr/bin/env bash
# Explicit, one-time operator setup. Never run from a notification.
set -euo pipefail

self_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
crate="$self_dir/update-review-header"
target=wasm32-wasip1
destination="${XDG_DATA_HOME:-$HOME/.local/share}/post-apollo/zellij"
for program in rustup cargo install; do
    command -v "$program" >/dev/null || {
        printf "Missing command: %s\n" "$program" >&2
        exit 1
    }
done
rustup target add "$target"
cargo build --release --target "$target" --manifest-path "$crate/Cargo.toml"
mkdir -p "$destination"
install -m 0644 "$crate/target/$target/release/post_apollo_update_header.wasm" \
    "$destination/post_apollo_update_header.wasm"
printf "Installed Zellij update X plugin at %s\n" "$destination/post_apollo_update_header.wasm"
