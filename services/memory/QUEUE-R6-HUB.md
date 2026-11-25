# R6c // native Notification Hub binding

Explicitly unmounted MemoryQueueHubBinding.qml owns canonical host-state
publication for notification-enabled sessions. Complete bounded lines from
the trusted wrapper are fed exactly once; the Hub callback is collected,
then the returned host state is published before the actual singleton offer.
Busy guard rejects reentrant feed/state publication. Only one synchronous
offer, no new poller, queue, persistence, retry or privileged action. Actual
NotificationsService owns BLOCK/DND/history; outcome is observational, not
a disk/popup/read receipt. Terminal notices must match exact accepted
CANCEL/EXPIRE action result and its fresh IDLE publication. No uncorrelated
terminal alert. Existing host and notification service source unchanged.

Native disposable fixture uses real Python Session/Owner/Delivery, canonical
JS host, actual QML binding and actual existing NotificationsService, isolated
D-Bus and XDG directories. Tests NORMAL, BLOCK, DND, stale/duplicate frames,
uncorrelated terminal refusal, exact two attempt reservations and original
local action journal. Synthetic observation and fixture-only startup
injection, no installed activation or kernel memory action. New workflow
pending. The launcher must independently bound upstream bytes and own
generation/deadline/process custody; this binding is not a launcher.
