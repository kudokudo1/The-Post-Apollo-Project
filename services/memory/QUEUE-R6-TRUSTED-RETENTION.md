# R6e // trusted history gate and generation IO (development only)

Stacked on main reconciliation #2790. Controller consumes only a current
canonical LOCAL_DISPOSITION_HISTORY response, not a caller-supplied receipt
or the original live dismissal reply. Explicit selection binds owner epoch
via state, sequence, action UUID, review digest and storage generation.
Any subsequent packet invalidates proof. Matching LOAD snapshot and restored
unresolved message required; unknown ACK/dismissal, stale generation,
pending publication or corrupt snapshot refuses. Publish stopped/retired
state, stop and await exact trusted child exit before calling GEN_ADVANCE.
No queue frame is returned. The retired instance cannot restart; wrapper
must verify successful helper exit, exact generation/action response and
fresh LOAD before creating another locked controller with monotonic process
generation. GEN_LOAD/GEN_SAVE/GEN_ADVANCE are explicit bounded helper
commands. Updated legacy helper refuses retained directories and uses the
same advisory root lock. Pre-upgrade helpers must be excluded by launcher.
Storage helper cannot authenticate receipt provenance itself.

Node regression uses canonical host packet processing and real Python
helper, but synthetic backend replies. Actual native transport, exact
launcher custody/exit, QML adapter binding, committed-operation retention,
startup authorization, installed capacity and operator acceptance remain
pending. No automatic retry, replay, retention expiry or protected action.
