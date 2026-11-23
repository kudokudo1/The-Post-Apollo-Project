# Forest Core B5a // Disposable Host-Boundary Mechanics

PATIENT: The-Post-Apollo-Project
ROOM: Forest B1/B3/B4 native-host staging
STAFF ROLE: Forest backend DOC successor, external Hospital-compatible
PRODUCTION: HOLD
STATE: SOURCE-ONLY synthetic fixtures, not a protected host

## IMPLEMENTATION

This milestone adds a **test-only** model for the two exact Forest Core
seams identified in issue #2161. It does NOT implement a production host,
socket, installed service, registered process, private DB, C5 permission,
recipient authentication, or any model execution. No ForestW or Connections
source changes.

### A. Synthetic LIST_SESSIONS database projection

The existing B1 sessions(owner) queries all Trees and applies LIMIT 100
before a renderer filters one Tree. That can suppress a selected Tree's
sessions if 100 newer sessions belong to another Tree.

The new list_disposable_tree_fixture accepts an already-open SQLite
in-memory B1 fixture ONLY. It explicitly rejects disk-backed databases,
attached files, active transactions, missing schema, and malformed
syntactic owner/Tree labels. It binds owner and Tree and state OPEN
**inside one SQL SELECT before the LIMIT**. A 101st authorized-scope
candidate makes the entire fixture refuse, rather than falsely claiming
a complete 100-row snapshot. It validates exact seven metadata fields,
UTF-8 title length, timestamps, revision, private-control characters,
and overall serialized byte cap.

The output is deliberately NOT the proposed ForestW LIST_SESSIONS wire:
it has status DISPOSABLE_ROWS_UNAUTHENTICATED, uses rows rather than
sessions, carries no UI action, and always sets sourceAuthenticated,
permissionGranted, canListSessions, mayDiscloseTitles and
productionAuthority to false. Even a plausible owner/tree filter is
only synthetic fixture selection, NOT user authentication or C5 consent.
A fixture may contain synthetic titles for testing but cannot open a
private user database. The five UI presentation keys remain noncanonical
until independently mapped by security and Forest owners.

### B. Blocked provisional text observer

B3 exchange yields in-process provisional DELTA chunks before its final
pre-COMMIT authorization. There is still no real Forest-owned external
send/FD boundary, enrolled recipient, or C5 revocation serialization.

BlockedProvisionalEgressFixture only inspects synthetic B3-shaped DELTA
values and counts input UTF-8 bytes. It stores no text, emits zero bytes,
performs no sink/callback/IPC/network/file operation and cannot grant
permission. It refuses malformed frames, forged grant fields,
over-budget data and post-revoke chunks. A revoke request or subsequent
fence_ack returns UNKNOWN_HOLD with revocationFencedAck=false, even if
the fixture observed no sends; it cannot authenticate kernel queues or
external recipients. This is a negative security contract, not a native
lock implementation.

## HOW TO USE

No desktop UI change. Run disposable tests from the repo root:

    python3 -m unittest discover -s tests/forest -p 'test_host_boundary_fixture_b5a.py' -v

No CLI that enumerates native user sessions or posts to Ollama is added.
Do not point this module at live personal storage, wrap it as an
authenticated host, or connect fixture rows to ForestW.

## VERIFY

CI runs fake in-memory SQLite and synthetic event tests, B1 session
journal, B3 turn bridge, B4a host admission, and ForestW's source-only
LIST_SESSIONS policy (when available on CI). No real Ollama, private
database, user seat, message write, model response or OS sender is used.

Negative tests establish:
- per-owner, per-Tree and OPEN state SQL pre-LIMIT filtering;
- no truncated 100-row snapshots and no title/body/owner leakage;
- refusal of disk-backed DB, attached DB, active transaction;
- malformed or overlong titles/time fields and byte cap;
- hold-only egress, invalid forged positive fields, UTF-8 budget,
  irrevocable local revoke and no false native-fence ACK.

Passing CI demonstrates test-contract behavior only, not a genuine
trusted original process, authenticated issuer or protected revocation.

## WATCH OUT FOR

The query fixture is **deliberately in-memory only**, so it is not the
approved native LIST_SESSIONS provider. For actual protected storage,
the separately enrolled native Forest host must choose a trusted user
database and canonical Tree scope from independent custody evidence.
DOC 3 must authorize LIST_SESSIONS separately from READ_SESSION,
GENERATE, DISCLOSE_PROVISIONAL and COMMIT_GENERATE, including explicit
private-title policy. ForestW has recommended masked titles by default,
but final operator privacy choice is pending.

The egress fixture never calls B3 or Ollama and does not establish
real send admission. Protected future streaming needs a host-owned
serialized send/queue boundary that checks live one-use permit, exact
recipient, epoch/expiry, bytes and cancellation; it must coordinate
C5 revoke generation with outstanding sends and distinguish revoke
request from fenced ACK. Already submitted bytes cannot be recalled.

## CHECKLIST

- [x] Source scope aligned to Forest Core issue #2161
- [x] No change to B1/B3/B4/C5/ForestW existing behavior
- [x] Source-only in-memory DB and drop-only egress
- [ ] Exact-head CI and independent Forest Nurse 2 review before merge
- [ ] Operator merge/final acceptance
- [ ] Forest-specific native original-host identity/custody from DOC 1/2
- [ ] DOC 3 one-use title-read and provisional-disclosure policies
- [ ] Approved native send serialization/revocation integration
- [ ] Protected at-rest data, native tests and explicit production approval

## NEXT / DECISIONS

Forest Core proposes accepting these negative mechanics as a disposable
reference. Real native host API and recipient FD/channel remain REVISE,
not implemented. Synthetic LIST_SESSIONS contract remains distinct
from the #2362 presentation validator. No grants, hostConnected, SEND,
voice, live private titles or native GPU benchmark are authorized.
Forest production stays HOLD.
