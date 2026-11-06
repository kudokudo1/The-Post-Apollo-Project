# 🏥💜 Universal Connections // C2t native RPM signatures and transaction rollback

PATIENT // kudokudo1/The-Post-Apollo-Project  
ROOM // Universal Connections · CPU++ SETTINGS  
STAFF ROLE // External Hospital-compatible Doctor, provider OPEN AI // CHATGPT  
ASSIGNMENT // Signed native test RPMs, upgrade/downgrade/remove transactions inside disposable Fedora 44 VM  
BASE // main 6f886331d4b2747759beffb36dadf9ac33d54539 (C2s #1345 merged)  
PERMISSION // GitHub isolated branch, temporary signing key in CI, draft PR only. Not live Hospital registered.  

## IMPLEMENTATION

C2s #1345 merged after verifying a tar-bundle staged fake read-only Connections host, tamper refusal, SELinux enforcing, dedicated `postapollo_connections_t` domain and cleanup. C2t begins a **different, smaller distribution security question**: do Fedora's native RPM package signature, ownership and update transactions work under an offline enforcing guest?

The CI Fedora 44 builder uses `rpmbuild` and `rpmsign` to produce v0.1 and v0.2 of `postapollo-connections-c2t-fixture`. It creates a unique temporary OpenPGP signing identity inside a short-lived Fedora builder container. The **private key never leaves the container** and is destroyed with it. Only the two signed RPMs, an armored disposable public key, a fingerprint and SHA-256 manifest are staged into the offline Fedora Cloud VM. No production signing key or release identity is claimed.

The RPM contains root-owned **inert data** in `/usr/share/post-apollo/c2t-fixture`: the existing fake status host Python source, noninstallable C2n systemd and system D-Bus policy templates, candidate C2r SELinux text policy, its file-context proposal, and one version marker. It has **no install, upgrade, remove, trigger or service activation scriptlets**, no executable at `/usr/libexec/post-apollo`, no actual systemd unit, no registered bus policy, no SELinux module installation, no Linux service account and no credential operation. This deliberate boundary differs from a deployable Post-Apollo service RPM.

The guest is the same pinned Fedora Cloud Base Generic 44 image used by C2p–C2s, with an independent Fedora kernel in SELinux Enforcing mode and QEMU's `-nic none`. It checks an untrusted signer is rejected *before* public-key import, verifies tamper detection before any package transaction, imports the public key **only into the guest's disposable RPM trust database**, requires native `rpmkeys --checksig` success on both RPMs, installs v0.1, upgrades to v0.2, downgrades to v0.1 using `--oldpackage`, and erases the package. Each version must be readable from disk, agree with the rpmdb and pass `rpm -V`. It then removes the test signer key and compares the RPM trust set to its initial state. Real service paths must remain absent throughout.

## HOW TO USE

No desktop action is required. CPU++ → SETTINGS → CONNECTIONS remains its existing read-only observational interface. No workstation, Silverblue layer, service, keyring, signing key or credential is modified. This is repository and disposable CI work only.

## VERIFY

Require Fedora native signed RPMs, verified untrusted-before-import and accepted-after-import state, exact fixed input digests, corrupted-RPM refusal, v0.1 install, v0.2 upgrade, v0.1 rollback, erase, RPM database and file consistency, signer key cleanup, SELinux still Enforcing and guest still offline. Every false claim of 'signed production release' or 'Silverblue compatibility verified' is prohibited.

## WATCH OUT FOR

**CI signing demonstrates the mechanism, not production trust.** An ephemeral self-signed test key does not establish an OpenAI, Post-Apollo, operator, organization or Fedora trusted signing authority. A checksum bundled beside its own public key is not an independently authenticated release chain. A future packaging decision must cover protected long-lived keys, key rotation, public-key distribution, reproducible builds, SBOM and verification against a separately trusted root.

The RPM is intentionally inert. It is neither an activated protected Connections host nor a working encrypted TASKS recovery host. No `rpm-ostree` layering or immutable-base reboot validation occurs here. That requires a separate Fedora Silverblue VM/ostree deployment acceptance gate. C2r/C2s remain the evidence for actual isolated fake host execution under systemd and SELinux. They do not implement production operator consent.

The independent TASKS M13t PR #1304 has already merged. A shared-owner coordination comment in #1304 separates exact three TASKS recovery permissions, monotonic committed source revision and authenticated host/operator consent; this C2t package test does not change those responsibilities.

## CHECKLIST

- [x] Recheck C2s merge, Syntagma protocols, open Connections work and latest main
- [x] Add inert Fedora RPM spec with no scriptlets or production install paths
- [x] Add Fedora temporary key and native signing builder
- [x] Add offline Fedora guest signature and RPM transaction tests
- [ ] Complete exact-head CI and correct build/test-only failures
- [ ] Independent security review and operator PR acceptance
- [ ] Dedicated root-managed package installation path + signed release provenance
- [ ] Immutable Fedora Silverblue `rpm-ostree` upgrade/reboot/rollback acceptance
- [ ] Production authenticated consent, provider operation and source-revision checks

## NEXT

If CI passes, C2t establishes a reusable package-authenticity and rpmdb rollback test harness. Next stage may investigate a Fedora Silverblue/ostree VM, signed service package ownership/relabeling and rollback, and negative capability tests. No local installation unless specifically authorized.

## DECISIONS

Draft PR only. No workstation changes, no local package/keyring operations, no CI private keys exported, no actual production host installation, no NASA or TASKS draft access, no production grants and no merge.
