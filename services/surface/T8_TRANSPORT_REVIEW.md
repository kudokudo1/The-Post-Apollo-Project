# T5 → T8 SurfaceLaunch Transport Review

Observed T8 branch:
`team8/apps-core-prep`

Observed T8 HEAD during this review:
`7010492f29213e94ee6ffd68b2f9d230bd3ef5f2`

This is a cross-team implementation note only. Team 5 does not modify Team 8's
launch planner or own wrapper transport.

## Confirmed good

T8 currently:

- normalizes the published SurfaceLaunch payload generically
- blocks plans when `ready == false`
- preserves correlation/bootstrap/lease/conflict metadata
- applies direct/native argv augmentation structurally
- keeps Shell/Bottles transport ownership in T8
- does not infer Kitty/Accessibility/DevTools capability policy itself

Those behaviors match the ownership ruling.

## One current wrapper-placement gap

The current T8 Flatpak path effectively does:

```text
SOURCE_TOKENS
+ argvAfterExecutable
+ argvAppend
```

That is correct only when the Flatpak DesktopEntry has no pre-existing
application arguments after the APP_ID.

The SurfaceLaunch semantic rule is:

```text
flatpak run APP_ID
    <argvAfterExecutable>
    EXISTING_APPLICATION_ARGUMENTS
    <argvAppend>
```

For example, a wrapped Kitty launch conceptually shaped as:

```text
flatpak run net.kovidgoyal.kitty ssh host
```

must become:

```text
flatpak run net.kovidgoyal.kitty
    -o allow_remote_control=socket-only
    --listen-on <socket>
    ssh host
```

and not:

```text
flatpak run net.kovidgoyal.kitty
    ssh host
    -o allow_remote_control=socket-only
    --listen-on <socket>
```

because `ssh host` may already cross Kitty's option/payload boundary.

This is a T8 transport implementation issue, not a T5 policy issue.

## Recommended T8 regression case

Add a Flatpak fixture with real pre-existing application arguments after APP_ID,
then verify `argvAfterExecutable` lands before those arguments.

The launch-domain adapter must identify its application boundary rather than
assuming either:

```text
token 0
```

or:

```text
end of wrapper argv
```

is always correct.

## Readiness note

T5 now returns rejected augmentations fail-closed:

```text
ready: false
env: {}
argvAfterExecutable: []
argvAppend: []
bootstrap endpoint coordinates: empty
leases: []
```

T8 should continue treating `ready` as authoritative even though the rejected
payload is no longer executable by accident.
