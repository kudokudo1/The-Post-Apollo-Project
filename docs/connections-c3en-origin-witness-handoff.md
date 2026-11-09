# 🏥💜 Connections C3e-N // Installed origin ↔ protected witness handoff

PATIENT // The-Post-Apollo-Project  
ROOM // Universal Connections · protected host architecture  
STAFF ROLE // DOC · Original protected Connections development lane  
ASSIGNMENT // Define a fail-closed read-only compatibility boundary between C3b/C4b installed status and C3e-L root witness  
DEPENDENCY // C3b/C3c and C3e-L on main; C3e-M mainline recovery PR #1601 separately active  
CONCURRENT OWNER // C2v/C4b Silverblue installation + rollback, TASKS C5 consent/reviewer  
PRODUCTION // HOLD · No active host, credential, grant or API action

## IMPLEMENTATION

The C3b/C4b signed Silverblue status process and the C3e-K/L read-only witness are **two different Linux processes, not one service with interchangeable credentials**. C3b checks a nonroot service in a fixed systemd unit, D-Bus owner and enforcing SELinux domain. The read-only witness is a separate root-owned ledger process exposed through a restricted UNIX socket to a nonroot client.

C3e-N implements a **pure test-only compatibility contract** for these two independent observations. It imports C3b's actual fail-closed origin evaluator rather than reproducing its dozens of installation, D-Bus, canonical /opt, parent-directory and confinement rules. It accepts C4b's canonical symlink only when the original C3b snapshot proof is valid, and checks the separate C3e-L status's exact schema, kernel-verified transport indicator, UID, witness digest and release floors. No caller-supplied `"status": "OK"` string bypasses the real C3b evaluation.

The fixed returned shape expressly distinguishes two observed PIDs: installed status service and root witness. It refuses accidental PID collapse, mismatched expected service PID, missing/untrusted witness status, unsigned-looking pass markers, altered /opt proof, nonenforcing confinement, stale floors and any production authorization assertion. The only positive state is `C3EN_CI_ONLY_ORIGINS_COMPATIBLE_NOT_BOUND` and the output still sets `hostAuthenticated:false`, `canApprove:false`, `credentialActionsEnabled:false`, `productionAuthority:false`.

The CI suite includes one **real** nonroot-to-root kernel-socket witness interaction from C3e-L, plus test-controlled C3b/C4b origin evidence. The synthetic status service evidence must not be mistaken for a live installed C4b service.

## HOW TO USE

CI-only workflow `.github/workflows/connections-c3en-origin-witness-handoff.yml`. The 19-case new suite, canonical C3b tests and C3e-L/K/J and signed C3e-I regressions run inside a disposable Ubuntu GitHub runner. No Fedora workstation commands or QML changes.

## VERIFY

- [ ] Exact-head 19 C3e-N contract cases, including real Linux root witness process.
- [ ] C3b canonical origin and /opt proofs, C2n deny-only, C3e-L/K/J and signed recovery tests.
- [ ] Meta Apollo Grammar and workflow complete at current head.
- [ ] Independent security and ownership review.
- [ ] Operator decides merge separately from test success.

## WATCH OUT FOR

**The C3b service evidence and C3e-L witness evidence are not cryptographically bound to each other here.** Their JSON values and expected PIDs are supplied by the test harness. A hostile caller could invent compatible objects if this were treated as authentication. The adapter is a CI contract, not an attested signer, installed host verifier, or production broker. A positive `testEvidenceCompatible` is NOT permission to connect, approve, use a provider credential, or update a release.

This intentionally leaves C4b's guest installer, custom SELinux policy and C2v rollback tests to their owner. C3e-M's signed native executable test is separate and still not the installed Python-script C4b service. **Do not equate a signed native ELF with the C4b Python interpreter and script provenance.** Real signed installed host evidence needs an owner-approved integration to link executable, package origin, service unit, OS identity, witness release floors and operator-approved trust root.

## CHECKLIST

- [x] Recheck main, current C2v/C4b and C5 owners and completed C3e-K/L.
- [x] Discover #1597 merge-to-stale-branch; restore C3e-M on current-main PR #1601.
- [x] Create main-based C3e-N read-only compatibility contract with 19 adversarial tests.
- [x] Add CI and durable handoff.
- [ ] Fix any observed CI failure in N-owned files.
- [ ] Review #1601 and N independently; operator retains merge authority.
- [ ] Define signed deployment attestation and guest-origin evidence transfer with C4b owner; define how trusted pins are delivered and what remains non-production.
- [ ] Connect C5 genuine operator consent and provider-specific scope only after separately reviewed host registration.

## NEXT / DECISIONS

This work stays main-based to avoid repeating stale feature-branch merges. After CI, the next **substantive integration gate** is a real signed installed C4b host attestation measured in the disposable Silverblue guest and independently verified against C3e-M signing/witness policy, not a synthetic JSON join. That gate needs explicit C4b-owner collaboration and must not activate live Connections.

Production HOLD, no local machine changes, no PR merge, no operator final acceptance.
