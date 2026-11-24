# Forest UI2.1b // Guarded preview lifecycle and insertion proposal

DEVELOPMENT ACTIVE / PRODUCTION HOLD. External Hospital-compatible UI2; Nurse 2F independent review. Prior #2516 merged, 19/19 focused and 4/4 exact-head workflows; independent review not recorded at this checkpoint.

## IMPLEMENTATION
Additive UI2-owned PublicPreviewGate: opt-in default-off; fixed CHERRY fixture only, no trusted chat host, exactly zero active sessions, usable viewport. Losing any eligibility clears the local request; Tree changes and window close never restore it. This is presentation policy only, not authentication or permission. Eight real QtQml lifecycle tests; no Quickshell/ForestW instantiated.

## HOW TO USE
Not installed or reachable from ForestW. Offscreen CI tests only.

## VERIFY
Latest inspected base 42813c4f. ForestW blob 44969300 sessionPreview is bounded by chatDivider.bottom, promptRow.top and reasoningRailHost.left. ConversationFeed blob d784ce40 has no supported transcript-only option: header height 60, composer height 54 plus bottom margin 16. Its discordMode hides the actual feed too. Cropping or manipulating internal IDs would introduce fragile geometry and possibly hidden controls. No shared-file changes in this candidate.

## WATCH OUT FOR
The existing fixture's own header and disabled composer would duplicate the existing ForestW heading and prompt row. Do not insert it until the shared component owner agrees to a default-preserving transcript-only presentation seam. Proposal for shared owner: two opt-in presentation properties (default header/composer visible; hidden header yields viewport top at parent.top, hidden composer yields viewport bottom at parent.bottom; preserve ordinary consumers, disabled composer focus and send path). Alternatively owner-approved existing transcript-only API if one becomes available. This is an API proposal, not authorization to modify shared code. No use of discordMode, clipping hacks, fake sessions, external transcript inputs or authority flags.

## CHECKLIST / NEXT
After shared owner acceptance and implementation of transcript-only seam: bind gate inside ForestW sessionPreview to existing menuOpen, selected Tree presentation key, chatHostTrusted, activeChatSessions.length, actual measured viewport eligibility; explicit local preview toggle; Loader active only when gate.active, restore existing placeholder otherwise. Keep current anchors, heading, prompt, Coffee, model/diagnostic overlays and trusted flags unchanged. No sample over a real conversation. No sample under a different Tree. UI1 review exact shared diff and compact/full geometry before merge; Nurse 2F independent review and operator native acceptance. Preview threshold and visual control placement require UI1 review. No native ForestW geometry verified by this candidate.

## DECISIONS
Fixed sample is CHERRY-only to avoid associating it with another Tree. Reuse ConversationFeed; no second messaging shell or generic shared edits. Production HOLD.
