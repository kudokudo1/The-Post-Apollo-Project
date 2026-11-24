# ForestW // Independent Models and Diagnostics

**Patient:** The-Post-Apollo-Project  
**Room:** ForestW UI, operator-directed menu split  
**Role:** External ForestW DOC successor; independent review and native acceptance pending.

## IMPLEMENTATION

The flower popup is now MODELS only, preserving discovery, the selected model profile, USE/SCAN/SCAN ALL and the existing shared P0 resident-status source. The existing P2C hardware panel is moved intact into a separate in-widget diagnostic pane with the canonical `DiagnosticsDockButton` medical staff and stars, immediately to the left of the resize arrows in the header.

The shared `DiagnosticsServicePopup` currently has a fixed service-row schema, not an interactive body slot. This milestone uses its visual grammar and shared button/close control without changing the shared Weather/Finance component or duplicating the P2C adapter. The Forest-specific popup hosts the existing interactive CHECK and read-only hardware view. Its left-side width is bounded by the model popup's left edge; both menus can remain open. Each button and close control owns only its menu; Escape closes MODELS, then diagnostics, then Forest. Closing Forest clears both flags. Opening diagnostics performs no scan. The existing manual P2C CHECK, snapshot expiry, source validation, and P0 model LIVE status are unchanged.

## NEXT // Operator-directed architecture

- MODELS: per-model installed artifact disk size and comparison (not free disk, RAM, or intelligence); exact model identity; separate user-equipped SMALL and BIG bindings; AUTO/SMALL/BIG model-form control; actual benchmark comparison when evidence exists.
- COFFEE: preserve the existing per-Tree reasoning controls; recover independent canonical reasoning policy and provider translation. NONE is not automatically AUTO.
- DIAGNOSTICS: host CPU/RAM/GPU/VRAM, actual device mapping, resource fit and governance, measured performance; machine-wide disk capacity belongs here, while per-model artifact size belongs in MODELS.
- Model-form and reasoning decisions historically belong to a particular execution context (main Tree or Clone); the current per-Tree visual preference is only a staging surface, not a global runtime decision. Do not silently change another Clone or shared model binding.
- Historical Phase 14.11 archive: [architecture checkpoint](https://github.com/kudokudo1/The-Post-Apollo-Forest-Project/blob/main/raw-import/2026-09-22-transfer/The_Forest_Model_Form_Clone_and_Resource_Management_Architecture_Checkpoint_2026-08-11_v3.md). Small and Big are capability tiers, not synonyms for reasoning depth. Auto is policy, not a model. Explicit Big must not silently downgrade; Auto may use Small when justified. Cross-form handoff must preserve task continuity; never claim that two assigned slots mean two models are resident.
- Compare model facts (size, parameter count/quantization if actually provided, supported capabilities, measured latency/quality) independently. No invented intelligence/reasoning bar based on disk size or parameter count. Native benchmark, provider/model availability, resource policy and protected execution remain separate approval gates.

## HOW TO USE

After merge and deployment, open Forest. Open the flower to see models; click the medical staff button beside the arrows to open Diagnostics. Both panes may remain visible; press CHECK in Diagnostics for current P2C information. Close either via its own X/button.

## VERIFY

Run the ForestW source contract suite. Native Fedora acceptance: both panels open at once, neither overlaps the other, close each independently, resize through chassis stages, verify prompt and header controls remain reachable, CHECK updates only diagnostics, SCAN ALL refreshes the original P0 source. Review native compact geometry and pointer ownership; source tests alone do not prove rendered behavior.

## DECISIONS

This is the menu separation milestone only. No model slot assignments, new model routing, intelligence claims, new process, benchmarking, inference, shared component changes or protected SEND/voice access. Future execution remains Forest Core/Connections owned.