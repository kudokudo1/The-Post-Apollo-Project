# 🏥💜 DOC 1 // Forest-purpose independent custodian ↔ original producer contract (RFC)

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** Universal Connections · Protected C3e Trust / Forest cross-owner boundary  
**STAFF ROLE //** DOC 1 · external Hospital-compatible; live Hospital registration unverified  
**ASSIGNMENT //** Propose the protected Forest-purpose issuer/currentness/receipt semantics needed by DOC 2's future original-producer evidence and DOC 3's distinct Forest C5 policies  
**STATE //** **OWNER DECISION REQUIRED · PROPOSAL ONLY · FOREST/IDENTITY/HOSPITAL/TIMEW PRODUCTION HOLD**

This RFC does not modify an installed source, create a signing key, designate an authority, define a deployable wire format, authorize private session/title access, or change a production grant. It is a new **Forest-specific** counterpart to [DOC 1's Identity witness-custody RFC](./connections-c3e-protected-identity-witness-custody-admission-rfc.md), not an amendment granting Identity's existing keys or host authority to Forest.

## IMPLEMENTATION // Current actual mechanism and missing link

Files and processes are the trust boundary. Forest Core has a `scripts/forest/session_journal_v0.py` SQLite data primitive and `scripts/forest/host_admission_b4a.py` injected admission callbacks, but its [original-host decision](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2161#issuecomment-7114899467) identifies **no verified installed native Forest process**, no independently protected database opener/owner and no authenticated serializer-to-recipient file descriptor. ForestW `ForestSessionListConsumerPolicy.js` can validate the shape of a list response, but does **not** authenticate the source or grant permission to fetch/show titles.

DOC 2's completed [#2360](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2360) and [#2366](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2366) exercise real **Identity-purpose** Silverblue process and signed-denial observations in disposable native CI. Their [owner disposition](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2119#issuecomment-7116062103) explicitly **REVISES** any Forest producer claim until Forest Core identifies the original installed host/DB/recipient channel. This is correct: a Linux PID, boot ID, process executable hash, signed `UNAVAILABLE` or locally pinned public key cannot enroll a separate Forest custodian.

DOC 1's merged [#2369](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2369), [#2374](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2374) and corrective [#2382](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2382) verify *synthetic Identity-purpose* Ed25519 denial candidates over real local processes. [Nurse 2's #2382 review](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2382#pullrequestreview-6030716153) scoped the FD fix PASS. Those test-only keys and unchanged `postapollo.connections.identity-custodian-ci-only` purpose **must never become Forest enrollment credentials**.

DOC 3's merged [#2385](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2385) adds separate, always-refusing C5 `authorize_list_sessions` and `authorize_disclose_session_titles` entrypoints. Its independent review was **not recorded at this RFC's source checkpoint**; its merge does not approve a native metadata reader or production title disclosure. DOC 3 / Forest Nurse 2 owns that separate audit.

**Therefore:** C3e can document the future custodian's required *proof, state and terminal semantics*, but cannot honestly return a protected authorization without an independently enrolled root, an approved original Forest host/DB/recipient and operation-specific C5 policy.

## DECISIONS // Required independent roles and custody

The operator's accepted **local development first → separately administered protected hardware later** sequence remains a development direction only. Neither a NAS nor any named administrator, root, key material, network endpoint, antirollback mechanism or final recovery operator is approved yet.

The proposed roles are **distinct by purpose and permission**, even if the same physical hardware is eventually selected:

| Role | Owns / proves | Cannot infer |
| --- | --- | --- |
| **Forest enrollment authority** | Out-of-band operator-approved fingerprint, root lifecycle, delegation to **Forest-only** issuer/history/receipt roles, current rotation/revocations | Approval from an Identity, TimeW, Hospital or test key |
| **Forest independent custodian** (DOC 1's semantic responsibility) | External current policy and history head/epoch/sequence, durable one-use request fences, exact operation-purpose challenge, serial history advance and authenticated terminal lookup | Owner/Tree identity from guest-local JSON, permission from a correctly signed denial |
| **Forest original native producer** (Forest Core identifies; DOC 2 subsequently measures if approved) | Exact installed signed release, executable/systemd service, process PID/start/boot/session/seat, authenticated original inbound challenge and outbound recipient FD, real database-opener and serializer checkpoints | Identity gateway CI, Ollama model provider or ForestW render process as equivalent host |
| **Forest C5 consent/policy issuer** (DOC 3) | Distinct `LIST_SESSIONS`, `may_disclose_titles`, `READ_SESSION`, `DISCLOSE_PROVISIONAL`, `COMMIT_GENERATE` entitlements, principal/Tree/recipient and expiry/current revocation | Permission for title egress from a permission to list IDs or read one known session |
| **Forest Core protected DB and egress** | Storage custody, canonical owner + exactly one Tree restriction **before** query/serialization, actual recipient bytes and stop-after-revoke admission | A signed receipt as proof that already-sent bytes vanished |
| **ForestW** | A masked UI rendering of *already authorized* data | Authority to read local files, inspect SQLite or reveal a private title |
| **Connections Nurse 2 / Forest Nurse 2 / operator** | Independent exact-head review, cross-owner interface judgment, final acceptance as separate actions | Merge, CI green or a `COMMENTED` review as production activation |

## Proposed original-source ↔ custodian exchange (SEMANTICS ONLY)

**No JSON schema, endpoint name, exact fields, signature encoding, transport, host ID or signer key is frozen by this RFC.** The following are *required facts* a future approved interface must prove.

1. **Pre-existing independent trust:** The verifier obtains Forest-purpose root/role/current revocation from a separately administered source, not an enrollment key sent with the request, a guest-local file, a response header, an Identity root, or an unsigned CI pin. If currentness or revocation cannot be independently checked: **HOLD**.
2. **Original principal and privacy scope:** The authority identifies an authenticated requesting principal/owner, one canonical protected Tree, Forest purpose and exact operation. It binds the exact intended service, recipient/channel/seat and an externally current policy generation. A guest-supplied `owner_key` or Tree string is only a candidate, **not owner authentication**.
3. **One unique operation, one protected fence:** The custodian durably issues an unpredictable challenge for the **specific original operation and exact request digest**, with a deadline, independent current history head and monotonic sequence, policy/revocation epoch, approved host+recipient and operation-specific permit intent. It must refuse a challenge replay or a request copied across audience, operation, Tree, owner, recipient or release. This issuance is **not** itself C5 consent.
4. **Verified actual original producer:** Forest Core must name the installed host, protected database custody and serialization/write gate first. DOC 2 can then offer independently authenticated, challenge-bound actual package/release, process PID/start/boot, owner/seat, recipient FD and message-source evidence **before and after** original native work, without allowing a replaced process, inherited FD or unsigned claims to masquerade as the selected host.
5. **Distinct C5 policy acknowledgment:** A `LIST_SESSIONS` authorization for opaque ID enumeration is not permission to disclose private titles. `may_disclose_titles` is separately issued and current. A provisional text egress permit is separately scoped from final generation, SEND, voice or tool permissions. Forest C5 and the protected issuer must agree on exact operation, authenticated principal/Tree/recipient/seat, generation and revocation. Missing any: **no private data fetch, serialization or egress**.
6. **Durable atomic custody:** The independent custodian serially checks its **own** current history head/sequence, revocation floor, challenge state and original operation. On an approved future state transition, challenge consumption and next history head are **one independently durable atomic event**. Two concurrent forks from the same predecessor cannot both commit, even after local OS snapshot rollback. A guest-local SQLite row or two copies of one local DB cannot establish this property.
7. **Terminal recovery is distinct:** A signed `UNAVAILABLE` or missing ACK is not proof of `COMMITTED` and not an authorization to retry. The custodian's authenticated original-operation lookup must return a terminal original receipt tied to operation/nonce/challenge/current head/recipient, or **UNKNOWN/HOLD**. No automatic replay or reissuance of a previously attempted command. Any production action still requires separate operator acceptance.

### Forest operation separation (proposed authority matrix)

| Operation | Data/effect boundary | Distinct required decision | Default |
| --- | --- | --- | --- |
| `LIST_SESSIONS` | Opaque session ID/metadata enumeration for one owner + Tree | `may_list_sessions`; **no title bytes** implied | **HOLD** |
| `DISCLOSE_SESSION_TITLES` | Private session-title fetch/serialization/display | `may_disclose_titles` for original principal/Tree/recipient in addition to independently authorized list scope | **HOLD** |
| `READ_SESSION` | Contents of one already-known session | Per-session content entitlement; not enumeration | **HOLD** |
| `GENERATE` | Model work with a selected request | Separate generation authority; not provisional egress | **HOLD** |
| `DISCLOSE_PROVISIONAL` | Provisional `DELTA` bytes to named recipient | Distinct revocable egress permit and fenced serialized send | **HOLD** |
| `COMMIT_GENERATE` | Durable history/result and terminal effect | Independently settled original operation and separate commit authority | **HOLD** |
| `SEND`, voice or tools | External side effects | Independent operation- and recipient-specific authority; no inheritance from any above | **HOLD** |

**Untrusted evidence remains nonauthorizing even when internally consistent:** response shape, locally generated signed Ed25519 key, current-looking signed timestamp, Linux pidfd, SQLite row, matching guest-local head, duplicate signed witnesses, or a product widget's `live` indicator cannot create the absent protected root or consent.

## VERIFY // Future owner-accepted native acceptance matrix

Before calling a future custodian **authoritative**, reviewers need demonstrable independent evidence, not a fresh batch of same-host signed-test-denial cases:

- [ ] Operator/custody owner records **ACCEPT** for the selected independent host/admin, root enrollment and offline fingerprint verification, storage/backups, revocation and recovery roles. Production roots and test keys are mutually disjoint.
- [ ] Forest Core identifies actual installed host (source path, executable/systemd unit, release), canonical protected DB owner and exact outbound recipient/serializer file descriptor and write-admission point. Operator records acceptance.
- [ ] DOC 2 and Forest Core demonstrate genuine installed native Forest source identity, process/boot/seat/recipient lifetime and independently challenged packet origin; a swapped process, replaced FD, expired release or revoked root refuses.
- [ ] C3e independent custodian authoritatively issues and durably consumes one-use Forest-purpose challenges; double spend, restored guest snapshot, concurrent head fork and stale revocation floor refuse in actual separate trust domains.
- [ ] DOC 3's distinct LIST/title/read/provisional/final permissions are reviewed with Forest Nurse 2 and bind the original principal, one Tree, recipient, C5 consent and current revocation **before** private data is retrieved or serialized.
- [ ] Revocation/stop ACK promises **no new authorized submissions after the fence**, not retroactive recall of bytes already sent; verify against the actual outbound FD and native serialization checkpoint.
- [ ] Crash before/after atomic history advance, lost original ACK, lost receipt, signer rotation and source restart all remain either independently queryable terminal state or `UNKNOWN/HOLD`, no auto-retry.
- [ ] Forest C5, C4b, C3e, Forest Core/W and Nurse 2 review exact-head source, permissions, native logs and any installed integration; operator separately accepts rollout.

Until these are proven, **no protected read, private session title, provisional byte, generation commit, external SEND, credential action or production sign-in** is authorized by C3e.

## HOW TO USE // Ownership / next concrete decisions

This RFC is intended for **owner response in GitHub**, not activation. The next owner decisions must be explicit and independently recorded:

1. **Forest Core + operator:** **HOLD currently.** Identify/accept the actual installed original Forest host, real protected database owner, canonical Tree and recipient serializer/FD before DOC 2 implements a new Forest producer. Do not substitute B1 SQLite, callbacks, Ollama or ForestW.
2. **DOC 3 + Forest Nurse 2:** **HOLD currently.** Finalize separate title/metadata policy, list versus title permission, provisional egress/ACK fence and private-owner data controls. [DOC 3 #2385](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2385) merged its fail-closed semantics but was not independently reviewed at this checkpoint.
3. **DOC 2:** **ACCEPT previously reviewed Identity diagnostics; REVISE proposed Forest producer pending real Forest host.** Verify the semantic original challenge / process / release / boot / seat / recipient binding only after scope is approved. Do not reuse Identity's installed gateway as Forest.
4. **DOC 1 / eventual independent custodian:** **ACCEPT developing this proposal; HOLD authority-bearing production integration.** Operator names the independent administration, offline key enrollment, release and revocation policy, atomic history and recovery. Only then author an operator-approved protected verification client; no synthetic signer is needed now.
5. **Nurse 2 and operator:** Independently review the new source-only RFC and record necessary corrections. Later implementation, enrollment, merge, installation and production remain separate authorization/acceptance steps.

**Recovery pointers:** [Connections cross-owner issue #2119](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2119#issuecomment-7115960976), [DOC 1 disposition](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2119#issuecomment-7116110612), [DOC 2 owner response](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2119#issuecomment-7116062103), [Forest Core owner report #2161](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2161#issuecomment-7114899467) and [DOC 1 corrective #2382](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2382) (merged, independent scoped PASS). `main` and reviewer status must be rechecked before any future shared seam change.

## WATCH OUT FOR / DECISIONS

- No shared real Forest producer or independent custodian exists as an **operator accepted** trust source. This RFC **must not be treated as implementation permission** for new systemd units, native signers, direct DB readers, key installation, production wires or automated credentials.
- An Identity-purpose Ed25519 verifier, a genuinely observed per-packet Linux sender, and an Identity signed `UNAVAILABLE` are **not** Forest authorization. Distinct audiences and terminal effects stay separated.
- The original #2374 reviewer `REVISE` is historical; merged #2382 independently scoped PASS corrected the narrow test-helper descriptor leak. This does not establish enrolled production Sign-In or independently protected history.
- **External Hospital-compatible DOC 1**, no live Hospital registration or assignment mutation. Operator retains final authority; user acceptance of a reviewed/merged RFC is separate from technical completion.
- **PRODUCTION SIGN-IN, FOREST PRIVATE SESSION/TITLE ACCESS, HOSPITAL C5 AND TIMEW RESTORE REMAIN HOLD.**
