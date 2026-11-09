# 🏥💜 Connections C3e-O // Actual signed Python-host RPM payload provenance

PATIENT // The-Post-Apollo-Project  
ROOM // Universal Connections · protected host trust  
STAFF ROLE // DOC · Original parallel development lane  
ASSIGNMENT // Prove real C3d signed RPM contains exact host script, unit and bus policy bytes  
OTHER OWNERS // C4b/C2v Silverblue installation/rollback; C5 protected consent  
BASE // Current main, following C3e-N #1603  
PRODUCTION // HOLD

## IMPLEMENTATION

C3e-M proved that a purpose-signed native ELF could be identified from Linux `/proc/PID/exe`. But the **actual C4b installed service is not that C test ELF**. Its signed C3d RPM contains a Python script at `/usr/libexec/post-apollo/connections-status-host`, launched through a distinct Python interpreter path. Signing the interpreter alone does not authenticate the installed Python script.

C3e-O closes the first concrete artifact-side gap using the **existing C3d signed RPM builder**, without changing or duplicating its packaging source:

1. Build the actual C3d signed fake-status RPM in the already-established disposable Fedora container, with its temporary package signer and immutable artifact manifest.
2. In a different Fedora verifier container, create a completely isolated RPM trust database and import only the disposable test signer whose fingerprint is explicitly pinned by the test harness. Verify the RPM's real OpenPGP signature, signed RPM identity and package manifest. The test key is not imported into the host system RPM database.
3. Refuse unexpected RPM payload paths, install scriptlets and triggers. Extract the signed archive into a private temporary directory; **do not install or execute** it.
4. Check the actual extracted script's bytes against the tracked `C2rStatusHost.py` source (including its specific /opt Python shebang), the root-owned static systemd service template and the default-deny D-Bus policy template. Require exactly 0555 script and 0644 unit/policy modes.
5. Emit bounded SHA-256 hashes of the signed RPM and its three installed payload members with all permission flags false. Adversarial tests reject wrong signer pin, tampered signed package, forged/invalid public key, altered script/unit/DBus policy bytes, symlinks, writable source, missing files and execution outside disposable CI.

This verifies **actual signed package payload provenance**, rather than relying on a claimed JSON digest or Python interpreter signature. It is a read-only artifact verification and does not measure a running installed process.

## HOW TO USE

`.github/workflows/connections-c3eo-signed-python-payload.yml` performs the build and checks in isolated Fedora 44 containers on an ephemeral GitHub runner. No operator desktop, keyring, production package installation, client credentials, internet provider request or UI authorization is involved.

## VERIFY

- [ ] New signed RPM build in Fedora, isolated rpmdb OpenPGP signature and exact three installed members.
- [ ] All 14 adversarial/matching test cases pass.
- [ ] Prior C3b origin/C2n default-deny and Meta Apollo Grammar remain green.
- [ ] Independent security review and operator acceptance.

## WATCH OUT FOR

The C3d builder's key is disposable and self-generated. An isolated RPM database with its exported public key proves the *artifact signed by that test key*, not a persistent operator-enrolled trust root. The checked source tree is also CI-controlled. No secret or production signing key exists here.

This still **does not measure a running installed process** in the actual disposable C4b Silverblue VM, tie the Python script to its D-Bus/systemd PID or SELinux domain at runtime, authenticate a human operator or provide rollback-resistant independent witness custody. No proof is carried across the C4b guest boundary in this milestone. All outputs are diagnostic only; `installedGuestMeasured`, `hostAuthenticated`, `canApprove`, `credentialActionsEnabled`, and `productionAuthority` are false.

A malicious root actor could replace the script between an observation and use, and even identical RPM contents alone cannot prevent that. A future C4b-owner-approved guest read-only measurement must use the real service PID/UID, executable interpreter, script inode, package ownership and signed payload hashes together with the existing C3b OS/D-Bus/SELinux evidence, and it must be authenticated by a separately trusted producer to be usable outside CI.

## CHECKLIST

- [x] Recheck current main and C3e-N, C3e-M, C4b/C2v, C5 concurrent ownership.
- [x] Inspect C3d builder and exact script, systemd unit, D-Bus policy sources.
- [x] Build independent signed RPM payload verifier, 14 tests, workflow and handoff.
- [ ] Repair any observed CI defects in DOC-owned source only.
- [ ] Independent review and operator disposition.
- [ ] Obtain C4b owner's read-only runtime measurement producer, or a concrete ownership handoff, before modifying their guest runner.
- [ ] Define genuine secure evidence transport and signer enrollment before attaching witness authority.

## NEXT / DECISIONS

Coordinate a narrow C4b-owned runtime witness seam to hash the **actual installed script** and tie it to the systemd/D-Bus service PID *during* the accepted booted C4b test, comparing to these signed RPM payload hashes. The C4b producer must avoid changing the existing two-reboot rollback sequence, guest confinement, installed files, or cleanup gates.

The source and workflow remain standalone, main-based, CI-only. No merge, local host change, actual provider grant, real credentials or production activation.
