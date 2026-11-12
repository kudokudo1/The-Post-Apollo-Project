# SocialW Publisher // P1 local foundation

**Owner:** Post-Apollo Publisher subsystem. **State:** P1.1 merged; P1.2
proposed on a separate review branch. **Authority:** explicitly selected
local-only records. No account login, external publishing, upload or queue.

## Architecture

- Publisher remains an exclusive companion surface inside SocialW's existing
  FloatingWindow. No second window, provider index, chat adapter, or account
  identity writer.
- **P1.1** uses \`PublisherDraftStore\` as the only writer of
  \`Quickshell.dataDir/publisher-drafts-v1.json\` (text-only v1).
- **P1.2** uses a distinct single writer, \`PublisherMediaStore\`, for
  \`Quickshell.dataDir/publisher-media-v1.json\`. A media record contains a
  local file URI, harmless display name/type/byte length, stat-based stamp,
  and time. A link contains an existing draft ID and asset ID.
- The media catalog is a **reference library**, not a file upload, backup,
  snapshot, encryption service, or Camera/Trash collection. It NEVER
  deletes, copies, moves, rewrites, or scans a whole directory.
- \`PublisherMediaProbe.py\` runs read-only after explicit user selection
  and again before every preview. It requires a regular, user-owned,
  single-linked file, resolves within HOME, refuses hidden/symlinked file
  sources, validates extension + header + size, and issues a stamp from
  inode/device/size/mtime. This is **change detection**, not content integrity
  or a defense against an attacker modifying the file immediately afterward.
- Selected images preview locally in QML only after the second probe. The
  optional QtMultimedia video viewer loads lazily and never auto-plays.
  Video playback is user-triggered and muted.
- A draft must already be saved to link media. Maximum eight linked items per
  draft, 250 media records. Unlink is confirmed and only removes the
  relationship; it never touches the source file.
- Both stores use bounded versioned JSON, FileView atomicWrites, single
  pending mutation, explicit reload and fail-closed corrupt/newer-version
  errors. A FileView onSaved signal is only local write acknowledgment,
  not independent OS-level integrity proof.

## Accepted local files

Images: PNG, JPG/JPEG, WebP (32 MiB maximum each).
Videos: MP4, WebM, MOV (1 GiB maximum each).
Only files owned by the current user **inside the real HOME** are accepted.
Cloud URLs, SMB shares, hidden directories, sandboxed document-portal paths
and external drives are not granted by this slice. A file picker may provide
a portal URI; the probe will refuse if it is not an allowed local path.

There is no archive copy. If the original is renamed, replaced, edited or
deleted, a later preview fails and the reference remains for manual review.

## Operator route once merged and installed

Social → PUBLISHER → COMPOSE → SAVE DRAFT → MEDIA.
In MEDIA, IMPORT IMAGE / VIDEO adds a reference after validation and a
confirmed local metadata save. Select an item to recheck and preview it.
ATTACH TO DRAFT creates a separate local link. UNLINK requires a second click.
LIBRARY continues to display text drafts; attachments appear on the
COMPOSE MEDIA button as an actual count.

## Limitations and safety

- Both JSON stores are **unencrypted**. File names and local paths should not
  describe confidential HR, financial, health or family materials.
- A local Social identity label is NOT an authenticated person/company
  permission. P1.5 must establish the proper ownership boundary before
  multi-tenant publishing.
- No calendar scheduler, upload queue, remote tokens, API access or auto-post.
- The media probe and UI source tests run in CI, but local Wayland + Qt
  visual/runtime acceptance remains with the operator. Optional QtMultimedia
  preview availability must be confirmed on the actual host.
- Do not merge or deploy without the project's review/approval path.

## NEXT

P1.3: approved reusable templates and locked factual content, after P1.2
runtime review. P1.4: durable scheduler and queue, requiring crash-safe
reconciliation. P1.5: account permissions. P1.6: history and recovery.

## Recovery

An unmerged P1.2 branch can be closed without affecting production.
Existing P1.1 drafts require **no schema migration**. The new media file is
independent and no media originals are altered by this feature.
