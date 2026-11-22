# 🏥💜 Connections C3e ↔ Hospital // D4 independently protected history admission RFC

**PATIENT //** The-Post-Apollo-Project  
**ROOM //** Universal Connections · Hospital staffing Session/Doctor protected recovery  
**STAFF ROLE //** Connections DOC successor, external Hospital-compatible; live registration unverified  
**STATE //** OWNER REVIEW REQUESTED · PROPOSAL / NO PRODUCTION AUTHORITY  
**COUNTERPART //** Hospital PX source owner [#130](https://github.com/kudokudo1/The-Post-Apollo-Dev-Exp/pull/130), Hospital staffing recovery [draft #133](https://github.com/kudokudo1/The-Post-Apollo-Dev-Exp/pull/133) at `be4f1becc4cfe193079c3818c6295ef07698c1b1` (source seen during this drafting), [Hospital D4 custody options](https://github.com/kudokudo1/The-Post-Apollo-Dev-Exp/blob/be4f1becc4cfe193079c3818c6295ef07698c1b1/docs/hospital-staffing-d4-history-custodian-options.md)  
**UPSTREAM //** Connections merged [#2103](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2103) RECOVER query *format* and merged [#2107](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2107) *test-key* purpose isolation

## IMPLEMENTATION // Concrete mechanism first

Hospital's Session/Doctor, consumed signed grants, and proposed COMMITTED journal are stored in SQLite. An older whole-DB restore removes the original requestNonce and grant history together. The Hospital test demonstrates that a new coordinator can issue a **different valid signed grant for the same original requestNonce**, and the locally rolled-back source accepts it. A matching signature is not antirollback evidence.

**C3e recommendation to owners, NOT a selected production solution:** Evaluate **Hospital's option C** (an independently administered, monotonic append-only or equivalent history authority **outside the Hospital DB and its backup/root rollback domain**) with **option B only as a local authenticated front end** when needed. Reject A (signed Hospital SQLite rows) or B (one local root-owned DB/daemon without an independent anchor) as sole D4 protection. A remote service and a TPM-backed counter are alternatives to investigate, not statements that they exist or satisfy requirements. An independent append-only authority must authenticate each retained original request, not merely advance a scalar counter.

### Minimum proposed custody roles

| Role | Owns | Must not be assumed from |
| --- | --- | --- |
| **PX protected writer** | Same-transaction grant, original source Session/Doctor, and versioned result journal; native all-path original-request enforcement, backup/cutover | CI monkeypatch, fixture SQLite, desktop process UID |
| **D4 history custodian** | Permanent original request reservation/fence, current monotonic log head and historical membership/consistency, independent authorization/keys and recovery of lost local history | Same-host writable backup, self-chosen Ed25519 root, signed stale PENDING packet |
| **C3e / C4b verifier and release custodian** | Explicit installed release and signer-role enrollment, root-pinned signed history/channel + current head, revocation, replay/fresh challenge, native host/process/seat provenance | Identity-only C3e-AF CI role, a single SO_PEERCRED, test-supplied floor, JSON signature alone |
| **C5 staffing consent custodian** | Original staffing-specific visible Room/Session/Doctor scope approval under actual active unlocked seat | RECOVER query, TimeW/Room Trash credentials, old consent inferred from history |
| **Hospital + Connections D3/D5 owners** | Typed read-only RECOVER, authenticated result/origin, UNKNOWN/HOLD/COMMITTED/REFUSED semantics | Any local journal row or synthetic positive fixture |

The cryptographic signing keys for **staffing grant issuer**, **Hospital writer result**, and **independent D4 history authority** need separate purpose/role enrollment, private-key custody and rotation/revocation. A separate TimeW key/audience is mandatory. The current merged CI role/enrollment preflights do not establish real operator custody or host attestation.

## Proposed reservation / source / recovery transaction ordering

The independent custodian must provide a **linearizable, durable, antirollback original-request reservation**; a mere signed `RESERVED` claim without independently current head and one-use serial admission is insufficient.

1. **ADMIT / RESERVE:** Native authenticated protected writer requests admission for exact original `requestNonce`, immutable original request bytes/hash, Room/action/Session, current graph/review/scope, original PREPARE/PREPARED/COMMIT digests, grant nonce/digest/approval, writer and issuer release/host identities and policy generation. Custodian checks current enrolled authorization and atomically persists one reservation under a globally unique original request identity. Conflicting grants for the same nonce are rejected, including if an earlier local DB was restored. **Durable signed reservation ACK and stable history position precede any source COMMIT.**
2. **CONSUME ORIGINAL:** One narrow, nonexportable, one-use reservation lease is bound to the original enrolled writer process and exact source transaction, not regenerated after restart. Native source must validate it **before any grant consumption**, with all old-writer routes fenced. Missing/unavailable/competing custodian yields HOLD before mutation. Whether a crashed original writer can ever resume must be separately proven, not inferred from PENDING.
3. **SOURCE COMMIT:** The writer atomically updates grant consumption, Session/Doctor source mutation and original COMMITTED journal under its own SQLite `BEGIN IMMEDIATE`. A protected refusal fence requires a durable provable no-COMMIT outcome and must exclude later different grants for the original nonce. External reservation remains an unresolved fence until reconciled; never remove it just because the local writer stopped.
4. **RECONCILE / READ_HISTORY:** A separately versioned **read-only** native RECOVER query (not a COMMIT replay) uses a **fresh independent one-use challenge**. Responses bind exact original identity and both signed current history head and cryptographically authenticated historical membership/consistency proof; query and receipt must be tied to independently enrolled writer and custodian release/host roles. A previously signed PENDING packet is only evidence of an unresolved reservation; it is not a COMMITTED or REFUSED receipt.
5. **FAIL CLOSED / MANUAL:** After partial acknowledgement, writer crash, database rollback, witness partition, stale fork, mismatched release/seat/policy, signer rotation uncertainty or conflicting historical evidence, return **UNKNOWN or security HOLD**. No new signed grant for the same original nonce, no silent retry, no automated local erase. Manual reconciliation requires a separate authorized procedure.

### Historical membership is required even when current head advances

Hospital's new [CI historical membership candidate](https://github.com/kudokudo1/The-Post-Apollo-Dev-Exp/blob/be4f1becc4cfe193079c3818c6295ef07698c1b1/tests/test-px-hospital-staffing-history-membership-ci.py) checks a signed PENDING at sequence 1 against a later current head using a bounded in-memory full hash-chain prefix. This is useful CI evidence; it does **not** establish a separate deployed append-only history, anti-fork current-head trust, root custody or cheap production inclusion proof. Future heads must preserve authentic *historical inclusion and non-equivocation* for earlier reservations, not reject every old valid reservation merely because new unrelated requests advanced the head. Absence/nonmembership claims must be issued atomically by the authorized history custodian; a client-computed absent-row result is not proof of no earlier COMMIT.

## D3/D4 interface acceptance fields (proposal; no wire version selected)

Before implementing native code, PX/C3e/History custodian owners must explicitly agree on:

- Immutable identifiers: `requestNonce` and full original request hash; grant nonce/digest/approval separately, canonical COMMIT hash and writer transaction ID; Room/action/Session/Doctor, scope/review/graph digest, schema/policy generation.
- Separate **issuer and protected writer** installed release identities, process/socket peer custody, host/systemd/SELinux identity, signed enrollment lineage, root fingerprint and revocation history. Do not mistake verified *packet sender* for authenticated writer or actual source transaction.
- **Custodian-owned** monotonically current head, independent trusted head signer, append position/epoch, historical inclusion and consistency proof, replay prevention, versioned response audience, time/freshness and one-use challenge. The native verifier must obtain the trusted head from an independently approved trust source; never from the untrusted reply itself.
- Original one-use reservation lease lifecycle, expiry and crash cutoff; revocation and host restore response; old writer fencing. Distinguish `RESERVED/PENDING` from `COMMITTED`, `REFUSED`, `UNKNOWN` and `CONFLICT/HOLD` with no automatic same-request retry.
- Explicit source error semantics, bounded packet size, canonical framed bytes, replay/duplicate refusal, installer/upgrade and operator release gates.

**No concrete production schema, cryptographic accumulator, hardware selection, remote endpoint address, root location, signing key or socket name is chosen by this RFC.** Those are separate owner and operator decisions.

## VERIFY // Required adversarial release cases

| Test / failure boundary | Required safe outcome |
| --- | --- |
| Hospital source COMMITTED then restored to pre-COMMIT DB; new grant/approval/writer for same original request | Custodian retains original fence; no second Session/Doctor or spent replacement grant |
| External reservation succeeds; source never starts or crashes before COMMIT | Permanent PENDING / UNKNOWN, no automatic new lease |
| Source COMMIT succeeds; external outcome ACK lost | PENDING/UNKNOWN until independently reconciled, never no-commit assumption |
| Missing, stale, duplicated, forked or unavailable external history / reset root / old valid head | HOLD, no grant consumption |
| Current monotonic head advances from unrelated requests | Historical original PENDING remains verifiably included and fenced |
| Two writers concurrently race to reserve same original nonce with changed grant | At most one original writer lease; no second source mutation |
| Original proof correct but reissued under different audience/host/release/role | HOLD; wrong domain never authorizes staffing or TimeW |
| Old writer still has a legacy mutation route after migration | Cutover test MUST refuse; no unguarded grant consumption |
| Exact signed writer receipt vs absent/conflicting source history | Only authenticated durable source evidence can prove terminal status; otherwise UNKNOWN/HOLD |

## WATCH OUT FOR

**Independent trust is an organizational and installation property, not a property of Ed25519 alone.** The Hospital CI source and current C3e tests mint signing keys and expected roots in the same disposable runner. A purported off-host history service is not safe until actual key control, backup domains, monotonic rollback prevention, endpoint compromise and availability are reviewed and verified.

A history-custodian service must not itself make Hospital Session changes. C3e RECOVER remains read-only. Do not silently move PX protected writer ownership to C3e or claim D1/D2 approval from a Nurse 2 scoped test review.

## CHECKLIST / NEXT / DECISIONS

- [x] Analyze Hospital original-request rollback attack, signed PENDING check and advancing-head membership test
- [x] Provide a bounded C3e D4 custody recommendation and explicit native trust prerequisites
- [ ] **PX #130:** ACCEPT / REVISE / HOLD on D1 same-transaction durable journal and D2 terminal original-request fence, including chosen version/cutover
- [ ] **D4 authorized custodian/operator:** ACCEPT / REVISE / HOLD on protected off-DB history authority, control plane, root enrollment and recovery
- [ ] **Connections + Hospital:** ACCEPT / REVISE / HOLD on D3 request/receipt fields, external head and role pins, D5 terminal meanings
- [ ] **Nurse 2:** independent scoped review of this cross-owner interface contract after owner responses
- [ ] C5 real staffing consent, native supervised test/release, operator final acceptance

**Decision state:** Option C is recommended for *evaluation*, not selected. Production HOLD. No database, source transaction code, actual signing service, installer, SwayPX, C5, root key or workstation changed.
