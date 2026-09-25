# Team 7 — Surface launch ownership seam

Status: architecture escalation note only.

Current certified patient when observed:
`6c74628baeaf7cf2f37808f9e57293aaad7e1788`

Team 8 has documented an unresolved ownership seam around launch-time
instrumentation whose purpose is making Team 5 surfaces discoverable.

Examples currently preserved in donor behavior include:

- Kitty remote-control socket preparation
- accessibility-enabling environment/flags
- Chromium/Electron remote-debugging ports

## Team 7 boundary

Team 7 should **not** own these mutations.

Semantic identity may eventually supply evidence such as:

- application family / aliases
- DesktopEntry relationship
- running instance relationship
- ambiguity state

That evidence can help an authorized launch/provider adapter decide whether an
augmentation applies. It does not make Team 7 the owner of argv/environment
mutation or provider bootstrap policy.

## Why this is an event

The seam crosses Team 5 and Team 8 ownership and neither published contract
currently owns the middle augmentation step.

That makes it an ownership ambiguity under the hospital's event-driven reporting
rules.

No Team 7 code should silently solve the ambiguity by adding launch mutation to
the identity service.

## Safe architecture invariant

Whatever owner management selects, preserve this separation:

```text
APPS launch intent                 Team 8
        |
        v
surface-discovery augmentation     explicit owner required
        |
        v
execution
        |
        v
surface observation               Team 5
        |
        v
semantic joins                    Team 7
```

Team 7 remains downstream of observations and upstream of semantic consumers.
