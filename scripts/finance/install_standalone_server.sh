#!/usr/bin/env bash
# Opt-in host installer: NEW empty Actual server, separate from desktop data.
# No user budget migration, cleanup, password copies, or source switching.
set -euo pipefail
umask 077

if [[ "${EUID}" -eq 0 ]]; then
    printf 'Use your normal user account; do not run with sudo.\n' >&2
    exit 1
fi
for command in npm node systemctl; do
    command -v "$command" >/dev/null || {
        printf 'Missing prerequisite: %s\n' "$command" >&2
        exit 1
    }
done
major="$(node -p 'process.versions.node.split(".")[0]')"
if (( major < 22 )); then
    printf 'Actual Server needs Node.js 22 or newer.\n' >&2
    exit 1
fi
if systemctl --user is-active --quiet financew-actual-server.service; then
    printf 'Standalone Actual is already active. No changes made.\n'
    exit 0
fi
# Do not occupy a port belonging to another service.
if command -v ss >/dev/null && ss -H -ltn | awk '$4 ~ /:5006$/ {found=1} END {exit !found}'; then
    printf 'Port 5006 is already in use. No changes made.\n' >&2
    exit 1
fi

app="$HOME/.local/share/financew/actual-server"
data="$HOME/.local/share/financew/actual-server-data"
unitDir="$HOME/.config/systemd/user"
unitFile="$unitDir/financew-actual-server.service"
if [[ -e "$unitFile" ]]; then
    printf 'Service file already exists; refusing to overwrite: %s\n' "$unitFile" >&2
    exit 1
fi

mkdir -p -m 700 "$app" "$data" "$unitDir"
chmod 700 "$app" "$data"
npm install --prefix "$app" --no-save --package-lock=false \
    --no-audit --no-fund '@actual-app/sync-server@26.10.0'
bin="$app/node_modules/.bin/actual-server"
if [[ ! -x "$bin" ]]; then
    printf 'Actual server executable not found; refusing to start.\n' >&2
    exit 1
fi
cat > "$unitFile" <<'UNIT'
[Unit]
Description=FinanceW standalone Actual Budget sync server
Documentation=https://actualbudget.org/docs/install/cli-tool/

[Service]
Type=simple
WorkingDirectory=%h/.local/share/financew/actual-server-data
Environment=ACTUAL_DATA_DIR=%h/.local/share/financew/actual-server-data
Environment=ACTUAL_HOSTNAME=127.0.0.1
Environment=ACTUAL_PORT=5006
UMask=0077
ExecStart=%h/.local/share/financew/actual-server/node_modules/.bin/actual-server
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
UNIT
chmod 600 "$unitFile"
systemctl --user daemon-reload
systemctl --user enable --now financew-actual-server.service
printf '\nStandalone Actual server installed on http://127.0.0.1:5006\n'
printf 'This server is EMPTY until you import your backed-up budget.\n'
printf 'Your desktop Actual data and FinanceW source were NOT changed.\n'
