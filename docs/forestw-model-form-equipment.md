# ForestW // Two-slot model equipment and Model Form

**Patient:** The-Post-Apollo-Project  
**Room:** ForestW UI / flower model selector  
**Role:** external ForestW DOC successor; live Hospital registration not asserted  
**State:** local presentation only; independent review and native acceptance pending

## IMPLEMENTATION

Each of the five displayed Trees now owns an independent local equipment record: SMALL model name, BIG model name and AUTO/SMALL/BIG form preference. The initial state is two empty slots and AUTO, matching the historical Model Form policy vocabulary. Selecting a model in the SMALL or BIG slot requires that exact name in the existing successful B0 inventory. Assigning or clearing one slot preserves the other, the current form preference and all other Trees. Switching form does not unequip, load, unload, scan or execute a model. Slot labels retain the user's intended assignment through inventory failure or disappearance, marking it unverified or not found rather than automatically substituting another model.

The MODELS popup replaces USE with explicit SMALL and BIG equipment buttons, retains SCAN and the disk comparison, and adds a three-position clickable form selector with slot labels and individual clear buttons. Compact heights hide the slot-summary rows before the model list; the existing selected-model P0 profile now appears only when sufficient vertical space remains. Manual form selection resolves only a discovered equipped model. AUTO is explicitly unresolved until a separately reviewed runtime router exists. The same existing P0 status drives the top-right badge, row status and profile; P2C receives the same explicitly selected model name or an empty host-only selection. The diagnostic menu and Coffee Bar are not redesigned.

## HOW TO USE

After review and merge, open Forest → flower → choose SMALL on the desired small model's row, BIG on the desired big model's row. Yellow buttons indicate slot assignment. Click SMALL or BIG in the top form row to change the selected model without losing either assignment. Click the small X next to a slot to clear it. AUTO retains both assignments but has no resolved model until the router is implemented. Close/reopen the popup or switch Trees to see the independent local selections.

## VERIFY

Run `python3 tests/forest/test_forest_model_form_equipment.py` and the existing ForestW source-contract suite. The new tests exercise independent copies, replacement and clearing, repeated manual switches, unavailable inventory, missing names, wrong Tree/slot/form, unresolved AUTO and unchanged Coffee Bar/adapter/SEND locks.

## WATCH OUT FOR

This is an in-memory QML presentation preference, not a persistent or authenticated model binding, and not a runtime inference selector. It resets when the component reloads. No slot is auto-assigned using disk size, parameter count or supposed intelligence; no simultaneous model residency is assumed. Explicit Small/Big with an absent slot never falls back. AUTO does not execute or simulate the future router. Historical Phase 14.11 distinguishes Model Form, reasoning and execution-context ownership; eventual protected task/Clone bindings belong to Forest Core and require continuity and review. Native popup geometry and pointer behavior are not proven by source CI.

## NEXT / DECISIONS

Native visual acceptance of the two-slot panel, then refine the compact form selector/slider interaction; recover automatic routing and connect authenticated runtime Model Form and reasoning semantics separately. Existing disk comparison is preserved from #2404. No production permission, benchmark, model execution, service change or shared component mutation.