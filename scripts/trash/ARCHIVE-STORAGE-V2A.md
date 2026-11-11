# Trash++ // Archive Storage V2a and Owner Registry

**Patient:** The-Post-Apollo-Project  
**Room:** Trash++ universal lifecycle  
**Role:** External DOC-compatible, not live Hospital registered  
**Scope:** bounded repository-only implementation, no host writes or merge

## V2a boundary

PR #1793 delivered the V1 source-owned read-only inventory. The original
research_records.py JSON managed-copy store (64 records / 1 MiB) and the GIO
file-trash adapter stay untouched.

archive_store_v2.py adds an isolated Python SQLite snapshot library:
- Immutable owner/resource/source-revision snapshots in transactional storage;
  no delete, restore, burn, migration or original-source readers.
- SHA-256 payload verification, database quick_check and byte accounting.
- SQLite DELETE journaling and synchronous FULL, plus concurrency-safe
  BEGIN IMMEDIATE writes. Interrupted transactions are recovered by SQLite.
- Bounded indexed keyset pagination, metadata-only listings, no payload
  contents shown in discovery results.
- 8 MiB maximum snapshot; 512 MiB default **payload-only** quota; no automatic
  eviction when full. Real disk use (DB pages/journal/filesystem) is higher.
- Only demo-scrape and weather-events owner IDs allowed in this pilot library;
  no source-owned adapter calls it yet, and no widget action reaches it.
- Caller must supply an existing, private user-owned root directory. Symlinked
  database, journal and root are refused. These checks are not an authentication
  boundary against another hostile program running under the same user.
- No actual user records are migrated. Tests use temporary synthetic files.

## Candidate register (not an executable permissions list)

| Owner | Candidate | V1 discovery | V2a source integration | Gate |
| --- | --- | --- | --- | --- |
| Camera / Screenshot | captures, recordings, cleanup queue | Existing Camera cleanup | None | GIO authority |
| Media / Radio | downloaded files, exports and caches | No | None | disposable-only |
| File Service | generated/imported working copies | No | None | path safety |
| Weather events | saved event histories | Yes | None | source revision witness |
| Weather dossiers | saved dossiers | Yes | None | source snapshot schema |
| Weather caches | persistent, place and live-history caches | No | None | cache classification |
| Research / crawler | demo scrapes and downloaded exports | Demo only | None | allowlisted sources |
| Cosmos | calculated exports and observations | No | None | authored vs derived |
| Apollo Hub Notes | note metadata | Yes | None | reversible copy first |
| Apollo Hub To-do | task metadata | Yes | None | project-link recovery |
| Projects / TASKS | SQLite tasks and project snapshots | No | None | owner-owned database |
| Favorites | favorites/collections and locations | No | None | reference integrity |
| Clock / Angels / Alarm | observations, saved alarms | No | None | schedule dependencies |
| Notifications | histories and attachments | No | None | privacy retention |
| Phone / Messaging | attachments and exports | No | None | multi-party privacy |
| Time Machine | checkpoints and layouts | No | None | protected continuity |
| Git / GitHub | diagnostics and generated reports | No | None | never rewrite Git history |
| Hospital | reports, transcripts and checkpoints | No | None | evidence and records holds |
| Finance | drafts and temporary exports | No | None | transactions protected |
| Company / Social | portfolio and organization copies | No | None | organization authority |
| Identity / Connections | temporary diagnostics | No | None | signed ledgers protected |
| Network / CPU++ | telemetry snapshots, exports | No | None | private diagnostic data |

Presence here conveys no permission to delete or copy source records. In
particular, authoritative financial transactions, signed trust ledgers, audit
history and Hospital evidence are not eligible for generic Burn.

## Developer verification

Run: python3 -m unittest discover -s tests/trash -p 'test_*.py' -v

The V2a API is an importable developer library and **not** a live Trash widget
control. Example: instantiate ArchiveStore(temporary_private_directory),
call save() with synthetic validated bytes, check read_verified() and verify().
There is intentionally no CLI mutation verb.

## Next gates

1. GitHub CI + independent security review, including real disk overhead and
   directory-race attack model.
2. Owner-specific disposable Weather/research snapshot adapters, verifying
   exact original revision, schema and content before saving.
3. Read-only V2 paginated Archive screen with clear source-vs-copy labels.
4. Separate consent for Restore writers, retention rules, Burn receipts,
   production host installation, data migration and protected owners.
5. Native four-size Quickshell and crash/restart acceptance with test data.

## Recovery and rollback

Inspect branch feat/trashpp-archive-store-v2a-20261110 and its draft PR.
Revert the new library/test/document files if needed. V1 storage, GIO Trash,
Camera Cleanup, owner writers and the current widget remain unaffected.
