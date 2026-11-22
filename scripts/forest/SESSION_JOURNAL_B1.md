# Forest Core B1 // Synthetic Durable Conversation Journal

> STATE // draft, disposable-test-only data design. No production activation.

## WHY

Forest needs a conversation to outlive the QML window, a specific local model,
or a replaceable AI worker. This is the first minimal conversation record
contract, not Leaves personal memory, Hospital protected worker history, an
authentication service, or an agent runtime.

The SQLite schema has two tables:

- forest_sessions: stable session, syntactic owner key, Tree key, title, state,
  revision, and timestamps.
- forest_turns: append-only ordered turn body, role, time, provider and model
  per turn. One Tree conversation can switch models without being recreated.

All meaningful mutations require an explicit method call. A stale revision
fails rather than overwriting another worker's update. SQLite transaction
rollback prevents a turn from surviving if its matching session revision cannot
be committed.

## BOUNDARIES

ForestSessionJournal accepts an already-open SQLite connection. It does not
choose a home directory, create a live database, unlock encryption, issue
a user identity, or run an Ollama/Hermes process. bootstrap_synthetic(db) is
an explicit fixture initializer that refuses existing/unknown schema state.

The supplied owner_key is only a filtering value. IT IS NOT AUTHENTICATION
OR A SOURCE OF AUTHORITY. Do not use a client-supplied owner key to allow
access to someone else's sessions. A future protected host must select the
correct per-user database and verify the requester's current rights through
Post-Apollo Identity/Connections BEFORE calling this library.

All text is stored as PLAINTEXT in the disposable fixture. That is
NOT approved for live private memories. Encryption-at-rest, backup/recovery,
source retention, searchable Leaves, data deletion, identity binding,
file/symlink safety, authorization, and trusted native Linux tests are not
implemented. The UI worker must not start using B1 for user data yet.

## VERIFY

    python3 -m unittest discover -s tests/forest -p 'test_session_journal_v0.py' -v

Runs only temporary SQLite fixtures. Tests include second-connection recovery,
switching from Qwen to Granite within one conversation, owner-based scoped
queries, stale worker rejection, failed-transaction rollback, pause/resume,
terminal archive, bounded text, and unknown-schema refusal.

## CONTINUATION

B0 Ollama inventory lives on a separate PR. Neither B0 nor B1 is wired to
ForestW. When a trusted local host, a session permission model and private
storage/backup policy have been approved, a separate integration milestone can
connect Forest's chat UI to this journal. Personal Leaves knowledge requires
a distinct, operator-owned schema and privacy review, not a silent promotion
of all conversation text to permanent memory.
