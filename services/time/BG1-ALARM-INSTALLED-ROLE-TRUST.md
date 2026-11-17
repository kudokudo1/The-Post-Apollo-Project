# CLOCK BG1-B2B9 // Protected Installed Role Trust Preflight

**Status:** A real read-only loader for *already provisioned* Clock-specific
trust files, plus an explicit disposable test mode. No trust key, signing
policy, installed service, authority grant, or Quickshell release has been
created on the user's computer.

## IMPLEMENTATION

The existing BG1-B2B2 `AlarmSignedRoleOrigin.py` can verify an independently
signed role policy against an AF_UNIX kernel-connected process, executable
inode, exact installed Python entrypoint bytes, argv, credentials and
release epoch/sequence. But its callers previously supplied an in-memory
Ed25519 public key. BG1-B2B9 adds a strict loader for that missing
**installed public-key provenance**.

Protected location, **proposed for a future signed RPM**:
`/usr/share/post-apollo/clock/trust-v1/`. Three files:
- `clock-root-ed25519-v1.pub`: raw 32-byte Ed25519 public key.
- `clock-clock-ui-bridge-origin-v1.json` (or
  `clock-clock-background-worker-origin-v1.json`): exact canonical
  B2B2 signed role policy, purpose-separated from Identity or Connections.
- Matching `.sig`: raw 64-byte Ed25519 signature over B2B2's domain
  prefix plus the exact JSON bytes.

The signed JSON names an installed executable, interpreter, exact
arguments, UID/GID, role, release epoch and sequence. B2B2 already
verifies the actual program. Production requires the protected
`/usr/libexec/post-apollo/clock/` installed executable prefix; test
fixtures live in a private owner-only disposable directory instead.

### Trust observations

1. Require an independently provided **SHA-256 fingerprint of the
   approved Clock release-root public key**, expected role, and
   minimum epoch/sequence floor. These must come from a supervisor or
   operator-protected release source, never a requester/socket.
2. Refuse any protected-mode trust directory other than the exact
   proposed location. Walk every parent directory with `lstat`;
   ancestors and role files must be root-owned and not group/other
   writable. Symlinks are refused; regular files use `O_NOFOLLOW`,
   `O_CLOEXEC`, `O_NONBLOCK`, file size limits, link-count checks
   and before/after inode and metadata comparison.
3. Compare the public key's digest with the **external pin** and verify
   the signed policy under B2B2's Clock-specific Ed25519 domain.
   Reject the wrong role, malformed JSON, untrusted signature, unsafe
   installed executable path or rollback below the independently
   supplied release floor.
4. Given an accepted AF_UNIX socket and externally pinned PID/start
   ticks, invoke B2B2's existing `SignedClockRoleProbe.inspect`.
   Reload the entire installed bundle *after* verification and refuse
   if the policy/signature/root has changed during observation.
5. Return a **deny-only observation**: role signature and OS identity
   matched, `roleAuthenticated=false`,
   `writerStopped=false`, `releaseAcknowledged=false`,
   `canTransferOwnership=false`, `canRing=false`, and
   `canNotify=false`.

### What this does not provide

- **No trust root is provisioned.** A private key is never generated,
  imported or persisted by this module. The public key fingerprint is
  supplied by a future *independent* trusted installer/supervisor;
  self-supplied peer fingerprints are not acceptable authority.
- **No durable release-floor authority is provisioned.** The external
  minimum epoch/sequence is required on every call, but the future
  protected supervisor must maintain it across updates and rollback.
- No Quickshell IPC, FileView callback control, true QUIESCING
  transition, native old-writer process supervision, protected
  restart revocation or BG2 audio. `blockWrites` is not a lock.
- Signed program identity remains **observation**, not installed
  authorization. Existing Identity C4b is a different protected
  purpose and does not grant Clock authority.

## VERIFY

The CI fixture creates a real AF_UNIX subprocess, independent test
Ed25519 release issuer, signed Clock policy and public root in a
private 0700 temporary directory. Tests compare the actual pidfd
origin, program digest and args while exercising bad root fingerprints,
forged signatures, wrong role, rollback floor, symlinks, weak
permissions, untrusted paths, process substitution and exits, and
bundle modification during inspection. Existing B2B2/B2B7/B2B8/B2B6/
B2B1 regressions rerun.

No actual installed root-owned RPM trust bundle was provisioned or
validated by this fixture; protected-host verification remains a
separate native Silverblue acceptance gate.

## NEXT IMPLEMENTATION

1. Coordinate an operator-approved **Clock-specific** trust issuer,
   root fingerprint, release-floor custody, and signed Silverblue RPM
   path with the separately owned Connections/Identity installations.
2. Build the native protected Clock session supervisor, in which
   installed role observation must remain an input to an explicit
   *separate* authorization decision. No approval via a status bit.
3. Only after the supervisor enforces session ownership and
   old-writer restart denial, wire the real Quickshell barrier's
   QUIESCING transition with verified FileView queue flush and durable
   source digest. STOP/SNOOZE local silence must remain available.
4. Transfer a *single* canonical alarm writer, test rollback and
   at-most-once delivery, then separately authorize BG2 background
   audio/notifications.

## Hospital checkpoint

PATIENT // The-Post-Apollo-Project
ROOM // Clock Reliable Background Alarm Ownership
ROLE // External Hospital-compatible DOC, no verified live registration
ASSIGNMENT // BG1-B2B9 installed Clock role public-key provenance read-only
SCOPE // New Clock-only module, test, CI, docs
PERMISSIONS // Draft PR only; no merge, host writes or production activation
RECOVERY // Exact PR head + workflow logs
DECISIONS // All trust outcomes deny ownership, writer release and ringing
