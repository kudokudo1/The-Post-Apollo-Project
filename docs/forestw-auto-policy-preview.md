# ForestW // AUTO model-form policy preview

**Patient:** The-Post-Apollo-Project · **Role:** ForestW UI DOC, external Hospital-compatible · **Production:** HOLD

## IMPLEMENTATION
The MODELS menu adds an opt-in AUTO PREVIEW page in the existing model-list space. It demonstrates the archived Phase 14.11 policy with explicitly selected example evidence; it does not classify a real prompt or alter the active form, equipment, reasoning, persisted preferences, resource state or permission. Closing the menu or preview resets the examples. The result explains which equipped slot would be recommended and labels its current B0 inventory evidence; neither this result nor B0 is runtime authorization.

## RECOVERY PROVENANCE
Original read-only source: The-Post-Apollo-Forest-Project/raw-import/2026-09-22-transfer/The-Forest/bristlecone/model_form/automatic_routing_policy.py (blob 9500987188c85fc351b09d20bf59da6f0fce1003) and automatic_routing_evidence.py (blob 1dbf61159ddf126dfa6699a2097fa6b9ff04b302). Archived rules: high task complexity, known Small semantic failure, or insufficient Small capability each recommends Big; otherwise recommend Small. Reasoning is observed but does not mechanically select form. UNSET means absent example evidence; absence of escalation evidence is not proof of suitability. The UI implementation is an illustrative truth table only, not a recovered authoritative runtime implementation. Invalid example values refuse.

## HOW TO USE
Open flower MODELS → AUTO PREVIEW at bottom. Choose sample values; read recommendation, reasons and equipped-slot label. MODELS returns to inventory. The real AUTO selector remains unresolved while the protected runtime is unavailable.

## VERIFY
Run tests/forest/test_forest_auto_policy_preview.py. The Node regression covers all 48 example combinations plus malformed inputs; source checks guard against runtime actions. Native scroll/interaction acceptance is separate.

## NEXT / DECISIONS
Forest Core owns the authoritative automatic routing and evidence-producer contract: recover normalized semantic evidence with producer provenance; freeze reasoning and model-form decisions once per task/context; resolve an exact authenticated binding; use resource governance and independent permissions before execution; retain resolved choice across retries; explicit BIG never silently falls back. No prompt classification, AI cost claims, private session reads, direct B3 wiring, provider actions or new authority in this UI PR. The preview must not be imported by production runtime. AUTO remains unresolved in the actual ForestW selection policy.