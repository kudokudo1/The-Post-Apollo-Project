# Team 1 — Process action parity audit

This audit compares the prepared Team 1 process-action organs against the
currently certified donor behavior. It is a compatibility record, not host
integration authority.

## Preserved behavior

The prepared stack preserves:

```text
protected/unprotected confirmation kinds
  protected-restart / task-restart
  protected-term    / task-term
  protected-freeze  / task-freeze

1400 ms optimistic freeze-state reset

one-shot/sticky danger-action unlock policy

cancel consumes the one-shot action unlock when the captured live process
still resolves

confirmed freeze
  -> captured-target revalidation
  -> SIGSTOP
  -> optimistic frozen state
  -> relock freeze action
  -> refresh request

resume
  -> remains available even when the protected-process one-shot unlock was consumed
  -> SIGCONT
  -> optimistic thaw state only after SIGCONT dispatch succeeds
  -> relock freeze action
  -> refresh request

confirmed terminate
  -> captured-target revalidation
  -> SIGTERM
  -> relock kill action
  -> refresh request

confirmed restart
  -> captured-target revalidation
  -> ProcessControl.restart
  -> relock kill action
  -> refresh request
```

## Intentional hardening

The donor resolves confirmed Task actions by captured PID + process name.

The prepared stack routes this through `ProcessIdentity` and also carries the
process-persistent identity. With normal process rows this resolves to the same
comm/name identity; if comm/name is absent, argv-basename identity gives a
stronger stale-target guard.

This is safety hardening, not semantic application identity.

## Favorite-wrapper normalization

All safety, limits, state reads, and captured identity now operate on:

```text
ProcessIdentity.sourceEntry(entry)
```

so Favorites-backed wrapper rows cannot silently lose PID/comm/vsz/state data.

## PRE-EXISTING LESION — preserved intentionally

The certified donor's `metricIsCritical(entry, "rss")` checks
`entry.mem >= 80`, not RSS bytes.

The extracted `ProcessPresentation.qml` currently preserves this exact
behavior.

Classification:

```text
PRE-EXISTING LESION
not repaired during compatibility extraction
```

If the product later wants RSS-specific criticality, that should be a separate
behavior change with its own test and approval.

## Integration status

No host tissue is changed by this audit.

```text
AppControlW.qml           untouched
service lifetime          untouched
CPU++ wiring              untouched
serialized slot required  NO
```
