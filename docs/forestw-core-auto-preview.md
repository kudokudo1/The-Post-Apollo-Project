# ForestW // Core I1 routing example integration

**Patient:** The-Post-Apollo-Project · **Room:** ForestW UI · **Role:** external ForestW DOC · **Production:** HOLD

## IMPLEMENTATION
Replace the independent JavaScript AUTO truth table with the actual merged Core I1 recommend() and presentation_reference() functions. The existing AUTO PREVIEW page retains the three example evidence controls and adds explicitly hypothetical requested form and resolved reasoning controls. EVALUATE invokes a bounded UI helper with only five fixed-choice arguments. The helper constructs a disposable fixed TaskContext/TurnScope, omits unset evidence and calls I1; it never accepts a real identity, task, prompt, model or runtime. The UI validates the echoed inputs and fixed I1 reference, including null resolved form/binding, empty safeActions and false authority/authentication flags. Complete successful stdout/stderr/exit is required. No duplicate recommendation rules remain in UI JavaScript. Edits clear previous results; closing resets examples and discards pending results. The existing equipped-slot label remains a separate local display hint, not a binding.

## HOW TO USE
Forest → flower → AUTO PREVIEW. Choose example AUTO/SMALL/BIG, LIGHT/NORMAL/DEEP reasoning and evidence, then EVALUATE. Compare explicit form precedence and independent reasoning. The selected Tree equipment, Coffee Bar, actual AUTO state and saved preferences are unchanged.

## VERIFY
python3 -B tests/forest/test_forest_auto_policy_preview.py exercises all 432 combinations using actual I1, invalid CLI inputs, actual helper receipt validation and source guards. Native UI and independent review separate.

## WATCH OUT FOR
The previous instantaneous illustrative decision now requires EVALUATE, which runs a local Python calculation only. No prompt classifier, live producer, resolved binding, real task correlation, model call, resource reservation, consent or private data. I1 is merged but independent review was not recorded at reconciliation. A missing or failed helper shows no recommendation, never falls back to a duplicate policy.

## NEXT / DECISIONS
Independent scoped review and operator testing. I2 model binding reference projection is the next planned UI integration, not actual runtime binding or a reason to use local inventory as authenticated identity. Production HOLD.