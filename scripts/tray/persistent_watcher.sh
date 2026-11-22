#!/usr/bin/env bash
# Post-Apollo tray registry preflight. Default mode is strictly observational.
# A separately installed SNI watcher must own D-Bus across Quickshell restarts.
set -euo pipefail

mode="${1:---status}"
if [[ $# -gt 1 || ( "$mode" != "--status" && "$mode" != "--enable-next-login" ) ]]; then
    printf 'Usage: %s [--status|--enable-next-login]\n' "$0" >&2
    exit 64
fi
for command_name in busctl systemctl awk grep; do
    if ! command -v "$command_name" >/dev/null 2>&1; then
        printf 'Missing prerequisite: %s\n' "$command_name" >&2
        exit 69
    fi
done

unit=sni-watcher.service
name=org.kde.StatusNotifierWatcher

# Listing D-Bus names is observational. Avoid get-property on an absent name,
# because asking an absent D-Bus name to reply can AUTO-ACTIVATE a service.
if ! bus_names="$(busctl --user --no-pager list 2>&1)"; then
    printf 'Cannot inspect the user session bus: %s\n' "$bus_names" >&2
    exit 70
fi
watcher_row="$(printf '%s\n' "$bus_names" | awk -v name="$name" '$1 == name { print; exit }')"
service_type="$(systemctl --user show -p Type --value "$unit" 2>/dev/null || true)"
service_bus="$(systemctl --user show -p BusName --value "$unit" 2>/dev/null || true)"
service_state="$(systemctl --user show -p ActiveState --value "$unit" 2>/dev/null || true)"
service_file="$(systemctl --user show -p UnitFileState --value "$unit" 2>/dev/null || true)"

printf 'WATCHER_BUS_NAME=%s\n' "$name"
if [[ -z "$watcher_row" ]]; then
    printf 'WATCHER_CURRENT_OWNER=ABSENT\n'
else
    printf 'WATCHER_CURRENT_OWNER=%s\n' "$watcher_row"
fi
printf 'PERSISTENT_UNIT=%s\n' "$unit"
printf 'PERSISTENT_UNIT_TYPE=%s\n' "${service_type:-unavailable}"
printf 'PERSISTENT_UNIT_BUS=%s\n' "${service_bus:-unavailable}"
printf 'PERSISTENT_UNIT_STATE=%s\n' "${service_state:-unavailable}"
printf 'PERSISTENT_UNIT_ENABLED=%s\n' "${service_file:-unavailable}"

if [[ "$mode" == "--status" ]]; then
    if [[ "$service_state" == "active" && "$service_type" == "dbus" \
          && "$service_bus" == "$name" && -n "$watcher_row" ]]; then
        printf 'TRAY_REGISTRY_STATUS=PERSISTENT_WATCHER_ACTIVE\n'
    else
        printf 'TRAY_REGISTRY_STATUS=PERSISTENCE_NOT_VERIFIED\n'
    fi
    exit 0
fi

# Explicit, one-time operator actuation for NEXT login only. No package
# download/install, no "--now", no shell or app restart and no D-Bus takeover.
# Require the reviewed unit's early-start ordering; a late watcher does not
# solve Electron apps that register only once.
if [[ "$service_type" != "dbus" || "$service_bus" != "$name" ]]; then
    printf 'Refused: no installed Type=dbus sni-watcher unit for %s.\n' "$name" >&2
    exit 78
fi
if ! unit_text="$(systemctl --user cat "$unit" 2>/dev/null)"; then
    printf 'Refused: cannot inspect installed watcher unit.\n' >&2
    exit 78
fi
if ! grep -Eq '^[[:space:]]*Before=graphical-session-pre\.target([[:space:]]|$)' <<<"$unit_text" ||
   ! grep -Eq '^[[:space:]]*WantedBy=graphical-session-pre\.target([[:space:]]|$)' <<<"$unit_text" ||
   ! grep -Eq '^[[:space:]]*ExecStart=/usr/bin/sni-watcher([[:space:]]|$)' <<<"$unit_text"; then
    printf 'Refused: installed unit lacks the reviewed early-start and executable contract.\n' >&2
    exit 78
fi
systemctl --user enable "$unit"
printf 'NEXT_LOGIN_ENABLED=YES\n'
printf 'No live tray process was stopped or restarted. Verify service activation at the next graphical login.\n'
