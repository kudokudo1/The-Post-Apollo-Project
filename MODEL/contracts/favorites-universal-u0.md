# Favorites++ // U0 provider-neutral read-only contract

> **STATUS:** draft implementation / awaiting independent review and operator acceptance.
> **OWNER:** Post-Apollo Favorites foundation in services/favorites/.
> **SCOPE:** identity and capability projections only; no runtime activation or migration.

## Existing behavior preserved

- FavoritesStore owns the four AppControl arrays in appcontrol-favorites.json. HUNTER still interprets task favorites with its existing process-safety policy.
- Weather HOME owns weather-home-favorites-v1.json and source provenance. A saved card identity is not a saved measurement.
- TimeSettings owns timezone favorites; PlaceRegistry owns saved places and temporary location context.
- Notifications owns favorite source keys independently of DND and history. Receptionist owns pin ordering and archive retention. Radio owns favorite/recent station memory.
- U0 does not import, activate or modify these writers.

## New contract

services/favorites/FavoritesResourcePolicy.js takes a descriptor with:

| Field | Meaning |
| --- | --- |
| provider | Lowercase owner namespace: e.g. time, appcontrol, weather-home |
| kind | Lowercase resource kind within that namespace |
| resourceId | Stable owner-issued resource identity, not a PID or measurement |
| scope | Optional; U0 supports local only |
| label | Optional bounded display text, never a command |
| capabilities | Explicit subset of favorite, pin, watch, recent, recall, collection, rotate, preferred-action, protect |

normalize(input) returns only schema, key, scope, provider, kind, resourceId, label, capabilities and availability=unresolved.
The stable key is fav1:local:<provider>:<kind>:<percent-encoded-resourceId>.
Bad identities, duplicate or unknown capabilities, nonlocal scopes, control-character labels, and malformed Unicode are rejected.
mergeSnapshots([records, ...]) rejects duplicate identities and invalid resources rather than silently choosing an owner.

**Critical distinction:** capabilities are descriptive, never authorization or evidence of a live feature.
A protect declaration never overrides KILL/HUNTER, Hospital retention or provider policy. U0 adapters do not advertise protect.
Recall requires a separately authorized provider binding, absent in U0. No action callbacks cross this contract.

## Read-only legacy adapters

| Adapter function | Owner input | Projection |
| --- | --- | --- |
| appControl(snapshot) | Four FavoritesStore lists | Items, preferred actions, monitor and task watches |
| weatherHome(snapshot) | panelRoutes/cardKeys | Screens and cards with no measurement data |
| worldClock(snapshot) | zones | Timezone identities; installed-zone checks stay with Time |
| places(savedPlaces) | PlaceRegistry savedPlaces | Stable record IDs and display labels, no coordinates |
| notifications(sources) | NotificationService favorite source entries | Source identity; no message bodies |
| hospital(pinnedKeys) | Reception archive keys | Favorite event identities, no retention action |
| radio(favorites,recents) | Normalized Radio Browser station rows | UUIDs only, no stream URL or autoplay |

All adapters return items and invalidCount. Callers supply snapshots, not mutable owner services.
The adapters contain no FileView, writes, network, process, playback or service-side execution.
U0 does not create a second favorites database or bind a runtime UI.
Presentation must render labels as plain text, and action requests must be separately validated by the owning provider.

## Verification / unfinished gates

The path-scoped GitHub workflow favorites-universal-u0.yml runs the new identity, capability, scope, projection, corruption and collision tests plus established Clock, Weather HOME, Radio, Places and Notifications regressions.
These are source and pure-policy tests, not native Fedora Quickshell integration or proof of live wiring.

- U1: default versioned atomic store for new widgets, retaining provider-owned existing data.
- U2: registered read-only providers, live resolution and unavailable states; verify real source truth.
- U3: optional reusable pin/collection/watch/recall/rotation controls with provider-owned action policy.
- U4+: unified Favorites Center and separately approved identity, organization and sync boundaries.

**No local machine mutation, existing JSON migration, global UI activation, or privileged actions are authorized in U0.**
