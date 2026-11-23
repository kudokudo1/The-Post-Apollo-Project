# TimeW M5 // Read-only local fractional capture preview in MACHINE → STORED

**PATIENT //** The-Post-Apollo-Project  
**ROOM //** TimeW MACHINE · Desktop & Brave Recovery · Scope A  
**STAFF ROLE //** TimeW DOC owner, external Hospital-compatible; live registration unverified  
**STATUS //** Isolated source/CI implementation; **NOT** live installed or production approved  
**TIMEW RESTORE // HOLD**

## Mechanism

TimeW M3 [#2284](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2284) creates a *separate* private local SQLite v3 file for untrusted caller-supplied binary64 CURRENT geometry. TimeW M4 [#2306](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2306) previews one explicit v3 checkpoint, returns bounded JSON, preserves fractional display including one-ULP differences, and never authorizes a native command. M4 is merged and retrospectively reviewed but still not connected to the live TimeW UI.

M5 adds a narrowly scoped optional **LOCAL FRACTIONAL CAPTURES // READ ONLY** button to the existing **MACHINE → STORED** scroll area, after the existing V2 saved-geometry review and before the unchanged Restore section.

Only clicking that button launches services/time/MachineV3LocalPreviewUiRead.py through the existing Quickshell Process.exec pattern. The UI passes **only** a canonical selected checkpoint UUID. The bridge resolves the standard XDG local v3 data path with suggested_path(), calls M4 preview(checkpoint_id, store=...), and prints bounded non-authorizing JSON. It accepts no arbitrary file path or save, restore, all, or native command option. No process runs at application startup, on selection change, when opening STORED, or on a timer.

A distinct QML JS policy, MachineV3LocalPreviewPolicy.js, validates the exact expected M4 schema, checkpoint freshness, explicit local-data origin, all false authority flags, empty actions, record counts, IDs and bounded display data. It strips non-display fields rather than forwarding stored objects to action code. QML shows only sanitized strings with Text.PlainText. Selection changes and leaving STORED invalidate the preview; stale process results are ignored. One window per page is displayed using existing previous/next ActionButton controls. This UI **cannot trigger** any move/resize/retry/undo or become a C5 grant.

## Operator use, once separately installed and accepted

Open **TimeW → MACHINE → STORED**, select a saved checkpoint with the existing previous/next controls, then press **LOCAL FRACTIONAL CAPTURES // READ ONLY**. The panel will show the currently available *local v3* fractional window geometries for that selected UUID, or NO LOCAL FRACTIONAL CAPTURES if none exists. Scroll down to review one window at a time.

**Important:** The old V1/V2 Save controls do **not** populate this separate v3 store yet. For ordinary checkpoints the correct M5 result may be **NO LOCAL FRACTIONAL CAPTURES**. This is not a failure and should not trigger a Save, migration, or Restore. A future separately scoped capture/Save path requires its own review. This source PR alone does **not** install the UI on the user's actual desktop.

## Security, scope and known gaps

- Ordinary local SQLite data can be edited or rolled back by the same user, including substituting another valid finite binary64 value; precise display is **not tamper detection**.
- M5 checks UI freshness but cannot authenticate a physical operator, SwayPX selected native XDG lifetime, compositor transaction, ACK, settled frame or protected independent C5 SPENT. The TimeW service data is *local geometry preview only*, never a signed native receipt or a permission to restore.
- No changes to V1/V2 checkpoint storage, M3 data format, M4 preview engine, C3e/C4b/C5 services, SwayPX compositor, Company Map, NAS, install scripts or native Restore runner.
- Tests use disposable XDG directories and child Python/Node workers; do not read the operator's XDG data. Without separately approved local installation, this remains a source-only UI change.
- The new UI element lives in the existing scrollable STORED pane, in the Post-Apollo cyan/orange visual grammar, with no new window or popup.
- Native acceptance and production Restore remain independently blocked on trusted selected-surface provenance, genuine per-step terminal settlement and protected consent custody. SwayPX synthetic transaction diagnostics and local C5 SQLite rows do not establish those properties.

## VERIFY

Run the dedicated M5 workflow to test the click bridge, QML JS validator, spoofed authority/extra-field refusal, stale/malformed checkpoint and bad-path cases, two independent local checkpoint records, exact fractional display, no DB write on read, corrupt-record fail-closed, and no native-command strings in new modules. Re-run M4, M3, exact geometry, fractional observation, old SQLite and durable journal tests.

Require independent Nurse 2 **exact-head** review of the new UI source and bridge **before merge**, plus separate operator control over merge and live desktop installation. A CI pass is not a native UI screenshot or operator final acceptance.

**DECISIONS //** Operator-approved local ordinary TimeW data now; protected hardware/NAS later. UI preview now, Save bridge and native Restore remain separate future contracts. **TimeW Restore HOLD.**
