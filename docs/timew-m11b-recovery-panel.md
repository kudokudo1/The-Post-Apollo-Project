# TimeW M11b // Read-only Save recovery panel

**PATIENT //** The-Post-Apollo-Project  
**ROOM //** TimeW MACHINE / Scope A  
**ROLE //** TimeW owner DOC, external Hospital-compatible; live registration unverified  
**STATE //** Source/CI integration, installed native acceptance pending  
**PRODUCTION RESTORE // HOLD**

## IMPLEMENTATION

A separate MachineSaveRecoveryPanel is mounted in the existing MACHINE capture pane, following ordinary Save status and before Brave preview. It uses existing ActionButton and GohuText components. It has its own Process and no write, Save, Restore, adoption, retry or repair entrypoint. Existing root Process count and actual Save/MARK/Customize/STORED handlers stay unchanged. Opening the panel does not read. Refresh and inspect are explicit clicks; selection arrows only change the selected original UUID.

Each explicit request gets a fresh canonical v4-shaped local correlation token from a monotonically increasing 48-bit sequence within the component lifetime; it is not random, cryptographic or a source credential. Selection, closing the panel, leaving MACHINE/capture, closing the window or a competing ordinary operation invalidate results. An in-flight read remains busy until both stream completion and process exit, irrespective of signal order. Only normal exit, bounded JSON, matching token/mode/identity and M11a display-policy acceptance can populate results. A one-shot 45-second deadline invalidates the token and displays HOLD; it never starts a second Process or retries. If required completion signals never arrive, the panel remains blocked rather than risk reusing that Process; native launch-failure recovery must be separately verified.

## HOW TO USE

After authorized installation: TimeW → MACHINE → SAVE RECOVERY // READ ONLY → REFRESH LOCAL ATTEMPTS → select with arrows → INSPECT ORIGINAL ATTEMPT. Ordinary and fractional outcome lines are separate. Full UUID allows manual correlation of attempts with no saved checkpoint. Close or navigate away to discard the view. Current Save remains the existing path; it does not create these coordinated intents, so a normal installation may have no entries. No automatic reading, polling, retries or restore authorization.

## VERIFY

Run actual extracted QML JavaScript functions and lifecycle handlers with the real M11a JS policy in a Node VM, stubbed process and timer boundaries. Verify explicit launch, list/inspect, wrong identity/token, malformed/oversized response, nonzero/abnormal exit, both signal orders, concurrent refusal, selection/close/mode/busy/timeout invalidation and no replay. Python M11a real SQLite and existing M10/M5 regressions remain unchanged. This is not a native QML load/render or Quickshell signal observation; native installed/disposable acceptance still needed. M11a was merged before independent review; M11b is draft and requires independent review before merge.

## WATCH OUT FOR

Local records only, not verified original execution or source/consent/native receipt. Read-only UI does not solve unlinked intent adoption, retention or durable caller input. A missing process completion can keep panel blocked; no automatic Process replacement. Actual fractional producer and active Save integration remain separate. No live host modifications or activation.

## NEXT / DECISIONS

Obtain M11a retrospective review and M11b exact-head independent review; perform controlled UI acceptance before treating it as installed. Keep Save and Restore authorization separate.
