# Forest Core B5c // Installed original-host candidate and custody proposal

PATIENT: The-Post-Apollo-Project  
ROOM: Forest Core native host staging / DOC1-2-3 integration  
ROLE: Forest backend DOC, external Hospital-compatible  
STATE: CI-only Fedora RPM mechanics, operator choice required; PRODUCTION HOLD.

## IMPLEMENTATION

B5b #2390 merged at b9b058c8 with 96/96 focused CI tests; independent review
was absent when preparing this milestone and remains a separate gate. B5c
does not alter that host source or any Connections, ForestW or B1 implementation.
It builds an unsigned, test-only RPM from the exact B5b candidate bytes,
installs it into a fresh disposable Fedora 44 container, runs it as an
unprivileged account with an inherited unnamed Unix SEQPACKET descriptor,
then removes the test package. The runtime container does not mount the
candidate source checkout; expected source digest is supplied by the CI
controller, not by the guest response. This is local build/install evidence,
not an independently signed release or enrolled authority.

| Boundary | Disposable CI target |
| --- | --- |
| Package | post-apollo-forest-host-ci |
| Installed source | /usr/libexec/post-apollo/forest-ci/forest-host |
| Invocation | /usr/bin/python3 -I -B, installed source, explicit test FD |
| Lifecycle | one on-demand child, no persistent service |
| Actual output | B5b _submit_public_hold_once(channel), one fixed public HOLD packet |
| Storage | NONE, no database open or private data |
| Recipient | disposable same-UID requester, not authenticated |
| Authority | false |

The source path is root-owned, 0555, exact RPM owner and SHA-256; package
contains only its directory and candidate file. No service unit, install
scriptlet, trigger, signer, systemd enablement, or private state. The test
checks real installed child PID, interpreter, argv, UID, socket inode and
one public denial. The package is removed before the fresh container exits.

## PROPOSED production boundary (REVISE/HOLD pending owner acceptance)

Forest Core proposes an on-demand original producer, separate from
Quickshell and Ollama, under an approved existing launcher/broker rather
than another always-running permission daemon. Candidate production source
path: /usr/libexec/post-apollo/forest/forest-host (not the CI path). Package
name, exact launcher and confinement require operator and DOC1/2 approval.
No service/installer for that proposed path is included.

**Proposed private storage ownership:** an independently administered,
dedicated Forest runtime identity holds per-principal storage beneath a
service-owned directory (candidate /var/lib/post-apollo/forest/). The
authenticated principal-to-storage mapping must come from independently
verified custody state, never request JSON, an owner string, QML or Ollama.
The launcher must supply a protected storage capability only after
Forest-purpose C3e/C4b/C5 admission; ForestW must have no direct file
access. Do not create that directory, account, key, or DB here. Exact
UID/GID, principal identifiers, encrypted store/key custody, backup,
recovery, retention, SELinux domain and filesystem/open race policy
are unapproved. Ordinary Unix mode bits alone do not protect from root
or malicious code sharing the service identity. SQLite sidecars, WAL,
rollback, backup and temporary storage require equal protection. B1's
synthetic schema is not a live storage authorization or migration plan.

**Proposed recipient / egress:** the authorized launcher supplies exactly
one enrolled recipient-channel capability. The installed Forest producer
owns that descriptor's serialization/submission point, not ForestW.
DOC2 must independently establish source release, PID/start/boot, seat,
recipient identity, descriptor provenance and replacement/inheritance
refusal before a private response. DOC1 independently establishes
Forest-purpose root/current history/challenge custody. DOC3 supplies
distinct LIST_SESSIONS, title consent, provisional disclosure, and commit
policy; a public HOLD or a matching packet grants none. A future shared
serialized gate must block new admissions after a protected revoke fence;
local send completion is not a delivery receipt or evidence of recall.

## HOW TO USE

GitHub CI only, no operator commands. Build container and separate
verification container run without privileged Docker, host device
mounts, or user-data mounts. Neither executes an AI model or installs on
the operator's workstation.

## VERIFY

Exact roster and no scriptlets/triggers; byte-exact installed package
file, mode/owner and rpm -V; unprivileged actual process and socket
observations; protected actions always public HOLD, malformed/STOP
close, default invocation refuses; package removal. Inherited B5b,
B5a, B1, B3, B4a and ForestW tests also run. Report actual CI results only.

## WATCH OUT FOR

Fedora container installation is NOT Silverblue rpm-ostree layering or
reboot rollback, independent signed release/SELinux/seat attestation,
native issuer trust, operator-approved installed host, private storage
provenance or a protected C5 revocation fence. An unsigned CI package,
root ownership and source digest are not an enrollment. No private
data, model execution or protected capability supplied.

## NEXT / DECISIONS

- B5b independent review remains due; B5c exact-head review separate.
- Operator + DOC1/2 ACCEPT/REVISE/HOLD the proposed production location,
  on-demand launcher, private runtime identity and custody policy.
- After explicit acceptance, test a separately approved Silverblue
  installed/reboot lifecycle and native storage boundary. Do not
  reuse Identity-purpose roots or service as Forest authority.
- DOC3 and ForestW keep titles, SEND/voice and protected output locked.
- No native inference, local install, automatic merge or production.
