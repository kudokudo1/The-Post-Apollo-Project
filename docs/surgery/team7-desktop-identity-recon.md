# Team 7 — Desktop Application Identity Bridge
## Reconnaissance chart — certified fused baseline

**Baseline:** `943d27310f68d9941e7b19631fbd56aa9bd633e8`  
**Branch:** `team7/desktop-identity-recon`  
**Phase:** Deep reconnaissance / provider architecture  
**Scalpel status:** No AppControlW rewiring or donor-block removal

---

## Mission

Team 7 owns semantic desktop identity across the graph:

```
DesktopEntry
     ↕
Application
     ↕
Sway Window
     ↕
PID / process scope
     ↕
Tab / surface
```

That graph feeds APPS, WINDOWS, TABS, AUDIO, PROCESS CONTROL and Favorites identity adapters.

This team does **not** own Sway enumeration, tab discovery, audio discovery, process mutation, Favorites persistence or APPS launching. Those providers emit observations. Team 7 defines how observations attach to the same desktop entity.

The first rule is:

```
identity != matching heuristic
```

A successful fuzzy match is evidence. It is not automatically semantic identity.

---

# 1. Current identity anatomy at 943d273

## 1.1 DesktopEntry / APPS observation

Current application matching uses these DesktopEntry-facing fields:

- `entry.startupClass`
- `entry.id`
- `entry.name`
- command basename derived from `entry.command[0]`

`appEntryKey(entry)` currently resolves to:

1. `entry.id`
2. fallback `entry.name`

This key is used by APPS selection memory, Favorites application identity, application audio policy keys and application resource-scope keys.

### Current normalization

`normalizeAppToken()`:

- lowercases
- strips trailing `.desktop`
- removes all non-alphanumeric characters

This destroys provenance and punctuation distinctions. It is useful for matching, but it is not suitable by itself as canonical identity.

---

## 1.2 Sway Window observation

The Sway tree is treated as authoritative for current top-level window state.

Current window records contain:

```
id              Sway container id
name            title
appId           Wayland app_id
className       X11 class
instance        X11 instance
pid             compositor-reported PID
focused
workspace
output
floating
tabbed
tabGroupId
tabGroupName
fullscreen
rect
```

Current window identity helper:

```
windowKey =
    sway container id
  + pid
  + appId/className/instance
```

That is an excellent **session/window-instance key**. It is not persistent application identity.

### Current DesktopEntry ↔ Sway match

`windowMatchesApp()` compares:

DesktopEntry side:
- startupClass
- desktop entry id
- display name
- command basename
- final reverse-DNS id segment

against Sway side:
- app_id
- class
- instance

through normalized exact-or-suffix matching.

Important consequence: the current relation is heuristic and many-to-many capable. It should be retained as evidence, but not elevated unchanged into the semantic contract.

`appEntryForWindow()` currently returns the **first** DesktopEntry whose tokens match the window. That means catalog order can break ties silently.

---

## 1.3 Tab / Surface observations

Team 5 currently inherits several provider-native identities.

### Kitty

Record shape includes:

```
id           = "kitty:<tab_id>"
provider     = "KITTY"
appName      = "Kitty"
windowName   = kitty OS-window id
kittyAddress
kittyTabId
processPids[]
tabTitle
selected
```

This is strong provider identity and can also provide direct process evidence.

### Chromium / Electron DevTools

Record shape includes:

```
id                    = "devtools:<debug_port>:<target_id>"
provider              = "DEVTOOLS"
appName               = inferred from process executable
windowName            = target URL
debugPort
targetId
webSocketDebuggerUrl
tabTitle
selected
```

The `targetId` is provider-native surface identity.  
The debug port is provider-instance evidence, not application identity.

The current process scanner labels browser/Electron families from executable names such as Brave, Chrome, Chromium, VS Code or Electron. That label should remain provider evidence.

### libatspi

Record shape includes:

```
id         = "libatspi:<accessibility path>"
provider   = "LIBATSPI"
path
appName    = accessibility application ancestor
windowName = accessibility window ancestor
role
roleName
tabTitle
selected
```

This is accessibility-tree identity. It may be stable only for the current accessibility object lifetime.

### AT-SPI cache / DBus providers

The fallback cache provider carries:

```
id         = "atspi-cache:<busName>:<objectPath>"
provider   = "AT-SPI-CACHE"
busName
objectPath
appName
windowName
tabTitle
selected
```

These are strong provider-local coordinates, not cross-provider canonical application IDs.

### Current tab → DesktopEntry match

`appEntryForTab()` currently compares `tabInfo.appName` to:

- application display name
- desktop entry id
- substring relations
- hand-written special handling for VS Code and Kitty

This is significantly weaker than the Sway/DesktopEntry relation and should not become canonical.

---

# 2. Process / resource identity anatomy

Current process scope joining already proves identity is not one string.

### Application → process roots

For an application:

1. resolve Sway windows through `windowsForApp(entry)`
2. collect each window PID
3. expand descendants by PPID

So application process scope currently depends on the DesktopEntry ↔ Sway heuristic.

### Window → process roots

Window scope begins with the window's compositor PID.

A PID can be shared by multiple Sway windows, and the UI already detects this condition.

### Tab → process roots

Current order:

1. use provider-supplied `processPids[]` if present
2. for DevTools, locate process rows carrying the matching remote-debugging port
3. otherwise fuzzy-match tab app/window/provider text against Sway identity fields and use matching Sway PIDs

This is good evidence hierarchy. It is not a canonical identity hierarchy.

### Process-policy key

Per-PID resource policy currently uses:

```
pid | taskPersistentIdentity(process)
```

This guards against PID reuse. That pattern is important: ephemeral coordinate + persistent-ish evidence.

---

# 3. Audio identity anatomy

Team 6 currently has three separate matching systems embedded in AppControl.

## 3.1 Window audio

Audio properties considered:

```
application.process.id
application.process.binary
application.name
application.id
media.name
```

Window match order:

1. exact Sway-window PID == PipeWire application.process.id
2. fuzzy token match between Sway app_id/class/instance and audio properties

This is currently the strongest cross-provider relation because it prefers an exact PID join.

## 3.2 Application audio

Application aliases are derived from:

- startupClass
- desktop entry id
- command basename
- application display name

Generic tokens such as electron, chromium, browser, desktop, flatpak, shell names and reverse-DNS boilerplate are blocked.

Application audio match order:

1. audio process PID equals one of the application's matched Sway-window PIDs
2. exact alias match against PipeWire application binary/id/name

Unlike window audio, this intentionally avoids fuzzy suffix matching.

## 3.3 Tab audio

Tab audio tokens come from:

- appName
- windowName
- provider

They are matched fuzzily against PipeWire properties.

Current tab audio key is:

```
tab id | appName | windowName
```

This is a local policy/probe key, not a semantic tab-to-application identity.

### Team 7 conclusion for Team 6

Team 6 should preserve the raw PipeWire properties and matching observations, but should not expose a new canonical `AudioIdentity`.

---

# 4. Favorites identity anatomy

Favorites already exposes one of the clearest known identity deficits.

Current `favoriteKeyFor()`:

- APPS → `appEntryKey(entry)`
- RUN → Run-specific key
- THERMAL/SYSTEM → domain id
- KILL → persistent task identity
- WINDOWS/remaining modes → `mode:<modeIndex>:<label>`

The source comment explicitly states that WINDOWS still uses temporary labels until it gets a real stable identity.

This is a direct Team 7 seam.

Current result stability is also heterogeneous:

- Favorite wrapper → favorite key
- Tab → id/path/title/name fallback
- Task → persistent task identity
- generic → id/path/name fallback

Team 2 should receive provider reconstruction adapters from Team 7, not reach into WINDOW/TAB internals.

---

# 5. Identity classes discovered

The current patient already contains at least four distinct classes of identity. They must not be collapsed accidentally.

## A. Persistent semantic identity

Intended to survive session/process/window recreation.

Candidate evidence:
- DesktopEntry id
- Flatpak/application package identity where available
- explicit aliases/provider adapters

This class is **not yet fully defined**.

## B. Session application identity

Represents one running application instance or family during a desktop session.

Potential evidence:
- root process scope
- launch instance
- provider instance
- matched windows

This may be one-to-many relative to DesktopEntries.

## C. Ephemeral object identity

Examples:
- Sway container id
- PID
- Kitty tab id
- DevTools target id
- AT-SPI object path
- PipeWire sink-input index

These are valuable exact coordinates with limited lifetimes.

## D. Match evidence / aliases

Examples:
- app_id
- WM_CLASS / instance
- startupClass
- executable basename
- PipeWire application.name/id/binary
- accessibility app name
- normalized tokens

These should carry provenance and confidence instead of being converted immediately to truth.

---

# 6. Cardinality hazards

The bridge must support, not erase:

```
1 DesktopEntry -> many running application instances
1 Application  -> many Sway windows
1 Application  -> many PIDs
1 Window       -> one or several relevant PIDs
1 Application  -> many surfaces/tabs
1 Surface      -> provider-specific process scope
many PIDs      -> one logical application
many windows   -> one process
multiple DesktopEntries -> potentially same application family
```

The existing code already contains evidence for shared-PID windows and browser multi-process trees.

A final architecture that assumes every layer is 1:1 is rejected.

---

# 7. Proposed provider architecture — reconnaissance contract

No host rewiring is authorized here. This is the provider contract Team 7 should build toward.

## 7.1 Observation records

Each provider should expose raw observations without claiming canonical identity.

Example conceptual shapes:

```
DesktopEntryObservation
SwayWindowObservation
ProcessObservation
SurfaceObservation
AudioObservation
```

Each observation needs:

```
provider
providerKey
lifetimeClass
raw identity fields
aliases[]
relationships/evidence[]
timestamp or generation
```

## 7.2 Semantic entity

Team 7 should eventually publish an application entity separately from observations.

Conceptually:

```
ApplicationEntity {
    semanticKey
    desktopEntries[]
    aliases[]
    runningInstances[]
    windows[]
    processScopes[]
    surfaces[]
}
```

The exact schema is intentionally **not frozen yet**.

## 7.3 Relationship evidence

A relation should be explainable.

Candidate evidence types:

```
EXACT_PID
EXACT_DESKTOP_ID
EXACT_STARTUP_CLASS
EXACT_APP_ID
EXACT_PROVIDER_PARENT
EXACT_DEBUG_PORT_OWNER
EXACT_KITTY_PROCESS
EXACT_PIPEWIRE_APP_ID
ALIAS_EXACT
TOKEN_SUFFIX_HEURISTIC
DISPLAY_NAME_HEURISTIC
```

Team 7 should be able to answer not just “these match,” but “why do we believe these match?”

## 7.4 Confidence and ambiguity

Provider joins should be allowed to return:

```
resolved
ambiguous
unresolved
```

Never silently convert “first matching DesktopEntry” into semantic truth.

---

# 8. Initial authority boundaries

## Team 7 owns

- semantic application identity
- alias vocabulary and provenance
- cross-provider joins
- ambiguity handling
- DesktopEntry ↔ Application ↔ Sway ↔ PID ↔ Surface relationship graph
- identity adapters consumed by Teams 1/2/5/6/8

## Team 7 does not own

- Sway enumeration
- AT-SPI/DevTools/Kitty discovery
- PipeWire enumeration/mutations
- process telemetry/mutation
- Favorites persistence
- application launch behavior
- generic AppControl navigation/presentation

---

# 9. Immediate provider requirements for sibling teams

## Team 5 — Tabs / Surface Discovery

Preserve:
- provider
- provider-local key
- appName/windowName exactly as observed
- provider-native parent/process metadata
- processPids when known
- debugPort/targetId
- busName/objectPath
- Kitty address/tab id

Do not promote appName or provider-local IDs into canonical application identity.

## Team 6 — Application Audio

Preserve raw PipeWire properties including:
- application.process.id
- application.process.binary
- application.id
- application.name
- media.name
- stream index

Expose match evidence separately from stream identity.

## Team 1 — Process / Resource

Expose process/PID/PPID/scope observations generically.  
Do not depend on an APPS-only identity representation.

## Team 2 — Favorites

Favorites should store/reconstruct through provider identity adapters.  
WINDOW/TAB reconstruction should not depend on label-only keys once Team 7 contracts exist.

## Team 8 — APPS Core

DesktopEntries remain a primary identity source, but APPS must not own all cross-provider identity semantics.

---

# 10. High-risk current seams

1. **`appEntryForWindow()` first-match bias**  
   Multiple DesktopEntries can satisfy fuzzy matching. Current catalog order decides.

2. **Normalization is lossy**  
   Removing punctuation/domain structure helps matching but erases provenance.

3. **Display names participate in semantic matching**  
   Human labels are mutable/localized and should be weak evidence.

4. **Tab app identity is mostly textual**  
   AT-SPI and DevTools rows often lack a direct DesktopEntry/Sway parent edge.

5. **Audio matching is already three different policies**  
   Window, app and tab matching encode different risk tolerances.

6. **Process scope inherits upstream match quality**  
   Wrong DesktopEntry ↔ Sway match can widen or redirect resource control.

7. **Favorites WINDOWS identity is explicitly temporary**  
   Label keys are not reconstructable semantic identity.

8. **Ephemeral keys are mixed with persistent keys**  
   Sway id, PID, provider tab id and DesktopEntry id currently coexist in local policy keys.

---

# 11. Next Team 7 reconnaissance cuts — no host surgery

Before implementing a canonical provider, Team 7 should next:

1. inventory exact DesktopEntry fields available from Quickshell on the live system
2. capture representative Sway records for native, Flatpak, browser, Electron, Kitty, Toolbox and Bottles launches
3. capture matching process trees for those same applications
4. capture Team 5 provider records for the same targets
5. capture Team 6 PipeWire properties for the same targets
6. build a cross-provider fixture matrix
7. classify each edge as exact, inferred, ambiguous or unavailable
8. only then freeze the first semantic provider schema

The fixture matrix should deliberately include difficult cases:
- Brave native
- Firefox
- VS Code/Electron
- Kitty
- Flatpak application
- Toolbox-launched application
- Bottles/Wine application
- two windows sharing one PID if reproducible
- browser with multiple tabs/processes
- application with no live audio stream
- application whose display name differs from executable/app_id

---

# 12. Operating rule

```
PARALLEL:
new provider files
identity mapping
fixtures/tests
adapters
reconnaissance

SERIAL THROUGH INTEGRATION ROOM:
AppControlW rewiring
donor-block removal
shared result/detail/navigation changes
service lifetime integration
```

This chart intentionally changes no current behavior.
