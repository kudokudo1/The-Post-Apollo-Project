# TimeW M6 // Local exact CURRENT admission after a saved checkpoint

**PATIENT //** The-Post-Apollo-Project  
**ROOM //** TimeW MACHINE / Scope A  
**STAFF ROLE //** TimeW owner DOC · external Hospital-compatible, live Hospital registration not verified  
**STATE //** Source/CI-only producer contract staging, **NO live Save wiring**  
**PRODUCTION RESTORE // HOLD**

## Mechanism / why this comes before changing the Save button

Current V1/V2 checkpoint Save stores **integer-only** positions and sizes in the existing private machine.db. Recasting integer rectangles into IEEE754 doubles cannot recreate missing fractional geometry. M3/M4/M5 already provide a separate local SQLite v3 exact-binary64 store and a read-only display. M6 prepares the missing **backend boundary for full-set local exact capture admission**, without pretending the current V2 Save produces exact fractional observations.

**M6 admits only explicitly supplied ExactLogicalRect(PHASE_CURRENT) objects.** A future separately reviewed actual fractional source must supply these values and map them to the window keys of a *saved* V1/V2 checkpoint. M6 never extracts numbers from V2 integer rectangles to fabricate fractions. Matching window metadata **does not authenticate** the time, compositor, source, selected XDG or final frame of the exact input.

The additive module services/time/MachineV3LocalCheckpointAdmission.py validates the caller's entire collection before writing. It reads the already saved V1/V2 checkpoint from their owners, rechecks the validated legacy/geometry pair and requires **exactly one** candidate for **every** saved checkpoint window, with identical checkpoint-local window key, app ID, output and workspace. Extra fields, partial sets, unknown/duplicate keys, PENDING values, raw dict coordinates, wrong metadata, missing V2 geometry and contradictory authority claims are refused. These are **ordinary local-data consistency** checks, not protected trust.

The existing local M3 store gains the narrowly scoped save_many(checkpoint_id, captures) method. It validates all proposed records *before* opening SQLite. Inside a single BEGIN IMMEDIATE transaction it checks total capacity, rejects any existing v3 row for that checkpoint rather than silently extending a partial set, inserts all rows and commits once. Failed later inserts roll back earlier inserts; no partial successful window set. The old single-window save() remains unchanged; existing v3 format and legacy V1/V2 formats remain unchanged.

The response is explicitly **LOCAL_EXACT_CAPTURE_RECORDED_UNTRUSTED**. No protected source/seat/operator selection, C5 SPENT, native receipt, confirmed frame, actionable Restore, retry or undo flags are produced. Neither ordinary SQLite nor its digest can detect a valid-bit substitution by the same user.

## How to use

**Developer-only API** on an isolated disposable local test checkout. Create an ordinary saved checkpoint through the existing V1/V2 save_pair test owner, obtain exact CURRENT observations from a separately provided candidate source, and call admit_checkpoint(checkpoint_id=..., observations=..., store=LocalExactCaptureStore(...)). A complete set is appended to the v3 file, and the existing M5 read-only preview can display it when a matching checkpoint is explicitly selected.

**Not yet exposed in TimeW UI.** The existing SAVE DESKTOP and MARK flows still do **not** populate v3. No CLI, background worker, compositor process, Quickshell reload, production code path, network access or installer is added. Do not run with real desktop data until the operator separately approves a specific native usage scope.

## Verification and limitations

The new disposable tests create a valid pair of V1/V2 checkpoint records using the real local writer, then submit two independent exact CURRENT values with a one-ULP difference. All V1/V2 reads must remain unchanged. Invalid and incomplete candidate sets must not create v3 DB. The two-window batch must persist atomically, refuse duplication, and preserve exact bits. A trigger that aborts the second INSERT must roll back the first, leaving zero rows for the new checkpoint. Existing partially populated checkpoints cannot be silently extended. Run old M5 read-only preview, M4, M3, V2 and crash-journal regressions.

**No cross-database transaction claim:** M6's v3 transaction is atomic only **within its own separate v3 SQLite file**. It cannot make the original V1/V2 Save atomic with an independently delayed v3 write. A future saved-but-no-v3 outcome is expected to remain visible and recoverable as **local data incomplete**, never cause duplicate automatic Save or Restore.

**Required later boundary:** a reviewed producer for genuine source-side fractional CURRENT values correlated with the saved checkpoint generation. SwayPX output PRESENT is not a selected-view final-frame proof. C3e/C4b/C5 protected provenance, hardware custody and one-use spend-before-effect are separate security integration. Do not treat a matching float or saved UUID as authority.

**NEXT //** Independent Nurse 2 exact-head source/CI review **before operator-controlled merge**. Then independently design opt-in normal Save population once an actual fractional candidate producer exists. Operator-approved installed desktop acceptance remains separate.

**DECISIONS //** UI considered adequate for continued development, polish deferred. Normal TimeW data local now; separately protected hardware/NAS later. Production Restore HOLD.
