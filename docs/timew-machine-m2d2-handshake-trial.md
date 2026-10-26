# MACHINE M2d2 // scoped handshake simulation, before real application access

**2026-10-26 // Stage:** repository-only protocol policy and synthetic tests.
**No live adapter, installed extension, authenticated transport, desktop
capture, local configuration change, application launch, or actual REVIVE /
RESTORE functionality has been activated.** The operator's seven existing v1
checkpoints remain outside this milestone.

## Mechanism

M2d1 already compared fictional host/compositor windows with fictional
application session observations. M2d2 formalizes *one attempt* at binding
these observations by a time-limited challenge. Its only new module is
`services/time/MachineAdapterHandshakeTrial.py`.

`SyntheticHandshakeSession` takes an invented `scope_id` and a set of
schema-only adapter manifests. The fixture caller must explicitly choose
an application, declared adapter, intended host platform and individual
host observation. A synthetic permission flag `explicit_synthetic_allow`
is required before beginning. This flag is *not* an actual permission token
or authenticated operator gesture.

`begin(...)` registers a unique, caller-provided opaque UUID nonce and
host-observation ID, a 1–30-second simulated time-to-live, and gives back a
read-only challenge record. `verify(...)` consumes the nonce **before**
processing two bounded input claims. Both synthetic host and synthetic app
records must agree on scope, nonce, observed host window and app ID. The app
also has to name the declared adapter, opaque app instance/namespace
reference and bounded *count* of inner session items. Both sources must be
explicitly tagged `synthetic_host` and `synthetic_app`.

Wrong app/adapter, missing scope, outdated reply, duplicate app instance,
repeated host observation, malformed UUID, unexpected private field,
invalid count, replay, cancellation or unpermitted target host fail closed.
A failure consumes the challenge; it cannot be resubmitted.

Results contain only synthetic observation IDs/counts, never the submitted
app namespace/instance reference, browsing URL, title, directory, program
command or other personal content.

**Even a perfectly matching synthetic challenge returns**
`real_app_identity_verified=false`,
`real_host_binding_verified=false`,
`operator_consent_verified=false`,
`exact_session_match=false`, `action_allowed=false`, `safe_actions=[]`.

The result is **not** a trusted connection. Anyone supplying the fixture
dicts could forge both claims. A UUID echo is *not* proof of the process
behind an app window, nor a substitute for an OS/browser authenticated
transport. It also does not prove a saved session's IDs survive an app
restart or that two browser windows have the same internal tabs.

## Synthetic verification

`tests/timew/test_machine_adapter_handshake_trial.py` tests 24 invented
instances including **17 Brave, four Kitty, Firefox, VS Code and Ghostty**,
with failure/replay/expiry cases. It exercises one-shot consumption, mismatch
of source, scope, app and adapter, host reuse, separate nonce lifetime,
denied simulated consent, incorrect platform, forged/private fields and
duplicate claimed instance IDs.

`tests/timew/test_machine_adapter_handshake_trial_contract.py` blocks
live OS/app interfaces, writes and privileged actions. Full TimeW
foundation regressions remain mandatory.

## Next actual implementation gate

The next worker should propose **one narrow read-only app-to-host transport
experiment** with the operator's explicit approval before modifying the
machine or inspecting real session data. This is not authorization to begin
a blanket all-app collector.

1. Review the existing `integrations/proton/browser/` extension/native
   messaging seam and coordinate with Notifications ownership; its Proton
   companion is not general tab access.
2. Define a trusted host-side observation origin, installed process/app
   identity checks, peer credentials or browser-extension origin boundary,
   short-lived challenges, replay resistance and scope binding. Keep
   trusted backend verification **outside** the untrusted app payload.
3. Determine how a SwayFX window corresponds to a browser/terminal/editor
   OS window without title/position/PID guessing. Application interfaces
   might not expose this; treat inability to prove the link as a blocker,
   not a signal to move all matching instances.
4. Ensure actual read permissions and local file storage are separate,
   explicit choices. Default exclude private/incognito browsing, URLs,
   documents, shell commands, terminal buffers and credentials. Set
   retention and revocation requirements before any durable sidecar.
5. Test in an isolated disposable session: two identical app IDs, reordered
   windows, stale scope, spoofed client, duplicate events, disconnect,
   reboot and rollback. Never execute terminal recipes automatically.
6. Only after passing those gates can a new adapter accurately advertise
   authenticated session-window correlations. **Actual launch, relocation
   and RESTORE require independent authorization and further tests.**

## Product semantics and human-facing behavior

- **REVIVE:** Preserve the present life; minimally repair missing or moved
  *verified* windows where possible, never wipe ongoing tabs.
- **RESTORE:** Preserve/branch the current live life and reconstruct toward
  the selected historical checkpoint, with no silent state replacement.
- **ALREADY IN PLACE:** Show this only when the relevant scope truly matches;
  distinguish *layout counts match* from *internal session verified*.
- **NEEDS ATTENTION:** Fail safe on ambiguous identities, rather than
  reporting a normal 17-window browser as 17 invalid candidates.

The operator prefers a simple SAVE/REVIVE/RESTORE control flow and does
not want typed action phrases or technical candidate-selection homework.
This protocol is backend-only. Friendly checkpoint names and button
appearance remain separately scheduled.

## Ownership, rollback, verification

Consult `Meta-Apollo-Logos-Syntagma/AGENTS.md`, existing durable worker
handoff `docs/timew-machine-revive-restore-worker-plan.md`, current GitHub
head/PRs, and any actual Hospital ownership before later work. No Hospital
assignment or live session is inferred here.

This change only adds an isolated Python module, synthetic tests and docs.
Revert its focused PR to roll back. No local rollback needed because no
system or checkpoint state is written or accessed. Do not merge/activate
without the operator's required authorization.
