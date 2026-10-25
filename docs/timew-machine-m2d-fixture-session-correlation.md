# MACHINE M2d // Fixture-backed host to app-window correlation

**Milestone:** M2d foundation, stage 1 only. **Nothing on the operator's
desktop is inspected or modified.** No app session collector, browser
extension, native messaging receiver, socket, window mover, writer, terminal
command, restore action or runtime activation is part of this PR.

## Purpose

The user has about 17 Brave and 3–4 Kitty windows, alongside other browsers,
terminals and VS Code. M2a can compare window *counts* and placements.
M2b/M2c define per-application session identity as a *proposed* sidecar.
But none of those prove a given saved browser window is the same live window
observed by the compositor. Matching by window order, app ID, title or PID
would create incorrect moves and duplicate reopened tabs.

M2d starts by testing a small, **pure fixture-only correlation contract**,
using one temporary synthetic scope and opaque per-window challenge strings.
This is a model of what a future **authenticated** connector would need,
*not evidence that such a connector exists*.

## Data model

`services/time/MachineAdapterFixtureCorrelation.py` accepts three
preconstructed Python dictionaries and optional *schema-only* adapter
manifest declarations:

1. An M2b v2 saved sidecar (strict `validate_sidecar`), containing only
   opaque checkpoint-local window IDs, app ID, saved workspace/floating
   fields, app-scoped synthetic instance references and inner-item counts.
2. A synthetic host snapshot with one UUID `scope_id` and records of
   `observation_id`, `app_id`, `workspace`, `floating` and an opaque
   temporary `challenge`. The observation ID is **not** a Sway con_id and
   is never considered durable.
3. Synthetic application observations with the same scope, app ID, declared
   adapter, opaque namespace and instance IDs, the same challenge and an
   inner-item **count**, not tab URLs or document contents.

The verifier rejects duplicate IDs/challenges, a challenge from a different
scope, claims for the wrong app/adapter, conflicting instance references,
unsupported kinds, malformed UUIDs, unexpected private fields and
oversized collections.

A saved sidecar entry is correlated in this **synthetic exercise** only if
an application observation pairs to exactly one host observation and the
reported app-scoped namespace/instance tuple matches the saved record.
Host order and app observation order never matter.

An app window without a corresponding observation remains unlinked. That
is **not** proof the application is closed. A saved instance without a
matching observation is **not** an automatic launch request. Unknown apps
stay layout-only, with `identity_not_available`.

If its workspace/float fields agree, the result is
`placement_fields_match` and if an inner-item count agrees,
`item_counts_match_contents_unverified`. Neither result means that the
*same* browser tabs, VS Code documents or Kitty programs are restored.
Different tabs can easily have equal counts.

## What these tokens do NOT prove

This fixture works with fabricated equal challenge UUIDs. **A malicious or
mistaken adapter can still report the wrong instance or swap two identities.**
The model does not authenticate app processes, prove that an instance survived
restart, prove browser profile identity or acquire any permission to move,
launch or reopen. It hardcodes:

- `input_provenance: synthetic_untrusted`;
- `live_identity_verified: false`;
- `exact_session_match: false`;
- `safe_actions: []`;
- `capture_enabled: false`, `launch_enabled: false`,
  `restore_enabled: false`, `executable: false`.

**No existing v1 checkpoint is read, changed or migrated.** All seven user
saves remain with the existing v1 SQLite store. No QML control or background
poller is introduced.

## Synthetic tests

`test_machine_adapter_fixture_correlation.py` includes 17 distinct Brave,
four Kitty, Firefox and VS Code fixtures (**23 windows** in total).
It tests different ordering, swapped claims, misplaced windows, missing
observations, extra live instances, an unknown application, mismatched inner
counts and 20+ failure paths. The companion contract test ensures the pilot
cannot call live Sway/app interfaces, write a database or execute a command.

All fixtures use invented UUIDs and do not capture URLs, filenames, window
titles, terminal buffers, shell commands, credentials or personal data.
The TimeW foundation workflow runs the tests alongside every prior M1/M2
regression.

## Future M2d stages // explicit approval gates

A future worker may propose one **trusted read-only** bridge for a narrowly
scoped application and host pairing. Before attempting it:

1. Check current GitHub code, `Meta-Apollo-Logos-Syntagma/AGENTS.md`,
   Hospital assignment boundaries and the Notifications/Proton extension
   owner's scope. No implicit takeover.
2. Agree on an authenticated process/extension identity and a protocol to
   *bind* a host window to one application window within a short lifetime,
   with replay rejection and exact version/permissions. No title/PID/order
   fallback.
3. Obtain explicit consent before installing/enabling a browser extension,
   remote-control socket, native host or reading live session metadata.
   Private/incognito browsing must be opt-in or excluded. Treat session URLs,
   file paths and commands as sensitive.
4. Validate a **single disposable test session**, including two identical
   app IDs, window reordering, mismatched app process, stale challenges,
   restart/replay attempts and dropped/duplicate events. Fail closed.
5. Move on to v2 owner-only storage only after a separate security and
   retention decision. No silent upgrade of current saves.

Only then may an adapter declare *independently verified* live correlation.
A parser-accepted UUID is not a trusted proof. User-facing text should remain
simple: **ALREADY IN PLACE**, **NEEDS MOVING**, **NEEDS OPENING**, or
**NEEDS ATTENTION**. No automatic actions come from aggregate identity alone.

## REVIVE versus RESTORE

Both future modes can consume trusted correlation facts, but they stay
separate policy engines:

- **REVIVE:** preserve extra active work and minimally repair the current
  session; no restarting when a window is already correct.
- **RESTORE:** protect the present timeline, then reconstruct the selected
  checkpoint with explicit conflict review. Never overwrite newer work just
  because a synthetic token matches.

Next: independent approval for one real, read-only and privacy-scoped
application/host identity experiment, then separate authorization for
checkpoint capture, app reopening and actual window movement.
