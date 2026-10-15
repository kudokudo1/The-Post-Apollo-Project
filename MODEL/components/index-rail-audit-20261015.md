✦︎✦︎✦︎ Meta Apollo Logos //

# INDEX RAIL // TEAM 3 READ-ONLY AUDIT

> DATE // 2026-10-15
> OBSERVED SOURCE // `components/IndexRail.qml`, blob `27ddb578c6fa77385271a715b564f360bdbdb53a`
> AUTHORITY // READ ONLY. No IndexRail migration or redesign is authorized by this audit.

## Relationship to SelectorSlider

`IndexRail` is a distinct **compact index navigation** component, not a
numeric VALUE slider and not automatically an alias of `SelectorSlider`.

| Property | IndexRail | SelectorSlider existing INDEX |
| --- | --- | --- |
| Nominal width | 24 px | 40 px |
| Track | 10 px solid accent, contrast ticks | 12 px dark slot, luminous center, separate side ticks |
| Thumb | 6 px wide magenta, 30–58 px adaptive height | 28 × 52 px tactile handle |
| Selection | Immediate `indexRequested(index)` while dragging | Immediate by default; optional isolated preview-release |
| Wheel | Discrete single-index step | Discrete single-index step |
| Keyboard focus/keys | No dedicated keyboard handling in IndexRail | Opt-in INDEX and VALUE support dedicated focus/step |
| Activity indicators | None | Distinct activityPoints supplied by owner |
| Input context | Item index/count/currentIndex | Item index/count/currentIndex; new isolated F2 numeric profile |

Both use a normalized vertical handle travel, an owner-supplied current index,
and pointer offsets to avoid a handle jump at pickup. Both do not perform
external operations themselves; owners respond to `indexRequested`.

## Findings, not change orders

1. Compact rail is materially different from the full tactile selector;
   retaining both is legitimate until real usage demonstrates convergence.
2. Its immediate selection behavior supports the operator's workflow of
   watching branch maps, floor/repo details, and names change *while moving*.
   Replacing that with release-only selection would be a regression.
3. IndexRail's narrow handle, tick density, keyboard support and glow layers
   differ intentionally or historically; those are possible future
   accessibility/grammar audit topics, not proven defects.
4. F2 VALUE belongs in a separate opt-in selector profile. It does not justify
   moving numeric behavior into IndexRail or replacing its 24 px geometry.
5. No IndexRail runtime observation was performed in this read-only pass.

## Decision gate

**STATUS // NO MIGRATION PROPOSED.** Leave `IndexRail.qml` as-is. If a
concrete consumer later needs the numeric/value semantics, audit that
consumer and its layout before choosing to reuse or extract behavior.

This audit accompanies F2 exploration; it is not a prerequisite to deploying
F2 into existing menus or a rationale for editing any production IndexRail.
