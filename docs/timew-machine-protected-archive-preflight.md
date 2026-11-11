# MACHINE // Protected archive migration readiness: read-only source inventory

PATIENT // The-Post-Apollo-Project
ROOM // TimeW MACHINE · Protected Brave Archive
STAFF ROLE // External Hospital-compatible DOC; no verified live Hospital registration
ASSIGNMENT // Safely prepare for a future separate-service-identity archive migration without performing it
SCOPE // New read-only preflight and synthetic tests only; no C3e, C5, account, systemd, Brave or Quickshell changes

## IMPLEMENTATION

MACHINE #1888 is verified merged to main, following #1883 and the NRS-2 post-merge technical PASS for #1876. The protected metadata broker is still unconditionally deny-only because independently verified installed-host/active-seat evidence and C5 one-use user consent do not exist for production MACHINE.

The current offline sealed-vault importer/manager stores private encrypted records under the **ordinary interactive account**, so another process running as the same UID may access those files. A future protected-service design requires an operator-approved move/copy of ciphertext into a separately owned filesystem tree. This PR does **NOT** perform such a migration.

`services/time/MachineBraveProtectedArchivePreflight.py` adds two strictly read-only operations, reusing the existing sealed vault's private-directory, no-symlink, no-hardlink, exact-record and size validations:

- `plan`: locate the existing ordinary-account source through the effective Unix account's passwd home, ignoring HOME/XDG_DATA_HOME overrides. Read existing sealed record IDs, UTC creation timestamps, sizes and SHA-256 hashes, twice. Refuse if either inventory differs, contains incomplete temp files, has unsafe ownership/modes, malformed metadata, a symlink or hardlink, or exceeds the record cap. Generate an opaque, domain-separated SHA-256 inventory fingerprint of canonical metadata. A missing vault is reported as absent and remains absent.
- `recheck INVENTORY_SHA256`: recompute the exact inventory and refuse if its fingerprint differs. It **does not** copy, reserve, lock, chown, chmod, delete or export an archive and does not authorize a later migration.

The CLI accepts no caller-selected source or target path, and no destination argument. Tests alone may inject an isolated temporary ordinary-account source path. Neither operation creates a file, directory, account, socket, service, background watcher, backup or plaintext session record.

The resulting JSON explicitly states `migration_authorized:false`, `client_authenticated:false`, `operator_consent_verified:false`, `protected_destination_inspected:false`, `distinct_service_uid_installed:false`, `independent_backup_verified:false` and `restore_allowed:false`. It exposes only encrypted-record metadata, **not** ciphertext, browser titles, tab URLs, credentials or passphrases.

## HOW TO USE

**There is no new TimeW button or automatic migration.** After independent source review, an operator can choose to use the read-only CLI:

```bash
python3 -B -I services/time/MachineBraveProtectedArchivePreflight.py plan
```

The response includes an `inventory_sha256`. Before planning any future migration of those specific ciphertext files, recheck without changing data:

```bash
python3 -B -I services/time/MachineBraveProtectedArchivePreflight.py recheck INVENTORY_SHA256
```

A refused recheck means **stop and make a new plan**, not retry a copy using an old digest. An unchanged digest is **not** operator approval, proof against same-UID tampering, or proof that a protected destination exists.

## VERIFY

The dedicated synthetic CI tests create sealed records only under a disposable private temp directory. They verify stable two-pass metadata inventory, exact reproducible fingerprint, no directory creation for an absent source, read-only unchanged bytes and permissions, stale fingerprint refusal after source change, hardlink/symlink/temporary-orphan/unsafe-mode failure, mid-pass inventory drift refusal, HOME/XDG spoofing resistance in the normal CLI, and rejection of any requested path override, `copy` or `migrate` command.

The existing protected-archive GitHub workflow additionally reruns the actual Linux pidfd/exec process lifecycle tests, Linux setsid/EOF cancellation, absolute request deadline, privileged separate-UID archive bypass denial, offline AES-GCM synthetic encrypted record/manager, and TimeW foundation/grammar source checks.

## WATCH OUT FOR

- No protected service identity is installed or even selected. The output deliberately makes no promise of target readiness, different UID, encryption-key recovery, independent backup, active-seat verification or C5 consent.
- SHA-256 inventory comparison detects changes *between sampled reads*. A malicious same-UID process could alter and restore bytes between samples, and may race future migration operations. This is **not atomic migration authorization**.
- The inventory hashes encrypted file bytes, not their AES-GCM tags. A passphrase is still required to authenticate/decrypt, and cannot be recovered by this tool.
- The current source remains under the ordinary user's UID, not isolated from processes with that UID. Do **not** expose it through Brave as a privileged host.
- Moving, copying, changing ownership, installing a service, selecting a protected destination, provisioning an account, taking a backup, or deleting originals requires **separate operator approval**, a reviewed rollback plan and independently verified kernel isolation.
- This source PR and tests do not touch workstation files, change Git worktrees, or activate production services.

## CHECKLIST

- [x] Reconcile merged #1888, Syntagma, Nurse 2 #1876 audit and C3e/C5 dependencies
- [x] Read-only source record inventory and stable fingerprint
- [x] Explicit stale-plan refusal and metadata-only output
- [x] Synthetic nonexistent/unsafe/racing inventory and false-auth guards
- [ ] Exact-head CI and independent Nurse 2 security review
- [ ] Operator acceptance and future local usage approval
- [ ] Independently verified backup, protected target UID, package install and OS permission design
- [ ] Operator-approved ciphertext-only migration with rollback
- [ ] Live authenticated C3e process/active-seat witness and C5 one-use consent
- [ ] Protected TimeW metadata UI and authorized multi-monitor restoration

## NEXT / DECISIONS

The next MACHINE implementation, once this dry-run source preflight is reviewed, can prepare an independently reviewed **protected-destination readiness and rollback protocol** using a separate service-owned CI fixture. It must not move actual archives or invent an installed service identity. Connections C3e and C5 keep their ownership. MACHINE stays in this Room; the user has final authority, and technical CI success alone does not signify final acceptance.
