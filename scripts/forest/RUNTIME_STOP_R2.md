# Forest Runtime R2 // Local STOP arbitration candidate

Development only, disposable public fixture. This additive DOC 2F component
does not change B3, B1, C5 or the UI. It is not an additional runtime,
database, task registry or permission issuer.

A host creates one RuntimeStopControl for an already-resolved B6 TaskContext
and original operation. The worker binds the real B3 attempt after RESERVED.
The B2 transport receives transport_event; only request_stop may set it,
and it must never be cleared or reused. Before reservation the exact
operation and no attempt are required; after binding the exact attempt is
required. Stale operation, task, generation or attempt references refuse.

At the future B3 integration seam, try_enter_commit and request_stop share
a short local lock. STOP before entry latches cancellation; entry before
STOP means cancellation cannot promise rollback. Entry is NOT permission,
a successful commit, a terminal receipt, resource release or disclosure.
The existing B4/C5 authorization, transaction and recovery logic remain
mandatory. Closing the control does not establish terminal state. No lock
is held across I/O or a journal transaction. No automatic retry.

Shared B3 integration remains pending exact owner agreement. No model
execution, storage read, positive protected admission or UI delivery.
Native resource termination and production acceptance remain HOLD.

Tests:
    python3 -m unittest discover -s tests/forest -p 'test_runtime_stop_control_r2.py' -v
