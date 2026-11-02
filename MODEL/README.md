✦︎✦︎✦︎ Meta Apollo Logos //

# ✮˙๋࣭⭑ MAP // MODEL

![](../BUILD/assets/design/chassis/focus-rail.svg)

> **STATE //** active \~\~ **VIEW //** architecture and contracts

// [🧭 ATLAS](../ATLAS/) \~\~ // **[✮˙๋࣭⭑ MODEL](../MODEL/)** \~\~ // [🖨 BUILD](../BUILD/) \~\~ // [⚒ DEV](../DEV/) \~\~ // [🖳 OPERATE](../OPERATE/) \~\~ // [⊹ ࣪ℼ˖ EVIDENCE](../EVIDENCE/) \~\~ // [࣪⋅˚🕮‧₊˚ ARCHIVE](../ARCHIVE/)

---

### ★⋆˙ CORE // WHAT THIS ROOM IS

MODEL describes architecture, ownership, contracts, services, and subsystem relationships beneath the desktop.

### ✮˙๋࣭⭑ CONTENTS // CURRENT

- `components/`
- `modules/`
- `services/`
- architectural contracts represented by the live QML tree

### ✮˙๋࣭⭑ CONTRACT INDEX // EXISTING PATHS

**Navigation / classification only.** These links identify contracts in their *current* paths; they do not rename, certify, relocate or supersede the originals.

- **TASKS / storage ownership architectural decision (operator-selected direction; design only):** [M12l local-first coordinator, separate GitHub/format adapters, and deferral of a privileged broker](./contracts/tasks-storage-ownership-adr-m12l.md). Evidence includes M12j's isolated native receipts, M12k's independently tested same-UID writer limitations, and official local-first/synchronization references. No production writer approval or activation.

- **Weather Station / Observatory worker recovery (proposed plan):** [Backend-first master roadmap](../docs/weather-station-backend-first-roadmap.md) covers connected sources, shared Hi-Fi radio, terminal/viewer architecture, remaining domains and acceptance gates. It is a proposed staged plan, not a live Hospital Assignment or implementation certification. The [Syntagma rules entry](https://github.com/kudokudo1/Meta-Apollo-Logos-How-I-Think/blob/main/AGENTS.md) owns shared operator/semantic guidance; this repository owns QML implementation and local technical contracts.

- **P // Weather Station / Stage Director virtual viewport:** [Real Kitty scene clipping, mouse pan/zoom and CRT shader preservation (strong proposal)](./weather-station-virtual-viewport-proposal-20261024.md). Mirrored with SwayPX; documentation only and no compositor implementation authorization.

- **Apollo Hub capability levels and succession (proposed):** [Level 1 display / Level 2 explore / Level 3 operate, TASKS + Weather integration boundaries, Stage 7 recovery](./contracts/apollo-hub-capability-levels-v0.md). Geometry W/H remains independent; no new service or action authority is implied.
- **Control families:** [Selector family foundation](./components/selector-family-foundation.md); [SelectorDial variants](../docs/selector-dial-variants.md); [NeonScrollBar API](../docs/neon-scrollbar-syntagma-api.md).
- **Visual behavior:** [Visual-language effects and recipes](./components/visual-language-recipes.md); consult [current QML components](../components/) before implementing changes.
- **Keyboard / focus:** [internal widget navigation](../docs/unified-widget-keyboard-navigation.md), [sub-mode navigation](../docs/sub-mode-keyboard-contract.md), [cross-widget Koinoikos](../docs/koinoikos-focus-mode.md), [window keyboard ownership](../docs/window-keyboard-focus-contract.md). These are distinct layers.
- **Presentation lifecycle and exceptions:** [window opening A/B result](../docs/window-opening-lifecycle-pilot.md); retain its observed crash boundary without claiming a proven root cause.
- **Social Hub / Phone Bridge (operator-selected architecture, design only):** [Network-first phone integration for iPhone and Android, with opt-in Bluetooth per-capability fallback](./contracts/social-phone-bridge-network-first-adr-v0.md). Covers SMS/messages, cellular calls, PC audio, contacts, safe provider arbitration, identity isolation and staged feasibility gates. No bridge is deployed; iPhone messaging/calling capabilities require device-specific verification.
- **Social Phone Bridge / Capability Policy P0 (synthetic, no phone access):** [Network-first per-capability route planner, strict identity/device/line scope, Bluetooth consent and unsafe-retry blocks](./contracts/social-phone-capability-policy-v0.md). New offline-only `services/phone/CapabilityPolicy.py` and tests do not discover/pair phones, contact users or modify the live Social UI.
- **Social Phone Bridge / KDE Connect P1 (presence-only, no SMS/phone access):** [Opt-in paired-and-reachable device count probe with transport and capabilities left unverified](./contracts/social-phone-kdeconnect-presence-p1-v0.md). Mock-tested inventory only; no automatic pairing, message access, Bluetooth enablement or Social UI wiring.
- **Social Phone Bridge / KDE Connect D-Bus plugin evidence P1 (synthetic only):** [Loaded/supported desktop SMS, Contacts and Telephony plugin evidence with explicit unknown permissions and transport](./contracts/social-phone-kdeconnect-dbus-evidence-p1-v0.md). Offline-only classifier and tests never query a real phone or produce a route-eligible backend.
- **Social Hub / provider access fallback:** [Native adapter status, existing Signal/Viber/WeChat desktop clients, and WhatsApp/Messenger official web fallback](../services/messaging/PROVIDER-ACCESS.md). Provider-owned desktop/web access does not imply native personal-message API support.
- **Social Hub / Account Manager handoff v0 (proposed):** [Identity-scoped service catalog and Connect All planning boundary](./contracts/social-account-manager-handoff-v0.md). Read-only discovery/planning only; no automatic login, account switching, or credential access yet.
- **Post-Apollo Identity Center / multi-organization and portfolio access (operator-directed scope; proposed architecture and build sequence v0.2):** [Canonical upgrade plan and worker handoff](./contracts/post-apollo-identity-center-upgrade-plan-v0.md). Requires independent LLC/nonprofit/customer tenants, above-company portfolio views, overlapping division + geography grants, several roles per person, and delegated personal/company/branch social accounts. **First-build priority:** organization/portfolio data model and permission engine design, with minimal authentication, a synthetic isolated-tenant pilot, then management UI and secure provider broker. Engineering details, staffing, implementation and deployment still require review and approval. The [earlier Social Account Manager v0 handoff](./contracts/social-account-manager-handoff-v0.md) remains a historical read-only catalog contract.
- **Identity Center foundation / synthetic tenant-permission fixture (experimental):** [Executable in-memory organization and grant gate, limitations and tests](./contracts/identity-center-synthetic-gate-v0.md). No IdP, live database, credential access, real workforce records or production API; this is an isolated policy-semantics proof alongside the [canonical upgrade plan](./contracts/post-apollo-identity-center-upgrade-plan-v0.md).
- **Identity Center authentication/request binding (synthetic v0):** [Versioned offline request boundary and trusted-verifier limitations](./contracts/identity-center-request-boundary-v0.md). Fake sessions in tests are resolved to principals by an injected verifier before invoking the tenant permission gate. **No actual IdP, HTTP service, login or production authorization.**
- **Identity Center / offline signed JWT + pinned JWKS verifier (experimental):** [RSA signature, issuer/audience, token-lifetime and revocation gate](./contracts/identity-center-oidc-jwks-verifier-v0.md), integrated only with the synthetic tenant/request fixtures. **No real IdP, login, API service or production activation**.
- **Identity Center / trusted OIDC discovery and JWKS rotation (experimental):** [Offline provider metadata snapshot and key refresh contract](./contracts/identity-center-discovery-rotation-v0.md). Tests exact issuer/JWKS URI, code + S256 metadata, key rotation/expiry and deny-on-failure using an in-memory issuer; **no live provider, secure HTTP transport or production sign-in**.
- **Identity Center / real disposable Keycloak PKCE CI pilot (experimental):** [Real-server authorization-code, S256 PKCE, signed-token, introspection and logout contract](./contracts/identity-center-real-keycloak-pkce-pilot-v0.md). Starts a temporary loopback-only Keycloak in GitHub Actions with generated test users; **no actual company login, local machine, production service or IdP vendor selection**.
- **Identity Center / existing Social USER // SETTINGS integration (UI-only v0):** [Read-only in-place Profile, Organizations, Connected Accounts, Security and Social Layout tabs](./contracts/identity-center-social-settings-navigation-v0.md). Preserves the current Social editor and keeps the organization switcher disabled until verified backend grants exist. **No actual login, company membership, desktop activation or account-provider changes.**
- **Identity Center / verified read-only membership context summary (synthetic):** [User-session organization, scope-grant and portfolio response contract](./contracts/identity-center-context-summary-v0.md). The offline `readMyContexts` request returns only the verified person's independent tenant memberships and unexpired grant previews. **No live API, production organization data, active UI switcher or desktop sign-in integration.**
- **Identity Center / durable read-only membership API (experimental):** [SQLite file-backed issuer/subject mapping and CI-only WSGI current-user Organizations response](./contracts/identity-center-durable-context-api-v0.md). Complements merged synthetic summary PR #986; **no public service, real company DB, production IdP or desktop login.**
- **Identity Center / real Keycloak-to-durable Organizations API (CI-only integration):** [End-to-end OIDC PKCE, signed session, persisted membership visibility, revocation and post-logout denial](./contracts/identity-center-keycloak-durable-context-e2e-v0.md). Integrates the existing disposable Keycloak pilot with the file-backed read-only API **in GitHub CI only**, without real accounts, UI wiring, production database or deployment.
- **Identity Center / tokenless desktop Organizations projection (staged UI v0):** [Fail-closed, read-only context display projection and future privileged host handoff](./contracts/identity-center-desktop-context-projection-v0.md). Adds a strict response validator and optional display-only input in the existing Social settings, with the organization switcher still disabled and **no connected session host, QML credentials, real user login or desktop activation**.
- **Identity Center / native privileged session host contract (offline v0):** [Host-only system-browser PKCE state, one-shot callback checks and in-memory access-token boundary](./contracts/identity-center-desktop-session-host-v0.md). Uses injected test callbacks with no real IdP, token vault, listener, deployed process, live UI IPC or company account. **No credentials ever enter Social QML.**
- **Identity Center / native browser loopback callback receiver (CI-only v0):** [One-use HTTP callback receiver and tokenless host integration tests](./contracts/identity-center-native-loopback-callback-v0.md). Binds only on explicit isolated test activation at numeric 127.0.0.1, never logs codes/state, refuses replay and invalid Host/Origin, with **no live desktop listener, Keycloak callback integration, real sign-in or Social credentials**.
- **Identity Center / real Keycloak browser redirect to native callback (CI-only v0):** [Actual disposable IdP Location, loopback callback, signed tokens, persisted Organizations and tokenless display](./contracts/identity-center-keycloak-real-loopback-callback-e2e-v0.md). Extends the existing Keycloak CI flow **without relaxing the native host's HTTPS rules**, activating a desktop service or enabling organization switching.
- **Identity Center / private desktop Organizations IPC (Linux CI v0):** [Separate-process host token custody and view-only Unix-socket display transport](./contracts/identity-center-private-desktop-ipc-v0.md). Validated snapshot-only protocol under a private 0700 directory and 0600 socket, with **no live QML bridge, OS credential store, production process or organization switching**.
- **Identity Center / Social Organizations read-only IPC viewer (stacked CI v0):** [Fixed tokenless XDG-runtime snapshot reader and existing-settings QML display wiring](./contracts/identity-center-social-ipc-viewer-v0.md). Depends on open draft #1013; a five-second gated viewer clears on closure, host failure or invalid responses, **without desktop deployment, privileged commands, credentials or organization switching**.
- **Identity Center / offscreen Qt Organizations reader smoke (CI v0):** [Native Qt 6 QML-engine property, signal and lifecycle verification of the existing read-only IPC viewer](./contracts/identity-center-offscreen-qml-smoke-v0.md). Uses isolated fake Quickshell.Io process stubs, **not** the live Sway/Quickshell desktop, real sessions or organization switching.
- **Social Hub / native schema v1.1 (proposed):** [Capability keys, timestamp units, composer-safety review](./contracts/social-messaging-schema-v1.1-proposal.md). This is pending separate operator acceptance and does not supersede v1.0 yet.
- **Social Hub / shared native messaging adapter contract (operator-approved v1.0):** [Technical API, normalized records, lifecycle and worker ownership](../services/messaging/ADAPTER-CONTRACT.md). Acceptance governs future adapter implementation; it does not certify live integrations or authorize merges.
- **Provider architecture:** [Git/GitHub evidence contract](./contracts/git-github-evidence-contract.md), [media-controller draft](./contracts/media-controller-v0-draft.md), [media/tab/audio investigation](./contracts/media-tab-audio-identity-v0.md), [audio service-local Team 6 contract](../services/audio/TEAM6_CONTRACT.md).
- **Weather Station / Observatory roadmap (operator direction + worker recovery, not implementation authorization):** [Backend-first master plan and shared Hi-Fi/terminal integration backlog](../docs/weather-station-backend-first-master-roadmap-20261023.md).
- **Diagnostics by current owner:** [focus audit](../docs/focus-acquisition-reconciliation-20261013.md) stays in `docs/` during active focus work; [Quickshell freeze evidence](../EVIDENCE/syntagma-main-thread-freeze-evidence-20261013.md) and [Git startup trace](../EVIDENCE/syntagma-git-startup-trace.md) live in `EVIDENCE/`; the [optional UI-lag probe instructions](../OPERATE/syntagma-ui-lag-probe.md) live in `OPERATE/`. These are evidence/procedures, not universal design laws or proof of a performance fix.
- **Certification:** [Hospital certification state contract](./contracts/hospital-certification-contract.md) defines normative certification behavior; implementation verification and runtime outcomes remain distinct evidence.

**Reconciliation rule:** preserve the original URLs and concurrent workers' active files; repair routing and links before any physical move. A valid static test is not automatically a runtime-verified appearance.

## 🧭 MAP // WHERE TO GO NEXT

![](../BUILD/assets/design/chassis/nav-rail.svg)

- Need repository orientation? Go to **ATLAS**.
- Need architecture? Go to **MODEL**.
- Need the live product? Go to **BUILD**.
- Need development machinery? Go to **DEV**.
- Need operator guidance? Go to **OPERATE**.
- Need observed results? Go to **EVIDENCE**.
- Need provenance? Go to **ARCHIVE**.