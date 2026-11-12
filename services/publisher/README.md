# SocialW Publisher // P1 local draft foundation

**Scope:** P1 first implementation slice, source branch only. This is not a
production publishing service and grants no provider account access.

## Architecture and boundaries

- Existing SocialW owns the FloatingWindow, app rail, identity metadata, and
  provider geometry. Publisher is a **companion workspace**, like Phone,
  not a messaging service index or a new Social login.
- The Publisher pane uses a single \`qs.services.publisher.PublisherDraftStore\`
  writer. It does not write to SocialIdentityStore, TASKS, Git, Hospital, or a
  remote platform. Social IDs are local organization labels, not authorization.
- Local draft file: \`Quickshell.dataDir/publisher-drafts-v1.json\`.
  Text-only records; no tokens, passwords, financial/health data or attachments.
  Not encrypted and not intended for sensitive company or family documents.
- Valid JSON: \`{version:1,nextId:1,drafts:[]}\`, with stable \`dN\` IDs,
  title/body, createdAtMs/updatedAtMs. Bounded to 100 drafts, 120-character
  titles, and 10,000-character bodies.
- Single-writer FileView with atomicWrites, explicit save, no background sync,
  and fail-closed malformed/newer-version behavior. Only \`onSaved\` acknowledges
  a save. Errors lock writes pending deliberate reload and reconciliation.
- The P1.1 screen is a local compose/library slice. Calendar, Queue and History
  are clearly marked future, not implemented and NEVER auto-publish.

## P1 sequence

1. P1.1: SocialW companion navigation and safe local text drafts.
2. P1.2: Dedicated media library with approved filesystem operations.
3. P1.3: Templates and verified content fact boundaries.
4. P1.4: Persisted scheduler and queue with crash-safe handoff and replay rules.
5. P1.5: Signed/consented account-specific capability and credential access.
6. P1.6: History and status reconciliation, tests, runtime/operator acceptance.

## Acceptance for this slice

- PUBLISHER opens inside the same Social window and closes by the same route.
- Messaging, Settings and Phone remain distinct, exclusive workspaces.
- No new provider app index, login, Process, daemon or outgoing network calls.
- Explicit Save creates/edits a local draft; save result appears only after
  FileView confirms completion.
- Restart reopens local drafts without rewriting them.
- Invalid input, duplicate IDs, unknown JSON fields, unsupported versions,
  file errors and in-flight overlapping writes fail closed.
- Unit + source contract tests pass; runtime Qt/Quickshell visual acceptance
  remains a separate operator checkpoint.

## Recovery

The branch contains only source-level changes; it is not installed on a live
desktop. If a review fails, close the P1 branch/PR without merging. No existing
phone sessions or social identity files require migration.
