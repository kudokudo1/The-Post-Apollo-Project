# Team 1 — Resource freeze optimism lesion

Classification:

```text
PRE-EXISTING LESION
```

The certified AppControl donor keeps APP/WINDOW/TAB optimistic freeze state in
`resourceFrozenScopes`.

Current donor behavior:

```text
bulk SIGSTOP dispatched
        ↓
resourceFrozenScopes[scopeKey] = true
        ↓
selectedResourceScopeIsFrozen()
        ↓
if any live row is not T:
    return optimistic map value
```

There is no expiry or reconciliation timer for that optimistic scope key.

Therefore a partial or failed bulk STOP can leave the UI reporting a frozen
scope even after fresh process telemetry shows one or more rows are not stopped.

The prepared `ProcessResourceState` intentionally preserves this behavior for
compatibility. It must not be described as verified kernel truth.

Terminology:

```text
frozenScopes
    = optimistic UI policy/state

live row.state contains T
    = observed process state
```

Do not silently change this behavior during extraction/transplant.

A future behavior-hardening operation may introduce bounded optimism or explicit
post-signal reconciliation, but that requires separate approval and runtime
testing because it changes visible APP/WINDOW/TAB resource behavior.
