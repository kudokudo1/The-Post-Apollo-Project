# TimeW M11a // Local Save recovery display contract

**PATIENT //** The-Post-Apollo-Project  
**ROOM //** TimeW MACHINE · Scope A  
**ROLE //** TimeW owner DOC, external Hospital-compatible; live registration unverified  
**STATE //** Read-only adapter and display policy, no active widget wiring  
**PRODUCTION RESTORE // HOLD**

## IMPLEMENTATION

An explicit read-only adapter lists bounded retained M10 intent UUIDs directly, including interrupted attempts that never created ordinary checkpoint rows. This is not a scan of saved checkpoints or an adoption of unlinked M8 attempts. Discovery reads one SQLite snapshot; checks the existing private path and association schemas, bounds at 64, validates each coordinated row and original association, and exposes sorted UUIDs only. Unavailable or inconsistent storage produces a generic HOLD packet rather than an invented empty result.

Inspect by exact original UUID through the existing M10 recovery owner. A strict versioned response projects only the correlated original identity and request token, mode, allowed ordinary and fractional outcome codes, linked attempt identity, and explicit denial flags. Unknown fields, inconsistent combinations and authority-bearing results are refused. No checkpoint documents, geometry, fingerprints, labels, paths or exceptions are exposed.

A pure JS display policy independently validates exact shape, IDs, status combinations, bounded sorted list and all denials. It returns only display text and list UUIDs. The future UI must provide a fresh request UUID per action and invalidate pending requests on selection change, close or mode exit. Merely reusing an ID is not a freshness guarantee; no current QML handler is implemented.

## HOW TO USE

Development API only: MachineV3LocalSaveRecoveryUiRead.py list REQUEST_UUID or inspect REQUEST_UUID ORIGINAL_UUID (Python -B -I). A valid invocation returns one bounded JSON packet. Invalid invocation exits nonzero without echoing input. MachineV3LocalSaveRecoveryPolicy.js accepts the packet with the current request token, mode and selection. No UI buttons call it yet. Existing ordinary Save, MARK, customize, preview and restore code untouched.

## VERIFY

Disposable real SQLite tests include empty local data, original reservation without checkpoint, ordinary pair with unlinked fractional intent, linked missing rows, complete local observation, contradictory link and corrupt association, unsafe permissions and unchanged files. Independent Node tests cover mapping of all allowed M10 outcome tuples, identity/request mismatch, forbidden authority flags and malformed/oversized discovery. Existing M10 through M6 and M5 preview regressions run unchanged.

## WATCH OUT FOR

Neither list nor inspect proves an original Save executed, source freshness, authenticated native state, consent or protected Restore. All results are local observations; three databases remain independent and may change between reads. Listing a UUID is not proof of a committed checkpoint. Empty listing only means no coordinated intents observed. Recovery never retries, repairs, adopts, dispatches, deletes or changes a link. Private same-user metadata remains mutable. UI request-token generation, Process lifecycle, selection invalidation and user-facing controls still require M11b. Genuine fractional source and active Save wiring are separate.

## NEXT / DECISIONS

Independent exact-head review, then wire explicit recovery list/inspect controls into MACHINE without changing existing Save. No merge, workstation or production activation authorized. Restore HOLD.
