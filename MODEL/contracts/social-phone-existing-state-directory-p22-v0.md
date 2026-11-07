# Social PHONE P22 // Existing state directory permission compatibility

> **STATE:** Isolated GitHub-only draft fix; no local Fedora change, no merge/production activation. **PATIENT:** `kudokudo1/The-Post-Apollo-Project`. **ROOM:** Social PHONE remembered Personal read permission. **WORKER:** OPEN AI // CHATGPT, external Hospital-compatible; live Room/Assignment/Staff registration unverified. **BASE:** `main` at `e3595b0035bb3d89aa87c6ba2bd1aac04a975181`; P21 PR #1403 verified merged; no overlapping open PHONE/Identity PR.

## IMPLEMENTATION

User's Nov 6 screenshot shows the *new* in-PHONE remembered permission popup, with **"SAVED PERMISSION UNAVAILABLE // Check local state permissions."** This means the button runs, but `PhoneRememberedRead.py --approve` returns `STORAGE_UNAVAILABLE`. The user's actual on-disk folder mode has **not** been verified from this browser session.

A source-level compatibility defect is reproducible: `_private_directory` currently requires owner-only **0700** on the pre-existing **shared** `$XDG_STATE_HOME/post-apollo` directory. An otherwise safe, user-owned, conventional **0755** folder (readable/listable, **not writable** by group or others) is rejected before the application can create its 0600 file and 0600 lock. Other Post-Apollo components can already use this shared directory.

P22 replaces the parent directory's `mode & 0o077 == 0` check with `mode & 0o022 == 0` while preserving exact owner UID, real-directory (not symlink) checks, exact record shape/operation binding, file/lock owner-only **0600**, atomic replacement, `O_NOFOLLOW`, same BlueFerry profile/provider guards and revocation. **Never chmod the shared directory.** The file may be listed by other users in a 0755 folder, but no other UID may read or write its contents; this local user preference is **not** an app-authenticated grant or protection against other programs of the same UID.

## HOW TO USE

After operator-approved merge and separately approved Fedora update, go to **Social → PHONE → APPROVE READ → ALLOW BOTH / REMEMBER**. The choice should persist in a normal existing Post-Apollo state directory. Use **STOP ACCESS** to revoke that local preference. No terminal or repeating ten-minute approval should be necessary. **No local chmod command is needed or recommended** to force the shared state directory to 0700.

## VERIFY

`tests/phone/test_phone_remembered_read.py` adds a regression covering a pre-existing 0755 directory, persisting one-time approval, read of synthetic messages and contacts, 0600 file+lock, revoke and unchanged parent directory mode. Additional negative regressions refuse 0775/0777 parent directories and a symlinked parent. Existing full PHONE CI must pass on exact PR head. This is a synthetic source fix, not a claim that Fedora's actual folder permissions have been inspected.

## WATCH OUT FOR

The screenshot's error could also arise from a different local problem (filesystem ownership, bad lock, missing disk permission or invalid existing preference file). This patch addresses the **specific reproduced overly strict parent mode check**, not every potential source. After a successful approval, MAP/PBAP read data still depends on BlueFerry's actual cache; notifications do not prove historical threads or contact-card data exist. The personal preference is still **Linux-user scoped**, not a browser-like signed per-app grant, and the broader Identity Center/Account Broker production ownership remains separate. Preserve the working iPhone Bluetooth/audio and oFono/HFP boundaries.

## CHECKLIST

- [x] Confirm screenshot state and merged P21 #1403/current main.
- [x] Read Syntagma rules and verify open PHONE/Identity PR collision-free.
- [x] Make minimal safe parent-directory permission change without chmod.
- [x] Add positive 0755 and negative group-write/symlink regression tests.
- [ ] Exact-head CI.
- [ ] Operator review/merge, separately authorized desktop update.
- [ ] Real PHONE approval/read/revoke verification without exposing phone data.

## NEXT

After CI and approved deployment, retry the **ALLOW BOTH / REMEMBER** control. If `STORAGE_UNAVAILABLE` persists, inspect **metadata only** for `$XDG_STATE_HOME/post-apollo`, permission file and lock (owner/mode/file type), without printing file contents, phone profile IDs, messages or contacts. Otherwise verify the Personal read returns either a supported BlueFerry snapshot or a specific `READ_UNAVAILABLE`/empty cache outcome. Do not re-pair the phone.

## DECISIONS

Small GitHub-only provider preference fix, no UI changes or shared owner edits, no local machine modifications, no permission file contents disclosed, no merge or production activation. Operator final acceptance distinct from CI. Recovery: close the draft PR or revert its bounded commit after separately authorized merge.
