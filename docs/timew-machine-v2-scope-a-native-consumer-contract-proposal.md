# 🏥💜 TimeW MACHINE // Scope A protected native consumer contract

**PATIENT //** The-Post-Apollo-Project  
**ROOM //** TimeW MACHINE · Desktop & Brave Recovery  
**STAFF //** External Hospital-compatible DOC, live registration unverified  
**STATE //** TIMEW OWNER-SIDE PROPOSAL FOR JOINT REVIEW · NOT AN ACCEPTED NATIVE INTERFACE  
**DECISION ALREADY MADE //** Scope A first: operator-selected **existing** same-session floating surface, geometry only. Scope B Brave-window identity later.  
**UPSTREAM //** Merged Connections C3e [RFC #2115](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2115) and TimeW CI-fusion [#2114](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2114).  
**COORDINATION //** [Issue #2067](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2067)

## 1 // Mechanism, scope and ownership

A real restore of **one already-live selected window** has at least two separate side effects: resizing, then moving. A saved SQLite rectangle, compositor IPC container ID, app/PID/title, or correctly signed **caller-supplied fixture** cannot establish the identity and current lifetime of the physical Wayland surface. TimeW must not execute merely because these values agree.

TimeW is the **consumer of independently protected evidence**, not the owner of the selection hook, native signer enrollment, human consent or privileged geometry authority.

| Owner | Supplied evidence or action | Explicitly not supplied by TimeW |
| --- | --- | --- |
| SwayPX | Real operator-selected surface, native object lifetime/generation, active seat/session, live geometry and revocation, protected guarded command/acknowledgment | A browser UUID, consent, or proof from ordinary focus / GET_TREE |
| C3e/C4b | Independently enrolled producer/root/release/process/host provenance, audience-bound fresh challenge, source admission and revocation | C5 consent, TimeW authorization from a CI signature |
| C5 | Visible exact-action consent for selected surface + saved checkpoint/window key + before and target rectangles, active unlocked seat, **protected one-use spend before any command** | A Hospital recovery grant or a generic UI boolean |
| TimeW | Match checkpoint and geometry, request protected rechecks, record durable operation intent/outcomes, refuse on ambiguity | Production trust root, compositor-selected object authority, silent retry |
| Nurse 2 / operator | Independent security and native acceptance, separate merge/install/release decisions | Acceptance merely because a document or fixture test passes |

**Open contracts in this document are proposed requirements, not chosen wire field names, socket paths, installed identities or a production permission.** Do not silently activate on the basis of an RFC merge or an NRS-2 scoped CI PASS.

## 2 // TimeW-consumed evidence, all required together

Each proposed native Scope A operation must be bound to **one exact intent**, not just a window class. A protected operation should correlate:

- **Selected object:** protected compositor boot epoch, live surface lifetime/generation, transient container ID, exact authenticated seat/session, selected floating/nonfullscreen state, output/workspace, before-geometry, and explicit operator-selection event. Neither a reused ID nor focus counts.
- **Saved target:** one immutable loaded V2 checkpoint ID + saved window key and the specific target rectangle, with a digest or equivalent bound to the signed source and separately to C5 consent.
- **Producer:** independently pinned approved compositor/release/host/process/seat proof under the TimeW-specific audience, fresh C3e challenge and protected replay/revocation rules. Host/process IDs, test keys and release fields cannot be chosen by an untrusted client as its own trust anchor.
- **Consent:** distinct C5 TimeW action, visible reviewed selected surface and exact before/target geometry, current unlocked seat, protected grant identity and irreversible one-use **spend**. A grant can cover the reviewed **two-command operation**, but is consumed **once before the first side effect**, never separately retried for the second command.
- **Outcome:** per-command protected compositor receipt tied to the same selection, issuer release/epoch, operation and spent grant, plus fresh after-command observation. An ordinary shell command exit code or untrusted Sway JSON acknowledgment is not enough to conclude that the exact selected live object reached its target.

A proposal for source evidence fields must be versioned separately from Brave `PAIR_SCHEMA=post-apollo.timew.external-window-pairing.v1`. No invented `browser_window_ref`, Brave session/token, tab content, title/PID match, or Scope B restart inference is acceptable.

## 3 // Proposed TimeW-side fail-closed state transitions

| Stage | Required observation / commit boundary | Refusal / recovery |
| --- | --- | --- |
| `INSPECT` | Read V2 saved checkpoint, select one live surface via **protected SwayPX action**, compare target and actual current rectangle | No witness, ambiguous same-app windows, changed monitor/surface, or mismatched saved key: **HOLD; no side effects** |
| `PROPOSE_INTENT` | Bind exact selected lifetime, source challenge, checkpoint and before/target rectangle to pending C5 review; preview only | Consent not yet approved or seat locked: **HOLD** |
| `PREPARE` | Durable TimeW operation entry with exact request/receipt correlation and no action yet | Local journal failure: **HOLD before spend/dispatch** |
| `SPEND` | C5 independently verifies exact intent, active seat/source, then **durably spends** the one-use grant before any command | Refusal or unknown spend outcome: **UNKNOWN/HOLD**, never infer unspent |
| `DISPATCH_INTENT` | Durable TimeW dispatch marker correlated with the **already spent** C5 operation; both authorities must agree before side effect | If C5 says spent but local marker lost, or vice versa: **UNKNOWN/HOLD**; do not re-consume/reissue |
| `RESIZE_GUARDED` | SwayPX atomically or equivalently protects current selected object's lifetime and exact pre-command state; performs only approved resize | Revocation, timeout, crash, uncertain reply/partial action: **UNKNOWN/HOLD** |
| `OBSERVE_RESIZE` | Independently recheck same exact surface, actual resulting rectangle and issuer/seat; compare against **SwayPX-owner-approved real compositor resize rule** | Unexpected x/y, dimensions, object identity or monitor state: **UNKNOWN/HOLD**, do not silently assume old x/y |
| `MOVE_GUARDED` | Revalidate the **same** spent operation and protected live object immediately before second action, against newly observed resize geometry. Must be within owner-approved provenance/expiry policy | Lease expired, source/seat locked, changed surface or ambiguous prior resize: **UNKNOWN/HOLD**, no new grant or automatic retry |
| `OBSERVE_FINAL` | Protected native observation matches exact target geometry and selected lifetime; correlate exact operation receipts | Missing/uncertain acknowledgment: **UNKNOWN/HOLD**, even if a later ordinary GET_TREE seems plausible |
| `COMPLETE_VERIFIED` | Durable TimeW completed record only after native evidence, protected spend and final state can be independently reconciled | A CI fixture's `verified_fixture_placement` is **not** production completion |

**Critical crash gap:** the existing TimeW `MachineV2GeometryJournal.py` is an owner-private SQLite ledger used by the disposable pilot, with `prepared`, `dispatching`, `uncertain_requires_review`, and `verified_fixture_placement` phases. It is **not C5's independently protected one-use spend authority**. A crash after spend but before a local dispatch record cannot be classified as unspent merely by reopening SQLite. Reconciliation must query the *protected* C5/source records; absent independent proof, keep UNKNOWN/HOLD. If a local record exists but the protected spent ledger is unavailable, HOLD. No fallback to replaying a command.

The existing `MachineV2FloatingPilot.execute_disposable` is **CI-only** and uses `swaymsg` commands; it is not an approved secure native dispatch implementation. Its current assumption that x/y are unchanged after resize must be verified against the real SwayPX version and explicitly accepted or revised before production.

## 4 // Required native acceptance evidence, not yet collected

| Test | Expected safe outcome |
| --- | --- |
| Two Brave windows share PID/app/title; operator explicitly selects second | Only the compositor-attested second surface is bound; no fallback to arbitrary matching window |
| Copy valid CI source/signature but no independently installed issuer or true selection event | Refuse production source |
| Compositor restarts or con ID is reused during a pending operation | Old lifetime invalid; stop, cannot attach to replacement |
| Surface closes after C5 spend and before resize | No command; spent outcome reconciled, UNKNOWN/HOLD where necessary |
| C5 spends grant, TimeW crashes before local `DISPATCH_INTENT` | No retry and no assumption grant remains reusable |
| Resize succeeds but move acknowledgment is lost | Preserve UNKNOWN/HOLD, prohibit blind move, redo or undo |
| Resize changes x/y legitimately due to compositor constraints | Do not apply synthetic original-x/y assumption; require owner-approved post-resize state/next target |
| Source challenge expires after resize and before move | Do not move; maintain spent operation, UNKNOWN/HOLD |
| Seat locks, user switches session, SwayPX selected object unmaps, output/workspace changes | Revoke protected selection and stop before next side effect |
| Another unrelated window changes | Apply the **scope of inventory** actually bound by the native witness. Fixture freeze-all is not automatically a production rule |
| Signed Hospital RECOVER or old Brave PAIR v1 token substituted | Wrong audience and role: refuse |
| Native receipt exists but final protected live observation unavailable | No `COMPLETE_VERIFIED` |
| TimeW restarted with `prepared`/`dispatching` local record | Read-only manual-review screen; no automatic completion, retry, undo or reassignment |

## 5 // Concrete owner decisions requested

**TimeW (this owner-side proposal):** TimeW accepts in principle the distinct **selected current live surface, same-session geometry-only** mode already selected by the operator. Recommend **REVISE** on RFC #2115's undecided native details: operation-bound C5 spend **before first command**, crash-safe cross-authority reconciliation, per-command current state, protected receipts, and real post-resize geometry semantics must be specified before TimeW can implement a privileged consumer. A proposal is not a unilateral binding acceptance.

**SwayPX:** `ACCEPT / REVISE / HOLD` the compositor-internal explicit selection/lifetime origin, guarded operation and native command/receipt behavior, particularly whether resize moves x/y. Do not conflict with paused Company Map, autoscroll or gray-screen-recovery owner branches.

**C3e/C4b:** `ACCEPT / REVISE / HOLD` the separately enrolled producer, protected challenge/revocation, active-seat and source/receipt lifecycle. Source-only #2107 / TimeW #2114 establish **fixture format consistency only**.

**C5:** `ACCEPT / REVISE / HOLD` the exact geometry intent, one-use spend before side effects, active/unlocked seat, ambiguous spend/crash reconciliation and no-retry. Keep Hospital authorizers/signing keys separate.

**Nurse 2:** Independently review this proposed TimeW consumer transition model and the later actual native code/host evidence as **separate** scopes.

**Operator:** Maintains final authority for acceptance, PR merge, installation, workstation changes and production activation.

## VERIFY / NEXT / DECISIONS

This is a **documentation-only technical interface proposal** for [issue #2067](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2067). No native code or contract is activated; source-only tests and reviews from prior PRs do not verify this document's future implementation. Do not edit other workers' code or create a privilege bridge by reusing fixture signers.

**PRODUCTION RESTORE HOLD. Scope A first, Scope B afterward.**
