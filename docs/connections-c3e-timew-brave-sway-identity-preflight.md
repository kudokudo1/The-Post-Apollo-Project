# 🏥💜 Connections C3e ↔ TimeW // Brave/Sway signed live-window identity preflight

PATIENT // `The-Post-Apollo-Project`  
ROOM // Protected Connections C3e/Identity · TimeW native trust witness  
STAFF ROLE // DOC successor, explicitly operator-authorized for this bounded C3e preflight; no verified live Hospital registration  
ASSIGNMENT // Source-only **one currently selected floating window** identity-correspondence preflight. Previous C3e worker remains paused.  
RELATED // [TimeW trust issue #2067](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2067), [TimeW #2065](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2065) merged; separate C5 consent ownership  
BASE // `main` at `5f08318197cefbcf580b4ae10e814abfd0110bba`  
PRODUCTION // HOLD. No native witness, actual Brave identity, installed signer, Sway command, geometry, C5 human consent or restore.

## IMPLEMENTATION

The input to this preflight is not a privileged Sway or Brave process. It consists entirely of **synthetic, caller-provided test observations** and a signed TimeW pairing. Rather than reimplementing the TimeW pairing format, the module imports the exact current `services/time/MachineV2PairConsent.py` verifier, calling its Ed25519 `_verify` with `TimeW.PAIR_DOMAIN`. The original signed TimeW `PAIR_SCHEMA`, `PAIR_FIELDS`, `AUDIENCE`, canonical JSON rules and 10-second lease are checked without altering TimeW or minting a competing pairing format.

The signer public key must match a separately supplied SHA-256 fingerprint, but **the fingerprint itself is not independently enrolled**: a test harness can choose both key and pin. It therefore cannot establish issuer authority.

The synthetic matcher compares:
- TimeW's signed `checkpoint_id`, `window_key`, `live_con_id`, `app_id`, `workspace`, `output`, `session_id` and opaque `browser_window_ref` against an independently *provided* selected-window record, with strict types and canonical UUIDs.
- A supplied process observation carrying PID, process start ticks, UID/GID, executable SHA-256, session UUID and an alive flag, compared byte-for-byte to the selected window's claimed process identity.
- A bounded list of at most 32 synthetic compositor windows, each with container ID, PID, app ID, workspace/output, session, floating status and capture generation. Selection must exactly match one live con_id; non-floating, stale generation, mismatched session/scope and duplicate con_ids refuse.
- Any **second Brave window in the same supplied PID/app/session** refuses as ambiguous, even with a different con_id. A Brave process can own multiple windows, and one title/app ID/PID is not a browser-window-to-Wayland-surface binding.
- A selection must be within 1.5 seconds of the supplied snapshot and within TimeW's signed lease. These inputs are synthetic, not a real kernel monotonic clock or a trusted Sway snapshot.

### Important limitation

The module is **not** a Brave-to-Sway window identity witness. It does not read /proc, authenticate a pidfd, query Sway, bind a browser native messaging window, obtain a trusted Wayland surface identifier, measure SELinux/logind, or examine an operator prompt. The pairing can be correctly signed by a disposable attacker-controlled key if the same attacker supplies its expected pin. The `snapshot_generation` and `browser_window_ref` are **caller-supplied test labels**, not kernel-authenticated identity.

Consequently the only positive fields are `testOnlyTimeWPairSignatureMatchesCallerPin` and `testOnlySingleFloatingWindowMatchesCallerSnapshots`. **Every** installed issuer, independent root custody, native Sway/Brave identity, C5 consent, window movement, restoration and production grant flag is permanently false. The native witness entrypoint always refuses.

## HOW TO USE

One GitHub-only workflow runs 34 adversarial source tests with ephemeral Ed25519 keys and the original TimeW verifier. It does not alter the user's Fedora/Silverblue desktop. No browser, compositor, extensions, tabs, real user data, secrets, external signing keys or real Sway commands are accessed.

The test matrix covers wrong pairing root, forged/unsigned or correctly signed wrong-purpose field, swapped checkpoint/window/session/container/browser reference, expiration, stale snapshot, Boolean integer coercion, PID reuse, process start-tick/UID/GID/executable change, duplicate con_ids, two Brave windows in the same process, changed Wayland capture generation, session/workspace/output drift, tiled/non-floating windows, and the complete inability to grant restoration. It includes a deliberate case where an attacker selects **both** a new signing key and corresponding root pin: CI may observe format correspondence, but production authority stays false.

## VERIFY

- [ ] 34/34 new cases pass at exact PR head
- [ ] Relevant Grammar and any other triggered workflows pass
- [ ] New PR contains only four additive C3e-owned source/test/workflow/doc files
- [ ] Independent Nurse 2 review at exact head
- [ ] TimeW owner acknowledges exact pair schema compatibility and scope
- [ ] C5 owner separately approves a TimeW-specific real human consent contract
- [ ] Operator final merge and production decisions remain separate

## WATCH OUT FOR

**A signed pairing record is not a trusted window identity.** TimeW's existing V2 pairing verifier cryptographically binds supplied fields, but neither a browser extension, its displayed window ID, nor synthetic Sway snapshot tokens establish which Wayland surface is really that browser window. Even when a single fixture window matches, production authorization remains false.

Before a real witness can sign a TimeW pair, the operator must approve (1) independent root enrollment/custody/revocation, (2) actual installed source/ELF/unit and Linux kernel peer evidence, (3) authenticated Brave-window ↔ Sway-surface evidence in the same live session, and (4) independent C5 active/unlocked-seat and per-operation operator approval, safely consumed before Sway geometry dispatch. A simple Sway `get_tree` PID, app ID, title or stable con_id alone is insufficient; duplicate Brave windows must fail closed.

Persistent Brave identity across restarts, browser tabs, restoring a lost window and any native compositor effects are **outside this assignment**. Hospital Room Trash/Restore keys, policies, ledgers and PX grant writing may not be reused.

## CHECKLIST

- [x] Check Syntagma AGENTS/Hospital and current source/ownership
- [x] Confirm TimeW #2065 and merged C4b/C3e foundations, identify C5 distinction
- [x] Reuse exact signed TimeW pairing verifier, not a new schema
- [x] Add source-only matcher and adversarial tests on isolated C3e branch
- [ ] New exact-head CI and independent review
- [ ] Operator decision on merging source-only preflight
- [ ] Future separately authorized native process/window witness

## NEXT

Record a fresh CI result and solicit independent scoped Nurse 2 security review plus TimeW owner interface review on the same PR. Next actual native milestone is an **operator-approved, installed, independently anchored** Wayland/Brave witness that can attest a specifically selected existing surface, with periodic rechecks and a separately trusted TimeW-only C5 consent issuer. Do not edit TimeW's restoration code under this Connections task.

## DECISIONS

DRAFT source-only; no root/prod signer, persistent Brave identity, geometry action, native service, local machine modification, Hospital Room transfer, C5 implementation, merge or production activation. The user retains final authority; live Hospital registration unverified.
