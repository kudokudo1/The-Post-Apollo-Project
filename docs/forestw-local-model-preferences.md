# ForestW // Persistent local model preferences

**Patient:** The-Post-Apollo-Project · **Room:** ForestW UI · **Role:** external ForestW DOC · **Production:** HOLD

## IMPLEMENTATION

A new local-only versioned JSON preference document stores exact SMALL/BIG model names, AUTO/SMALL/BIG form and the existing NONE/LOW/MED/HIGH reasoning step for each of the five stable Tree keys. The document lives at `$XDG_DATA_HOME/post-apollo/forest/ui-preferences/model-preferences-v1.json` (default `~/.local/share/post-apollo/forest/ui-preferences/model-preferences-v1.json`). It is separate from protected Forest Core journals, bindings and credentials.

Startup reads the document only. Missing file yields defaults without creating anything. The MODELS header offers SAVE when changed, SAVED after a verified receipt, DEFAULT for unsaved defaults, LOAD when a read/write fails, and ... while busy. Saving records all five Trees with a revision comparison, private directory/file modes, a cooperating-writer lock and fsync/atomic replacement. The UI validates all fields and the successful complete process result against the submitted values. A malformed, inaccessible or stale document refuses saving; no automatic reset or overwrite. Explicit LOAD replaces current unsaved preferences with a successfully read document. Edits remain blocked during the in-flight operation. No background saving or model queries are introduced by restore.

## HOW TO USE

Open Forest → flower. Equip SMALL and BIG, select model form and Coffee Bar level for each Tree. Click SAVE in the MODELS header. SAVED indicates a validated successful save. Restart Quickshell through the operator's normal approved process; reopen Forest and verify the choices. Missing models remain assigned but unverified/not found until existing B0 inventory evidence confirms them.

## VERIFY

`python3 tests/forest/test_forest_ui_model_preferences.py` exercises the actual helper in disposable XDG storage, no-write startup, save/restore, stale revision and corrupt/unsafe records, exact Tree-key projection including reordered keys, and UI source boundaries. CI is not a native Quickshell restart test.

## WATCH OUT FOR

The file is a same-login local preference, not a protected identity or authority record. No model load, session disclosure, inference, credential access or permission change follows from the document. AUTO stays unresolved. A save error can occur after the atomic replacement but before receipt; explicit LOAD reconciles rather than blindly retrying. The private leaf directory and files are checked, but same-user processes and ancestor directories are not an authenticated security boundary. SAVE is explicit; unsaved edits do not survive restart.

## NEXT / DECISIONS

Review exact source and CI, then operator-controlled merge and native save/restart acceptance. Historical automatic Model Form routing and runtime reasoning integration remain separate Forest Core/Connections milestones.