# 🏥💜 TASKS // M13x Linux Kernel Source-Owner Boundary Evidence

**PATIENT //** `kudokudo1/The-Post-Apollo-Project`  
**ROOM //** TASKS source integrity and encrypted recovery preflight  
**STAFF ROLE //** DOC, Hospital-compatible external / OPEN AI // CHATGPT, no live registration verified  
**GITHUB BASE //** main `5c1faab33836388175038c59d52231fad6c921e5` on November 6, 2026  
**SCOPE / PERMISSIONS //** Additive GitHub-only disposable Linux OS tests, CI, documentation. No actual TASKS/Quickshell file changes, Fedora machine writes, account creation, keyring, source migration, Connections host edits or merge.

## IMPLEMENTATION

Merged M13w #1367 introduced an unmounted, fail-closed source receipt interface. The intended next step was to prove that a native save came from the correct source owner, not just that JSON bytes matched. Before attempting that promise, M13x probes a fundamental obstacle in the actual architecture:

1. The production `services/hub/ApolloHubTodoStore.qml` runs `FileView.setText()` under the ordinary user's Quickshell process and is still the sole JSON writer.
2. An independent host with a **different Linux UID** can own its own private directory with `0700` and synthetic source file with `0600`. The kernel denies an unrelated desktop process direct reads, writes and path replacement.
3. That same protection also denies **the current FileView writer** when it executes under the desktop UID. A protected host would need to become the writer or introduce an authenticated, controlled capability into a refactored single-writer path. It cannot be secretly inserted as an approval token while leaving direct, ordinary-user FileView writes untouched.
4. When desktop software owns the source in a user-writable directory, an uncooperative process with the **same UID** can replace it, even when another process holds an advisory `flock`. This is consistent with M12k and demonstrates an actual Linux filesystem behavior, not merely a fake state-machine refusal.
5. Linux Unix-domain `SO_PEERCRED` provides kernel-reported PID/UID/GID for a peer. Two separate processes running under the same desktop UID receive the **same UID** even if their user-controlled labels are `TASKS_UI` and `OTHER_SAME_UID`. The PID differs but an integer PID by itself does not attest executable integrity, approved release provenance, sender isolation, operator consent or exclusive authority.

The new `tests/tasks/test_task_kernel_owner_boundary_m13x.py` uses Python standard library and actual Linux subprocesses. The runner starts as **root in a disposable GitHub Ubuntu VM**, allocates three unused numeric test UIDs without adding users or groups, creates only a new `/tmp/m13x-custody-*` tree, and drops OS credentials with `setgroups([])`, `setgid()`, `setuid()` for child processes. It checks DAC denial on protected source, successful same-owner access, adversarial same-UID atomic replacement under an unrelated flock, and `SO_PEERCRED` kernel PID/UID/GID observation for three separately spawned clients. All fixture file content is an explicit fake `M13X_DISPOSABLE_ONLY` marker, never a real task.

There is **no installation** and no SELinux module or policy change. A clean GitHub-runner UID experiment is not a Fedora Silverblue acceptance, a native Quickshell callback run, a dedicated authenticated host, or a production permission service.

## HOW TO USE

No desktop action. GitHub Actions runs only in its disposable Ubuntu runner:

```sh
sudo env GITHUB_ACTIONS=true M13X_DISPOSABLE_CI=1 \
  python3 -B -m unittest discover -s tests/tasks \
  -p 'test_task_kernel_owner_boundary_m13x.py' -v
```

This command uses root privileges and should **not** be run on the operator's live Fedora system. The test actively refuses when the two explicit CI environment markers or root identity are absent. These markers are a safety preflight, **not trusted authorization or anti-spoofing**. They do not grant production access.

## VERIFY

- Two distinct Linux UIDs: kernel refuses read/write/replace on another user's private fixture; source remains byte-identical.
- Legitimate owner UID can edit its own synthetic source. That is a kernel permissions observation, not evidence that an application is an approved release.
- Desktop UID cannot direct-write a host-owned file. This is an architectural compatibility constraint for the existing `FileView` writer.
- Two separate same-UID processes: one can atomically replace an ordinary same-UID fixture despite an existing flock.
- Unix `SO_PEERCRED`: PID is the real connecting child, UID/GID match the kernel credential, and a forged caller label does not create a different OS identity.
- Existing sole TASKS source writer, M13w fail-closed receipt, M13v and M13u revision evidence, and Connections deny-all regression tests are unchanged.
- No real QML launch, OS accounts, source ownership migration, live task data, key, application sandbox, SELinux domain, user consent or signed executable identity was tested by M13x.

## WATCH OUT FOR

These are genuine **kernel-enforced test principals**, but the process running the test is root in an ephemeral GitHub runner. The CI test's arbitrary numeric UIDs are not real installed accounts and must not be copied into production. `SO_PEERCRED` authenticates Linux process credentials, not a Post-Apollo app, signer, business user or request purpose. A provider string, UI role, IPC label or process PID alone is insufficient. Filesystem permissions can enforce an ownership boundary only when the source is actually outside the untrusted principal's write reach. Granting desktop UID direct write access recreates the original same-UID threat.

M13x does **not prove who completed a native Quickshell save**. The existing M12i native harness and M12k race evidence remain relevant, and no draft may be cleared merely because source bytes or a callback match. The live guard constants remain false.

## CHECKLIST

- [x] Recheck canonical Syntagma rules, main HEAD, merged M13w and active PR ownership
- [x] Inspect M12l accepted single-coordinator ADR, M12i actual FileView harness and M12k adversary
- [x] Add real Linux OS UID/DAC + SO_PEERCRED disposable feasibility tests
- [x] Preserve single production writer, no extra host, no actual draft/credential writes
- [x] Add targeted CI and coordination report
- [ ] PR-head GitHub CI and independent review
- [ ] Operator PR merge / final acceptance
- [ ] **Architecture decision** if hostile same-UID protection is a hard requirement
- [ ] Real native source-owner proof and crash/restart acceptance in a separately approved isolated environment
- [ ] Connections host caller/operator authentication and key-release consent
- [ ] Real opt-in encrypted capture, preview, deletion and restore testing

## NEXT

Preserve **M12l's accepted default** unless the operator explicitly changes the threat model: one local-first logical storage coordinator with honest limitations against malicious same-UID processes. Improve independent native save readback, conservative draft retention and crash recovery, without falsely claiming OS-enforced hostile-writer protection.

If protecting the real saved JSON from malicious same-UID desktop processes becomes a hard security requirement, escalate an explicit design decision before modifying the running writer. The alternatives have different costs:

- **A. Stay with the single Quickshell `FileView` writer:** protect against ordinary stale state, crashes, conflicts and accidental changes with revision checks and backups, but **do not claim** secure source custody from all same-UID peers.
- **B. Give a separate OS-confined owner exclusive write custody:** requires moving the actual sole writer behind an authenticated trusted IPC boundary, giving up direct FileView writes, and providing signed launch, stable authority, bootstrap, rollback, native tests and production acceptance.

Neither option is chosen by this CI experiment; the accepted M12l architectural direction remains in force. Connections credential authorization is still an independent owner-bound concern; do not conflate C2 protected status with TASKS source custody.

## DECISIONS

No second TASKS writer, production QML modifications, filesystem access outside disposable CI, new OS accounts, SELinux changes, real credential lookup, local workstation work, automatic replay, recovery activation or PR merge. This is a kernel facts experiment and a concrete feasibility blocker, not an implementation of real protected TASKS save acknowledgment.
