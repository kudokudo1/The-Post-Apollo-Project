# R6j // Retention of committed local queue actions

Only exact historical acknowledgment of a COMMITTED local journal row
can close a committed checkpoint generation. PREPARED acknowledgment
alone remains insufficient; PREPARED requires the existing separate
dismissal receipt. A committed seal is written under committed-v1.json
rather than dismissed-v2.json, so older generation readers refuse it.
Both seal names together, wrong receipt, absent intent or corrupt
snapshot refuse. Original action and review slots remain write-once.
The existing one-shot helper returns the same locked envelope. The host
accepts a fresh canonical RECOVERY_REVIEW_HISTORY response for the exact
durable committed review; live acknowledgment alone cannot authorize
rotation. No frame accompanies retirement; the wrapper's existing
supervisor-exit and fresh-load gates remain unchanged. Historical local
commit and acknowledgment do not establish a physical memory adjustment,
cancel a pending request, authorize another action or unlock startup.

New storage tests and two actual native wrapper scenarios exercise
COMMITTED and COMMITTED_MISSING with synthetic observation; preserve
the real local request and original journal/receipt. Fresh CI required.
Independent review, installed launcher/identity custody, bounded
generation policy and DOC2 visible controls remain. No production
activation.
