# Forest Core B3 // Synthetic Durable Turn Bridge

STATUS: DRAFT, disposable SQLite + fake Ollama streams ONLY.
OWNER: Forest backend DOC lane. ForestW visuals belong to the separate UI chat.

## What B3 actually does

B0 finds installed model identifiers. B1 stores ordered conversations in an
explicitly injected SQLite connection. B2 streams a response from Ollama.
B3 joins the B1 and B2 interfaces in a synthetic host fixture.

The host must first authenticate an owner and persist the user's message
using B1. B3 requires that a session is OPEN, has the exact expected revision,
and has an already durable final user turn. It writes a unique RESERVED
attempt to SQLite before invoking inference. It streams provisional deltas,
then waits for B2's matching COMPLETE event and for the stream to terminate
normally. Only then does it atomically insert the assistant response, advance
the session revision, and mark the attempt COMMITTED in one SQLite transaction.

The B3 event sequence is:

RESERVED -> STARTED -> DELTA (provisional, zero or more) -> COMMITTED

There is NO successful response on DELTA. A COMPLETE event from a model
is not forwarded as durable success; it must first pass B3 admission and a
successful SQLite transaction.

If transport, SQLite or session verification fails, the attempt becomes
ABORTED. If the host crashes before marking it ABORTED, the durable RESERVED
record remains. Both states prevent automatic replay of the same user's
turn. A future manual/approved recovery protocol must resolve uncertainty.
B3 never claims that a model didn't execute merely because no reply was saved.

## Explicit synthetic setup

These are developer-only Python APIs; they accept an already-open SQLite
connection chosen by the test host. There is no live database opener or
migration CLI in this PR.

First use B1's bootstrap_synthetic(db) in an empty disposable database.
Then call bootstrap_attempts_synthetic(db) explicitly. The B3 table has
a unique (session_id, user_turn_id) constraint and a partial unique index
limiting each session to one RESERVED attempt.

After creating a B1 ForestSessionJournal(db), construct ForestTurnBridge(
journal, clock_ms=verified_host_clock, streamer=explicit_streamer). B3 trusts
neither a user-provided owner key nor arbitrary network/model settings. A
real protected host MUST select the authorized user/database, authenticate
the principal, and approve any local model operation before this bridge is
considered for deployment.

The model identity is recorded per assistant turn. Switching between Granite
and Qwen within one session does not rewrite older conversation history.

## Test

    python3 -m unittest discover -s tests/forest -p 'test_turn_bridge_b3.py' -v

Disposable SQLite files in a temporary directory; all streams are fakes.
This does not load a local model, contact Ollama, access user profiles, create
Hospital rooms, or update the Forest widget.

Checks include completed-turn atomic admission, rollback under an injected
SQLite failure, concurrent duplicate-worker refusal, cancellation and
uncertain restart, owner scope, stale session refusal, bad provider events,
oversized text, preflight invalid endpoint/context, pause, and model history.

## Explicitly NOT ready

This B3 code is not a server, login, Identity/Connections integration, memory
index, safe personal database, production backup, encrypted store or
operator-facing chat application. The B1 database is PLAINTEXT in testing.
Its owner_key is a filter, not authentication. No trusted user/private data
is accepted here. Do not wire ForestW directly to this module or use it to
store personal conversations until storage protection, durable identity,
host IPC, cancellation and recovery are separately approved.

NEXT: independent review, then protected host-owned identity/connection
contract and native Linux acceptance. No automatic retry, promotion to Leaves
memory, permission escalation or silent model switching.
