# R6i // Linux child custody, unmounted

The reviewed R6h wrapper now requires a pinned custody launcher path.
The exact QML Process launches a fixed Python supervisor in isolated
interpreter mode, not the backend directly. The supervisor forks its own
child, holds it behind a private pipe until pidfd acquisition succeeds,
arms parent-death SIGKILL on both processes and waits for the same
pidfd's normal zero exit plus matching waitpid. Abnormal exit, missing
Linux primitives or invalid path refuse success. No automatic restart.
The existing native wrapper trials now traverse this supervisor; the
external test-only independent pidfd witness and DB-lock barrier remain.
Additional tests cover normal and abnormal exits, malformed launch
inputs, environment stripping and supervisor death.

Trusted caller still selects the paths. Basic ownership/mode checks are
not race-free file identity attestation; same-UID replacement, exec
provenance, ancestor mount integrity, installed protected bundle/provider,
raw byte bounds, and helper custody remain unresolved. Parent-death
coverage is for the direct child, not arbitrary descendant trees.
The fixture-only environment flag is not a production permission.
No actual installed owner entrypoint or UI mount is selected here.
No protected operation, startup unlock, or deployment. Fresh CI required.
