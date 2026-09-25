# Team 8 / Team 5 Surface-Launch Ownership Seam

## Status

Parallel-safe architecture note only.

No AppControlW wiring or donor removal is authorized here.

Current certified patient when this seam was rechecked:
`6c74628baeaf7cf2f37808f9e57293aaad7e1788`

Team 8 branch remains rooted at `943d273` by instruction and is not rebased merely to
follow canonical movement.

## Why this needs an ownership decision

The donor currently couples two different responsibilities inside
`launchApplicationWithTabProvider(entry)`:

1. APPS launch behavior
2. launch-time preparation whose purpose is to make tabs/surfaces discoverable

Team 5's published provider contract now clearly owns:

- provider-native tab/surface discovery
- provider lifecycle
- activation
- diagnostics
- refresh
- DEVTOOLS-native lifecycle mutation
- raw provider identity evidence

It also explicitly avoids DesktopEntries and does not currently publish a launch-preparation
API.

Therefore Team 8 must not continue assuming that Team 5 will wrap normal APPS launch.

## Donor behavior that must not be lost

### Kitty bootstrap

For an entry classified as Kitty, the donor does not use ordinary DesktopEntry execution.
It launches Kitty with:

```
-o allow_remote_control=socket-only
--listen-on "unix:@appcontrol-kitty-$$"
```

Team 5 later discovers Kitty sockets from `KITTY_LISTEN_ON` in process environments and
uses Kitty remote control for tab discovery/activation.

This creates a real launch -> discovery dependency.

### Chromium / Electron accessibility bootstrap

The donor classifies these families from DesktopEntry-facing launch evidence:

- Brave
- Chromium
- Google Chrome / Chrome
- Code OSS
- VS Code
- VSCodium
- Electron

For those entries, normal launch may inject:

```
NO_AT_BRIDGE=0
ACCESSIBILITY_ENABLED=1
QT_ACCESSIBILITY=1
QT_LINUX_ACCESSIBILITY_ALWAYS_ON=1
--force-renderer-accessibility=complete
```

This exists so native accessibility surfaces are available after launch.

### DevTools bootstrap

The same donor path may add:

```
--remote-debugging-address=127.0.0.1
--remote-debugging-port=<port>
```

Current donor port policy:

```
Brave          9222
Chrome         9223
Chromium       9224
VS Code        9225
VSCodium       9226
generic Electron 9300-9499 via deterministic hash
```

Team 5's provider later scans running process command lines for
`--remote-debugging-port`, then discovers targets through the local DevTools endpoint.

This is another real launch -> discovery dependency.

## Current ownership facts

### Team 8 owns

- DesktopEntry catalog consumption
- APPS source semantics
- normal / Toolbox / Bottles launch policy
- APPS action catalog
- APPS-local presentation

### Team 5 owns

- tab/surface discovery
- provider-native activation
- provider lifecycle
- provider diagnostics
- provider-native DEVTOOLS lifecycle
- raw surface evidence

### Team 7 owns

- semantic application identity
- cross-provider joins
- ambiguity handling

## Unresolved question

Who owns **launch-time instrumentation whose only purpose is enabling a surface provider**?

This is narrower than APPS launch policy and narrower than tab discovery.

Possible architectures include, but are not selected here:

### A. Team 8-owned launch support profile

Team 8 classifies the DesktopEntry and includes surface-enabling environment/argv in its
normal launch plan.

Advantages:
- DesktopEntry evidence already belongs in Team 8 territory.
- Team 5 remains independent of DesktopEntries.
- execution remains a single launch plan.

Risk:
- Team 8 permanently owns provider-specific knowledge.

### B. Neutral surface-launch adapter

Team 8 emits a launch plan plus APPS-local behavior classification.
A neutral adapter augments environment/argv for enabled surface providers.

Advantages:
- separates APPS policy from provider bootstrap.
- Team 5 discovery remains clean.

Risk:
- introduces another shared contract/service whose ownership must be explicit.

### C. Team 5 launch-preparation descriptor

Team 5 publishes neutral augmentation requirements without performing launch.

Advantages:
- provider enabling policy stays near the provider.

Risk:
- current Team 5 contract explicitly avoids DesktopEntries, so Team 8 or Team 7 would
  still need to supply enough classification evidence.

## Team 8 recommendation for management review

Do not move `launchApplicationWithTabProvider()` wholesale into either Team 5 or Team 8.

Split it into:

```
APPS launch intent
      |
      v
surface-launch augmentation decision
      |
      v
final launch execution
```

The middle boundary needs an explicit owner before host integration.

Until that decision exists:

- Team 8 will preserve only pure launch planning.
- Team 8 will not implement Kitty/debug/accessibility bootstrap in the isolated provider.
- Team 5 remains free of DesktopEntry coupling.
- no current donor behavior is removed.
- no AppControlW surgery is performed.

## Event classification

This is a **new cross-team dependency / ownership ambiguity** under the event-driven
reporting model and should be routed to T0/T3 management before either Team 5 or Team 8
integrates host launch behavior.
