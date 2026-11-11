# Trash++ // V2b Source-Witness Snapshot Pilot

PATIENT // The-Post-Apollo-Project
ROOM // Trash++ universal lifecycle
ROLE // External DOC-compatible, live Hospital registration unverified
SCOPE // Bounded GitHub-only pilot; no host writes, merge or activation

## IMPLEMENTATION

The owner_snapshot_adapter_v2.py module reuses the existing fixed-path,
allowlisted V1 research_records.py Weather/demo read-only source validators.
No new generic file scanner or source writer is introduced.

- preview_demo(url, observed_at) and preview_weather(event_key,
  last_captured_ms) return metadata only: owner, hashed record ID, capture
  timestamp, safe label and SHA-256 of the selected normalized record.
- capture_demo and capture_weather explicitly re-read the source item, verify
  source schema and selected identity/timestamp, and require the expected
  SHA-256 witness from preview before passing a copy to V2a ArchiveStore.
- Changes to an entry with the *same* timestamp are detected, not silently
  accepted. Duplicate exact content cannot be saved under the same
  owner/resource/revision identity.
- Weather covers only existing GDACS, USGS, EONET and FIRMS archive records.
  Demo crawler covers only the existing quotes.toscrape.com allowlist, never
  Finance accounts, transactions, SEC filings or arbitrary URLs.
- Source files and owners' writers remain untouched; the archive copy is an
  independent immutable record with SQLite transaction and payload checksum.
- This module is **not connected to the Trash++ UI or any scheduled task**.
  No source deletes, Restore, Burn, automatic migration or generic write
  permissions are included.

## VERIFY

Run from project root:

    python3 -m unittest discover -s tests/trash -p 'test_*.py' -v

Synthetic tests cover stale witnesses, same-timestamp content rewrites,
symlinks, missing sources, invalid hosts and identities, duplicate refusal,
independent payload integrity, no source changes and no destructive verbs.
No actual live user data is involved.

## WATCH OUT FOR

Witnesses prove equality of a selected item at the instant it is read; they
are not authorization credentials or proof the source stays unchanged later.
A captured record can become stale after the copy operation completes.

For a future live integration, data/home roots MUST be provided by the trusted
host service, not a dynamic source item, page or untrusted UI argument. The
V2a archive DB's SHA-256 currently protects payload contents but not all
metadata fields independently. An independent security review is needed
before trusting restore/delete/retention decisions to it.

SQLite payload quotas are not disk usage limits (metadata, pages, journal
and filesystem overhead are separate). No auto-expiry is implemented.

## CHECKLIST

- [x] Reuse old owner-validated readers, not another scanner
- [x] Explicit preview/capture witness contract
- [x] Standalone tests with disposable fixtures
- [ ] Confirm full CI and resolve failures
- [ ] Independent security review
- [ ] Owner-approved read-only V2 UI display (future branch)
- [ ] Native four-size Quickshell verification (not yet applicable)

## NEXT

After successful CI and independent review, add a source-vs-copy distinction
to a read-only V2 page with paginated lists. Only then consider explicit
source-approved snapshot operations for Weather dossiers and disposable
research exports. Restore, Burn, protected owners, host installation and
production activation require their separate gates.

## DECISIONS

Keep original V1 managed research JSON, GIO Trash, Camera Cleanup, and all
source writer code unchanged. The pilot's authorizing condition is a specific
operator-requested source revision witness, not a source-wide permission.
Rollback is simply reverting the new adapter/test/doc without migrating data.

Recovery branch: feat/trashpp-owner-snapshot-adapter-v2b-20261110
