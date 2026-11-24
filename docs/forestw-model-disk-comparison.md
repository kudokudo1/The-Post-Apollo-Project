# ForestW // Model disk-size comparison

**Patient:** The-Post-Apollo-Project · **Room:** ForestW model selector · **Role:** external ForestW UI DOC · **State:** source staging; independent review and native acceptance pending.

## IMPLEMENTATION

The flower MODELS menu now shows each model's provider-reported installed artifact size and a relative bar, scaled against the largest artifact in the same successful B0 inventory. No additional process, query, network endpoint or model execution is introduced. The new pure UI comparison refuses malformed, duplicate or unsafe-integer size records; unknown inventory clears the comparison. Zero-size entries remain zero, and all-zero inventory has no meaningful relative denominator.

The existing 82px model row reserves its previous unused gap for the size text and 5px bar. USE/SCAN, FOUND, P0 LIVE and ACCESS indicators are unchanged. The independent diagnostics menu remains separate. No model-form assignment or reasoning preference is modified.

## HOW TO USE

After review and merge, open Forest → flower → SCAN ALL. Read DISK REP and REL MAX below each model name. The largest reported artifact has a full bar, and each other bar represents its byte-size ratio to that model. Inventory refresh recalculates the scale.

## VERIFY

Run `python3 tests/forest/test_forest_model_disk_comparison.py`. Focused source and Node tests cover exact matching, safe integer bounds, duplicate and missing values, all-zero comparisons, changed inventory, complete B0 process barrier, and unchanged model/diagnostic control ownership. Native compact layout acceptance remains separate.

## WATCH OUT FOR

These are Ollama-reported artifact bytes, not unique filesystem allocation, remaining free disk, model quality, intelligence, parameter count, context capacity or RAM/VRAM requirements. Shared model blobs can make reported artifact sizes unsuitable for totaling real storage consumption. Bars are not calibrated model-form or performance scores. No auto assignment to SMALL/BIG.

## NEXT / DECISIONS

Recover two explicit SMALL/BIG equipped model bindings and the independent AUTO/SMALL/BIG Model Form selector, retaining the Coffee Bar for reasoning effort. No runtime routing, benchmark, local machine mutation, protected SEND or voice activation in this milestone.