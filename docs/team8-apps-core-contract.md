# Team 8 — APPS Core Integration Contract

Certified origin used by this branch: `943d27310f68d9941e7b19631fbd56aa9bd633e8`

Current canonical patient may advance independently. Do not rebase this branch merely to
look current. Re-anchor only when T3 Overhead releases an authorized host-integration slot.

## Scope

Team 8 owns APPS-specific behavior that remains after shared physiology is removed:

- DesktopEntries catalog consumption
- Native / Flatpak source classification
- HIDDEN adapter input from future RunService
- normal launch semantics
- Toolbox launch semantics
- Bottles launch semantics
- DesktopEntry action presentation
- browser-specific APPS actions
- APPS-local metadata / presentation helpers

## Explicit non-ownership

Team 8 does not own:

- process/resource scope or mutations — Team 1
- tab/surface discovery, activation or provider lifecycle — Team 5
- application/window/tab audio — Team 6
- cross-provider semantic application identity — Team 7
- Favorites persistence/reconstruction — Team 2
- RUN command discovery/history — future RunService
- generic AppControl navigation/detail/result/focus behavior — host-owned

## Current isolated files

### AppCoreProvider.qml

Owns APPS catalog/source/presentation behavior only.

Important contract points:

- `hiddenEntries` is an input seam; APPS must not build a second RUN catalog.
- `appOverrides` is presentation-only and must not become semantic identity.
- Native/Flatpak classification preserves current donor behavior.

### AppLaunchPlanner.qml

Pure planning layer. It does not execute processes.

Produces intent for:

- normal DesktopEntry launch
- Toolbox argv launch
- Toolbox shell launch
- Bottles launch
- HIDDEN dispatch
- unavailable launch states

Normal execution must remain hookable so Team 5 can add surface/accessibility launch
preparation without moving tab discovery into APPS.

### AppActionCatalog.qml

Pure action-description layer.

Owns:

- DesktopEntry action harvesting
- browser-specific synthetic actions
- browser keyboard shortcut plans
- browser launch-argument plans

Its browser classifier is a behavior classifier only. It is not canonical identity.

## Future host integration rule

When T3 Overhead eventually releases Team 8 for host integration:

1. re-anchor to the exact certified patient named in that order
2. re-read APPS against that patient
3. preserve all already-landed shared services
4. adapt these isolated files to sibling contracts as they exist at that time
5. do not reintroduce Team 1/5/6/7 physiology into Team 8
6. submit a certification request to T0 Manager rather than giving runtime commands
   directly to the operator

## Identity rule

Until Team 7 freezes a shared contract:

- existing DesktopEntry IDs may be used as local catalog coordinates
- temporary provider keys are acceptable where required
- Team 8 must not publish a competing canonical application identity
- fuzzy browser/source classification remains behavior evidence, not semantic truth

## Launch rule

Launch selection belongs to Team 8.

Provider-specific surface preparation may wrap execution, but must not own APPS launch
policy.

Conceptually:

```
APPS Core
  -> choose launch intent
  -> emit/plan execution

surface provider hook
  -> optionally augment normal execution environment/argv

executor
  -> perform the launch
```

This prevents `launchApplicationWithTabProvider()`-style coupling from becoming the
permanent APPS architecture.

## Certification state

These files are currently standalone and unwired. They do not alter live AppControl
behavior, so there is no runtime certification request yet.

Do not call this work CERTIFIED unless T3 Overhead explicitly says so.
