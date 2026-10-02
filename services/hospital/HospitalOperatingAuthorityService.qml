import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: authority

    // One serialized host slot for operations that mutate the patient.
    property string slotName: "HOST"

    property string ownerTeam: ""
    property string ownerBranch: ""
    property string ownerHead: ""
    property string ownerLeaseId: ""
    property string acquiredAt: ""

    property var queue: []
    property var history: []

    property string lastError: ""
    property string lastEvent: ""

    readonly property bool available:
        ownerTeam.length === 0

    readonly property bool occupied:
        !available

    readonly property string state:
        available ? "OPEN" : "HELD"

    signal slotAcquired(string team, string leaseId)
    signal slotQueued(string team)
    signal slotReleased(string team)
    signal collisionDetected(string owner, string requester)

    FileView {
        id: authorityFile

        path: Quickshell.dataPath("hospital-operating-authority.json")
        atomicWrites: true

        adapter: JsonAdapter {
            id: authorityAdapter

            property int schemaVersion: 1
            property string slotName: "HOST"
            property string ownerTeam: ""
            property string ownerBranch: ""
            property string ownerHead: ""
            property string ownerLeaseId: ""
            property string acquiredAt: ""
            property var queue: []
            property var history: []
        }

        onAdapterUpdated: writeAdapter()

        onLoaded: authority.hydrate()
        onLoadFailed: authority.hydrate()

        onSaveFailed: function(error) {
            authority.lastError =
                "AUTHORITY SAVE // " + String(error);
        }
    }

    function nowIso() {
        return new Date().toISOString();
    }

    function hydrate() {
        slotName = String(authorityAdapter.slotName || "HOST");
        ownerTeam = String(authorityAdapter.ownerTeam || "");
        ownerBranch = String(authorityAdapter.ownerBranch || "");
        ownerHead = String(authorityAdapter.ownerHead || "");
        ownerLeaseId = String(authorityAdapter.ownerLeaseId || "");
        acquiredAt = String(authorityAdapter.acquiredAt || "");

        queue = Array.isArray(authorityAdapter.queue)
                ? authorityAdapter.queue.slice()
                : [];

        history = Array.isArray(authorityAdapter.history)
                  ? authorityAdapter.history.slice()
                  : [];

        lastError = "";
        lastEvent = "";
    }

    function persist() {
        authorityAdapter.slotName = slotName;
        authorityAdapter.ownerTeam = ownerTeam;
        authorityAdapter.ownerBranch = ownerBranch;
        authorityAdapter.ownerHead = ownerHead;
        authorityAdapter.ownerLeaseId = ownerLeaseId;
        authorityAdapter.acquiredAt = acquiredAt;
        authorityAdapter.queue = queue.slice();
        authorityAdapter.history = history.slice();
    }

    function appendEvent(type, team, details) {
        const event = {
            recordedAt: nowIso(),
            slot: slotName,
            type: String(type || ""),
            team: String(team || ""),
            owner: ownerTeam,
            leaseId: ownerLeaseId,
            details: details || {}
        };

        const next = history.slice();
        next.push(event);

        // Keep the local authority history bounded.
        history = next.slice(-500);
        lastEvent = String(type || "");
        persist();
    }

    function queueContains(team) {
        const wanted = String(team || "");

        return queue.some(function(entry) {
            return String(entry.team || "") === wanted;
        });
    }

    function acquireSlot(team, branch, head, reason) {
        const requester = String(team || "").trim();

        if (!requester) {
            lastError = "AUTHORITY REFUSED // TEAM MISSING";
            return false;
        }

        if (available) {
            ownerTeam = requester;
            ownerBranch = String(branch || "");
            ownerHead = String(head || "");
            ownerLeaseId = nowIso() + "::" + requester;
            acquiredAt = nowIso();
            lastError = "";

            appendEvent(
                "ACQUIRED",
                requester,
                {
                    branch: ownerBranch,
                    head: ownerHead,
                    reason: String(reason || "")
                }
            );

            slotAcquired(requester, ownerLeaseId);
            return true;
        }

        if (ownerTeam === requester) {
            ownerBranch = String(branch || ownerBranch);
            ownerHead = String(head || ownerHead);
            lastError = "";
            persist();
            return true;
        }

        if (!queueContains(requester)) {
            const nextQueue = queue.slice();
            nextQueue.push({
                team: requester,
                branch: String(branch || ""),
                head: String(head || ""),
                requestedAt: nowIso(),
                reason: String(reason || "")
            });
            queue = nextQueue;

            appendEvent(
                "QUEUED",
                requester,
                {
                    blockedBy: ownerTeam,
                    reason: String(reason || "")
                }
            );

            slotQueued(requester);
        }

        lastError =
            "AUTHORITY BUSY // "
            + ownerTeam
            + " OWNS "
            + slotName;

        collisionDetected(ownerTeam, requester);
        return false;
    }

    function isOwner(team, leaseId) {
        return ownerTeam === String(team || "")
            && ownerLeaseId === String(leaseId || "");
    }

    function releaseSlot(team, leaseId, reason) {
        const requester = String(team || "");

        if (!isOwner(requester, leaseId)) {
            lastError =
                "RELEASE REFUSED // NOT OWNER";
            return false;
        }

        const releasedTeam = ownerTeam;

        ownerTeam = "";
        ownerBranch = "";
        ownerHead = "";
        ownerLeaseId = "";
        acquiredAt = "";

        appendEvent(
            "RELEASED",
            releasedTeam,
            {
                reason: String(reason || "")
            }
        );

        slotReleased(releasedTeam);
        lastError = "";

        promoteNext();
        return true;
    }

    function promoteNext() {
        if (!available || queue.length === 0)
            return false;

        const nextQueue = queue.slice();
        const next = nextQueue.shift();
        queue = nextQueue;

        return acquireSlot(
            next.team,
            next.branch,
            next.head,
            "QUEUE PROMOTION"
        );
    }

    function cancelQueued(team) {
        const wanted = String(team || "");

        const next = queue.filter(function(entry) {
            return String(entry.team || "") !== wanted;
        });

        if (next.length === queue.length)
            return false;

        queue = next;

        appendEvent(
            "QUEUE_CANCELLED",
            wanted,
            {}
        );

        persist();
        return true;
    }
}
