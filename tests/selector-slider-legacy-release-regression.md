✦︎✦︎✦︎ Meta Apollo Logos //

# REMOTE LEGACY RELEASE // FLICK REGRESSION

> STATE // candidate hotfix, **not** operator-runtime certified  
> SOURCE // 2026-10-15 user observed with LIVE REMOTE // OFF  
> SCOPE // Git REMOTE only; Git REPO and Hospital FLOOR remain untouched

## Report and hypothesis

When the operator drags the actual Git REMOTE slider in its legacy OFF mode,
releasing makes the handle visibly flick to the very top of the track before
returning to the dropped position.

Static code inspection found that the legacy thumb position resolves to y=0
when the owning selection index is temporarily invalid (or the item count
temporarily falls below two), and its y-animation re-enables on pointer release.
A transient invalid index around that boundary is a **plausible mechanism**,
not yet proved to be the cause in the operator runtime.

## Candidate fix

- Preserve the last known-good normalized index position through a short
  350ms window spanning a **legacy** pointer press and release.
- Use that fallback *only when the owning index/count becomes invalid*.
- Prefer the owner’s current valid index immediately once available.
- Never invent a commit, suppress a real valid index, or change wheel/drag
  selection service calls.
- Apply only to Git's REMOTE instance using
  `stabilizeLegacyRelease: true`; all other sliders use the unchanged default
  `false`. ON (preview-release) mode has its own unchanged positioning path.

## Retest on operator machine

1. Sync/reload Quickshell from a reviewed build containing this patch.
2. Git > CONTROL; ensure `LIVE REMOTE // OFF`.
3. Move real REMOTE handle to multiple middle/bottom positions; release.
4. Observe whether the handle stays or settles at the selected position
   **without visiting the top of the track**.
5. Repeat with rapid dragging, remote menu refresh, wheel movement and mouse
   release at the endpoints. Confirm the actual selected remote and activity
   lights stay correct.
6. Switch `LIVE REMOTE // ON`; verify preview/release semantics unaffected.
7. Check real REPO and Hospital FLOOR stay visually and behaviorally identical.

If the flick persists, capture the index label during flick (e.g. `1` or
`—`), and whether the selected remote name changes. This will distinguish
a transient owner reset from a Qt animation-target problem. Do not certify
until tested. Disable pilot or revert hotfix if a new regression appears.
