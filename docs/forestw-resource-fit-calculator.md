# ForestW // Resource fit calculator

**Patient:** The-Post-Apollo-Project · **Room:** ForestW Diagnostics · **Role:** external ForestW UI DOC · **Production:** HOLD

## IMPLEMENTATION
A collapsible RESOURCE FIT // P1 EXAMPLE section accepts nine explicitly hypothetical inputs: required, budget and available quantities for host RAM (MiB), accelerator memory (MiB) and CPU threads. Blank represents unknown for requirements/availability and no explicit ceiling for budget; zero remains zero. Deferral is selectable. EVALUATE runs a bounded UI helper using the actual existing Core P1 evaluate_resource_request function. The request has fixed synthetic identifiers, small/normal form/reasoning, standard priority, and no real task or model binding. It does not duplicate the governor logic.

The helper echoes exact input tokens with decision, reasons and false execution/authority flags. The UI requires matching input and successful complete stdout/stderr/exit before showing a result. Edits clear previous results. MODELED FIT is a synthetic calculation, not permission. The new section does not consume or change live P2C, P0, model selection or Coffee Bar state.

## HOW TO USE
Open Forest → top-deck Diagnostics → scroll to RESOURCE FIT // P1 EXAMPLE → expand. Enter hypothetical quantities and press EVALUATE. Example: host 2048 / 4096 / 4096 MiB; accelerator 512 / 1024 / 1024 MiB; CPU 2 / 4 / 4 threads. This yields MODELED FIT. Change host budget to 1024 for DENY or host available to 1024 (with original budget) for DEFER. Blank requirements produce unknown requirements rather than guessing.

## VERIFY
python3 -B tests/forest/test_forest_resource_fit_example.py runs the actual Python helper and P1 evaluator, verifies policy precedence, unknown/zero semantics, malformed inputs, receipt matching and nonauthority. Native QML input/scroll and process behavior remain separate.

## WATCH OUT FOR
No model-specific measured requirements, trusted resource availability, protected resource lease or admission exists here. No model load, inference, scheduler, file write, background polling, real task identifiers or actual budget changes. P2C resident memory and DRM headroom are not fed to P1. The calculator is independent of the current Tree and model. Values reset on component reload.

## NEXT / DECISIONS
Core acknowledged the calibration contract request in issue #2161 comment 7129903444. Preserve owner boundaries; future real resource-fit presentation consumes Core's reviewed calibrated requirement/availability/budget projection, not synthetic inputs. Real benchmark trials require separate operator approval, capacity/concurrency safety and review. Production HOLD.