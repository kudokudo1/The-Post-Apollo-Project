import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: root

    property var roundsService: null
    property var registryService: null
    property var assignmentService: null
    property string currentRoomId: ""

    property var durableRooms: []
    property var durableSessions: []
    property bool graphLoading: false
    property string graphError: ""
    property bool roomsLoaded: false
    property bool sessionsLoaded: false

    signal graphRefreshed()

    function refreshDurableGraph() {
        if (graphLoading || roomsProcess.running || sessionsProcess.running)
            return false;

        graphLoading = true;
        graphError = "";
        roomsLoaded = false;
        sessionsLoaded = false;

        roomsProcess.exec([
            "bash",
            "-lc",
            'exec "$HOME/.local/bin/px" hospital rooms --json'
        ]);
        sessionsProcess.exec([
            "bash",
            "-lc",
            'exec "$HOME/.local/bin/px" hospital sessions --json'
        ]);
        return true;
    }

    function finishGraphPart(kind, textValue, exitCode) {
        const kindName = String(kind || "").toUpperCase();
        const body = String(textValue || "").trim();

        if (Number(exitCode || 0) !== 0) {
            graphError =
                "RESPONSIBILITY " + kindName
                + " // PX EXIT " + String(exitCode);
        } else {
            try {
                const parsed = body ? JSON.parse(body) : [];
                if (!Array.isArray(parsed))
                    throw new Error("expected array");

                if (kindName === "ROOMS")
                    durableRooms = parsed;
                else
                    durableSessions = parsed;
            } catch (error) {
                graphError =
                    "RESPONSIBILITY " + kindName
                    + " // " + String(error);
            }
        }

        if (kindName === "ROOMS")
            roomsLoaded = true;
        else
            sessionsLoaded = true;

        if (roomsLoaded && sessionsLoaded) {
            graphLoading = false;
            graphRefreshed();
        }
    }

    Process {
        id: roomsProcess

        property string outputText: ""

        stdout: StdioCollector {
            onStreamFinished: roomsProcess.outputText = this.text
        }

        onExited: function(code, exitStatus) {
            root.finishGraphPart("ROOMS", outputText, code);
        }
    }

    Process {
        id: sessionsProcess

        property string outputText: ""

        stdout: StdioCollector {
            onStreamFinished: sessionsProcess.outputText = this.text
        }

        onExited: function(code, exitStatus) {
            root.finishGraphPart("SESSIONS", outputText, code);
        }
    }

    Connections {
        target: roundsService

        function onRefreshed() {
            root.refreshDurableGraph();
        }
    }

    Component.onCompleted: Qt.callLater(root.refreshDurableGraph)

    function normalized(value) {
        return String(value || "")
            .trim()
            .toLowerCase();
    }

    function roomScore(roomValue, repositoryValue, branchValue) {
        const room = roomValue || {};
        const repository = root.normalized(repositoryValue);
        const branch = root.normalized(branchValue);
        const roomRepository = root.normalized(room.repository);
        const roomBranch = root.normalized(room.branch);
        const roomTeam = root.normalized(room.team);
        const responsibility = root.normalized(room.responsibility);
        let score = 0;
        const reasons = [];

        if (repository && roomRepository === repository) {
            score += 60;
            reasons.push("REPOSITORY");
        }

        if (branch && roomBranch && roomBranch === branch) {
            score += 40;
            reasons.push("BRANCH");
        } else if (branch && roomTeam && roomTeam === branch) {
            score += 30;
            reasons.push("TEAM");
        } else if (branch
                && responsibility
                && responsibility === branch) {
            score += 20;
            reasons.push("RESPONSIBILITY");
        }

        return {
            score: score,
            reasons: reasons
        };
    }

    function bestRoom(repositoryValue, branchValue) {
        const rows =
            roundsService && Array.isArray(roundsService.rooms)
            ? roundsService.rooms
            : [];
        let best = null;
        let bestScore = 0;
        let bestReasons = [];

        for (let i = 0; i < rows.length; ++i) {
            const room = rows[i] || {};
            const scored = root.roomScore(
                room,
                repositoryValue,
                branchValue
            );

            if (scored.score > bestScore) {
                best = room;
                bestScore = scored.score;
                bestReasons = scored.reasons;
            }
        }

        return {
            room: best,
            score: bestScore,
            reasons: bestReasons
        };
    }

    function specialistMatch(recordValue, roomValue) {
        const record = recordValue || {};
        const room = roomValue || {};
        const assignment = root.normalized(record.assignment);

        if (!assignment || assignment === "unassigned")
            return false;

        const needles = [
            room.team,
            room.responsibility,
            room.branch,
            room.repository
        ].map(function(value) {
            return root.normalized(value);
        }).filter(function(value) {
            return value.length > 0;
        });

        for (let i = 0; i < needles.length; ++i) {
            if (assignment === needles[i]
                    || assignment.indexOf(needles[i]) >= 0
                    || needles[i].indexOf(assignment) >= 0)
                return true;
        }

        return false;
    }

    function roomForSpecialist(recordValue) {
        const rows =
            roundsService && Array.isArray(roundsService.rooms)
            ? roundsService.rooms
            : [];
        const matches = [];

        for (let i = 0; i < rows.length; ++i) {
            const room = rows[i] || {};
            if (!root.specialistMatch(recordValue, room))
                continue;

            if (String(room.team || "") === String(currentRoomId || ""))
                return room;

            matches.push(room);
        }

        return matches.length === 1 ? matches[0] : null;
    }

    function specialistsForRoom(roomValue) {
        const rows =
            registryService && Array.isArray(registryService.specialists)
            ? registryService.specialists
            : [];
        const out = [];

        for (let i = 0; i < rows.length; ++i) {
            const record = rows[i] || {};
            if (!root.specialistMatch(record, roomValue))
                continue;

            out.push({
                id: String(record.id || ""),
                name: String(record.name || record.id || "SPECIALIST"),
                role: String(record.role || "SPECIALIST"),
                provider: String(record.provider || ""),
                presence: String(record.presence || "UNKNOWN"),
                assignment: String(record.assignment || "")
            });
        }

        return out;
    }

    function durableRoomFor(roomValue, repositoryValue, branchValue) {
        const room = roomValue || {};
        const roomId = String(room.id || room.roomId || room.team || "").trim();
        const repository = root.normalized(repositoryValue || room.repository);
        const branch = root.normalized(branchValue || room.branch);
        const rows = Array.isArray(durableRooms) ? durableRooms : [];

        for (let i = 0; i < rows.length; ++i) {
            const candidate = rows[i] || {};
            const candidateId =
                String(candidate.id || candidate.roomId || candidate.team || "").trim();

            if (roomId && candidateId === roomId)
                return candidate;
        }

        for (let i = 0; i < rows.length; ++i) {
            const candidate = rows[i] || {};
            if (repository
                    && root.normalized(candidate.repository) === repository
                    && branch
                    && root.normalized(candidate.branch) === branch)
                return candidate;
        }

        return null;
    }

    function activeSessionForRoom(roomIdValue) {
        const roomId = String(roomIdValue || "").trim();
        const rows = Array.isArray(durableSessions)
            ? durableSessions : [];
        let fallback = null;

        for (let i = 0; i < rows.length; ++i) {
            const session = rows[i] || {};
            if (String(session.roomId || "") !== roomId)
                continue;

            if (!fallback)
                fallback = session;

            const status = String(session.status || "").toUpperCase();
            if (!session.endedAt
                    && ["COMPLETE", "FAILED"].indexOf(status) < 0)
                return session;
        }

        return fallback;
    }

    function activeAssignmentForRoom(roomValue) {
        const room = roomValue || {};
        const team = String(room.team || "").trim();
        const selected = String(currentRoomId || "").trim();

        if (!assignmentService
                || !team
                || team !== selected)
            return null;

        return assignmentService.activeAssignment || null;
    }

    function confidenceLabel(scoreValue) {
        const score = Number(scoreValue || 0);
        if (score >= 100)
            return "EXACT";
        if (score >= 80)
            return "STRONG";
        if (score >= 60)
            return "REPOSITORY";
        if (score > 0)
            return "PARTIAL";
        return "UNMAPPED";
    }

    function contextFor(repositoryValue, branchValue) {
        const repository = String(repositoryValue || "").trim();
        const branch = String(branchValue || "").trim();
        const matched = root.bestRoom(repository, branch);
        const room = matched.room || null;
        const specialists = room
            ? root.specialistsForRoom(room)
            : [];
        const assignment = room
            ? root.activeAssignmentForRoom(room)
            : null;
        const roomTeam = room ? String(room.team || "") : "";
        const responsibility =
            room ? String(room.responsibility || "") : "";
        const durable = root.durableRoomFor(
            room,
            repository,
            branch
        );
        const durableRoomId = durable
            ? String(durable.id || durable.roomId || roomTeam)
            : roomTeam;
        const session = durableRoomId
            ? root.activeSessionForRoom(durableRoomId)
            : null;
        const specialistNames = specialists.map(function(row) {
            return String(row.name || row.id || "SPECIALIST");
        });

        let ownerLabel = "UNMAPPED";
        if (specialistNames.length > 0)
            ownerLabel = specialistNames.join(", ");
        else if (durable && durable.doctorId)
            ownerLabel = String(durable.doctorId);
        else if (roomTeam)
            ownerLabel = roomTeam;
        else if (responsibility)
            ownerLabel = responsibility;

        return {
            repository: repository,
            branch: branch,
            confidence: root.confidenceLabel(matched.score),
            score: matched.score,
            reasons: matched.reasons,
            roomId: durableRoomId,
            roomTeam: roomTeam,
            roomResponsibility: responsibility,
            roomBranch:
                durable && durable.branch
                ? String(durable.branch)
                : room ? String(room.branch || "") : "",
            roomState: room ? String(room.state || "") : "",
            floorLabel: room ? String(room.floorLabel || "") : "",
            bedPath:
                durable ? String(durable.bedPath || "") : "",
            doctorId:
                session && session.doctorId
                ? String(session.doctorId)
                : durable ? String(durable.doctorId || "") : "",
            providerId:
                session && session.providerId
                ? String(session.providerId)
                : durable ? String(durable.providerId || "") : "",
            sessionId:
                session ? String(session.id || "") : "",
            sessionStatus:
                session ? String(session.status || "") : "",
            activeProviderPid:
                session ? Number(session.activeProviderPid || 0) : 0,
            specialists: specialists,
            specialistNames: specialistNames,
            ownerLabel: ownerLabel,
            assignmentId:
                assignment
                ? String(assignment.id || "")
                : durable ? String(durable.assignmentId || "") : "",
            assignmentTitle:
                assignment ? String(assignment.title || "") : "",
            assignmentGoal:
                assignment ? String(assignment.goal || "") : "",
            assignmentPhase:
                assignment ? String(assignment.phase || "") : "",
            assignmentPermissions:
                assignment && Array.isArray(assignment.permissions)
                ? assignment.permissions.slice()
                : []
        };
    }

    function blockerForWorkItem(itemValue) {
        const item = itemValue || {};

        if (Boolean(item.failedChecks)
                || Number(item.checkFailed || 0) > 0)
            return "FAILED CHECKS";
        if (Boolean(item.changesRequested))
            return "CHANGES REQUESTED";
        if (Boolean(item.mergeConflict))
            return "MERGE CONFLICT";
        if (Boolean(item.blocked))
            return "BLOCKED";
        if (Boolean(item.pendingChecks)
                || Number(item.checkPending || 0) > 0)
            return "CHECKS PENDING";
        if (Boolean(item.waitingOnReviewer))
            return "WAITING ON REVIEWER";
        if (Boolean(item.needsMyReview))
            return "NEEDS YOUR REVIEW";

        const state = String(
            item.primaryState || item.state || ""
        ).toUpperCase();
        if (state === "LOCKED")
            return "MERGE QUEUE LOCKED";
        if (state === "UNMERGEABLE")
            return "UNMERGEABLE";
        if (state === "AWAITING_CHECKS")
            return "CHECKS PENDING";

        return "";
    }

    function responsibilityChain(contextValue) {
        const context = contextValue || {};
        const parts = [];

        if (context.workItemNumber)
            parts.push(
                String(context.workItemKind || "WORK").toUpperCase()
                + " #" + String(context.workItemNumber)
            );
        if (context.roomTeam)
            parts.push("ROOM " + String(context.roomTeam));
        if (context.bedPath)
            parts.push("BED " + String(context.bedPath));
        if (context.doctorId)
            parts.push("DOCTOR " + String(context.doctorId));
        if (context.sessionId)
            parts.push(
                "SESSION " + String(context.sessionId)
                + (
                    context.sessionStatus
                    ? " [" + String(context.sessionStatus) + "]"
                    : ""
                  )
            );
        if (context.assignmentId)
            parts.push(
                "ORDER "
                + (
                    context.assignmentTitle
                    ? String(context.assignmentTitle)
                    : "#" + String(context.assignmentId)
                  )
            );
        if (context.blocker)
            parts.push("WAITING // " + String(context.blocker));

        return parts.join(" → ");
    }

    function contextForWorkItem(itemValue) {
        const item = itemValue || {};
        const repository = String(item.repository || "").trim();
        const branch = String(
            item.headRefName
            || item.branch
            || item.headBranch
            || ""
        ).trim();
        const context = root.contextFor(repository, branch);

        context.workItemKind = String(
            item.kind || item.workItemKind || "pull_request"
        );
        context.workItemNumber = Number(
            item.number || item.pullRequestNumber || 0
        );
        context.workItemTitle = String(item.title || "");
        context.workItemUrl = String(item.url || "");
        context.workItemHeadSha = String(
            item.headSha || item.headRefOid || ""
        );
        context.workItemBaseBranch = String(
            item.baseRefName || item.baseBranch || ""
        );
        context.attentionState = String(
            item.primaryState || item.state || ""
        );
        context.attentionStates =
            Array.isArray(item.attentionStates)
            ? item.attentionStates.slice()
            : [];
        context.blocker = root.blockerForWorkItem(item);
        context.evidence = {
            checksPassed: Number(item.checkPassed || 0),
            checksFailed: Number(item.checkFailed || 0),
            checksPending: Number(item.checkPending || 0),
            reviewDecision: String(item.reviewDecision || ""),
            mergeState: String(
                item.mergeStateStatus
                || item.mergeable
                || item.state
                || ""
            ),
            headSha: context.workItemHeadSha
        };
        context.chain = root.responsibilityChain(context);
        return context;
    }

}
