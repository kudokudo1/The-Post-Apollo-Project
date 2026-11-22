# Forest Core B4a // Host-Injected Admission Contract

STATUS: EXPERIMENTAL synthetic contract, NOT production authentication.
PATIENT: The-Post-Apollo-Project
ROOM: Forest Core backend // B4a host admission
STAFF: external Hospital-compatible DOC, no live Hospital registration.
OWNER: backend lane only. ForestW UI and Identity/Connections remain separate.

## Mechanism and responsibilities

Forest B0 reads available local models. B1 records synthetic sessions in an
injected SQLite connection. B2 performs bounded local streaming. B3 pairs
successful inference with durable reservation/commit transactions.

B4a is an IN-PROCESS contract for a future protected host. A client supplies
only an exact small intent: READ_SESSION or GENERATE with a random request ID,
session ID and (for GENERATE) chosen model and expected revision. The client
cannot supply a principal, owner key, peer UID, approval, seat, token, file
path, prompt body or agent tools. Client-provided request IDs correlate
responses but do not constitute authorization or replay defense.

The independent host must already have read Linux peer credentials and
cryptographically or otherwise strongly verified the installed caller,
its process lifetime/witness identity and current seat. B4a's KernelPeer is
only a test carrier for that HOST-OWNED evidence, not client-side JSON.

The host injects TWO mandatory, distinct callbacks:
1. verified_peer(KernelPeer, now_ms) -> VerifiedCaller | None
   It verifies the live caller and resolves the correct principal/owner.
2. approved_intent(VerifiedCaller, action, sessionId, model, now_ms) -> bool
   It checks current policy for THIS operation, model, resource and consent.

Both run before any journal read or generation reservation. A non-exact True
permission result is denied. The only read response contains bounded session
ID, Tree key, state and revision, never conversation body, owner or title.
Generate delegates to B3 only when explicitly authorized; B3 still requires
a pre-committed user turn and fences old revision/duplicate worker execution.

This code has NO socket listener, user account, cryptographic verifier,
credential store, persistent daemon, Qt UI, host file opener, model loader,
or automatic registration in Hospital. It is deliberately not exposed to
other processes or to untrusted code in the same Python process.

## Test

    python3 -m unittest discover -s tests/forest -p 'test_host_admission_b4a.py' -v

Uses temporary synthetic B1/B3 SQLite and fake model events. No installed
Ollama, live service, real identity, user data or desktop UI is needed.

## Safety / unresolved requirements

- VerifiedCaller is a plain Python object and IS FORGEABLE within a process.
  It is NOT a cryptographic identity or privilege boundary.
- A same-UID Unix socket and SO_PEERCRED alone are INSUFFICIENT to establish
  a trusted program. Reuse C3e/C4b installed identity and C5 consent/permission
  contracts through the security-owner integration rather than copying code.
- B4a verifies at START, not before every final B3 durable COMMIT. Revocation
  during an ongoing response is not guaranteed. A production implementation
  MUST add trusted pre-COMMIT reauthorization (and cancel/close transport on
  revoked permission), plus lost-ack reconciliation and protected receipts.
- B1 and B3 are unencrypted plaintext SYNTHETIC fixtures. This code must not
  be connected to real conversations or memories without protected per-user
  data custody, backups, deletion and native filesystem security review.
- A future listener must bind a trusted owner-private directory, validate the
  Unix peer, verify process identity/seat via host-owned evidence and enforce
  bounded framing. The B4a module does NOT implement those steps.
- No unrestricted tools, desktop actuation, cloud fallback or Hermes authority.

## Scope and ownership

This PR changes only scripts/forest/host_admission_b4a.py, its tests, docs
and one dedicated CI workflow. No ForestW, ApolloHub, shell, Identity,
Connections, or Hospital source is edited.

NEXT: independent review and native-host boundary design with existing
Connections owners. Production use remains on HOLD until real caller binding,
revocation-at-commit, storage and consent checks are independently verified.
