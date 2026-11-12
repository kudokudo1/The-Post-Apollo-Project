# Social PHONE // P41b exact protected edit commitment (in-memory CI only)

**Patient:** `kudokudo1/The-Post-Apollo-Project`  
**Staff:** external Hospital-compatible ordinary DOC; live Hospital Room / Assignment / Session unverified.  
**Source checkpoint:** P41a merged PR #1938. Active dependency: issue #1885.  
**Scope:** new PHONE-owned pure in-memory helper + synthetic tests and isolated workflow. No production host, C5 or Identity ownership.

## IMPLEMENTATION
P37's deny-only signed contact-save request already contains `editHmac` but relies on a test caller to supply it. P41b makes the candidate change commitment explicit and unambiguous, using only in-memory synthetic inputs:
- Requires an exact P37 request draft *without* `editHmac`. Reuses P37's current exact request-field validator to check profile, unique BlueFerry owner, session, snapshot, selectedCardHmac, expected revision, challenge, release floor and request nonce.
- `LINK`: no local ID (P34 must generate random local UUID at authorized commit). `UNLINK`: requires a local UUID; `FAVORITE`: local UUID and exact boolean; `NOTE`: local UUID and exact Unicode note, including an intentionally empty string for clearing. Invalid and cross-action values are refused.
- Produces a keyed HMAC-SHA256 using a separate purpose/domain subkey derived from the caller-supplied 32-byte in-memory P35 master key. The canonical commitment includes all other P37 request fields and the exact proposed value, preventing swapping a note, favorite, action, selected contact, profile, revision, nonce or session without changing `editHmac`.
- Returns only a P37-shaped request and its hex `editHmac`, not the raw note, local ID or key. No disk write, Secret Service lookup, IPC, CLI, QML or actual note saving.

**Trust boundary:** a matching HMAC only proves internal value consistency to a party already holding the key. It does not prove device identity, stable person identity, C5 human action, trusted process custody or allow production saves. Do not give P35 keys or this service to QML. HMAC-derived candidate metadata is not an alternative to a real C5 one-use consent receipt.

## HOW TO USE
No new operator-facing PHONE controls. The pure helper is only called by isolated synthetic tests and is not wired into the installed app.

## VERIFY
Tests check determinism; P37 exact-field compatibility; every request dimension (profile, owner, session, snapshot, selected-card proof, revision, challenge, release floor and nonce); changed note/boolean/action/key/linked-local-ID; empty-note clearing; invalid types/IDs/Unicode; fixed privacy-safe exceptions; absence of filesystem, keyring, or QML hooks. Dedicated GitHub CI runs P41b and P37 adversarial regressions. Final exact-head CI and operator acceptance remain separate.

## WATCH OUT FOR
C4b [PR #1785](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1785) remains unmerged; C3e-AB [PR #1939](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1939) reports missing full real Silverblue rollback completion. Independent installed trusted host and genuine C5 PHONE one-action receipts are not established. P37–P39 test signers, P36 fixture and P41a callback are never production authorization. P40 Favorite/Notes remain hard-false and disabled.

## CHECKLIST
- [x] Recover P41a merge, main HEAD and no active PHONE PR ownership conflict.
- [x] Document exact operation commitments and request field binding without storing notes.
- [x] Add in-memory HMAC builder and adversarial synthetic tests.
- [x] Add isolated GitHub workflow.
- [ ] Exact PR-head CI and operator review.
- [ ] Trusted installed C4b/Identity gateway and C3e external replay/source verification.
- [ ] Real C5 signed one-use PHONE human approval, private key lifecycle, commit authority lease.
- [ ] Native disposable installed-host testing and real UI save acknowledgment.
- [ ] Final operator acceptance.

## NEXT
Once issue #1885's owner-produced authentic host/C5 evidence is available, build a PHONE-native verification receiver that binds its actual signed bytes to the P37 request including P41b's exact edit commitment. Couple a genuine one-use lease to P35's revision-locked write; test revoke during commit, crash recovery and rollback before activating Favorites or Notes. No synthetic grant promotion or direct QML key access.

## DECISIONS
PHONE-only CI work; P34–P41a and existing UI are unchanged. No merge, local Fedora file changes, service installation, real keyring use or production activation by this worker.
