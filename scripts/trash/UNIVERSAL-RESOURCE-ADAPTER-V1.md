# Trash++ Universal Resource Adapter V1

**Scope:** read-only owner resource discovery. This is a technical interface contract for this repository, not a new Hospital governance rule or authority grant.

## Why this exists

Trash++ already has separate working GIO system-file deletion and a bounded store for copied demo scrapes and Weather event snapshots. Neither should acquire permission to edit a third widget's original JSON, SQLite, audit record, or checkpoint merely because it appears in a common list.

The current indexed envelope is `post-apollo.trash-resource.v1`:

| Field | Meaning |
| --- | --- |
| `resourceContract` | Fixed version of the read-only discovery envelope |
| `ownerId` | Explicit source owner, never inferred from an arbitrary path |
| `resourceId` and `id` | Stable owner-namespaced display identity |
| `source`, `kind`, `title` | Bounded display metadata |
| `recordedAtMs`, `recordedAt`, `details` | Bounded timestamps/details; no private body payload |
| `capabilities` | Advertised read/copy and lifecycle permissions, with write actions defaulting to false |
| `retention` | Source-owned read-only authority warning |

The index returns a separate `sources` status entry for **each fixed allowlisted source**. An unavailable/malformed/unsafe source reports its status without inventing data or disabling all other owners. Only `index` is a permitted CLI verb.

## Read-only allowlist

| Owner ID | Source store | V1 behavior |
| --- | --- | --- |
| `weather-events` | `weather-event-archive-v1.json` | Index; existing separately validated SAVE COPY |
| `weather-dossiers` | `weather-dossier-archive-v1.json` | Index only |
| `demo-scrape` | Existing allowlisted quotes.toscrape.com crawl export | Index; existing separately validated SAVE COPY |
| `apollo-hub-notes` | `apollo-hub-notes-v1.json` | Index note ID/title/revision/time only; never body |
| `apollo-hub-todo` | `apollo-hub-todo-v1.json` | Index task ID/title/done/time only; never description/draft |

The first three were already indexed before V1. Hub Notes and To-do are the new discovery adapters. No owner service or source file is modified; these are one-shot reads of fixed filenames with regular-file and size checks.

**Important:** A `saveCopy: true` flag refers only to the *already existing* validated independent copy action for Weather events or the demo scrape. An indexed row's `archive`, `trash`, `restore` and `burn` flags remain **false**, including for Notes and To-do. The managed-copy store is a separate resource authority, not proof that an original source may be deleted.

## Remaining universal lifecycle assignments

1. **Shared storage contract:** Implement source-supplied immutable snapshots, stable resource generations, atomic durable manifests, bounded file/blob storage, leases and crash recovery. Do not widen the current 64-record/1 MiB managed-copy store by simply raising constants.
2. **Camera/media exports:** Inspect the Camera-owned queue/GIO handoff and add selected generated media/export adapters without duplicate deletes or bypassing GIO.
3. **Weather & web research:** Add dossier and disposable cache copy adapters with source-specific schema, retention and exact revision witnesses; keep evidence originals read-only.
4. **Hub Notes and To-do:** After owner review, implement recoverable *copy* and Restore semantics before any source delete. Notes revisions and task/project links must survive recovery.
5. **Hospital/Time/Finance:** Protected discovery only with independent owner approval. Hospital checkpoints/transcripts and Time Machine checkpoints have continuity and recovery dependencies. Finance transactions, identity trust, audit ledgers and other authoritative journals are **not disposable by default**.
6. **Permanent burn receipts and retention:** Persist verified audit receipts safely apart from disposable payloads; make scoped bulk preview show source, count and dependency checks. Implement source-specific retention/hold policies, and test partial failures.
7. **Host acceptance:** Exercise all four Trash++ sizes, click/keyboard behavior, huge inventories, concurrent source writers, injected disk errors, symlink/special-file refusal and restore after crash on disposable fixtures.

### Integration rules for the next owner

- **No new destructive action is authorized by this document or index.** User approval for this initiative authorizes bounded GitHub development, not local files, merges or production activation.
- Keep GIO Trash (filesystem), managed copies (Trash++), and original source owners isolated. No universal `rm` operation and no cross-owner Burn All.
- Test mixed schema versions with the owning source policy, and reject unknown versions, malformed data and changing revisions before copying any sensitive payloads.
- Never return note bodies, task descriptions, Hospital reports or Finance account data in a discovery result.
- The source index is read-only and may be refreshed on demand. It is not a durable backup, restoration proof, or independent access-control boundary.

## Recovery checkpoint

Patient: `kudokudo1/The-Post-Apollo-Project`; Room: Trash++ universal resource lifecycle; staff: external DOC-compatible (live Hospital registration unverified). Assignment: operator-directed expansion toward universal Archive/Trash/Restore/Burn. Current bounded stage: owner-aware read-only adapter. PR branch `feat/trash-universal-resource-adapters-v1-20261110`. Required next gate: full CI, independent owner review before any source write, then native `♻ → ARCHIVE → HUB` verification after authorized merge/sync.
