# 🏥💜 Trash++ U10b // GIO Metadata on Reviewed Restore

PATIENT // The-Post-Apollo-Project
ROOM // Trash++ Universal Resource Lifecycle · GIO Restore hardening
STAFF ROLE // External Hospital-compatible DOC, live Hospital registration not verified
ASSIGNMENT // Integrate independently tested metadata + late collision proof into merged U10 #2030
BASE // main e66c61de866b22eae54721d280a4a81b43771496
PERMISSIONS // Repository draft only. No local workstation, live Trash, Camera, Media, Hospital, Burn, or Protected Archive changes.

## IMPLEMENTATION

U10 #2030 already binds the U4 reviewed full-index SHA-256 and per-row URI+original SHA-256 to the backend, checks the index twice, and observes post-Restore state. Those hashes cover listing strings, not file inode or content.

A second worker left complementary work on branch feat/trashpp-u10-gio-restore-identity-20261117 at ad6922fd. U10b adapts only its bounded secondary GIO metadata and real late-collision proof to the merged reviewed-restore path, without merging that diverged feature branch.

Backend: query the exact selected URI using gio info for trash::orig-path, trash::deletion-date, id::file, standard::type and standard::size. Require original-path equality and at least one secondary witness (deletion date or file ID). Reject missing, changed, duplicate, oversized and invalid metadata. Query metadata before and after the second exact U10 full-index revalidation, then compare the entire metadata tuple; reject disagreements. The original GIO no-force restore and U10 post-state checks stay intact.

Only the UI-reviewed restore-reviewed command gains metadata checks. Legacy direct Restore and all Burn/Burn All paths remain unchanged.

The isolated U9 real-GIO GitHub runner now performs an adversarial late-collision test THROUGH restore-reviewed. Immediately before its actual gio trash --restore subprocess, it creates one disposable destination sentinel inside its private CI HOME and requires the provider to reject the move without overwriting the sentinel, keeping the original item in Trash. It then removes only the sentinel and completes byte-identical Restore.

## HOW TO USE

After independent review and an approved merge / separate Fedora sync, use the existing Trash++ -> TRASH -> REFRESH -> select file -> RESTORE. The UI passes tokens automatically. An unavailable metadata provider causes a visible refusal, not a bypass. Do not Burn or auto-retry to recover from refusals.

Offline synthetic test command:

    python3 -B -m unittest discover -s tests/trash -p 'test_u10b_gio_metadata_review.py' -v

The actual-GIO fixture is GitHub-runner-only. Do not run on the operator workstation.

## VERIFY

- U10b tests exercise missing, invalid, duplicated, oversized, changed path and changed metadata with unchanged URI/listing, plus strict distinction from legacy/Burn.
- U10 existing race tests remain active with stable mock metadata; U4 and launcher contracts stay unchanged.
- All Trash Python, Node and Grammar CI pass, including real U9 GVfs/D-Bus fixture with flags gioMetadataCompared, lateCollisionPreserved, reviewedRestoreRevisionChecked, collisionDenied, restoredBytesVerified, staleReplayDenied.
- No new destructive action or permissions.

## WATCH OUT FOR

GIO info attributes and formatting vary by provider and mount. Requiring secondary metadata is intentionally FAIL CLOSED and may prevent legitimate Restore on providers lacking deletion-date or id::file. Passing Ubuntu CI does not establish Fedora or multi-mount compatibility. Before broad deployment, independently review supported providers and get operator acceptance. Never silently accept absent metadata.

This is NOT an atomic source identity operation. After the final read, another process can replace the item, or metadata can be reused. GIO's no-force move is the destination no-clobber boundary under the tested provider, not a proof that Python checks lock the selected source.

A successful post-listing proves only observed state, not arbitrary file contents. The U9 disposable runner independently checks bytes. Uncertain results must not auto-retry.

## CHECKLIST

- [x] Current Syntagma rules, latest main and conflicting worker branch inspected
- [x] Integrate bounded GIO metadata checks into reviewed Restore only
- [x] Add synthetic changed/reused metadata and unavailable-provider tests
- [x] Adapt real late-collision check to reviewed Restore
- [ ] Exact-head Trash, Node and Grammar CI / real GIO receipt
- [ ] Independent Nurse 2 security and compatibility review
- [ ] Operator acceptance and merge
- [ ] Optional separately approved Fedora and multi-mount compatibility verification

## NEXT

Verify full CI and hand off U10b for independent review. The follow-on engineering task, if full concurrency guarantees are required, is provider-level atomic identity design, not another preflight loop.

## DECISIONS

Draft only. Do not directly merge the old divergent branch; this integration preserves current main U10. No local machine modifications, no Burn, no source owner authority expansion, and no production Archive capture. Roll back only U10b-specific metadata helper, runner block, tests and this document if declined.
