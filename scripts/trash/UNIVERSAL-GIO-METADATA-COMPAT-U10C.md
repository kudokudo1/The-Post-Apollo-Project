# 🏥💜 Trash++ U10c // GIO Metadata Filename Fidelity and Fedora Compatibility

PATIENT // `The-Post-Apollo-Project`  
ROOM // Trash++ Universal Resource Lifecycle · reviewed GIO Restore compatibility  
STAFF ROLE // External Hospital-compatible DOC; live Hospital registration unverified  
ASSIGNMENT // Follow up merged U10b #2040 with narrowly scoped metadata parsing fidelity and disposable Fedora CI acceptance  
BASE // `main 3ae90b8eaf894457760f5ed98350d0353cb2b265`

## IMPLEMENTATION

Merged U10b #2040 (merge `3ae90b8eaf894457760f5ed98350d0353cb2b265`) correctly requires `gio info` original-path identity and a deletion date or file ID on **reviewed Restore**. Its parser, however, previously used `line.strip()` on GIO human-readable attribute lines. `strip()` removes **trailing spaces and tabs** from values. Valid Unix filenames can end in whitespace; the stripped `trash::orig-path` would then differ from the exact original path in `gio trash --list`, refusing an otherwise legitimate file. GIO documents `trash::orig-path` as a **byte-string** attribute, making value fidelity important.

This follow-up changes **only** that metadata parse operation to `line.lstrip(" \t")`: remove indentation before the known attribute key but preserve the remaining original-path value. Already-merged requirements remain:
- selected URI and original path, expected full-index SHA and reviewed per-row SHA match
- two fresh full GIO inventories and two identical GIO secondary identity observations
- required original-path plus secondary timestamp OR file ID
- vacant destination checks before real no-`--force` `gio trash --restore`
- checked post-Restore results, uncertain result deny/no automatic retry
- existing legacy Restore, Burn, Burn All and source-owner Camera/Media interfaces unchanged.

New synthetic tests exercise trailing spaces/tabs, leading whitespace in basenames, a one-character original mismatch and duplicate metadata refusal. No live GIO in the unit test.

A new narrowly triggered Fedora 43 container workflow runs:
1. source tests against the Fedora Python runtime;
2. the **existing real disposable U9 GIO runner fixture**, which creates its own private HOME/XDG/DBus and moves/restores one disposable file through current **reviewed** Restore;
3. upstream U9 late destination collision sentinel test, with real GIO no-force move, and SHA-256 verification of recovered bytes.

The Fedora container and installed packages exist only on a GitHub Actions runner. No workstation packages, source changes, user Trash entries, protected Archive or live service changes.

## HOW TO USE

After Nurse 2/security review and operator-authorized merge, normal UI remains:

Trash++ → TRASH → FILES → RESTORE

The Fedora workflow runs on PR/push changes to the listed Trash paths and can be manually dispatched. It does not use local Fedora state and is **not** a Silverblue VM acceptance claim.

## VERIFY

Check exact-head Trash contract CI, Grammar, **new Fedora compatibility workflow**, and raw actual-GIO receipt. Required receipt properties: `gioReal=true`, `reviewedRestoreRevisionChecked=true`, `gioMetadataCompared=true`, `lateCollisionPreserved=true`, `collisionDenied=true`, `restoredBytesVerified=true`, `postRestoreInventoryEmpty=true`, `fileBurnUsed=false`. Record exact results, never treat runner boot/provision errors as substantive GIO behavior.

Source-level GNOME documentation: `G_FILE_ATTRIBUTE_TRASH_ORIG_PATH` is a byte string, and the `trash://` GVfs backend exposes orig path and deletion date. This test still consumes the human-readable `gio info` CLI and is **not** a typed native GIO API proof.

## WATCH OUT FOR

Fedora 43 in a container is not the user's Fedora Silverblue desktop. It tests one local filesystem and one GVfs implementation, **not** all removable/network mounts, alternate GVfs providers or Unicode-invalid byte filenames. Mandatory metadata may still refuse providers with no deletion date and no file ID; this draft **does not** weaken that U10b fail-closed rule. If cross-provider compatibility is needed, conduct a separate, explicitly authorized probe for those providers before changing policy.

The GIO item and original destination remain subject to race conditions outside U10c's checks; no atomic identity claim. No Burn or file deletion authority is changed.

## CHECKLIST

- [x] Verify #2040 merged into current main, post-merge checks successful and no overlapping open Trash PR
- [x] Inspect exact U10b metadata parser, test and runbook
- [x] Preserve original-path whitespace without broadening Restore identity or execution verbs
- [x] Synthetic regression cases for trailing whitespace and mismatch
- [x] Add isolated Fedora 43 real-GIO workflow using existing U9 fixture
- [ ] Exact-head GitHub workflows and raw Fedora receipts, repair test-specific failures
- [ ] Independent Nurse 2 review and operator merge acceptance
- [ ] Separately approved Silverblue/multi-provider runtime acceptance, only if needed

## NEXT

Verify the Fedora container can provision GVfs and run the actual reviewed round-trip. If it fails, determine whether the failure is a runner/package/DBus issue or a provider's missing metadata. Fix only scoped CI setup problems; don't weaken mandatory safety checks as a quick route to green.

## DECISIONS

Small draft follow-up. No workstation writes or live Quickshell reload, no Merge, no arbitrary provider assertion, no new authority. Rollback: close the unmerged PR, leaving merged U10b unchanged.
