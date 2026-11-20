# 🏥💜 Connections C3e ↔ TimeW // Linux kernel packet sender evidence preflight

PATIENT // The-Post-Apollo-Project  
ROOM // Protected Connections C3e/Identity · TimeW native trust witness  
STAFF ROLE // DOC successor, bounded GitHub-source implementation; live Hospital registration not verified  
ASSIGNMENT // Read-only real Linux peer custody and per-packet sender identity, **not** an installed Brave-to-Sway witness  
BASE // [#2087](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2087) exact head `4f6aa0b8b108595fc0ef840af6728f994fd64a7d`; stacked draft  
TIMEW // [#2065](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2065) existing signed pairing verifier unchanged, TimeW owner retains geometry  
PRODUCTION // HOLD, no permission, signer, installed service, actual browser/Sway window access, human consent or restore.

## IMPLEMENTATION

The operating system maintains the process that opened a Unix socket and the process that actually sent a packet. These can be **different** after a fork inherits a connected file descriptor. Checking only the first process would mistakenly trust a packet emitted by its child.

This source-only C3e preflight reuses TimeW's existing `MachineBraveProcessLease` kernel `SO_PEERPIDFD` custody and /proc start-ticks/UID/GID/executable device+inode observations. It reads actual `SO_PEERCRED` from one disposable connected `AF_UNIX/SOCK_SEQPACKET` test socket and requires exactly one matching `SCM_CREDENTIALS` set for the **same actual sending PID/UID/GID**. Inherited-descriptor fork send, missing control credentials, wrong UID, dead/changed pidfd, wrong socket family/type, truncated/oversized canonical packet, duplicate JSON keys, modified challenge/parent pairing digest all refuse.

A caller-supplied one-use **CI challenge** and `pairPayloadSha256` bind the packet's data to the source-only [#2087](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2087) signed TimeW pairing correlation. That source has its **own caller-supplied public-key fingerprint, synthetic process and compositor window snapshot**. Comparing them is an integrity check of a disposable fixture, **not** independent root enrollment or proof of an actual Brave/Wayland mapping. This new module cannot assume the native bridge process is the Brave process. It returns both `actualKernelPeerCredentialsAndPidfdObservedInCI=true` and `nativePeerIsBraveWindowProven=false`; the distinction is essential.

The preflight does **not** read a running Brave extension, inspect any real Sway tree, install an authority socket, mint pairing signatures, call C5 Polkit, approve any TimeW window movement, save browser tabs or make a production claim. The native entrypoint always raises `NATIVE_WAYLAND_BRAVE_PAIRING_NOT_IMPLEMENTED`. Every actual installed issuer, Brave-to-Sway surface identity, separate C5 consent, native pairing key and restore flag is **false**.

### Source trust boundaries

| Evidence | What it does prove in disposable CI | What it does not prove |
| --- | --- | --- |
| Linux `SO_PEERCRED` | Kernel's original connected socket peer | That process owns the selected Brave window |
| Linux `SCM_CREDENTIALS` | Process that emitted the current packet | Independently enrolled signed executable or native host identity |
| `SO_PEERPIDFD` + /proc | Same peer task remains alive with original process-start/ELF inode/UID/GID | Complete installed Python/unit/extension provenance or TimeW consent |
| Signed TimeW pair, synthetic Sway list | Signature and caller-supplied selected fields agree | True Brave UUID ↔ Sway surface mapping or persistent identity |
| Synthetic challenge and pairing digest | Current packet matches test-selected challenge/pairing bytes | Independent fresh challenge issuer, replay ledger or real operator approval |

## HOW TO USE

Run only through the GitHub test workflow in an isolated Ubuntu 24.04 runner. It uses existing TimeW source with disposable key fixtures, a real local UNIX packet socket, a forked child sending through an inherited file descriptor and kernel pidfd observations. It never installs a service on the operator's workstation.

The 24 additional tests cover valid peer packet without any grants, wrong UID, changed challenge, wrong pairing digest, changed signed browser reference, duplicate/extra/missing/invalid JSON, wrong packet kind/schema, oversized/empty frame, missing SCM credentials, wrong socket type, forked inherited socket, dead pidfd, changed fake process, duplicate Brave surfaces, and native-grant refusal. It re-runs the earlier 34 TimeW pairing/window source tests in a separate step.

## VERIFY

- [ ] 24/24 new real-kernel sender and adversarial CI cases pass
- [ ] 34/34 inherited TimeW pairing source tests pass
- [ ] Exact-head GitHub workflow and Grammar succeed
- [ ] Four new C3e-only files; no TimeW/C5/native implementation modifications
- [ ] Independent Nurse 2 exact-head source/security review
- [ ] TimeW/C4b/C5 owner acceptance of proposed future native evidence contract
- [ ] Operator separate merge, installation, signer custody and production decisions

## WATCH OUT FOR

**A trusted native bridge packet is not a trusted Brave window.** Browser native messaging usually runs in a process different from Brave's renderer/compositor client. Even if a secure Unix peer sends a signed pairing digest, that does not identify the specific Wayland surface described in it. Existing TimeW source `MachineBraveFocusWitness.py` explicitly describes focus co-observation as diagnostic and may not be promoted to identity.

A real issuer will need a separately accepted, independently enrolled Brave window ↔ live Sway surface mechanism, actual Sway socket/session provenance, fresh kernel process evidence and revocation, root-pinned installed native source/unit release, a C5 TimeW-only active-seat/human review and protected one-use grant consumption. No self-declared browser UUID, window title, transient con_id, app ID or process PID can substitute. Root/issuer history on #2076 is also still CI-only, not durable independent custody.

## CHECKLIST

- [x] Inspected Syntagma protocols, current TimeW source and issue #2067 owner boundary
- [x] Retained unmodified #2087 head for its pending independent review
- [x] Added a strictly separate C3e source-only Linux-origin preflight
- [ ] Exact-head CI and external security review
- [ ] Native issuer/writer provenance, C5 consent and TimeW integration release

## NEXT

After exact-head CI, request a separate scoped Nurse 2 security review and TimeW owner's confirmation that this is evidence **only for the native bridge**. The next protected native implementation must first establish real Brave-window/Wayland surface identity from independently controlled sources and await explicit operator architecture/installation approval; otherwise restoration stays disabled.

## DECISIONS

DRAFT/UNMERGED CI-only. Original #2087 reviewer head, TimeW paired geometry, C5, Hospital Room Trash/Restore/PX, C4b and user desktop stay untouched. Previous C3e worker remains paused. No live Hospital registration or production authority.
