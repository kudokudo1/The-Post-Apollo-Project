# 🏥💜 Post-Apollo Connections // C2a Host Credential Boundary

**PATIENT //** `The-Post-Apollo-Project`  
**ROOM //** Universal Connections · CPU++ Settings  
**PHASE //** C2a only · read-only host capability and closed permissions  
**OPERATOR AUTHORITY //** User retains acceptance and local machine control  
**CURRENT IMPLEMENTATION //** [ConnectionsBroker.qml](../services/connections/ConnectionsBroker.qml), [ConnectionsBrokerPolicy.js](../services/connections/ConnectionsBrokerPolicy.js), [ConnectionsSecretServiceProbe.py](../services/connections/ConnectionsSecretServiceProbe.py)

## IMPLEMENTATION // What C2a actually does

The **CPU++ → SETTINGS → CONNECTIONS** UI is the shared user-facing management surface. The `qs.services.connections` module is a metadata/status boundary, **not a new password manager**. Social identity layouts and display account labels remain with the Social owners. Notifications owns its events, and Weather owns its provider retrieval.

C2a adds one deliberately narrow host capability:

- **CHECK KEYRING** initiates a user-clicked D-Bus call to the session **bus daemon** asking whether the name `org.freedesktop.secrets` is currently owned.
- A positive result means only `SECRET SERVICE FOUND // UNLOCK UNKNOWN`. It does **not** prove unlock, any stored entry, provider authentication, or authorization to fetch a key.
- A negative or malformed result remains explicit and fails closed. No inspection of the user's keyring contents, implicit service activation, auto-unlock, enumeration, secrets or login attempts.
- `ConnectionsBrokerPolicy.decision()` denies every access operation. Registered pairs are future **intended** consumers, not trusted caller identities. The UI presents their proposed scopes only.
- `ConnectionsBroker.credentialActionsEnabled` is hard-disabled. C2a contains no stored credential, token, API key, session, socket server or durable capability grant.

## HOW TO USE // Current screen

1. CPU++ → SETTINGS → CONNECTIONS.
2. Select **NASA FIRMS** or **Proton Mail** in the center bay.
3. The right bay shows the proposed required access and intended consumers.
4. Click **CHECK KEYRING** to inspect only whether the OS secret service is active. No privilege prompt should be initiated by this operation.
5. This is **diagnostic**; it cannot yet connect NASA, retrieve email, or store a key.

## C2b // Proposed bounded next implementation (NOT YET AUTHORIZED OR ACTIVE)

Use one host-side credential/action broker rather than giving QML widgets `secret-tool lookup` or environment variables. A simple caller-supplied `consumer: weather-earth` string is **not** authentication. The future broker must establish a trusted invoking process/capability boundary, with revocable user approval, and must perform scoped provider operations without revealing stored secrets to untrusted consumers.

Proposed boundary:

```text
CPU++ CONNECTIONS (consent UI)             SOCIAL (identity labels only)
               |                                      |
               v                                      v
       trusted connection broker <---- profile and permission context
        |                    |
        | keyring storage    | provider-specific action
        v                    v
 Linux Secret Service     NASA FIRMS HTTPS request
  (encrypted key)       (secret used internally only)
                              |
                              v
                        WEATHER // hotspots
                        no raw key in QML
```

Before any production storage, explicitly decide and verify:

1. **Caller authority.** Verify the caller using a host-controlled channel and scoped, unforgeable session/capability. UID/PID or a self-declared service name alone may not isolate same-user apps.
2. **Consent.** The operator approves provider, account scope, consumer, operations, expiry and revocation. Do not silently import account credentials from mail. Email is an untrusted source; matching a sender/subject is not sufficient evidence.
3. **Storage and unlock.** Confirm the actual OS Secret Service provider, locked/unlocked behavior, permission UX, recovery/backup, deletion and rotation. Avoid installing or switching keyrings automatically.
4. **Leak boundaries.** Do not put raw keys in QML properties, logs, CLI argv, process environment, URLs, JSON identity stores, GitHub issues or browser handoffs. Feed input to the host broker by a guarded IPC/pipe, not source literals.
5. **Provider proof.** Key presence is not validation. A bounded authenticated provider request must succeed before reporting CONNECTED. A failed request must retain a truthful last-good/degraded state and respect the provider cooldown.
6. **No browser yank.** Account setup belongs in the Post-Apollo UI. Embedded provider flows can be added through approved Stage Director hosting; unsupported pages must not be represented as fully in-world.
7. **Recovery.** Support explicit revoke/disconnect, lock/unlock, key loss, and restart without leaving a silent always-unlocked entitlement.
8. **Negative testing.** Use disposable Secret Service, synthetic keys and fake provider endpoints, with wrong consumer/scope/identity, expired grant, cross-profile, revoked grant, restart, and no-provider denial tests.

The initial production candidate is **NASA FIRMS**, one provider and one scoped read-only operation, before expanding to Proton Mail's much more sensitive read/send/modify permissions.

## VERIFY

Tests in C2a cover fixed policy scope, denied grants, non-activating D-Bus command, malformed results, UI status, and C1 regression. The extended native CPU++ acceptance clicks CHECK KEYRING in isolated CI. These tests **do not** certify actual Fedora runtime or production keyring authentication.

Prior TASKS M13g/M13h documented and tested Secret Service under a **disposable** environment. Reuse its safe provider evidence and do not seize the TASKS encryption owner or touch its keyring items.

## WATCH OUT FOR

OS Secret Service is generally scoped to a user session, not a verified individual Quickshell widget. Do not call it a cross-application permission manager. A malicious program running with equivalent user permissions may be able to access secrets in an unlocked collection unless stronger isolation is in place.

`ConnectionsRegistry` still reads the legacy FIRMS key *presence* from the startup environment, separate from this new broker. C2a does not migrate or remove that compatibility path.

## CHECKLIST

- [x] C1 UI and read-only owner registry merged
- [x] C1 native test merged and green
- [x] C2a deny-all broker policy
- [x] C2a manual non-activating OS probe
- [x] CPU++ right-bay keyring status and proposed scopes
- [x] Unit/contract tests and isolated native click workflow
- [ ] Final-head CI and native runtime evidence
- [ ] Operator PR review/merge and desktop UI acceptance
- [ ] C2b consented storage / scoped NASA action with security review

## NEXT

Review C2a. After user approval, implement a **disposable, fake-only** credential-broker transport and NASA action proof in an isolated test first. Then decide if production authorization is adequate before enabling user-provided keys.

## DECISIONS

C2a is not an authentication system. Caller identity, credential persistence, revocation semantics, unlock prompts, recovery, and production enablement are deferred to an explicit new assignment and user acceptance.
