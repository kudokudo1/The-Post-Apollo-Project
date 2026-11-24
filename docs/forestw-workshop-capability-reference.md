# ForestW // Workshop capability reference

**Patient:** The-Post-Apollo-Project · **Room:** ForestW UI · **Role:** external ForestW DOC · **Production:** HOLD

## IMPLEMENTATION
Add WORK to the top deck, with a separate Workshop popup. It shares the Diagnostics footprint, so those two panels are mutually exclusive; the flower/model panel stays independent. Only Bristlecone Pine has a complete recovered historical profile; other Trees display an unavailable profile message. LOAD REFERENCE runs the bounded UI helper against the actual merged B6-R2 Python registry and planner, using a fixed disposable TaskContext. The helper returns definitions, four Workshops, General/Ready membership and the selection plan. No hardcoded copy of the eighteen capabilities in QML. Each Workshop selection resets optional selections; General/Ready choices are individually toggled. Core entries cannot be deselected. All selection results remain UNKNOWN_HOLD and metadata only. The receipt validates exact requested arguments, catalog/plan consistency and false authority flags after successful stdout/stderr/exit. Closing the menu or changing profile support clears it and discards pending output. No sticky carry yet.

## HOW TO USE
Forest → Bristlecone Pine → WORK → LOAD REFERENCE. Select Research, Design, Code-Debug or Model, then individual optional capabilities. Scroll to inspect selected/dormant counts and the registry's historical targets. Close with the shared close button or Escape. No tool is loaded.

## VERIFY
Run python3 -B tests/forest/test_forest_workshop_reference.py. Exercises actual Core reference selections, malformed/mismatched requests and receipts, false authority flags and UI scope. Native menu geometry, scrolling and interaction require operator verification.

## WATCH OUT FOR
Historical adapter names are not installed provider capability evidence. Selection is not activation, task binding, permission or tool dispatch. No actual Clone, task, session, prompt, account, model, storage, protected access or sticky retention is created. Fixed synthetic context cannot become a live identity. This UI stage deliberately uses explicit load and resets on Workshop change; does not persist settings.

## NEXT / DECISIONS
Independent review and operator acceptance. Later consume Core's reviewed live capability and task-context projection. Reuse same reference for other Trees only when corresponding profile is recovered, not by copying Bristlecone membership. Actual AUTO policy integration remains next parallel UI milestone. Production HOLD.