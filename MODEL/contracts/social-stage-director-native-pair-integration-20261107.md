# Social W // Native Stage Director compositor handoff

**STATE //** Repository integration in a separate reviewable branch. Not locally installed or operator-accepted.  
**PATIENT //** `kudokudo1/The-Post-Apollo-Project` Social W, with compositor dependency `kudokudo1/Post-Apollo-SwayPx` production PR #109.  
**ROOM //** Unified Social W FloatingWindow and docked native Vesktop.  
**PROVIDER //** OPEN AI // CHATGPT. Operator-directed Stage Director integration lead; live Hospital registration unverified.

## IMPLEMENTATION

Social W already has a persistent Sway IPC geometry bridge, launched by `widgets/messanger/MessagingW.qml`, and a full *initial docking* handshake for the correct visible Vesktop main window. This branch reuses that as the trigger for the new native compositor pairing interface in SwayPX PR #109, instead of authorizing a pair based merely on application text.

`DiscordGeometry.py` now carries the exact Social container ID and shell from its read-only Sway tree snapshot. After QML marks Discord ready **and** docked, the helper requires a visible Social XDG toplevel, a visible native Wayland Vesktop **main** XDG toplevel, unique positive Sway IDs, exact Social slot alignment, valid selector width and inset. Only then does it ask local Sway to `stage_director_social pair HOST_ID GUEST_ID RAIL INSET`. The compositor separately validates live mapped native views/clients, output/workspace and pairing geometry.

When Sway acknowledges the pair, the helper reports `nativeStageDirector=true` and no longer sends fast-follow commands. `MessagingW.qml` likewise observes the new shared geometry but **does not** send follower geometry writes. The helper probes native `status` periodically; Sway refusing that status, a closed/hidden menu, app switching, container ID replacement or mode handoff revokes local native state and reverts to the existing 8 ms fast-follow behavior. The helper sends an explicit `stage_director_social clear` on a pair change or process exit.

The compositor production code supports native Wayland Vesktop first; XWayland and browser families continue the legacy bridge unchanged. An older SwayPX without the native command returns failure, is retried infrequently, and keeps the same previous behavior without prompting the user.

## VERIFY

`tests/messaging/test_social_native_stage_director_bridge.py` covers initial exact dock, native pair once, status, obsolete compositor fallback, refusal for splash/XWayland/hidden/missing identities, new exact guest replacement, explicit clear and no QML follower writes during native control. `.github/workflows/social-native-stage-director-bridge.yml` runs that test without touching the operator's system. Pair PR #109 separately compiles the **actual production SwayPX** compositor.

## WATCH OUT FOR

The Sway IPC socket is already a same-user desktop-control interface and not an independent multi-tenant security boundary; private Wayland custody would require another issuer. The helper cannot prove any exact client identity by itself, so the compositor must recheck live objects. Passing unit tests do not prove the physical mouse, actual Quickshell/Vesktop frames, popup clipping, multi-output/scaling or live deployment.

SwayPX and Social W PRs must be integrated in the correct order, **SwayPX first**, then Social. The bridge was explicitly designed to fall back when SwayPX is older or the native pair cannot be established. No automatic merge or local restart is authorized by writing these branches.

## DECISIONS

Preserve Settings++, rail dimensions, Social layouts and all other providers. Do not rewrite Company/MapLibre, Weather or notifications. Keep legacy geometry bridge as rollback and preserve the exact initial dock safety contract. No local Quickshell/Sway reload, file write, install or runtime activation occurred.
