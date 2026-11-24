# ForestW // Model Form selector rail

**Patient:** The-Post-Apollo-Project
**Room:** ForestW UI / independent model equipment
**Role:** External ForestW DOC; no live Hospital registration asserted

## IMPLEMENTATION
Reuse the existing shared vertical SelectorSlider in the flower MODELS popup. Three positions: BIG (top), AUTO (middle), SMALL (bottom). The rail uses preview-release interaction and the current Tree's existing Model Form preference. It is visible only when the popup is at least 320 by 320 pixels; the existing direct form buttons remain usable at every size. Reserve the rail's width beside the model list and resident profile. Closing the popup cancels uncommitted preview. No shared component edits, changes to Coffee Bar reasoning, automatic model selection, runtime loading or new provider calls.

## HOW TO USE
After review and merge, open the flower menu. Drag the FORM rail to BIG, AUTO or SMALL and release. Both equipped models stay assigned. If the window is too compact for the rail, use the original three buttons.

## VERIFY
The previously merged #2405 exact-head ForestW workflow failed on a stale single-slot assertion ('choices[selectedTreeIndex] = name'); this change updates the assertion to the real independent equipment contract. Existing grammar and TASKS checks passed on that previous head. Test the actual rail owner mapping, preview-release, compact fallback, no extra network actions and preserved reasoning/permission boundaries. Native visual, drag and resize acceptance remain separate.

## WATCH OUT FOR
AUTO is still an unresolved local preference; no protected runtime router is connected. Equipment state remains in memory. This UI rail does not load or unload model weights, persist preferences, or authorize inference.

## NEXT
Independent review and exact-head CI, native acceptance, then recover durable preference and automatic-routing contracts under the proper ownership boundaries.