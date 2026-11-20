# 🏥💜 Connections C3e ↔ TimeW // Sway IPC read-only wire preflight

PATIENT // The-Post-Apollo-Project  
ROOM // Protected Connections C3e / TimeW native-window identity witness  
STAFF ROLE // DOC successor (external Hospital-compatible; live registration unverified)  
ASSIGNMENT // Define/test bounded Sway IPC GET_TREE protocol observation with a disposable fake peer, **not** production compositor or Brave identity  
DEPENDENCY // [#2089](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/2089), source-only kernel native bridge peer evidence, awaiting independent review  
COORDINATION // [#2067](https://github.com/kudokudo1/The-Post-Apollo-Project/issues/2067)  
PRODUCTION // HOLD

## IMPLEMENTATION

The SwayPX compositor's own \`sway/ipc-server.c\` has a six-byte \`i3-ipc\` magic, two 32-bit native little-endian header fields, and \`IPC_GET_TREE\` opcode 4. This C3e-only preflight sends **only** the no-payload GET_TREE request to an **already-connected test-owned AF_UNIX SOCK_STREAM** socket with a bounded timeout. It accepts a finite reply header and bounded JSON tree and rejects truncated/wrong-type/oversized packets, duplicate JSON fields, invalid/duplicate container IDs, invalid structure and unbounded depth/children.

The test server is a disposable Python thread across a real Unix socketpair, not Sway. This proves the wire request/reader shape works on the specified fake fixture. The scanner reports a count of Brave-identified leaf nodes and whether two share one reported PID; it never returns titles, the raw tree, alleged extension window identity, or executable permission. It does not trust a title marker, window app_id, PID, focus, Sway con_id or fixture JSON \`browser_window_ref\` as proof.

**All native origin, installer/release root, Wayland surface / browser instance, TimeW pairing signer, C5 consent, compositor movement and restoration flags are immutable FALSE.** A single apparent Brave window is not proof either. The native issuer entrypoint unconditionally refuses.

## SECURITY DESIGN // Next source-of-truth decision (PROPOSED, not approved)

A future authenticated witness needs **both** independently protected strands:

1. A root/controller-enrolled actual compositor/seat connection, with a kernel-pinned installed SwayPX release identity, session binding, fresh per-window surface evidence, and revocation at process/window/session/seat changes. A user-selected \`SWAYSOCK\` path, mere JSON tree, native-host PID and temporary focus are insufficient.
2. An independently enrolled Brave/native bridge whose response is cryptographically or kernel-bound to the **specific browser window instance**, not merely the extension or browser process, then a trusted correlation to the exact compositor-side surface that survives simultaneous same-PID Brave windows and focus changes.

SwayPX/TimeW owners must jointly choose where the actual per-surface proof originates. A compositor-side protected event or explicitly approved protocol extension may be necessary. This PR **does not select or implement** that authority and does not change SwayPX or Brave.

Only after that source is independently reviewed and installed should C3e issue the existing TimeW \`MachineV2PairConsent.py\` PAIR-domain assertion. A separate C5 TimeW-specific protected native service must display exact before/target geometry and obtain fresh active-seat human consent, then the protected one-use operation writer must enforce spending and revocation.

## VERIFY

- [ ] 16 disposable Linux Unix-socket IPC and adversarial tree tests exact-head PASS
- [ ] Static code gate proves no native issuer, socket connection/listener, signer, subprocess or window movement
- [ ] GitHub exact-head workflow and Grammar PASS
- [ ] Independent Nurse 2 source review, TimeW interface compatibility, and SwayPX provenance-interface owner agreement
- [ ] Operator decides separately on merge, installed service, keys, host changes and final activation

## WATCH OUT FOR

A Linux SOCK_STREAM \`SO_PEERCRED\` check by itself names the original connected peer, not necessarily the process that wrote every byte after descriptor inheritance. A CI fake server is not an independently authenticated Sway compositor. This preflight neither authenticates any IPC peer nor bridges the gap from compositor tree to Brave window identity. #2089's \`SO_PEERPIDFD\` evidence concerns a *different* native bridge process; those facts must not be conflated.

## NEXT

Review the proposed compositor-and-browser provenance requirements with TimeW, SwayPX and Nurse 2. In the Connections lane, do not promote an observational match into a real pairing signer until a protected, reviewable **per-window** source of truth exists. Keep #2089 unchanged for its exact-head security review.

## DECISIONS

Source-only stacked draft, four additive C3e test/docs/workflow files. No live Sway IPC, Brave control, native service, installed key, C5, Hospital, TimeW geometry, SwayPX source or workstation modification. No merge or production grant.
