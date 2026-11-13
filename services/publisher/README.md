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

## P1.3 // Local reusable templates and locked source facts

- **Dependency:** P1.3 is stacked on P1.2's draft branch. Do not merge P1.3
  independently while the media-library dependency remains unaccepted.
- **Storage:** one separate local `PublisherTemplateStore` and
  `publisher-templates-v1.json`. No change to P1.1 draft or P1.2 media data.
- **Template fields:** name, category (recruitment/resource/announcement/
  creator), informational language code, freeform wording, and up to twelve
  explicit `key = value` factual fields. Versioned strict schema, bounded
  file, single-writer FileView, atomic-write acknowledgement. Unencrypted.
- **Mechanism:** `{{key}}` substitutes the exact supplied value. Unknown,
  malformed, missing, duplicated or unused locked fields reject the render.
  Recruitment requires `role`, `location`, `apply_url`; resource entries
  require `resource` and `contact`. Starter formats contain intentionally
  blank values: they cannot pass preview until the user fills them.
- **Interface:** Social → PUBLISHER → TEMPLATES → choose category → LOAD
  STARTER → fill facts → VALIDATE & PREVIEW → SAVE TEMPLATE. USE IN COMPOSE
  creates a new, **unsaved**, manually editable text draft. Existing unsaved
  Compose edits block replacement to prevent data loss.
- **Limits:** no AI rewrite, translation, platform API, authenticated facts,
  outreach automation or outgoing posts. Language is metadata only. Factual
  fields are preserved by deterministic rendering, but a user may subsequently
  edit the resulting freeform draft. Later publish gates must revalidate source
  claims and permissions; P1.3 does **not** provide that gate.
- **Verify:** Node executes the real template policy (positive rendering,
  missing fact refusal, unknown placeholders, immutable saves, corruption,
  version mismatches, language and category limits). Python source checks
  preserve the Social companion and existing draft/media writers. Native
  Quickshell UI acceptance remains separate.

**Recovery:** Close or discard the P1.3 branch without changing deployed
components. No original media or prior draft file requires migration.
