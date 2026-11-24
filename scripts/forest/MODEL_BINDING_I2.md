# Forest I2 // Exact Model Form binding reference

PATIENT: The-Post-Apollo-Project · ROOM: intelligence management
ROLE: Forest Core DOC, external Hospital-compatible · PRODUCTION HOLD.

## IMPLEMENTATION
Operator approved continuation after I1. R2 #2423 merged 4b945976
with independent scoped PASS; I1 #2426 merged 063a747a, 75/75 and
4/4, independent review still due at preparation.

Original Forest archive model_form/registry.py blob
bda9f7063ef85fe61e59e228a25c0751a5d61f6b and resolution.py
82ed54f75d490560dab993f55584fc029f22e3c5: immutable form-to-binding,
freeze once, missing slot refuses rather than substitute.
I2 consumes already frozen I1 recommendation. Does not yet recover
full historical exact-turn/task override/pinned baseline control.
Adds exact synthetic artifact digest, runtime instance/version/release
digest and configuration digest/context/output bounds. No arbitrary
runtime options, endpoint, path, credential or adapter execution.
Digest strings are references, not computed or independently verified.
Registry scope is owner/Tree plus revision; per-turn evidence binds
the exact selected binding and R1 context/Clone/turn. Missing or
changed evidence, missing slot, unknown installed/capability data,
unsupported required model feature or insufficient context => no
matching reference. No downgrade or alternate-model selection.
Model features are illustrative normalized inference features, not
R2 Workshop capabilities or C5 permissions. Actual normalized producer
and feature registry remain unimplemented. Preserve exact input reference
on retry comparison only, no rebind or permission to retry.
Public status reports only reference match, static reason, requested and
recommended form. Actual resolved form/binding stay null.

## HOW TO USE / VERIFY
python3 -B -m unittest discover -s tests/forest -p 'test_model_binding_i2.py' -v

20 focused cases + I1/R1/R2/P1 regressions. No live model data used.

## WATCH OUT FOR / CALIBRATION
B0 model inventory and P2C reported bytes/context/residency do not provide
independent digest/currentness or peak incremental resource requirements.
No automatic import of same-login UI equipment preferences. Future
measured trial must bind exact model/runtime/config plus hardware/device,
context, workload, reasoning and isolation, and distinguish baseline,
peak, incremental demand and actual availability. P1 fit remains pure,
not allocation. Unknown is not zero. Do not use disk size, resident
bytes or DRM headroom as calibrated requirements. No trial authorized.

## NEXT / DECISIONS
Independent review I1/I2. Recover exact evidence producers and calibration
contract in bounded next work. Current C5 native private operation remains
deny-only. No model load, tool execution, DB, private data, OS mutation,
new service or production authorization.
