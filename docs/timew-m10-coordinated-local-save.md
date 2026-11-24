# TimeW M10 // Coordinated local Save reference

**PATIENT //** The-Post-Apollo-Project  
**ROOM //** TimeW MACHINE · Scope A  
**ROLE //** TimeW owner DOC, external Hospital-compatible; no verified live registration  
**STATE //** Source/CI reference, no active Save wiring  
**PRODUCTION RESTORE // HOLD**

## IMPLEMENTATION

The caller supplies a new original v4 identity, matching validated V1/V2 captured pair, explicit complete exact CURRENT observations and existing local journal/store objects. M10 validates every candidate and its membership before opening a database. It freezes canonical copies, retains the original M9 pair and exact candidate fingerprints in an additive machine.db intent table, and creates the corresponding M9 reservation in the same transaction. It reuses M9's schema, connection, phase and original dispatch implementation; the small coordinated reservation uses the same checked INSERT under the same transaction rather than calling a second standalone prepare. Existing M9/M8/M6 and ordinary Save sources are unchanged.

One explicit save_once invocation:
1. Reserve original identity and candidate fingerprint (no checkpoint yet).
2. M9 dispatch_once commits V1/V2 and original association.
3. Verify ordinary readback. M8 prepares and retains the original fractional candidate set.
4. Persist the actual returned M8 attempt ID as a unique link in machine.db.
5. Record M8's one-way dispatch marker. Recheck M9, M8 and absence of fractional rows.
6. Invoke M6 atomic fractional admission once. Return the same read-only recovery observation used after interruption.

The linked M8 attempt must match the original checkpoint UUID and candidate digest. Recovery does not invoke any write, update a link, create a reservation, resume, repair or retry. Repeated save_once with an existing identity refuses. A missing link (including lost response after M8 prepared but before link commit) is held; do not search for or adopt a similar attempt. A missing/changed ordinary pair, wrong linked attempt, unmarked matching data, partial/conflicting rows or unreadable evidence cannot report coordinated match. Matching all records is only an observed ordinary local match, never verified execution.

## HOW TO USE

Developer reference API only: save_once(identity=..., v1_document=..., geometry_document=..., observations=..., journal=..., store=...). recover(identity, journal=..., store=...) uses retained link and original M7/M8/M9 evidence. No widget, CLI, Sway call or native Restore hook. Identity must be retained by caller; no production caller is supplied.

## VERIFY

Real disposable SQLite and child process exits at reservation, ordinary commit, fractional preparation, link, marker, and successful fractional commit. Observe partial states and refuse repeated invocation. Abort a real second fractional row with an SQLite trigger; ordinary Save persists and no fractional rows commit. Check contradictory links and changed ordinary data; normal legacy path unchanged. Independent M9 review remains outstanding at M10 creation; both milestones require independent review, M10 before merge.

## WATCH OUT FOR

This is not a transaction spanning three databases. Sequential checks cannot eliminate TOCTOU or hidden ABA, and local code/data is not independently protected. Candidate digest is retained before ordinary commit; full exact values are durable only after M8 preparation. Earlier interruption cannot reconstruct lost input, and no automatic continuation is provided. The initial caller must retain ID and capture payload as needed. A local M9-only or M8-only writer is not authenticated by a matching fingerprint. M10 allows 64 intents without eviction; independent M9 and M8 capacities still apply, so an ordinary checkpoint may commit when fractional capacity is exhausted. No hardware power-loss proof, source/time/lifetime binding, C5 consent, protected receipts or installed acceptance.

## NEXT / DECISIONS

Require independent exact-head review and verified genuine SwayPX observation producer. Later explicit Save UI/CLI orchestration must retain caller identity, present honest partial/HOLD results, handle unlinked attempts and retention, and preserve unchanged ordinary Save behavior. UI polish deferred. No merge or workstation activation authorized. Restore HOLD.
