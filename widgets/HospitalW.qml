import QtQuick
import Quickshell
import Quickshell.Wayland
import qs.components
import "../services/git"
import "../services/hospital"
import "../services/github"
import QtQuick.Effects
import Qt5Compat.GraphicalEffects

PanelWindow {
    id: root

    property bool menuOpen: false
    property bool keyboardActive: true
    property bool keyboardLock: false
    signal keyboardOwnershipRequested()

    property string selectedCommitSha: ""
    property string selectedRoomTeam: ""
    property bool remoteRefreshPending: false
    property int openAuditStaleInterval: 600000
    property bool openAuditPending: false
    property var lastOpenAuditByFloor: ({})
    property string auditedRoomTeam: ""
    property string pendingRoomAuditTeam: ""
    property string roomAuditInFlightTeam: ""
    property bool roomControlMode: false
    property string roomControlAction: ""
    property bool bedControlMode: false
    property string operationsSurface: ""
    property bool phoneMenuOpen: false
    property bool intercomMenuOpen: false
    property bool intercomTyping: false
    property bool receptionistTyping: false
    property string pendingRoundsRoomTeam: ""
    property int pendingRoundsFloorIndex: -1
    property string pendingReceptionTeam: ""
    property var pendingReceptionRoundsSelection: null

    readonly property bool operationsOpen:
        root.operationsSurface.length > 0
    readonly property var selectedRoomData:
        auditService.roomFor(selectedRoomTeam)
    readonly property string selectedRoomBranch: {
        const room = selectedRoomData || {};
        return String(room.branch || "");
    }
    readonly property bool bedIsClean:
        String(floorService.bedWorktree || "")
            .trim()
            .toUpperCase() === "CLEAN"
    readonly property bool bedAlreadyInSelectedRoom:
        selectedRoomBranch.length > 0
        && String(floorService.bedBranch || "") === selectedRoomBranch
    readonly property bool bedMoveEnabled:
        selectedRoomBranch.length > 0
        && floorService.bedPath.length > 0
        && !bedAlreadyInSelectedRoom
        && bedIsClean
        && !floorService.moveRunning
        && !roomService.running
        && !roomService.rehearsing
        && !roomService.integrating
        && !roomService.postOpRunning
        && !roomService.armed

    function toggleCommitSelection(sha) {
        const candidate = String(sha || "");
        selectedCommitSha = selectedCommitSha === candidate ? "" : candidate;
    }

    function toggleRoomSelection(team) {
        const candidate = String(team || "");
        selectedRoomTeam = selectedRoomTeam === candidate ? "" : candidate;
    }

    function roomIndexOfTeam(team) {
        const wanted = String(team || "");
        const rows = auditService.rooms || [];

        if (!wanted || !Array.isArray(rows))
            return -1;

        for (let i = 0; i < rows.length; ++i) {
            const row = rows[i] || {};
            const candidate = String(row.team || row.branch || "");

            if (candidate === wanted)
                return i;
        }

        return -1;
    }

    function ensureRoomVisible(index) {
        const count = (auditService.rooms || []).length;

        if (index < 0 || index >= count)
            return;

        const stride = 61;
        const rowTop = index * stride;
        const rowBottom = rowTop + 54;
        const viewTop = hospitalScroll.contentY;
        const viewBottom = viewTop + hospitalScroll.height;

        if (rowTop < viewTop)
            hospitalScroll.contentY = rowTop;
        else if (rowBottom > viewBottom)
            hospitalScroll.contentY = Math.min(
                scrollRail.maxContentY,
                Math.max(0, rowBottom - hospitalScroll.height)
            );
    }

    function selectRoomIndex(index) {
        const rows = auditService.rooms || [];

        if (!Array.isArray(rows) || rows.length === 0)
            return;

        const clamped = Math.max(0, Math.min(rows.length - 1, Number(index)));
        const row = rows[clamped] || {};
        const team = String(row.team || row.branch || "");

        if (!team)
            return;

        selectedRoomTeam = team;
        ensureRoomVisible(clamped);
    }

    function cycleRoom(delta) {
        const rows = auditService.rooms || [];

        if (!Array.isArray(rows) || rows.length === 0)
            return;

        let index = roomIndexOfTeam(selectedRoomTeam);

        if (index < 0)
            index = Number(delta || 0) < 0 ? rows.length : -1;

        index = Math.max(
            0,
            Math.min(rows.length - 1, index + Number(delta || 0))
        );

        selectRoomIndex(index);
    }

    readonly property var roomControlLayout: [
        { name: "STATUS", x: 0, y: 0 },
        { name: "DIFF", x: 1, y: 0 },
        { name: "LOG", x: 2, y: 0 },
        { name: "REFRESH", x: 0, y: 1 },
        { name: "LAZYGIT", x: 1, y: 1 },
        { name: "PREPARE", x: 2, y: 1 },
        { name: "REHEARSE", x: 1, y: 2 },
        { name: "ARM", x: 0, y: 3 },
        { name: "INTEGRATE", x: 2, y: 3 }
    ]

    readonly property bool roomBaseActionsEnabled:
        !root.operationsOpen
        && root.selectedRoomTeam.length > 0
        && !roomService.running
        && !roomService.rehearsing
        && !roomService.integrating
        && !roomService.postOpRunning
        && !roomService.armed

    function roomControlEnabled(name) {
        const action = String(name || "");

        if (action === "STATUS"
                || action === "DIFF"
                || action === "LOG"
                || action === "REFRESH"
                || action === "LAZYGIT"
                || action === "PREPARE")
            return roomBaseActionsEnabled;

        if (action === "REHEARSE")
            return rehearseButton.enabledAction;

        if (action === "ARM")
            return armButton.enabledAction && !roomService.armed;

        if (action === "INTEGRATE")
            return integrateButton.enabledAction;

        return false;
    }

    function firstEnabledRoomControl() {
        const layout = roomControlLayout || [];

        for (let i = 0; i < layout.length; ++i) {
            const name = String(layout[i].name || "");

            if (roomControlEnabled(name))
                return name;
        }

        return "";
    }

    function enterRoomControls() {
        if (root.operationsOpen || !selectedRoomTeam)
            return;

        bedControlMode = false;
        roomControlMode = true;

        if (!roomControlEnabled(roomControlAction))
            roomControlAction = firstEnabledRoomControl();
    }

    function leaveRoomControls() {
        roomControlMode = false;
        roomControlAction = "";
    }

    function enterBedControls() {
        if (root.operationsOpen || !selectedRoomTeam)
            return;

        roomControlMode = false;
        roomControlAction = "";
        bedControlMode = true;
    }

    function leaveBedControls() {
        bedControlMode = false;
    }

    function invokeMoveBed() {
        if (root.operationsOpen
                || !menuOpen
                || !moveBedButton.enabledAction)
            return;

        floorService.moveBedToRoom(root.selectedRoomBranch);
    }

    function moveRoomControl(dx, dy) {
        if (root.operationsOpen)
            return;

        if (bedControlMode) {
            // The Bed box has one keyboard-selectable action: MOVE BED.
            // Left returns to the Room action grid. Down exits back to the
            // Room selector while keeping the current Room selected.
            if (Number(dx || 0) < 0) {
                enterRoomControls();
                return;
            }

            if (Number(dy || 0) > 0) {
                leaveBedControls();
                return;
            }

            return;
        }

        if (!roomControlMode) {
            if (Number(dy || 0) < 0)
                cycleRoom(-1);
            else if (Number(dy || 0) > 0)
                cycleRoom(1);
            else if (Number(dx || 0) < 0)
                cycleFloor(-1);
            else if (Number(dx || 0) > 0)
                cycleFloor(1);
            return;
        }

        if (!roomControlEnabled(roomControlAction))
            roomControlAction = firstEnabledRoomControl();

        const layout = roomControlLayout || [];
        let current = null;

        for (let i = 0; i < layout.length; ++i) {
            if (String(layout[i].name || "") === roomControlAction) {
                current = layout[i];
                break;
            }
        }

        if (!current) {
            roomControlAction = firstEnabledRoomControl();
            return;
        }

        let bestName = "";
        let bestScore = Number.MAX_VALUE;
        const horizontal = Number(dx || 0) !== 0;

        for (let i = 0; i < layout.length; ++i) {
            const candidate = layout[i];
            const name = String(candidate.name || "");

            if (!name
                    || name === roomControlAction
                    || !roomControlEnabled(name))
                continue;

            const deltaX = Number(candidate.x) - Number(current.x);
            const deltaY = Number(candidate.y) - Number(current.y);

            if (dx < 0 && deltaX >= 0)
                continue;
            if (dx > 0 && deltaX <= 0)
                continue;
            if (dy < 0 && deltaY >= 0)
                continue;
            if (dy > 0 && deltaY <= 0)
                continue;

            const primary = horizontal ? Math.abs(deltaX) : Math.abs(deltaY);
            const secondary = horizontal ? Math.abs(deltaY) : Math.abs(deltaX);
            const score = primary * 100 + secondary;

            if (score < bestScore) {
                bestScore = score;
                bestName = name;
            }
        }

        if (bestName) {
            roomControlAction = bestName;
            return;
        }

        if (Number(dx || 0) > 0) {
            enterBedControls();
            return;
        }

        // When there is no enabled control below the current one, Down exits
        // the Room action grid back to the Room selector. The Room itself
        // stays selected, so the next Up/Down moves between Rooms.
        if (Number(dy || 0) > 0)
            leaveRoomControls();
    }

    function performRoomControl(actionName) {
        const action = String(actionName || "");

        if (!roomControlEnabled(action))
            return;

        if (action === "STATUS"
                || action === "DIFF"
                || action === "LOG") {
            roomService.runInspection(action.toLowerCase());
            return;
        }

        if (action === "REFRESH") {
            patientService.refresh();
            root.runAuditForCurrentRoom();
            roomService.runInspection("status");
            return;
        }

        if (action === "LAZYGIT") {
            roomService.launchLazygit();
            return;
        }

        if (action === "PREPARE") {
            certificationCoordinator.prepare();
            return;
        }

        if (action === "REHEARSE") {
            certificationCoordinator.rehearse();
            return;
        }

        if (action === "ARM") {
            const gateState = certificationCoordinator.state;

            if (gateState === "CANDIDATE") {
                certificationCoordinator.requestVerification("");
                return;
            }

            if (gateState === "VERIFIED") {
                certificationCoordinator.certify();
                return;
            }

            if (gateState === "CERTIFIED")
                certificationCoordinator.arm();

            return;
        }

        if (action === "INTEGRATE")
            certificationCoordinator.integrate();
    }

    function activateRoomControl() {
        if (!roomControlMode)
            return;

        performRoomControl(roomControlAction);
    }

    function invokeRoomShortcut(actionName) {
        if (root.operationsOpen
                || !menuOpen
                || !selectedRoomTeam)
            return;

        performRoomControl(actionName);
    }

    function handleRoomEnter() {
        if (root.operationsOpen)
            return;

        if (!selectedRoomTeam) {
            selectRoomIndex(0);
            return;
        }

        if (bedControlMode) {
            invokeMoveBed();
            return;
        }

        if (!roomControlMode) {
            enterRoomControls();
            return;
        }

        activateRoomControl();
    }

    function ensureFirstRoomSelected() {
        const rows = auditService.rooms || [];

        if (!menuOpen
                || selectedRoomTeam
                || !Array.isArray(rows)
                || rows.length === 0)
            return;

        selectRoomIndex(0);
    }

    function scheduleRoomEntryAudit(team) {
        const candidate = String(team || "").trim();

        auditedRoomTeam = "";
        pendingRoomAuditTeam = candidate;

        if (!candidate || !menuOpen)
            return;

        // Room entry owns the audit trigger. There is no settle/debounce
        // window: run immediately, or remain queued behind an audit that is
        // already in flight.
        runPendingRoomAudit();
    }

    function runPendingRoomAudit() {
        const candidate = String(pendingRoomAuditTeam || "");

        if (!candidate
                || !menuOpen
                || selectedRoomTeam !== candidate
                || auditService.running)
            return;

        roomAuditInFlightTeam = candidate;
        auditService.runAudit(false);
    }

    function runAuditForCurrentRoom() {
        const candidate = String(selectedRoomTeam || "").trim();

        if (candidate) {
            auditedRoomTeam = "";
            pendingRoomAuditTeam = candidate;
        }

        if (!auditService.running)
            roomAuditInFlightTeam = candidate;

        auditService.runAudit(false);
    }

    readonly property bool floorSwitchEnabled:
        !root.operationsOpen
        && floorService.floorCount > 1
        && !floorService.discovering
        && !patientService.refreshing
        && !roomService.running
        && !roomService.rehearsing
        && !roomService.integrating
        && !roomService.postOpRunning
        && !roomService.armed

    function selectFloor(index) {
        if (!floorSwitchEnabled)
            return;

        const requested = Number(index);
        const current = floorService.selectedFloorIndex;

        if (requested < 0
                || requested >= floorService.floorCount
                || requested === current)
            return;

        selectedCommitSha = "";
        selectedRoomTeam = "";
        roomService.clearResult();
        certificationCoordinator.bindRoom(roomService);
        auditService.resetResult();
        floorService.selectFloor(requested);
    }

    function cycleFloor(delta) {
        if (!floorSwitchEnabled)
            return;

        const count = floorService.floorCount;
        let current = floorService.selectedFloorIndex;

        if (count <= 0)
            return;

        if (current < 0)
            current = 0;

        const requested =
            (current + Number(delta || 0) + count) % count;

        selectFloor(requested);
    }

    readonly property bool bedSwitchEnabled:
        !root.operationsOpen
        && floorService.bedCount > 1
        && !floorService.discovering
        && !patientService.refreshing
        && !roomService.running
        && !roomService.rehearsing
        && !roomService.integrating
        && !roomService.postOpRunning
        && !roomService.armed

    function selectBed(index) {
        if (!bedSwitchEnabled)
            return;

        const requested = Number(index);

        if (requested < 0
                || requested >= floorService.bedCount
                || requested === floorService.selectedBedIndex)
            return;

        selectedCommitSha = "";
        roomService.clearResult();
        certificationCoordinator.bindRoom(roomService);
        floorService.selectBed(requested);
    }

    function cycleBed(delta) {
        if (!bedSwitchEnabled)
            return;

        const count = floorService.bedCount;
        let current = floorService.selectedBedIndex;

        if (count <= 0)
            return;

        if (current < 0)
            current = 0;

        selectBed(
            (current + Number(delta || 0) + count) % count
        );
    }

    onSelectedRoomTeamChanged: {
        root.leaveRoomControls();
        root.leaveBedControls();
        roomService.clearResult();
        certificationCoordinator.bindRoom(roomService);
        root.scheduleRoomEntryAudit(root.selectedRoomTeam);
    }

    // 700px content chassis + 44px floor-selector lane.
    property int panelWidth: 744
    property int panelHeight: 1320
    property int panelTopMargin: 0
    // Extend the new floor-selector lane to the screen edge while keeping
    // the original Hospital content at the same desktop position.
    property int panelLeftMargin: 6
    property int frameInset: 8
    property int glowGutter: 14
    property int topGlowGutter: 12

    // Reserve transparent pixels above the visible chassis so its top glow
    // renders inside the PanelWindow instead of being clipped by the top bar.
    implicitWidth: panelWidth + glowGutter * 2
    implicitHeight: panelHeight + topGlowGutter + glowGutter

    anchors {
        top: true
        bottom: false
        left: true
        right: false
    }

    margins {
        top: panelTopMargin
        left: panelLeftMargin - glowGutter
        right: 0
        bottom: 0
    }

    exclusiveZone: 0
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.keyboardFocus:
        !root.menuOpen || !root.keyboardActive
        ? WlrKeyboardFocus.None
        : root.keyboardLock
        ? WlrKeyboardFocus.Exclusive
        : WlrKeyboardFocus.OnDemand

    color: "transparent"
    surfaceFormat.opaque: false

    // Keep the real surface mapped. Closed state is invisible + click-through.
    visible: true

    mask: Region {
        x: 0
        y: 0
        width: root.menuOpen ? root.width : 0
        height: root.menuOpen ? root.height : 0
    }

    Item {
        id: keyboardFocusAnchor

        anchors.fill: parent
        focus: root.menuOpen && root.keyboardActive
        enabled: root.menuOpen
        z: -1000
    }

    Shortcut {
        sequence: "Esc"
        context: Qt.ApplicationShortcut
        enabled: root.menuOpen && root.keyboardActive
        onActivated: {
            if (root.intercomMenuOpen) {
                root.intercomMenuOpen = false;
                root.intercomTyping = false;
                keyboardFocusAnchor.forceActiveFocus();
                return;
            }

            if (root.phoneMenuOpen) {
                root.phoneMenuOpen = false;
                return;
            }

            if (root.operationsOpen) {
                root.closeOperationsSurface();
                return;
            }

            root.close();
        }
    }

    Shortcut {
        sequence: "Up"
        context: Qt.ApplicationShortcut
        enabled: root.menuOpen && root.keyboardActive && !root.intercomTyping && !root.receptionistTyping
        onActivated: root.moveRoomControl(0, -1)
    }

    Shortcut {
        sequence: "Down"
        context: Qt.ApplicationShortcut
        enabled: root.menuOpen && root.keyboardActive && !root.intercomTyping && !root.receptionistTyping
        onActivated: root.moveRoomControl(0, 1)
    }

    Shortcut {
        sequence: "Left"
        context: Qt.ApplicationShortcut
        enabled: root.menuOpen && root.keyboardActive && !root.intercomTyping && !root.receptionistTyping
        onActivated: root.moveRoomControl(-1, 0)
    }

    Shortcut {
        sequence: "Right"
        context: Qt.ApplicationShortcut
        enabled: root.menuOpen && root.keyboardActive && !root.intercomTyping && !root.receptionistTyping
        onActivated: root.moveRoomControl(1, 0)
    }

    Shortcut {
        sequence: "Return"
        context: Qt.ApplicationShortcut
        enabled: root.menuOpen && root.keyboardActive && !root.intercomTyping && !root.receptionistTyping
        onActivated: root.handleRoomEnter()
    }

    Shortcut {
        sequence: "Enter"
        context: Qt.ApplicationShortcut
        enabled: root.menuOpen && root.keyboardActive && !root.intercomTyping && !root.receptionistTyping
        onActivated: root.handleRoomEnter()
    }

    Shortcut {
        sequence: "Shift+Left"
        context: Qt.ApplicationShortcut
        enabled: root.menuOpen && root.keyboardActive && !root.intercomTyping && !root.receptionistTyping
        onActivated: root.cycleBed(-1)
    }

    Shortcut {
        sequence: "Shift+Right"
        context: Qt.ApplicationShortcut
        enabled: root.menuOpen && root.keyboardActive && !root.intercomTyping && !root.receptionistTyping
        onActivated: root.cycleBed(1)
    }

    Shortcut {
        sequence: "Shift+S"
        context: Qt.ApplicationShortcut
        enabled: root.menuOpen && root.keyboardActive && !root.intercomTyping && !root.receptionistTyping
        onActivated: root.invokeRoomShortcut("STATUS")
    }

    Shortcut {
        sequence: "Shift+D"
        context: Qt.ApplicationShortcut
        enabled: root.menuOpen && root.keyboardActive && !root.intercomTyping && !root.receptionistTyping
        onActivated: root.invokeRoomShortcut("DIFF")
    }

    Shortcut {
        sequence: "Shift+F"
        context: Qt.ApplicationShortcut
        enabled: root.menuOpen && root.keyboardActive && !root.intercomTyping && !root.receptionistTyping
        onActivated: root.invokeRoomShortcut("LOG")
    }

    Shortcut {
        sequence: "Shift+R"
        context: Qt.ApplicationShortcut
        enabled: root.menuOpen && root.keyboardActive && !root.intercomTyping && !root.receptionistTyping
        onActivated: root.invokeRoomShortcut("REFRESH")
    }

    Shortcut {
        sequence: "Shift+G"
        context: Qt.ApplicationShortcut
        enabled: root.menuOpen && root.keyboardActive && !root.intercomTyping && !root.receptionistTyping
        onActivated: root.invokeRoomShortcut("LAZYGIT")
    }

    Shortcut {
        sequence: "Shift+P"
        context: Qt.ApplicationShortcut
        enabled: root.menuOpen && root.keyboardActive && !root.intercomTyping && !root.receptionistTyping
        onActivated: root.invokeRoomShortcut("PREPARE")
    }

    Shortcut {
        sequence: "Shift+M"
        context: Qt.ApplicationShortcut
        enabled: root.menuOpen && root.keyboardActive && !root.intercomTyping && !root.receptionistTyping
        onActivated: root.invokeRoomShortcut("REHEARSE")
    }

    Shortcut {
        sequence: "Shift+A"
        context: Qt.ApplicationShortcut
        enabled: root.menuOpen && root.keyboardActive && !root.intercomTyping && !root.receptionistTyping
        onActivated: root.invokeRoomShortcut("ARM")
    }

    Shortcut {
        sequence: "Shift+I"
        context: Qt.ApplicationShortcut
        enabled: root.menuOpen && root.keyboardActive && !root.intercomTyping && !root.receptionistTyping
        onActivated: root.invokeRoomShortcut("INTEGRATE")
    }

    Shortcut {
        sequence: "Shift+B"
        context: Qt.ApplicationShortcut
        enabled: root.menuOpen && root.keyboardActive && !root.intercomTyping && !root.receptionistTyping
        onActivated: root.invokeMoveBed()
    }

    function closeOperationsSurface() {
        receptionistService.endVisit();
        root.operationsSurface = "";
    }

    function showSurgery() {
        root.closeOperationsSurface();
    }

    function syncReceptionistActivity() {
        receptionistService.syncRounds(roundsService.rooms);
        receptionistService.syncStaff(
            specialistRegistryService.specialists
        );
        receptionistService.syncReports(
            certificationCoordinator.historyService.events
        );
    }

    function refreshReceptionData() {
        root.syncReceptionistActivity();

        if (!roundsService.running && !roundsService.available)
            roundsService.refresh();

        if (specialistRegistryService.loaded
                && !specialistRegistryService.probing
                && !specialistRegistryService.lastRefreshedAt)
            specialistRegistryService.refreshPresence();
    }

    function openReception() {
        root.leaveRoomControls();
        root.leaveBedControls();
        root.phoneMenuOpen = false;
        root.intercomMenuOpen = false;
        root.intercomTyping = false;
        root.operationsSurface = "reception";
        root.refreshReceptionData();
        receptionistService.beginVisit();
    }

    function handleReceptionRoute(route) {
        const target = String(route || "").toLowerCase();

        if (target === "surgery") {
            root.showSurgery();
            return;
        }

        if (target === "reports") {
            root.openReports();
            return;
        }

        if (target === "rounds") {
            root.openRounds();
            return;
        }

        if (target === "staff") {
            root.openStaff();
            return;
        }

        if (target === "phone") {
            if (!root.phoneMenuOpen)
                root.togglePhoneMenu();
            return;
        }

        if (target === "intercom") {
            if (!root.intercomMenuOpen)
                root.toggleIntercomMenu();
        }
    }

    function specialistMentionedIn(textValue) {
        const query =
            String(textValue || "").trim().toLowerCase();
        const rows =
            specialistRegistryService
            && Array.isArray(
                specialistRegistryService.specialists
            )
            ? specialistRegistryService.specialists
            : [];

        if (!query)
            return null;

        for (let i = 0; i < rows.length; ++i) {
            const row = rows[i] || {};
            const id =
                String(row.id || "").trim().toLowerCase();
            const name =
                String(row.name || "").trim().toLowerCase();

            if ((id && query.indexOf(id) >= 0)
                    || (name && query.indexOf(name) >= 0))
                return row;
        }

        return null;
    }

    function syncHospitalContextFromReception(questionValue) {
        const item = receptionistService.contextItem;
        const target =
            String(
                receptionistService.contextTarget
                || ""
            ).trim();

        if (item) {
            hospitalContextService.captureActivity(
                item,
                questionValue
            );
            return true;
        }

        if (target) {
            hospitalContextService.captureTeam(target);
            hospitalContextService.setOperatorQuestion(
                questionValue
            );
            return true;
        }

        if (hospitalContextService.active) {
            hospitalContextService.setOperatorQuestion(
                questionValue
            );
            return true;
        }

        if (root.selectedRoomTeam) {
            hospitalContextService.captureTeam(
                root.selectedRoomTeam
            );
            hospitalContextService.setOperatorQuestion(
                questionValue
            );
            return true;
        }

        return false;
    }

    function requestReceptionSpecialistHandoff(
            modeValue,
            operatorTextValue) {
        const mode =
            String(modeValue || "").trim().toLowerCase();
        const operatorText =
            String(operatorTextValue || "").trim();
        const specialist =
            root.specialistMentionedIn(operatorText);

        if (!specialist) {
            receptionistService.append(
                "RECEPTION",
                "HANDOFF // NAME A SPECIALIST FROM THE LIVE STAFF REGISTRY"
            );
            return false;
        }

        if (!root.syncHospitalContextFromReception(
                operatorText)) {
            receptionistService.append(
                "RECEPTION",
                "HANDOFF // NO LIVE ROOM, REPORT, EVENT, OR STAFF CONTEXT"
            );
            return false;
        }

        const body =
            hospitalContextService.handoffBody(
                operatorText
            );
        const specialistName =
            String(
                specialist.name
                || specialist.id
                || "SPECIALIST"
            );

        if (mode === "phone") {
            if (!phoneService.callSpecialist(
                    specialist,
                    floorService.bedPath,
                    body)) {
                receptionistService.append(
                    "RECEPTION",
                    phoneService.lastError
                    || "HANDOFF // PHONE FAILED"
                );
                return false;
            }

            receptionistService.append(
                "RECEPTION",
                "HANDOFF // PHONE // "
                + specialistName
                + " // CONTEXT ATTACHED"
            );
            return true;
        }

        const channelType =
            hospitalContextService.team
            ? "ROOM"
            : "HOSPITAL";
        const channelLabel =
            hospitalContextService.team
            || "HOSPITAL WIDE";

        if (!intercomService.sendMessage(
                specialist,
                channelType,
                channelLabel,
                body,
                floorService.bedPath)) {
            receptionistService.append(
                "RECEPTION",
                intercomService.lastError
                || "HANDOFF // INTERCOM FAILED"
            );
            return false;
        }

        receptionistService.append(
            "RECEPTION",
            "HANDOFF // INTERCOM // "
            + specialistName
            + " // "
            + hospitalContextService.label
        );
        return true;
    }

    function openReceptionReportEvent(itemValue) {
        const item = itemValue || {};
        const context = item.context || {};
        const identity = {
            team: String(context.team || ""),
            eventType: String(context.eventType || ""),
            state: String(context.state || ""),
            recordedAt: String(
                context.recordedAt
                || item.recordedAt
                || ""
            )
        };

        root.openReports(identity.team);

        Qt.callLater(function() {
            if (reportsView.selectEventIdentity(identity))
                return;

            receptionistService.append(
                "RECEPTION",
                "REPORT // "
                + (
                    identity.team
                    ? identity.team + " // "
                    : ""
                  )
                + "EXACT EVENT NOT FOUND IN RETAINED REPORTS"
            );
        });
    }

    function receptionRoundsIdentity(itemValue) {
        const item = itemValue || {};
        const context = item.context || {};
        const room = context.room || {};

        return {
            team: String(
                context.team
                || room.team
                || room.branch
                || ""
            ),
            repository: String(room.repository || ""),
            floorIndex:
                Number.isFinite(Number(room.floorIndex))
                ? Number(room.floorIndex)
                : -1
        };
    }

    function finishPendingReceptionRoundsSelection(reportMissing) {
        const identity =
            root.pendingReceptionRoundsSelection;

        if (!identity)
            return false;

        if (roundsView.selectRoomIdentity(identity)) {
            root.pendingReceptionRoundsSelection = null;
            return true;
        }

        if (!reportMissing)
            return false;

        root.pendingReceptionRoundsSelection = null;
        receptionistService.append(
            "RECEPTION",
            "ROUNDS // "
            + String(identity.team || "ROOM")
            + " // NOT FOUND IN LIVE ROUNDS"
        );
        return false;
    }

    function openReceptionRoundsEvent(itemValue) {
        const identity =
            root.receptionRoundsIdentity(itemValue);

        root.pendingReceptionRoundsSelection = identity;
        root.openRounds();

        Qt.callLater(function() {
            if (root.finishPendingReceptionRoundsSelection(false))
                return;

            // openRounds() starts a refresh whenever the lane is free.
            // If no refresh is running, there will be no later callback.
            if (!roundsService.running)
                root.finishPendingReceptionRoundsSelection(true);
        });
    }

    function activateReceptionActivity(item) {
        const row = item || {};

        hospitalContextService.captureActivity(
            row,
            ""
        );

        const kind =
            String(row.kind || "").toLowerCase();
        const source =
            String(row.source || "").toLowerCase();
        const context = row.context || {};
        const specialistId =
            String(context.specialistId || "").trim();

        if (source === "reports") {
            root.openReceptionReportEvent(row);
            return;
        }

        if (source === "rounds") {
            root.openReceptionRoundsEvent(row);
            return;
        }

        if (kind === "room") {
            root.openRoomFromRounds(context.room || {});
            return;
        }

        if (kind === "staff") {
            root.openStaff();

            if (specialistId) {
                Qt.callLater(function() {
                    if (specialistsView.selectSpecialistById(
                            specialistId))
                        return;

                    receptionistService.append(
                        "RECEPTION",
                        "STAFF // "
                        + specialistId
                        + " // NOT FOUND IN LIVE REGISTRY"
                    );
                });
            }
            return;
        }

        if (source === "phone") {
            if (!root.phoneMenuOpen)
                root.togglePhoneMenu();

            if (specialistId
                    && !phoneDropdown.focusSpecialistId(
                        specialistId))
                receptionistService.append(
                    "RECEPTION",
                    "PHONE // "
                    + specialistId
                    + " // NOT FOUND IN LIVE REGISTRY"
                );
            return;
        }

        if (source === "intercom") {
            if (!root.intercomMenuOpen)
                root.toggleIntercomMenu();

            const focused =
                intercomDropdown.focusActivityContext(
                    specialistId,
                    context.channelType,
                    context.channelLabel
                );

            if (specialistId && !focused)
                receptionistService.append(
                    "RECEPTION",
                    "INTERCOM // "
                    + specialistId
                    + " // NOT FOUND IN LIVE REGISTRY"
                );
            return;
        }

        if (row.route)
            root.handleReceptionRoute(row.route);
    }

    function roundsRoomForTeam(teamValue) {
        const wanted =
            String(teamValue || "").trim().toUpperCase();
        const rooms =
            Array.isArray(roundsService.rooms)
            ? roundsService.rooms
            : [];

        if (!wanted)
            return null;

        for (let i = 0; i < rooms.length; ++i) {
            const room = rooms[i] || {};
            const candidate =
                String(room.team || room.branch || "")
                    .trim()
                    .toUpperCase();

            if (candidate === wanted)
                return room;
        }

        return null;
    }

    function finishPendingReceptionTeam() {
        const team =
            String(root.pendingReceptionTeam || "")
                .trim()
                .toUpperCase();

        if (!team)
            return false;

        const room = root.roundsRoomForTeam(team);

        root.pendingReceptionTeam = "";

        if (!room) {
            receptionistService.append(
                "RECEPTION",
                "ROOM // "
                + team
                + " // NOT FOUND IN LIVE ROUNDS"
            );
            return false;
        }

        root.openRoomFromRounds(room);
        return true;
    }

    function requestReceptionTeamNavigation(teamValue) {
        const team =
            String(teamValue || "").trim().toUpperCase();

        if (!team)
            return false;

        const room = root.roundsRoomForTeam(team);

        if (room) {
            root.pendingReceptionTeam = "";
            root.openRoomFromRounds(room);
            return true;
        }

        root.pendingReceptionTeam = team;

        if (roundsService.running)
            return true;

        const started = roundsService.refresh();

        if (!started) {
            root.pendingReceptionTeam = "";
            receptionistService.append(
                "RECEPTION",
                "ROOM // "
                + team
                + " // LIVE ROUNDS UNAVAILABLE"
            );
            return false;
        }

        return true;
    }

    function togglePhoneMenu() {
        root.phoneMenuOpen = !root.phoneMenuOpen;

        if (root.phoneMenuOpen) {
            root.intercomMenuOpen = false;
            root.intercomTyping = false;
        }

        if (root.phoneMenuOpen
                && specialistRegistryService.loaded
                && !specialistRegistryService.probing)
            specialistRegistryService.refreshPresence();
    }

    function toggleIntercomMenu() {
        root.intercomMenuOpen = !root.intercomMenuOpen;

        if (root.intercomMenuOpen)
            root.phoneMenuOpen = false;
        else
            root.intercomTyping = false;

        if (root.intercomMenuOpen
                && specialistRegistryService.loaded
                && !specialistRegistryService.probing)
            specialistRegistryService.refreshPresence();
    }

    function openReports(teamValue) {
        receptionistService.endVisit();
        root.leaveRoomControls();
        root.leaveBedControls();

        const requestedTeam = String(teamValue || "");

        reportsView.teamFilter =
            requestedTeam
            ? requestedTeam
            : root.selectedRoomTeam;
        reportsView.stateFilter = "";
        root.operationsSurface = "reports";
    }

    function openRounds() {
        receptionistService.endVisit();
        root.leaveRoomControls();
        root.leaveBedControls();
        root.operationsSurface = "rounds";

        if (!roundsService.running)
            roundsService.refresh();
    }

    function openStaff() {
        receptionistService.endVisit();
        root.leaveRoomControls();
        root.leaveBedControls();
        root.operationsSurface = "staff";

        if (specialistRegistryService.loaded
                && !specialistRegistryService.probing)
            specialistRegistryService.refreshPresence();
    }

    function resolvePendingRoundsRoom() {
        const team = String(root.pendingRoundsRoomTeam || "");

        if (!team)
            return false;

        if (root.pendingRoundsFloorIndex >= 0
                && root.pendingRoundsFloorIndex
                   !== floorService.selectedFloorIndex)
            return false;

        const index = root.roomIndexOfTeam(team);

        if (index < 0)
            return false;

        root.selectRoomIndex(index);
        root.pendingRoundsRoomTeam = "";
        root.pendingRoundsFloorIndex = -1;
        root.scheduleRoomEntryAudit(team);
        return true;
    }

    function openRoomFromRounds(room) {
        const row = room || {};
        const team = String(row.team || "");
        const floorIndex = Number(row.floorIndex);

        if (!team)
            return;

        hospitalContextService.captureRoom(row);
        root.closeOperationsSurface();
        root.pendingRoundsRoomTeam = team;
        root.pendingRoundsFloorIndex =
            Number.isFinite(floorIndex) ? floorIndex : -1;

        if (root.pendingRoundsFloorIndex >= 0
                && root.pendingRoundsFloorIndex
                   !== floorService.selectedFloorIndex) {
            if (root.floorSwitchEnabled)
                root.selectFloor(root.pendingRoundsFloorIndex);
            return;
        }

        if (!root.resolvePendingRoundsRoom()
                && !auditService.running)
            auditService.runAudit(false);
    }

    function open() {
        root.keyboardOwnershipRequested();
        root.operationsSurface = "reception";
        root.menuOpen = true;
        root.refreshReceptionData();
        receptionistService.beginVisit();
    }

    function close() {
        receptionistService.endVisit();
        root.phoneMenuOpen = false;
        root.intercomMenuOpen = false;
        root.intercomTyping = false;
        root.receptionistTyping = false;
        root.pendingReceptionRoundsSelection = null;
        root.operationsSurface = "";
        root.menuOpen = false;
    }

    function toggle() {
        if (root.menuOpen)
            root.close();
        else
            root.open();
    }

    function requestOpenAudit() {
        openAuditPending = true;
        maybeRunOpenAudit();
    }

    function maybeRunOpenAudit() {
        if (!openAuditPending
                || !menuOpen
                || floorService.discovering
                || auditService.running)
            return;

        const key = String(floorService.floorId || "");
        const repo = String(auditService.repository || "");

        if (!key || !repo)
            return;

        const stamps = lastOpenAuditByFloor;
        const last = Number(stamps[key] || 0);
        const now = Date.now();

        if (last > 0 && now - last < openAuditStaleInterval) {
            openAuditPending = false;
            return;
        }

        stamps[key] = now;
        lastOpenAuditByFloor = stamps;
        openAuditPending = false;

        // First open after a Quickshell restart, or an open after the stale
        // window, gets one shared freshness pass. Audit and GitHub use the
        // same per-Floor timestamp, so they run together or not at all.
        auditService.runAudit(false);
        githubService.refresh();
    }

    onOperationsSurfaceChanged: {
        if (root.operationsSurface !== "reception"
                && speechInputService.busy)
            speechInputService.cancel();
    }

    onMenuOpenChanged: {
        if (!root.menuOpen) {
            if (speechInputService.busy)
                speechInputService.cancel();

            if (intercomSpeechInputService.busy)
                intercomSpeechInputService.cancel();

            root.leaveRoomControls();
            root.leaveBedControls();
            return;
        }

        Qt.callLater(function() {
            if (!root.menuOpen || !root.keyboardActive)
                return;

            keyboardFocusAnchor.forceActiveFocus();
        });

        root.ensureFirstRoomSelected();
        root.requestOpenAudit();
        floorService.discover();
    }

    onKeyboardActiveChanged: {
        if (!root.menuOpen || !root.keyboardActive)
            return;

        Qt.callLater(function() {
            if (!root.menuOpen || !root.keyboardActive)
                return;

            keyboardFocusAnchor.forceActiveFocus();
        });
    }

    Component.onCompleted: {
        certificationCoordinator.bindRoom(roomService);
    }

    Timer {
        id: openAuditKick
        interval: 75
        repeat: false
        onTriggered: root.maybeRunOpenAudit()
    }

    HospitalFloorService {
        id: floorService
        preferredFloorQuery: "taskbars-post-apollo"

        onFloorChanged: {
            root.selectedCommitSha = "";
            root.selectedRoomTeam = "";
            roomService.clearResult();
            certificationCoordinator.bindRoom(roomService);
            auditService.resetResult();

            if (root.menuOpen) {
                root.openAuditPending = true;
                openAuditKick.restart();
            }
        }

        onFloorsChanged: {
            if (root.menuOpen)
                openAuditKick.restart();
        }

        onBedChanged: {
            root.selectedCommitSha = "";
            roomService.clearResult();
            certificationCoordinator.bindRoom(roomService);
            patientService.refresh();
        }
    }

    HospitalRoundsService {
        id: roundsService
        floorService: floorService
    }

    HospitalSpecialistRegistryService {
        id: specialistRegistryService
    }

    HospitalPhoneService {
        id: phoneService
        registryService: specialistRegistryService
    }

    HospitalIntercomService {
        id: intercomService
        registryService: specialistRegistryService
    }

    HospitalReceptionistService {
        id: receptionistService
    }

    HospitalContextService {
        id: hospitalContextService
    }

    HospitalSpeechInputService {
        id: speechInputService

        onVoiceError: function(message) {
            receptionistService.append(
                "RECEPTION",
                String(message || "VOICE INPUT ERROR")
            );
        }
    }

    HospitalSpeechInputService {
        id: intercomSpeechInputService
        audioFileName: "hospital-intercom-voice.wav"
    }

    HospitalRemoteWatcher {
        id: remoteWatcher
        repoPath: floorService.bedPath
        floorKey: floorService.floorId
        active:
            root.menuOpen
            && floorService.bedPath.length > 0
            && !floorService.moveRunning
            && !floorService.liveMoveArmed
            && !roomService.integrating
            && !roomService.postOpRunning

        onRemoteSnapshotReady: function(changed) {
            // Remote refs changed (or this is the first baseline for the
            // Quickshell session). Refresh local topology only after fetch.
            root.remoteRefreshPending = true;
            patientService.refresh();
        }

        onRemoteCheckCompleted: function(refsChanged) {
            // Every later freshness check also performs a quiet PX audit.
            // If the visible first-open audit is still running, runAudit()
            // simply refuses the duplicate request.
            auditService.runAudit(true);
        }
    }

    GitService {
        id: hospitalEvidenceGitService
        repoPath: patientService.repoRoot
        repoLabel: "HOSPITAL PATIENT"
    }

    HospitalService {
        id: patientService
        repoPath: floorService.bedPath
    }

    GitHubService {
        id: githubService
        // Floor discovery already knows the remote identity before the async
        // patient refresh finishes. Using it here removes the first-open race
        // where the watcher could request an audit before repoSlug existed.
        originUrl: floorService.floorOrigin
    }

    HospitalAuditService {
        id: auditService
        repository: githubService.repoSlug
    }

    HospitalRoomService {
        id: roomService
        repository: githubService.repoSlug
        team: root.selectedRoomTeam
        localRepoPath: patientService.repoRoot
    }

    HospitalRoomPresenceService {
        id: roomPresenceService
        repoPath: floorService.bedPath
        branchName: root.selectedRoomBranch
    }

    GitEvidenceProvider {
        id: gitEvidenceProvider
        gitService: hospitalEvidenceGitService
        githubService: githubService
    }

    HospitalCertificationCoordinator {
        id: certificationCoordinator
        evidenceProvider: gitEvidenceProvider
    }

    Connections {
        target: receptionistService

        function onActivityHydratedChanged() {
            if (receptionistService.activityHydrated)
                root.syncReceptionistActivity();
        }

        function onActivityActionRequested(item) {
            root.activateReceptionActivity(item);
        }

        function onTeamNavigationRequested(team) {
            root.requestReceptionTeamNavigation(team);
        }

        function onContextEventKeyChanged() {
            Qt.callLater(function() {
                root.syncHospitalContextFromReception("");
            });
        }

        function onContextTargetChanged() {
            Qt.callLater(function() {
                root.syncHospitalContextFromReception("");
            });
        }

        function onSpecialistHandoffRequested(
                mode,
                operatorText) {
            root.requestReceptionSpecialistHandoff(
                mode,
                operatorText
            );
        }
    }

    Connections {
        target: specialistRegistryService

        function onRegistryLoaded() {
            receptionistService.syncStaff(
                specialistRegistryService.specialists
            );

            if ((root.operationsSurface === "staff"
                    || root.operationsSurface === "reception"
                    || root.phoneMenuOpen
                    || root.intercomMenuOpen)
                    && !specialistRegistryService.probing)
                specialistRegistryService.refreshPresence();
        }

        function onPresenceRefreshed() {
            receptionistService.syncStaff(
                specialistRegistryService.specialists
            );
        }
    }

    Connections {
        target: roundsService

        function onRefreshed() {
            receptionistService.syncRounds(roundsService.rooms);

            if (root.pendingReceptionTeam)
                root.finishPendingReceptionTeam();

            if (root.pendingReceptionRoundsSelection)
                root.finishPendingReceptionRoundsSelection(true);
        }
    }

    Connections {
        target: phoneService

        function onCallLaunched(specialist) {
            receptionistService.recordPhoneCall(specialist);
        }
    }

    Connections {
        target: intercomService

        function onMessageLaunched(entry) {
            receptionistService.recordIntercomMessage(entry);
        }
    }

    Connections {
        target: certificationCoordinator.historyService
        ignoreUnknownSignals: true

        function onEventsChanged() {
            receptionistService.syncReports(
                certificationCoordinator.historyService.events
            );
        }

        function onEventRecorded(event) {
            receptionistService.recordReportEvent(event);
        }
    }

    Connections {
        target: patientService

        function onRefreshed() {
            roomPresenceService.refresh();

            if (!root.remoteRefreshPending)
                return;

            root.remoteRefreshPending = false;
            githubService.refresh();
        }
    }

    Connections {
        target: roomService

        function onPostOpFinished() {
            patientService.refresh();
        }
    }

    Connections {
        target: auditService

        function onAudited() {
            // Capture ownership before auto-selecting a Room. Otherwise the
            // first Room can start its own audit inside this callback and the
            // just-finished Floor audit would be mistaken for that Room audit.
            const candidate = String(root.roomAuditInFlightTeam || "");

            if (candidate) {
                root.roomAuditInFlightTeam = "";

                if (root.selectedRoomTeam === candidate) {
                    root.auditedRoomTeam = candidate;
                    root.pendingRoomAuditTeam = "";
                    return;
                }

                // The operator can move to another Room while this audit is
                // finishing. Immediately hand the audit lane to the newest Room.
                if (root.pendingRoomAuditTeam
                        && root.pendingRoomAuditTeam === root.selectedRoomTeam)
                    root.runPendingRoomAudit();

                return;
            }

            if (!root.resolvePendingRoundsRoom())
                root.ensureFirstRoomSelected();
        }

        function onRunningChanged() {
            if (auditService.running)
                return;

            // A failed Room-entry audit does not count as fresh.
            if (root.roomAuditInFlightTeam && auditService.lastError)
                root.roomAuditInFlightTeam = "";

            // If Room entry happened while another audit was running, launch
            // the queued Room audit immediately when that audit releases.
            if (!root.roomAuditInFlightTeam
                    && root.pendingRoomAuditTeam
                    && root.pendingRoomAuditTeam === root.selectedRoomTeam)
                root.runPendingRoomAudit();
        }
    }

    component HospitalModeTab: Rectangle {
        id: modeTab

        property string label: ""
        property bool selected: false

        signal triggered()

        readonly property bool hovered: modeTabMouse.containsMouse
        readonly property bool pressed: modeTabMouse.pressed

        height: 36
        color:
            pressed
            ? Colors.magenta
            : hovered || selected
            ? Colors.yellow
            : Colors.black
        border.width: 1
        border.color:
            pressed
            ? Colors.magenta
            : hovered || selected
            ? Colors.orange
            : Colors.cyan

        GohuText {
            anchors.centerIn: parent
            text: modeTab.label
            font.pixelSize: 12
            color:
                modeTab.pressed
                ? Colors.black
                : modeTab.selected
                ? Colors.magenta
                : modeTab.hovered
                ? Colors.orange
                : Colors.cyan

            layer.enabled: !modeTab.pressed
            layer.effect: DropShadow {
                radius: 10
                samples: 11
                opacity:
                    modeTab.hovered
                    ? 0.64
                    : modeTab.selected
                    ? 0.60
                    : 0.34
                color:
                    modeTab.selected
                    ? Colors.magenta
                    : modeTab.hovered
                    ? Colors.orange
                    : Colors.cyan
                transparentBorder: true
            }
        }

        MouseArea {
            id: modeTabMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: modeTab.triggered()
        }
    }

    component SectionLabel: GohuText {
        font.pixelSize: 12
        color: Colors.magenta

        layer.enabled: true
        layer.effect: DropShadow {
            radius: 6
            samples: 7
            opacity: 0.46
            color: Colors.magenta
            transparentBorder: true
        }
    }

    component MetaLabel: GohuText {
        font.pixelSize: 10
        color: Colors.cyan

        layer.enabled: true
        layer.effect: DropShadow {
            radius: 4
            samples: 5
            opacity: 0.28
            color: Colors.cyan
            transparentBorder: true
        }
    }

    component MetaValue: GohuText {
        font.pixelSize: 11
        color: Colors.white
        elide: Text.ElideRight

        layer.enabled: true
        layer.effect: DropShadow {
            radius: 5
            samples: 7
            opacity: 0.10
            color: Colors.cyan
            transparentBorder: true
        }
    }

    component OrangeLabel: GohuText {
        font.pixelSize: 10
        color: Colors.orange

        layer.enabled: true
        layer.effect: DropShadow {
            radius: 5
            samples: 7
            opacity: 0.38
            color: Colors.orange
            transparentBorder: true
        }
    }

    component CyanValue: GohuText {
        font.pixelSize: 11
        color: Colors.cyan
        elide: Text.ElideRight

        layer.enabled: true
        layer.effect: DropShadow {
            radius: 5
            samples: 7
            opacity: 0.30
            color: Colors.cyan
            transparentBorder: true
        }
    }

    component BlueValue: GohuText {
        font.pixelSize: 11
        color: Colors.blue
        elide: Text.ElideRight

        layer.enabled: true
        layer.effect: DropShadow {
            radius: 7
            samples: 9
            opacity: 0.48
            color: Colors.cyan
            transparentBorder: true
        }
    }

    component RoomRow: Rectangle {
        id: roomRow

        property string team: ""
        property string responsibility: ""
        property string stateText: auditService.roomLabel(roomRow.team)
        readonly property string telemetryState:
            auditService.roomState(roomRow.team)
        readonly property color stateColor:
            telemetryState === "MISSING"
            ? Colors.red
            : telemetryState === "IN_MAIN"
              || telemetryState === "AT_MAIN"
            ? Colors.orange
            : telemetryState === "DIVERGED"
            ? Colors.magenta
            : Colors.cyan

        readonly property bool selected:
            root.selectedRoomTeam === roomRow.team

        width: roomsColumn.width
        height: 54

        color: Colors.dark
        border.width: selected ? 2 : 1
        border.color: selected ? Colors.orange : Colors.magenta

        RectangularShadow {
            anchors.fill: parent
            spread: selected ? 5 : 3
            z: -1
            opacity: selected ? 0.42 : 0.28
            color: selected ? Colors.orange : Colors.magenta
        }

        GohuText {
            anchors {
                left: parent.left
                right: roomStateText.left
                top: parent.top
                leftMargin: 12
                rightMargin: 10
                topMargin: 7
            }

            text: roomRow.team
            font.pixelSize: 13
            color: Colors.orange
            elide: Text.ElideRight

            layer.enabled: true
            layer.effect: DropShadow {
                radius: 5
                samples: 7
                opacity: 0.34
                color: Colors.orange
                transparentBorder: true
            }
        }

        GohuText {
            anchors {
                left: parent.left
                right: roomStateText.left
                bottom: parent.bottom
                leftMargin: 12
                rightMargin: 10
                bottomMargin: 7
            }

            text: roomRow.responsibility
            font.pixelSize: 9
            color: Colors.cyan
            elide: Text.ElideRight

            layer.enabled: true
            layer.effect: DropShadow {
                radius: 5
                samples: 7
                opacity: 0.10
                color: Colors.cyan
                transparentBorder: true
            }
        }

        GohuText {
            id: roomStateText

            anchors {
                right: parent.right
                verticalCenter: parent.verticalCenter
                rightMargin: 10
            }

            width: 105
            horizontalAlignment: Text.AlignRight
            text: roomRow.stateText
            font.pixelSize: 9
            color: roomRow.stateColor
            opacity: roomRow.telemetryState === "WAITING" ? 0.58 : 1.0

            layer.enabled: true
            layer.effect: DropShadow {
                radius: 5
                samples: 7
                opacity: roomRow.telemetryState === "WAITING" ? 0.14 : 0.38
                color: roomRow.stateColor
                transparentBorder: true
            }
        }

        MouseArea {
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor

            onClicked: root.toggleRoomSelection(roomRow.team)
        }
    }

    // Main chassis glow: exact AppControl / CPU++ structural recipe.
    // The surface has a transparent gutter so the outer glow is not clipped.
    Rectangle {
        id: chassisGeometry

        width: root.panelWidth
        height: root.panelHeight
        anchors.top: parent.top
        anchors.topMargin: root.topGlowGutter
        anchors.horizontalCenter: parent.horizontalCenter

        color: "transparent"
        opacity: root.menuOpen ? 1.0 : 0.0
    }

    RectangularShadow {
        anchors.fill: chassisGeometry
        spread: 6
        z: -20
        opacity: root.menuOpen ? 0.21 : 0.0
        color: Colors.magenta
    }

    RectangularShadow {
        anchors.fill: chassisGeometry
        spread: 12
        z: -21
        opacity: root.menuOpen ? 0.05 : 0.0
        color: Colors.magenta
    }

    Rectangle {
        id: frame

        width: root.panelWidth
        height: root.panelHeight
        anchors.top: parent.top
        anchors.topMargin: root.topGlowGutter
        anchors.horizontalCenter: parent.horizontalCenter

        color: Colors.black
        opacity: root.menuOpen ? 0.97 : 0.0

        border.width: 1
        border.color: Colors.magenta

        HoverHandler {
            enabled: root.menuOpen

            onHoveredChanged: {
                if (hovered && !root.keyboardActive)
                    root.keyboardOwnershipRequested();
            }
        }

        Rectangle {
            id: innerFrame

            anchors.fill: parent
            anchors.margins: root.frameInset

            color: "transparent"
            border.width: 1
            border.color: Colors.cyan
            opacity: 0.70
        }

        Rectangle {
            id: bottomStop

            height: 2
            anchors {
                left: parent.left
                right: parent.right
                bottom: parent.bottom
                leftMargin: root.frameInset
                rightMargin: root.frameInset
                bottomMargin: root.frameInset
            }

            color: Colors.cyan
            opacity: 1.0

            RectangularShadow {
                anchors.fill: parent
                spread: 3
                z: -1
                opacity: 0.34
                color: Colors.cyan
            }
        }

        // Persistent floor selector. This reuses the same tactile slider
        // component as the Git panel, but selects repositories instead of remotes.
        SelectorSlider {
            id: floorSlider

            visible: !root.operationsOpen
            z: 300
            anchors {
                left: parent.left
                leftMargin: 18
                top: parent.top
                // Align the floor rail with the top edge of the
                // FLOOR // REPOSITORY box and the bottom of the action bay.
                topMargin: 100
                bottom: parent.bottom
                bottomMargin: 18
            }

            count: floorService.floorCount
            currentIndex: floorService.selectedFloorIndex
            accentColor: Colors.cyan
            handleGlowColor: Colors.magenta
            sideLabel: "FLOOR"
            enabledSlider: root.floorSwitchEnabled

            onIndexRequested: function(index) {
                root.selectFloor(index);
            }
        }

        // Fixed diagnostic/header zone. Nothing above OPERATING ROOMS scrolls.
        Column {
            id: fixedTop

            anchors {
                top: parent.top
                left: parent.left
                right: parent.right
                topMargin: 18
                leftMargin:
                    root.operationsOpen ? 18 : 62
                rightMargin: 18
            }

            spacing: 12

            // ===== HEADER =======================================

            Item {
                id: hospitalHeader

                // Header spans back across the floor-selector lane.
                x: root.operationsOpen ? 0 : -44
                width:
                    parent.width
                    + (root.operationsOpen ? 0 : 44)
                height: 56

                GohuText {
                    anchors {
                        left: parent.left
                        top: parent.top
                    }

                    text:
                        root.operationsSurface === "reception"
                        ? "HOSPITAL // RECEPTION"
                        : root.operationsSurface === "reports"
                        ? "HOSPITAL // REPORTS"
                        : root.operationsSurface === "rounds"
                        ? "HOSPITAL // ROUNDS"
                        : root.operationsSurface === "staff"
                        ? "HOSPITAL // STAFF"
                        : "HOSPITAL // SURGERY ROOM"
                    font.pixelSize: 20
                    color: Colors.magenta

                    layer.enabled: true
                    layer.effect: DropShadow {
                        radius: 8
                        samples: 9
                        opacity: 0.52
                        color: Colors.magenta
                        transparentBorder: true
                    }
                }

                GohuText {
                    anchors {
                        left: parent.left
                        bottom: parent.bottom
                    }

                    text:
                        root.operationsSurface === "reception"
                        ? "FRONT DESK // COORDINATION"
                        : root.operationsSurface === "reports"
                        ? "SURGICAL HISTORY // EVIDENCE"
                        : root.operationsSurface === "rounds"
                        ? "HOSPITAL-WIDE // ATTENTION"
                        : root.operationsSurface === "staff"
                        ? "SPECIALISTS // PRESENCE"
                        : "CONTROL SURFACE // LOCAL PATIENT"
                    font.pixelSize: 10
                    color: Colors.cyan

                    layer.enabled: true
                    layer.effect: DropShadow {
                        radius: 6
                        samples: 7
                        opacity: 0.40
                        color: Colors.cyan
                        transparentBorder: true
                    }
                }

                Row {
                    id: hospitalHeaderActions

                    anchors {
                        right: parent.right
                        verticalCenter: parent.verticalCenter
                    }

                    spacing: 8

                    Rectangle {
                        id: intercomButton

                        width: 40
                        height: 34
                        anchors.verticalCenter: parent.verticalCenter

                        color:
                            intercomMouse.pressed
                            ? Colors.black
                            : root.intercomMenuOpen
                            ? Colors.yellow
                            : Colors.dark
                        border.width: 1
                        border.color:
                            root.intercomMenuOpen
                            ? Colors.magenta
                            : intercomMouse.containsMouse
                            ? Colors.orange
                            : Colors.omnitrix

                        RectangularShadow {
                            anchors.fill: parent
                            spread: 4
                            z: -1
                            opacity:
                                root.intercomMenuOpen
                                ? 0.54
                                : intercomMouse.containsMouse
                                ? 0.46
                                : 0.28
                            color:
                                root.intercomMenuOpen
                                ? Colors.magenta
                                : intercomMouse.containsMouse
                                ? Colors.orange
                                : Colors.omnitrix
                        }

                        GohuText {
                            anchors.centerIn: parent
                            anchors.verticalCenterOffset: 1
                            width: parent.width
                            height: parent.height
                            text: "🎙︎"
                            font.pixelSize: 23
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            color:
                                intercomMouse.pressed
                                ? Colors.black
                                : root.intercomMenuOpen
                                ? Colors.magenta
                                : intercomMouse.containsMouse
                                ? Colors.orange
                                : Colors.omnitrix

                            layer.enabled: !intercomMouse.pressed
                            layer.effect: DropShadow {
                                radius: 7
                                samples: 9
                                opacity: 0.52
                                color:
                                    root.intercomMenuOpen
                                    ? Colors.magenta
                                    : intercomMouse.containsMouse
                                    ? Colors.orange
                                    : Colors.omnitrix
                                transparentBorder: true
                            }
                        }

                        MouseArea {
                            id: intercomMouse

                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor

                            onClicked: root.toggleIntercomMenu()
                        }
                    }

                    Rectangle {
                        id: phoneButton

                        width: 40
                        height: 34
                        anchors.verticalCenter: parent.verticalCenter

                        color:
                            phoneMouse.pressed
                            ? Colors.black
                            : root.phoneMenuOpen
                            ? Colors.yellow
                            : Colors.dark
                        border.width: 1
                        border.color:
                            root.phoneMenuOpen
                            ? Colors.magenta
                            : phoneMouse.containsMouse
                            ? Colors.orange
                            : Colors.green

                        RectangularShadow {
                            anchors.fill: parent
                            spread: 4
                            z: -1
                            opacity:
                                root.phoneMenuOpen
                                ? 0.54
                                : phoneMouse.containsMouse
                                ? 0.46
                                : 0.28
                            color:
                                root.phoneMenuOpen
                                ? Colors.magenta
                                : phoneMouse.containsMouse
                                ? Colors.orange
                                : Colors.green
                        }

                        GohuText {
                            anchors.centerIn: parent
                            width: parent.width
                            height: parent.height
                            text: "☎︎"
                            font.pixelSize: 25
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            color:
                                phoneMouse.pressed
                                ? Colors.black
                                : root.phoneMenuOpen
                                ? Colors.magenta
                                : phoneMouse.containsMouse
                                ? Colors.orange
                                : Colors.green

                            layer.enabled: !phoneMouse.pressed
                            layer.effect: DropShadow {
                                radius: 7
                                samples: 9
                                opacity: 0.52
                                color:
                                    root.phoneMenuOpen
                                    ? Colors.magenta
                                    : phoneMouse.containsMouse
                                    ? Colors.orange
                                    : Colors.green
                                transparentBorder: true
                            }
                        }

                        MouseArea {
                            id: phoneMouse

                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor

                            onClicked: root.togglePhoneMenu()
                        }
                    }

                    Rectangle {
                        width: 86
                        height: 26
                        anchors.verticalCenter: parent.verticalCenter

                        color: Colors.dark
                        border.width: 1
                        border.color: Colors.magenta

                        RectangularShadow {
                            anchors.fill: parent
                            spread: 3
                            z: -1
                            opacity: 0.38
                            color: Colors.magenta
                        }

                        GohuText {
                            id: hospitalLocalStatusText

                            anchors.centerIn: parent
                            text:
                                root.operationsSurface === "reception"
                                ? "DESK OPEN"
                                : root.operationsSurface === "reports"
                                ? (
                                    "REPORTS "
                                    + String(
                                        reportsView.filteredEvents.length
                                    )
                                  )
                                : root.operationsSurface === "rounds"
                                ? (
                                    roundsService.running
                                    ? "ROUNDING"
                                    : roundsService.attentionCount > 0
                                    ? "ATTN "
                                      + String(
                                          roundsService.attentionCount
                                      )
                                    : "CLEAR"
                                  )
                                : root.operationsSurface === "staff"
                                ? (
                                    specialistRegistryService.probing
                                    ? "CHECKING"
                                    : "READY "
                                      + String(
                                          specialistRegistryService
                                              .readyCount
                                      )
                                      + "/"
                                      + String(
                                          specialistRegistryService
                                              .specialistCount
                                      )
                                  )
                                : floorService.bedIsLive
                                ? "LOCAL LIVE"
                                : floorService.bedPath.length > 0
                                ? "LOCAL BED"
                                : "OFFLINE"
                            font.pixelSize: 9
                            color:
                                root.operationsSurface === "reception"
                                ? Colors.green
                                : root.operationsSurface === "reports"
                                ? Colors.magenta
                                : root.operationsSurface === "rounds"
                                ? (
                                    roundsService.attentionCount > 0
                                    ? Colors.orange
                                    : Colors.cyan
                                  )
                                : root.operationsSurface === "staff"
                                ? (
                                    specialistRegistryService.lastError
                                    ? Colors.red
                                    : specialistRegistryService.readyCount > 0
                                    ? Colors.green
                                    : Colors.orange
                                  )
                                : floorService.bedIsLive
                                ? Colors.magenta
                                : floorService.bedPath.length > 0
                                ? Colors.cyan
                                : Colors.red

                            layer.enabled: true
                            layer.effect: DropShadow {
                                radius: 10
                                samples: 11
                                opacity:
                                    root.operationsOpen
                                    ? 0.82
                                    : floorService.bedPath.length > 0
                                    ? 0.82
                                    : 0.44
                                color: hospitalLocalStatusText.color
                                transparentBorder: true
                            }
                        }
                    }

                    Rectangle {
                        id: hospitalCloseButton

                        width: 40
                        height: 34
                        anchors.verticalCenter: parent.verticalCenter

                        color:
                            hospitalCloseMouse.pressed
                            ? Colors.black
                            : Colors.dark
                        border.width: 1
                        border.color:
                            hospitalCloseMouse.pressed
                            ? Colors.black
                            : Colors.red

                        RectangularShadow {
                            anchors.fill: parent
                            spread: 4
                            z: -1
                            opacity:
                                hospitalCloseMouse.containsMouse
                                ? 0.58
                                : 0.38
                            color:
                                hospitalCloseMouse.pressed
                                ? Colors.black
                                : Colors.red
                        }

                        NotoText {
                            anchors.centerIn: parent
                            anchors.verticalCenterOffset: 2
                            text: "×"
                            font.pixelSize: 31
                            color: Colors.red

                            layer.enabled: true
                            layer.effect: DropShadow {
                                radius: 7
                                samples: 9
                                opacity: 0.58
                                color: Colors.red
                                transparentBorder: true
                            }
                        }

                        MouseArea {
                            id: hospitalCloseMouse

                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor

                            onClicked: root.close()
                        }
                    }
                }
            }

            Rectangle {
                // Header rule spans the full Hospital chassis, including
                // the floor-selector lane.
                x: root.operationsOpen ? 0 : -44
                width:
                    parent.width
                    + (root.operationsOpen ? 0 : 44)
                height: 2
                color: Colors.cyan

                RectangularShadow {
                    anchors.fill: parent
                    spread: 3
                    z: -1
                    opacity: 0.34
                    color: Colors.cyan
                }
            }


            Row {
                id: hospitalModeTabs

                width: parent.width
                height: 36
                spacing: 10

                HospitalModeTab {
                    width: (parent.width - 40) / 5
                    label: "RECEPTION"
                    selected: root.operationsSurface === "reception"
                    onTriggered: root.openReception()
                }

                HospitalModeTab {
                    width: (parent.width - 40) / 5
                    label: "SURGERY"
                    selected: !root.operationsOpen
                    onTriggered: root.showSurgery()
                }

                HospitalModeTab {
                    width: (parent.width - 40) / 5
                    label: "REPORTS"
                    selected: root.operationsSurface === "reports"
                    onTriggered: root.openReports()
                }

                HospitalModeTab {
                    width: (parent.width - 40) / 5
                    label: "ROUNDS"
                    selected: root.operationsSurface === "rounds"
                    onTriggered: root.openRounds()
                }

                HospitalModeTab {
                    width: (parent.width - 40) / 5
                    label: "STAFF"
                    selected: root.operationsSurface === "staff"
                    onTriggered: root.openStaff()
                }
            }

            Rectangle {
                id: departmentContextStrip

                width: parent.width
                height: 44
                visible: root.operationsOpen
                color: Colors.dark
                border.width: 1
                border.color:
                    root.operationsSurface === "reception"
                    ? Colors.green
                    : root.operationsSurface === "reports"
                    ? Colors.magenta
                    : root.operationsSurface === "staff"
                    ? Colors.orange
                    : Colors.cyan

                RectangularShadow {
                    anchors.fill: parent
                    spread: 3
                    z: -1
                    opacity: 0.22
                    color:
                        root.operationsSurface === "reception"
                        ? Colors.green
                        : root.operationsSurface === "reports"
                        ? Colors.magenta
                        : root.operationsSurface === "staff"
                        ? Colors.orange
                        : Colors.cyan
                }

                Row {
                    anchors {
                        fill: parent
                        margins: 8
                    }
                    spacing: 12

                    GohuText {
                        width: 138
                        anchors.verticalCenter: parent.verticalCenter
                        text:
                            root.operationsSurface === "reception"
                            ? "RECEPTION // DESK"
                            : root.operationsSurface === "reports"
                            ? "REPORTS // CONTEXT"
                            : root.operationsSurface === "staff"
                            ? "STAFF // PRESENCE"
                            : "ROUNDS // HOSPITAL-WIDE"
                        font.pixelSize: 12
                        color:
                            root.operationsSurface === "reception"
                            ? Colors.green
                            : root.operationsSurface === "reports"
                            ? Colors.magenta
                            : root.operationsSurface === "staff"
                            ? Colors.orange
                            : Colors.cyan
                        elide: Text.ElideRight
                    }

                    GohuText {
                        width: parent.width - 150
                        anchors.verticalCenter: parent.verticalCenter
                        text:
                            root.operationsSurface === "reception"
                            ? (
                                "FLOOR "
                                + (floorService.floorLabel || "UNKNOWN")
                                + "  //  ROOM "
                                + (root.selectedRoomTeam || "NONE")
                                + "  //  STAFF READY "
                                + String(specialistRegistryService.readyCount)
                                + "/"
                                + String(specialistRegistryService.specialistCount)
                              )
                            : root.operationsSurface === "reports"
                            ? (
                                "FLOOR "
                                + (
                                    floorService.floorLabel
                                    || "UNKNOWN"
                                  )
                                + "  //  ROOM "
                                + (
                                    reportsView.teamFilter
                                    || "ALL"
                                  )
                                + "  //  VISIBLE "
                                + String(
                                    reportsView.filteredEvents.length
                                  )
                                + " / "
                                + String(
                                    certificationCoordinator.historyService
                                    && Array.isArray(
                                        certificationCoordinator
                                            .historyService.events
                                    )
                                    ? certificationCoordinator
                                        .historyService.events.length
                                    : 0
                                  )
                              )
                            : root.operationsSurface === "staff"
                            ? (
                                "SPECIALISTS "
                                + String(
                                    specialistRegistryService
                                        .specialistCount
                                  )
                                + "  //  READY "
                                + String(
                                    specialistRegistryService.readyCount
                                  )
                                + "  //  OFFLINE "
                                + String(
                                    specialistRegistryService.offlineCount
                                  )
                                + "  //  CALLABLE "
                                + String(
                                    specialistRegistryService.callableCount
                                  )
                              )
                            : (
                                "FLOORS "
                                + String(roundsService.floorCount)
                                + "  //  ROOMS "
                                + String(roundsService.roomCount)
                                + "  //  ATTENTION "
                                + String(roundsService.attentionCount)
                                + "  //  DIVERGED "
                                + String(roundsService.divergedCount)
                                + "  //  MISSING "
                                + String(roundsService.missingCount)
                              )
                        font.pixelSize: 11
                        color:
                            root.operationsSurface === "reception"
                            ? Colors.white
                            : root.operationsSurface === "reports"
                            ? Colors.white
                            : root.operationsSurface === "staff"
                            ? (
                                specialistRegistryService.lastError
                                ? Colors.red
                                : specialistRegistryService.probing
                                ? Colors.orange
                                : specialistRegistryService
                                    .callableCount > 0
                                ? Colors.green
                                : Colors.white
                              )
                            : roundsService.attentionCount > 0
                            ? Colors.orange
                            : Colors.white
                        elide: Text.ElideRight

                        layer.enabled:
                            root.operationsSurface === "reception"
                        layer.effect: DropShadow {
                            radius: 7
                            samples: 9
                            opacity: 0.52
                            color: Colors.cyan
                            transparentBorder: true
                        }
                    }
                }
            }

            // ===== FLOOR / REPOSITORY ==========================

            Rectangle {
                id: floorSelector

                visible: !root.operationsOpen
                width: parent.width
                height: 54

                color: Colors.dark
                border.width: 1
                border.color: Colors.cyan

                Row {
                    anchors {
                        fill: parent
                        margins: 8
                    }
                    spacing: 8

                    Column {
                        width: parent.width - 92
                        anchors.verticalCenter: parent.verticalCenter
                        spacing: 3

                        SectionLabel {
                            text: "FLOOR // REPOSITORY"
                        }

                        GohuText {
                            width: parent.width
                            text:
                                floorService.floorLabel
                                + (
                                    auditService.defaultBranch
                                    ? "  //  DEFAULT "
                                      + auditService.defaultBranch
                                    : ""
                                  )
                            font.pixelSize: 11
                            color: Colors.orange
                            elide: Text.ElideRight
                        }
                    }

                    Rectangle {
                        id: floorPrevButton

                        width: 38
                        height: 32
                        anchors.verticalCenter: parent.verticalCenter

                        color:
                            floorPrevMouse.pressed
                            ? Colors.orange
                            : Colors.black
                        border.width: 1
                        border.color:
                            floorPrevMouse.containsMouse
                            ? Colors.orange
                            : Colors.cyan
                        opacity: root.floorSwitchEnabled ? 1.0 : 0.42

                        RectangularShadow {
                            anchors.fill: parent
                            spread: 2
                            z: -1
                            opacity:
                                floorPrevMouse.containsMouse
                                ? 0.34
                                : 0.16
                            color:
                                floorPrevMouse.containsMouse
                                ? Colors.orange
                                : Colors.cyan
                        }

                        GohuText {
                            anchors.centerIn: parent
                            text: "<"
                            font.pixelSize: 13
                            color:
                                floorPrevMouse.pressed
                                ? Colors.black
                                : Colors.cyan
                        }

                        MouseArea {
                            id: floorPrevMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            enabled: root.floorSwitchEnabled
                            cursorShape:
                                enabled
                                ? Qt.PointingHandCursor
                                : Qt.ArrowCursor

                            onClicked: root.cycleFloor(-1)
                        }
                    }

                    Rectangle {
                        id: floorNextButton

                        width: 38
                        height: 32
                        anchors.verticalCenter: parent.verticalCenter

                        color:
                            floorNextMouse.pressed
                            ? Colors.orange
                            : Colors.black
                        border.width: 1
                        border.color:
                            floorNextMouse.containsMouse
                            ? Colors.orange
                            : Colors.cyan
                        opacity: root.floorSwitchEnabled ? 1.0 : 0.42

                        RectangularShadow {
                            anchors.fill: parent
                            spread: 2
                            z: -1
                            opacity:
                                floorNextMouse.containsMouse
                                ? 0.34
                                : 0.16
                            color:
                                floorNextMouse.containsMouse
                                ? Colors.orange
                                : Colors.cyan
                        }

                        GohuText {
                            anchors.centerIn: parent
                            text: ">"
                            font.pixelSize: 13
                            color:
                                floorNextMouse.pressed
                                ? Colors.black
                                : Colors.cyan
                        }

                        MouseArea {
                            id: floorNextMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            enabled: root.floorSwitchEnabled
                            cursorShape:
                                enabled
                                ? Qt.PointingHandCursor
                                : Qt.ArrowCursor

                            onClicked: root.cycleFloor(1)
                        }
                    }
                }
            }

            // ===== PATIENT TOPOLOGY =============================

            BranchMap {
                id: topologyFrame

                visible: !root.operationsOpen
                width: parent.width
                height: 190

                topologyService: patientService
                titleText:
                    "FLOOR TOPOLOGY // "
                    + patientService.repository
                selectedSha: root.selectedCommitSha

                onCommitSelected: function(sha) {
                    root.toggleCommitSelection(sha);
                }
            }

            // ===== ROOM / BED ===================================

            Row {
                id: patientRoomRow

                visible: !root.operationsOpen
                width: parent.width
                height: 328
                spacing: 10
                layoutDirection: Qt.RightToLeft

                Rectangle {
                    id: bedPane

                    readonly property string roomName:
                        String(patientService.branch || "")
                    readonly property bool roomIsMain:
                        roomName === "main"
                    readonly property bool roomIsFeature:
                        roomName.indexOf("feature/") === 0
                    readonly property bool roomIsDetached:
                        roomName.toUpperCase() === "DETACHED"
                    readonly property color roomAccent:
                        roomIsMain
                        ? Colors.orange
                        : roomIsFeature
                        ? Colors.blue
                        : roomIsDetached
                        ? Colors.white
                        : Colors.cyan
                    readonly property color roomGlow:
                        roomIsMain
                        ? Colors.orange
                        : Colors.cyan

                    width: (parent.width - parent.spacing) / 2
                    height: parent.height

                    color: Colors.dark
                    border.width: root.bedControlMode ? 2 : 1
                    border.color:
                        root.bedControlMode
                        ? Colors.orange
                        : roomAccent

                    RectangularShadow {
                        anchors.fill: parent
                        spread: 4
                        z: -1
                        opacity:
                            root.bedControlMode
                            ? 0.40
                            : bedPane.roomIsDetached
                            ? 0.24
                            : bedPane.roomIsFeature
                            ? 0.22
                            : bedPane.roomIsMain
                            ? 0.30
                            : 0.20
                        color:
                            root.bedControlMode
                            ? Colors.orange
                            : bedPane.roomGlow
                    }

                    Column {
                        anchors {
                            fill: parent
                            margins: 12
                        }

                        spacing: 8

                        Row {
                            width: parent.width
                            height: 32
                            spacing: 6

                            Column {
                                width: parent.width - 76
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 2

                                SectionLabel {
                                    width: parent.width
                                    text: "BED // LOCAL CHECKOUT"
                                    elide: Text.ElideRight
                                }

                                GohuText {
                                    width: parent.width
                                    text:
                                        floorService.bedLabel
                                        + (
                                            floorService.bedIsLive
                                            ? "  //  LIVE"
                                            : ""
                                          )
                                    font.pixelSize: 10
                                    color:
                                        floorService.bedIsLive
                                        ? Colors.orange
                                        : Colors.cyan
                                    elide: Text.ElideRight
                                }
                            }

                            Rectangle {
                                width: 32
                                height: 28
                                anchors.verticalCenter: parent.verticalCenter
                                color: bedPrevMouse.pressed ? Colors.orange : Colors.black
                                border.width: 1
                                border.color:
                                    bedPrevMouse.containsMouse
                                    ? Colors.orange
                                    : Colors.cyan
                                opacity: root.bedSwitchEnabled ? 1.0 : 0.42

                                GohuText {
                                    anchors.centerIn: parent
                                    text: "<"
                                    font.pixelSize: 12
                                    color:
                                        bedPrevMouse.pressed
                                        ? Colors.black
                                        : Colors.cyan
                                }

                                MouseArea {
                                    id: bedPrevMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    enabled: root.bedSwitchEnabled
                                    cursorShape:
                                        enabled
                                        ? Qt.PointingHandCursor
                                        : Qt.ArrowCursor
                                    onClicked: root.cycleBed(-1)
                                }
                            }

                            Rectangle {
                                width: 32
                                height: 28
                                anchors.verticalCenter: parent.verticalCenter
                                color: bedNextMouse.pressed ? Colors.orange : Colors.black
                                border.width: 1
                                border.color:
                                    bedNextMouse.containsMouse
                                    ? Colors.orange
                                    : Colors.cyan
                                opacity: root.bedSwitchEnabled ? 1.0 : 0.42

                                GohuText {
                                    anchors.centerIn: parent
                                    text: ">"
                                    font.pixelSize: 12
                                    color:
                                        bedNextMouse.pressed
                                        ? Colors.black
                                        : Colors.cyan
                                }

                                MouseArea {
                                    id: bedNextMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    enabled: root.bedSwitchEnabled
                                    cursorShape:
                                        enabled
                                        ? Qt.PointingHandCursor
                                        : Qt.ArrowCursor
                                    onClicked: root.cycleBed(1)
                                }
                            }
                        }

                        Row {
                            spacing: 8

                            MetaLabel {
                                width: 76
                                text: "PATH"
                            }

                            MetaValue {
                                width: bedPane.width - 108
                                text: floorService.bedPath || "NO LOCAL CHECKOUT"
                                elide: Text.ElideMiddle
                            }
                        }

                        Row {
                            spacing: 8

                            OrangeLabel {
                                width: 76
                                text: "ROOM"
                            }

                            GohuText {
                                width: bedPane.width - 108
                                text: patientService.branch
                                font.pixelSize: 11
                                color: bedPane.roomAccent
                                elide: Text.ElideRight

                                layer.enabled: true
                                layer.effect: DropShadow {
                                    radius: 7
                                    samples: 9
                                    opacity:
                                        bedPane.roomIsDetached
                                        ? 0.34
                                        : bedPane.roomIsFeature
                                        ? 0.20
                                        : bedPane.roomIsMain
                                        ? 0.44
                                        : 0.30
                                    color: bedPane.roomGlow
                                    transparentBorder: true
                                }
                            }
                        }

                        Row {
                            spacing: 8

                            MetaLabel {
                                width: 76
                                text: "PATIENT"
                            }

                            BlueValue {
                                width: bedPane.width - 108
                                text: patientService.head
                                elide: Text.ElideRight
                            }
                        }

                        Row {
                            spacing: 8

                            MetaLabel {
                                width: 76
                                text: "WORKTREE"
                            }

                            GohuText {
                                id: worktreeValue

                                readonly property bool cleanState:
                                    String(patientService.worktree || "")
                                        .trim()
                                        .toUpperCase() === "CLEAN"

                                width: bedPane.width - 108
                                text: patientService.worktree
                                font.pixelSize: 10
                                elide: Text.ElideRight
                                color: cleanState ? Colors.orange : Colors.white

                                layer.enabled: true
                                layer.effect: DropShadow {
                                    radius: worktreeValue.cleanState ? 9 : 7
                                    samples: worktreeValue.cleanState ? 13 : 9
                                    opacity: worktreeValue.cleanState ? 0.76 : 0.34
                                    color: worktreeValue.cleanState ? Colors.orange : Colors.cyan
                                    transparentBorder: true
                                }
                            }
                        }

                        Row {
                            spacing: 8

                            MetaLabel {
                                width: 76
                                text: "BEDS"
                            }

                            MetaValue {
                                width: bedPane.width - 108
                                text:
                                    floorService.bedCount > 0
                                    ? (
                                        String(floorService.selectedBedIndex + 1)
                                        + " / "
                                        + String(floorService.bedCount)
                                      )
                                    : "NONE"
                            }
                        }

                        Rectangle {
                            id: moveBedButton

                            readonly property bool enabledAction:
                                root.bedMoveEnabled
                            readonly property bool keyboardSelected:
                                root.bedControlMode
                            readonly property bool liveConfirm:
                                floorService.bedIsLive
                                && floorService.liveMoveArmed
                                && floorService.armedBedPath
                                   === floorService.bedPath
                                && floorService.armedRoomBranch
                                   === root.selectedRoomBranch

                            width: parent.width
                            height: 28

                            color:
                                moveBedMouse.pressed
                                ? Colors.orange
                                : liveConfirm
                                ? Colors.red
                                : Colors.black
                            border.width:
                                keyboardSelected || liveConfirm
                                ? 2 : 1
                            border.color:
                                keyboardSelected
                                ? Colors.orange
                                : liveConfirm
                                ? Colors.red
                                : root.bedAlreadyInSelectedRoom
                                ? Colors.orange
                                : moveBedMouse.containsMouse
                                ? Colors.orange
                                : Colors.cyan
                            opacity:
                                enabledAction
                                || root.bedAlreadyInSelectedRoom
                                || liveConfirm
                                ? 1.0
                                : 0.44

                            RectangularShadow {
                                anchors.fill: parent
                                spread: moveBedButton.liveConfirm ? 5 : 3
                                z: -1
                                opacity: moveBedButton.liveConfirm ? 0.46 : 0.20
                                color:
                                    moveBedButton.liveConfirm
                                    ? Colors.red
                                    : root.bedAlreadyInSelectedRoom
                                    ? Colors.orange
                                    : Colors.cyan
                            }

                            GohuText {
                                anchors.centerIn: parent
                                text:
                                    floorService.moveRunning
                                    ? "MOVING BED"
                                    : moveBedButton.liveConfirm
                                    ? "CONFIRM LIVE BED MOVE"
                                    : root.bedAlreadyInSelectedRoom
                                    ? "BED IS IN THIS ROOM"
                                    : root.selectedRoomBranch.length === 0
                                    ? "SELECT A ROOM"
                                    : !root.bedIsClean
                                    ? "BED DIRTY // COMMIT OR STASH"
                                    : "MOVE BED TO ROOM"
                                font.pixelSize: 9
                                color:
                                    moveBedMouse.pressed
                                    ? Colors.black
                                    : moveBedButton.liveConfirm
                                    ? Colors.white
                                    : root.bedAlreadyInSelectedRoom
                                    ? Colors.orange
                                    : Colors.cyan

                                layer.enabled: true
                                layer.effect: DropShadow {
                                    radius: moveBedButton.liveConfirm ? 9 : 5
                                    samples: moveBedButton.liveConfirm ? 13 : 7
                                    opacity: moveBedButton.liveConfirm ? 0.58 : 0.24
                                    color:
                                        moveBedButton.liveConfirm
                                        ? Colors.red
                                        : root.bedAlreadyInSelectedRoom
                                        ? Colors.orange
                                        : Colors.cyan
                                    transparentBorder: true
                                }
                            }

                            MouseArea {
                                id: moveBedMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                enabled: moveBedButton.enabledAction
                                cursorShape:
                                    enabled
                                    ? Qt.PointingHandCursor
                                    : Qt.ArrowCursor

                                onClicked: root.invokeMoveBed()
                            }
                        }

                        GohuText {
                            width: parent.width
                            text:
                                floorService.moveStatus.length > 0
                                ? floorService.moveStatus
                                : (
                                    root.selectedRoomBranch.length > 0
                                    && !root.bedAlreadyInSelectedRoom
                                    ? (
                                        floorService.bedBranch
                                        + "  →  "
                                        + root.selectedRoomBranch
                                      )
                                    : ""
                                  )
                            font.pixelSize: 8
                            color:
                                floorService.moveError.length > 0
                                ? Colors.red
                                : floorService.liveMoveArmed
                                ? Colors.red
                                : Colors.cyan
                            elide: Text.ElideRight
                            visible: text.length > 0
                        }
                    }
                }

                Rectangle {
                    id: roomPane

                    width: (parent.width - parent.spacing) / 2
                    height: parent.height

                    color: Colors.dark
                    border.width: 1
                    border.color:
                        root.selectedRoomTeam.length > 0
                        ? Colors.orange
                        : Colors.magenta

                    RectangularShadow {
                        anchors.fill: parent
                        spread: 4
                        z: -1
                        opacity:
                            root.selectedRoomTeam.length > 0
                            ? 0.30
                            : 0.18
                        color:
                            root.selectedRoomTeam.length > 0
                            ? Colors.orange
                            : Colors.magenta
                    }

                    Column {
                        anchors {
                            fill: parent
                            margins: 12
                        }

                        spacing: 8

                        Row {
                            width: parent.width
                            height: 28
                            spacing: 6

                            SectionLabel {
                                width: parent.width - 76
                                anchors.verticalCenter: parent.verticalCenter
                                text:
                                    root.selectedRoomTeam.length > 0
                                    ? "ROOM // " + root.selectedRoomTeam
                                    : "ROOM // NONE SELECTED"
                                elide: Text.ElideRight
                            }

                            Rectangle {
                                width: 32
                                height: 28
                                anchors.verticalCenter: parent.verticalCenter
                                color: roomUpMouse.pressed ? Colors.orange : Colors.black
                                border.width: 1
                                border.color:
                                    roomUpMouse.containsMouse
                                    ? Colors.orange
                                    : Colors.cyan
                                opacity:
                                    auditService.rooms.length > 0
                                    ? 1.0 : 0.42

                                GohuText {
                                    anchors.centerIn: parent
                                    text: "↑"
                                    font.pixelSize: 12
                                    color:
                                        roomUpMouse.pressed
                                        ? Colors.black
                                        : Colors.cyan
                                }

                                MouseArea {
                                    id: roomUpMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    enabled: auditService.rooms.length > 0
                                    cursorShape:
                                        enabled
                                        ? Qt.PointingHandCursor
                                        : Qt.ArrowCursor
                                    onClicked: root.cycleRoom(-1)
                                }
                            }

                            Rectangle {
                                width: 32
                                height: 28
                                anchors.verticalCenter: parent.verticalCenter
                                color: roomDownMouse.pressed ? Colors.orange : Colors.black
                                border.width: 1
                                border.color:
                                    roomDownMouse.containsMouse
                                    ? Colors.orange
                                    : Colors.cyan
                                opacity:
                                    auditService.rooms.length > 0
                                    ? 1.0 : 0.42

                                GohuText {
                                    anchors.centerIn: parent
                                    text: "↓"
                                    font.pixelSize: 12
                                    color:
                                        roomDownMouse.pressed
                                        ? Colors.black
                                        : Colors.cyan
                                }

                                MouseArea {
                                    id: roomDownMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    enabled: auditService.rooms.length > 0
                                    cursorShape:
                                        enabled
                                        ? Qt.PointingHandCursor
                                        : Qt.ArrowCursor
                                    onClicked: root.cycleRoom(1)
                                }
                            }
                        }

                        GohuText {
                            width: parent.width
                            text: {
                                const room = root.selectedRoomData || {};
                                return String(
                                    room.responsibility
                                    || "SELECT AN OPERATING ROOM"
                                );
                            }
                            font.pixelSize: 10
                            color: Colors.orange
                            elide: Text.ElideRight
                        }

                        Row {
                            spacing: 8

                            MetaLabel {
                                width: 66
                                text: "BRANCH"
                            }

                            CyanValue {
                                width: roomPane.width - 98
                                text: {
                                    const room = root.selectedRoomData || {};
                                    return String(room.branch || "NO DATA");
                                }
                                elide: Text.ElideRight
                            }
                        }

                        Row {
                            spacing: 8

                            MetaLabel {
                                width: 66
                                text: "LOCATION"
                            }

                            GohuText {
                                readonly property color presenceColor:
                                    roomPresenceService.running
                                    && !roomPresenceService.available
                                    ? Colors.orange
                                    : roomPresenceService.location === "MISSING"
                                    ? Colors.red
                                    : roomPresenceService.location === "LOCAL"
                                    ? Colors.blue
                                    : roomPresenceService.location === "REMOTE"
                                    ? Colors.magenta
                                    : roomPresenceService.syncState === "DIVERGED"
                                    ? Colors.magenta
                                    : roomPresenceService.syncState === "LOCAL_AHEAD"
                                    ? Colors.blue
                                    : roomPresenceService.syncState === "REMOTE_AHEAD"
                                    ? Colors.magenta
                                    : roomPresenceService.syncState === "SYNCED"
                                    ? Colors.orange
                                    : Colors.cyan

                                width: roomPane.width - 98
                                text: roomPresenceService.summary
                                font.pixelSize: 10
                                color: presenceColor
                                elide: Text.ElideRight

                                layer.enabled: true
                                layer.effect: DropShadow {
                                    radius: 6
                                    samples: 7
                                    opacity: 0.26
                                    color: parent.presenceColor
                                    transparentBorder: true
                                }
                            }
                        }

                        Row {
                            spacing: 8

                            MetaLabel {
                                width: 66
                                text: "HEAD"
                            }

                            BlueValue {
                                width: roomPane.width - 98
                                text: {
                                    const room = root.selectedRoomData || {};
                                    const head = String(room.head || "");
                                    return head ? head.slice(0, 12) : "NO DATA";
                                }
                                elide: Text.ElideRight
                            }
                        }

                        Row {
                            spacing: 8

                            MetaLabel {
                                width: 66
                                text: "RELATION"
                            }

                            GohuText {
                                width: roomPane.width - 98
                                text: {
                                    const room = root.selectedRoomData || {};

                                    if (!root.selectedRoomTeam.length)
                                        return "WAITING";

                                    const state =
                                        String(room.state || "WAITING");
                                    const ahead = Number(room.ahead || 0);
                                    const behind = Number(room.behind || 0);

                                    return state
                                           + " // +" + ahead
                                           + " / -" + behind;
                                }
                                font.pixelSize: 10
                                color: Colors.magenta
                                elide: Text.ElideRight
                            }
                        }

                        Row {
                            spacing: 8

                            MetaLabel {
                                width: 66
                                text: "TOUCHED"
                            }

                            MetaValue {
                                width: roomPane.width - 98
                                text: {
                                    const room = root.selectedRoomData || {};
                                    return String(
                                        room.updated_at
                                        || "NO DATA"
                                    );
                                }
                                elide: Text.ElideRight
                            }
                        }


                        Row {
                            id: roomInspectActions

                            width: parent.width
                            height: 24
                            spacing: 6

                            Repeater {
                                model: ["STATUS", "DIFF", "LOG"]

                                Rectangle {
                                    id: roomInspectButton

                                    required property string modelData
                                    readonly property bool selectedAction:
                                        roomService.action === modelData
                                    readonly property bool keyboardSelected:
                                        root.roomControlMode
                                        && root.roomControlAction === modelData
                                    readonly property bool enabledAction:
                                        root.selectedRoomTeam.length > 0
                                        && !roomService.running
                                        && !roomService.rehearsing
                                        && !roomService.integrating
                                        && !roomService.postOpRunning
                                        && !roomService.armed

                                    width:
                                        (
                                            roomInspectActions.width
                                            - roomInspectActions.spacing * 2
                                        ) / 3
                                    height: parent.height

                                    color:
                                        roomInspectMouse.pressed
                                        ? Colors.orange
                                        : selectedAction
                                        ? Colors.magenta
                                        : Colors.black
                                    border.width: keyboardSelected ? 2 : 1
                                    border.color:
                                        keyboardSelected
                                        ? Colors.orange
                                        : roomInspectMouse.containsMouse
                                        ? Colors.orange
                                        : selectedAction
                                        ? Colors.magenta
                                        : Colors.cyan
                                    opacity: enabledAction ? 1.0 : 0.48

                                    GohuText {
                                        anchors.centerIn: parent
                                        text:
                                            roomService.running
                                            && roomService.action
                                               === roomInspectButton.modelData
                                            ? "READING"
                                            : roomInspectButton.modelData
                                        font.pixelSize: 9
                                        color:
                                            roomInspectMouse.pressed
                                            ? Colors.black
                                            : roomInspectButton.keyboardSelected
                                            ? Colors.orange
                                            : Colors.cyan
                                    }

                                    MouseArea {
                                        id: roomInspectMouse

                                        anchors.fill: parent
                                        hoverEnabled: true
                                        enabled: roomInspectButton.enabledAction
                                        cursorShape:
                                            enabled
                                            ? Qt.PointingHandCursor
                                            : Qt.ArrowCursor

                                        onClicked:
                                            roomService.runInspection(
                                                roomInspectButton.modelData
                                                    .toLowerCase()
                                            )
                                    }
                                }
                            }
                        }

                        Row {
                            id: roomOperationActions

                            width: parent.width
                            height: 24
                            spacing: 6

                            Repeater {
                                model: ["REFRESH", "LAZYGIT", "PREPARE"]

                                Rectangle {
                                    id: roomOperationButton

                                    required property string modelData
                                    readonly property bool keyboardSelected:
                                        root.roomControlMode
                                        && root.roomControlAction === modelData
                                    readonly property bool enabledAction:
                                        root.selectedRoomTeam.length > 0
                                        && !roomService.running
                                        && !roomService.rehearsing
                                        && !roomService.integrating
                                        && !roomService.postOpRunning
                                        && !roomService.armed

                                    width:
                                        (
                                            roomOperationActions.width
                                            - roomOperationActions.spacing * 2
                                        ) / 3
                                    height: parent.height

                                    color:
                                        roomOperationMouse.pressed
                                        ? Colors.orange
                                        : roomService.action === modelData
                                        ? Colors.magenta
                                        : Colors.black
                                    border.width: keyboardSelected ? 2 : 1
                                    border.color:
                                        keyboardSelected
                                        ? Colors.orange
                                        : roomOperationMouse.containsMouse
                                        ? Colors.orange
                                        : modelData === "PREPARE"
                                          && roomService.action === "PREPARE"
                                        ? Colors.magenta
                                        : Colors.cyan
                                    opacity: enabledAction ? 1.0 : 0.48

                                    GohuText {
                                        anchors.centerIn: parent
                                        text:
                                            roomService.running
                                            && roomService.action
                                               === roomOperationButton.modelData
                                            ? "READING"
                                            : roomOperationButton.modelData
                                        font.pixelSize: 8
                                        color:
                                            roomOperationMouse.pressed
                                            ? Colors.black
                                            : roomOperationButton.keyboardSelected
                                            ? Colors.orange
                                            : Colors.cyan
                                    }

                                    MouseArea {
                                        id: roomOperationMouse

                                        anchors.fill: parent
                                        hoverEnabled: true
                                        enabled: roomOperationButton.enabledAction
                                        cursorShape:
                                            enabled
                                            ? Qt.PointingHandCursor
                                            : Qt.ArrowCursor

                                        onClicked: {
                                            if (roomOperationButton.modelData
                                                    === "REFRESH") {
                                                patientService.refresh();
                                                auditService.runAudit();
                                                roomService.runInspection(
                                                    "status"
                                                );
                                                return;
                                            }

                                            if (roomOperationButton.modelData
                                                    === "LAZYGIT") {
                                                roomService.launchLazygit();
                                                return;
                                            }

                                            certificationCoordinator.prepare();
                                        }
                                    }
                                }
                            }
                        }

                        Rectangle {
                            id: rehearseButton

                            readonly property bool keyboardSelected:
                                root.roomControlMode
                                && root.roomControlAction === "REHEARSE"
                            readonly property bool enabledAction:
                                roomService.canRehearse
                                && !roomService.running
                                && !roomService.rehearsing
                                && !roomService.integrating
                                && !roomService.postOpRunning
                                && !roomService.armed

                            width: parent.width
                            height: 24

                            color:
                                rehearseMouse.pressed
                                ? Colors.orange
                                : roomService.rehearsing
                                ? Colors.magenta
                                : Colors.black
                            border.width:
                                keyboardSelected
                                || roomService.rehearsalStatus.length > 0
                                ? 2 : 1
                            border.color:
                                keyboardSelected
                                ? Colors.orange
                                : roomService.rehearsalStatus === "CONFLICTS"
                                ? Colors.red
                                : roomService.rehearsalStatus === "CLEAN_MERGE"
                                ? Colors.orange
                                : rehearseMouse.containsMouse
                                ? Colors.orange
                                : Colors.cyan
                            opacity:
                                enabledAction
                                || roomService.rehearsing
                                || roomService.rehearsalStatus.length > 0
                                ? 1.0 : 0.42

                            RectangularShadow {
                                anchors.fill: parent
                                spread:
                                    roomService.rehearsalStatus.length > 0
                                    ? 4 : 2
                                z: -1
                                opacity:
                                    roomService.rehearsalStatus.length > 0
                                    ? 0.34 : 0.12
                                color:
                                    roomService.rehearsalStatus === "CONFLICTS"
                                    ? Colors.red
                                    : roomService.rehearsalStatus === "CLEAN_MERGE"
                                    ? Colors.orange
                                    : Colors.cyan
                            }

                            GohuText {
                                anchors.centerIn: parent
                                text:
                                    roomService.rehearsing
                                    ? "REHEARSING // ISOLATED"
                                    : roomService.rehearsalStatus === "CONFLICTS"
                                    ? "REHEARSE // CONFLICTS"
                                    : roomService.rehearsalStatus === "CLEAN_MERGE"
                                    ? "REHEARSE // CLEAN MERGE"
                                    : "REHEARSE MERGE"
                                font.pixelSize: 9
                                color:
                                    rehearseMouse.pressed
                                    ? Colors.black
                                    : roomService.rehearsalStatus === "CONFLICTS"
                                    ? Colors.red
                                    : roomService.rehearsalStatus === "CLEAN_MERGE"
                                    ? Colors.orange
                                    : Colors.cyan
                            }

                            MouseArea {
                                id: rehearseMouse

                                anchors.fill: parent
                                hoverEnabled: true
                                enabled: rehearseButton.enabledAction
                                cursorShape:
                                    enabled
                                    ? Qt.PointingHandCursor
                                    : Qt.ArrowCursor

                                onClicked: certificationCoordinator.rehearse()
                            }
                        }

                        Row {
                            id: integrationGateActions

                            width: parent.width
                            height: 24
                            spacing: 6

                            Rectangle {
                                id: armButton

                                readonly property bool keyboardSelected:
                                    root.roomControlMode
                                    && root.roomControlAction === "ARM"
                                readonly property string gateState:
                                    certificationCoordinator.state
                                readonly property bool rehearsalReady:
                                    roomService.integrationMode !== "DIVERGED"
                                    || roomService.rehearsalStatus === "CLEAN_MERGE"
                                readonly property bool enabledAction:
                                    !roomService.running
                                    && !roomService.rehearsing
                                    && !roomService.integrating
                                    && !roomService.postOpRunning
                                    && (
                                        (
                                            gateState === "CANDIDATE"
                                            && rehearsalReady
                                            && certificationCoordinator.canRequestVerification
                                        )
                                        || (
                                            gateState === "VERIFIED"
                                            && certificationCoordinator.canCertify
                                        )
                                        || (
                                            gateState === "CERTIFIED"
                                            && certificationCoordinator.canArm
                                        )
                                    )

                                width:
                                    (
                                        integrationGateActions.width
                                        - integrationGateActions.spacing
                                    ) / 2
                                height: parent.height

                                color:
                                    armMouse.pressed
                                    ? Colors.orange
                                    : roomService.armed
                                    ? Colors.orange
                                    : gateState === "VERIFIED"
                                      || gateState === "CERTIFIED"
                                    ? Colors.magenta
                                    : Colors.black
                                border.width:
                                    keyboardSelected
                                    || roomService.armed
                                    || gateState === "VERIFIED"
                                    || gateState === "CERTIFIED"
                                    ? 2 : 1
                                border.color:
                                    keyboardSelected
                                    ? Colors.orange
                                    : roomService.armed
                                    ? Colors.orange
                                    : gateState === "VERIFIED"
                                      || gateState === "CERTIFIED"
                                    ? Colors.magenta
                                    : armMouse.containsMouse
                                    ? Colors.orange
                                    : Colors.cyan
                                opacity:
                                    enabledAction
                                    || roomService.armed
                                    || gateState === "VERIFIED"
                                    || gateState === "CERTIFIED"
                                    ? 1.0 : 0.42

                                RectangularShadow {
                                    anchors.fill: parent
                                    spread:
                                        roomService.armed
                                        || armButton.gateState === "VERIFIED"
                                        || armButton.gateState === "CERTIFIED"
                                        ? 4 : 2
                                    z: -1
                                    opacity:
                                        roomService.armed
                                        || armButton.gateState === "VERIFIED"
                                        || armButton.gateState === "CERTIFIED"
                                        ? 0.38 : 0.14
                                    color:
                                        roomService.armed
                                        ? Colors.orange
                                        : armButton.gateState === "VERIFIED"
                                          || armButton.gateState === "CERTIFIED"
                                        ? Colors.magenta
                                        : Colors.cyan
                                }

                                GohuText {
                                    anchors.centerIn: parent
                                    text:
                                        roomService.armed
                                        ? (
                                            roomService.armedMode === "MERGE"
                                            ? "MERGE ARMED"
                                            : "ARMED"
                                          )
                                        : armButton.gateState === "CANDIDATE"
                                        ? (
                                            gitEvidenceProvider.requestBusy
                                            ? "VERIFYING"
                                            : "VERIFY"
                                          )
                                        : armButton.gateState === "VERIFIED"
                                        ? "CERTIFY"
                                        : armButton.gateState === "CERTIFIED"
                                        ? (
                                            roomService.canArmMerge
                                            ? "ARM MERGE"
                                            : "ARM"
                                          )
                                        : "ARM"
                                    font.pixelSize: 9
                                    color:
                                        roomService.armed
                                        ? Colors.black
                                        : armButton.gateState === "VERIFIED"
                                          || armButton.gateState === "CERTIFIED"
                                        ? Colors.magenta
                                        : Colors.cyan
                                }

                                MouseArea {
                                    id: armMouse

                                    anchors.fill: parent
                                    hoverEnabled: true
                                    enabled:
                                        armButton.enabledAction
                                        && !roomService.armed
                                    cursorShape:
                                        enabled
                                        ? Qt.PointingHandCursor
                                        : Qt.ArrowCursor

                                    onClicked: {
                                        if (armButton.gateState === "CANDIDATE") {
                                            certificationCoordinator.requestVerification("");
                                            return;
                                        }

                                        if (armButton.gateState === "VERIFIED") {
                                            certificationCoordinator.certify();
                                            return;
                                        }

                                        if (armButton.gateState === "CERTIFIED")
                                            certificationCoordinator.arm();
                                    }
                                }
                            }

                            Rectangle {
                                id: integrateButton

                                readonly property bool keyboardSelected:
                                    root.roomControlMode
                                    && root.roomControlAction === "INTEGRATE"
                                readonly property bool enabledAction:
                                    roomService.armed
                                    && certificationCoordinator.canIntegrate
                                    && !roomService.running
                                    && !roomService.rehearsing
                                    && !roomService.integrating
                                    && !roomService.postOpRunning

                                width:
                                    (
                                        integrationGateActions.width
                                        - integrationGateActions.spacing
                                    ) / 2
                                height: parent.height

                                color:
                                    integrateMouse.pressed
                                    ? Colors.orange
                                    : roomService.integrating
                                    ? Colors.magenta
                                    : Colors.black
                                border.width:
                                    keyboardSelected
                                    || roomService.armed
                                    ? 2 : 1
                                border.color:
                                    keyboardSelected
                                    ? Colors.orange
                                    : roomService.armed
                                    ? Colors.red
                                    : Colors.cyan
                                opacity: enabledAction
                                         || roomService.integrating
                                         ? 1.0 : 0.42

                                RectangularShadow {
                                    anchors.fill: parent
                                    spread: roomService.armed ? 4 : 2
                                    z: -1
                                    opacity: roomService.armed ? 0.34 : 0.12
                                    color:
                                        roomService.armed
                                        ? Colors.red
                                        : Colors.cyan
                                }

                                GohuText {
                                    anchors.centerIn: parent
                                    text:
                                        roomService.postOpRunning
                                        ? "POST-OP"
                                        : roomService.integrating
                                        ? "VERIFYING"
                                        : roomService.armedMode === "MERGE"
                                        ? "MERGE"
                                        : "INTEGRATE"
                                    font.pixelSize: 9
                                    color:
                                        integrateMouse.pressed
                                        ? Colors.black
                                        : roomService.armed
                                        ? Colors.red
                                        : Colors.cyan
                                }

                                MouseArea {
                                    id: integrateMouse

                                    anchors.fill: parent
                                    hoverEnabled: true
                                    enabled: integrateButton.enabledAction
                                    cursorShape:
                                        enabled
                                        ? Qt.PointingHandCursor
                                        : Qt.ArrowCursor

                                    onClicked: certificationCoordinator.integrate()
                                }
                            }
                        }

                        GohuText {
                            width: parent.width
                            text:
                                certificationCoordinator.state !== "IDLE"
                                ? "CERT // "
                                  + certificationCoordinator.state
                                  + " // "
                                  + (
                                      certificationCoordinator.lastError
                                      ? certificationCoordinator.lastError
                                      : roomService.summary
                                    )
                                : roomService.summary
                            font.pixelSize: 9
                            color:
                                certificationCoordinator.lastError
                                || roomService.lastError
                                ? Colors.red
                                : roomService.postOpStatus === "POST_OP_CLEAN"
                                ? Colors.cyan
                                : roomService.postOpRunning
                                ? Colors.orange
                                : roomService.armed
                                ? Colors.orange
                                : roomService.integrationMode === "DIVERGED"
                                ? Colors.magenta
                                : roomService.integrationMode === "FAST_FORWARD"
                                ? Colors.orange
                                : roomService.available
                                ? Colors.cyan
                                : Colors.magenta
                            elide: Text.ElideRight
                        }

                        GohuText {
                            width: parent.width
                            visible: roomService.rehearsalDetail.length > 0
                            text: roomService.rehearsalDetail
                            font.pixelSize: 8
                            color:
                                roomService.rehearsalStatus === "CONFLICTS"
                                ? Colors.red
                                : Colors.orange
                            elide: Text.ElideRight
                        }

                        GohuText {
                            width: parent.width
                            visible: roomService.postOpDetail.length > 0
                            text: roomService.postOpDetail
                            font.pixelSize: 8
                            color: Colors.cyan
                            elide: Text.ElideRight
                        }
                    }
                }
            }

            // ===== OPERATING ROOMS ==============================

            SectionLabel {
                visible: !root.operationsOpen
                text: "OPERATING ROOMS"
            }

            Rectangle {
                visible: !root.operationsOpen
                width: parent.width
                height: 2
                color: Colors.magenta

                RectangularShadow {
                    anchors.fill: parent
                    spread: 3
                    z: -1
                    opacity: 0.34
                    color: Colors.magenta
                }
            }


        }

        // Only the operating-room selector/detail surface scrolls.
        Flickable {
            id: hospitalScroll

            visible: !root.operationsOpen

            anchors {
                top: fixedTop.bottom
                bottom: actionBay.top
                left: parent.left
                right: parent.right
                topMargin: 8
                bottomMargin: 10
                leftMargin: 62
                rightMargin: 18
            }

            clip: true
            contentWidth: width
            contentHeight: scrollContent.height
            boundsBehavior: Flickable.StopAtBounds
            flickDeceleration: 1800

            Column {
                id: scrollContent

                width: hospitalScroll.width
                spacing: 12

            Column {
                id: roomsColumn

                width: parent.width
                spacing: 7

                Repeater {
                    model: auditService.rooms

                    RoomRow {
                        team: String(
                            modelData.team
                            || modelData.branch
                            || ""
                        )

                        responsibility: String(
                            modelData.responsibility
                            || "AUTO DISCOVERED"
                        )
                    }
                }
            }


            }
        }

        MouseArea {
            id: phoneMenuShield

            x: 0
            y:
                fixedTop.y
                + hospitalHeader.y
                + hospitalHeader.height
                + 4
            width: parent.width
            height: Math.max(0, parent.height - y)
            visible:
                root.phoneMenuOpen
                || root.intercomMenuOpen
            z: 1180
            acceptedButtons: Qt.AllButtons
            hoverEnabled: true

            onClicked: {
                root.phoneMenuOpen = false;
                root.intercomMenuOpen = false;
                root.intercomTyping = false;
                keyboardFocusAnchor.forceActiveFocus();
            }

            onWheel: function(wheel) {
                wheel.accepted = true;
            }
        }

        HospitalIntercomMenu {
            id: intercomDropdown

            visible: root.intercomMenuOpen
            z: 1200

            registryService: specialistRegistryService
            intercomService: intercomService
            speechInputService: intercomSpeechInputService
            workingDirectory: floorService.bedPath
            floorLabel: floorService.floorLabel
            roomLabel:
                root.selectedRoomTeam
                ? root.selectedRoomTeam
                : "NO ROOM"

            x:
                fixedTop.x
                + hospitalHeader.x
                + hospitalHeaderActions.x
                + intercomButton.x
                + intercomButton.width
                - width
            y:
                fixedTop.y
                + hospitalHeader.y
                + hospitalHeaderActions.y
                + intercomButton.y
                + intercomButton.height
                + 6

            onTypingChanged: function(active) {
                root.intercomTyping = active;

                if (!active
                        && root.menuOpen
                        && root.keyboardActive)
                    keyboardFocusAnchor.forceActiveFocus();
            }
        }

        HospitalPhoneMenu {
            id: phoneDropdown

            visible: root.phoneMenuOpen
            z: 1200

            registryService: specialistRegistryService
            phoneService: phoneService
            workingDirectory: floorService.bedPath

            x:
                fixedTop.x
                + hospitalHeader.x
                + hospitalHeaderActions.x
                + phoneButton.x
                + phoneButton.width
                - width
            y:
                fixedTop.y
                + hospitalHeader.y
                + hospitalHeaderActions.y
                + phoneButton.y
                + phoneButton.height
                + 6

            onCallLaunched:
                root.phoneMenuOpen = false
        }

        HospitalReceptionistView {
            id: receptionistView

            z: 700
            visible: root.operationsSurface === "reception"
            receptionistService: receptionistService
            speechInputService: speechInputService
            floorLabel: floorService.floorLabel
            roomLabel:
                root.selectedRoomTeam
                ? root.selectedRoomTeam
                : "NO ROOM"
            readyCount: specialistRegistryService.readyCount
            specialistCount: specialistRegistryService.specialistCount
            attentionCount: roundsService.attentionCount
            newCount: receptionistService.unreadCount
            recentCount: receptionistService.recentCount
            inbox: receptionistService.inbox
            sharedContextActive: hospitalContextService.active
            sharedContextLabel: hospitalContextService.label

            anchors {
                left: parent.left
                right: parent.right
                top: fixedTop.bottom
                bottom: actionBay.top
                leftMargin: 18
                rightMargin: 18
                topMargin: 8
                bottomMargin: 10
            }

            onRouteRequested: function(route) {
                root.handleReceptionRoute(route);
            }

            onAttentionActivated: function(item) {
                root.activateReceptionActivity(item);
            }

            onTypingChanged: function(active) {
                root.receptionistTyping = active;

                if (!active
                        && root.menuOpen
                        && root.keyboardActive)
                    keyboardFocusAnchor.forceActiveFocus();
            }
        }

        HospitalReportsView {
            id: reportsView

            z: 700
            visible: root.operationsSurface === "reports"
            historyService: certificationCoordinator.historyService
            roomTeams: {
                const seen = {};
                const teams = [];
                const liveRounds =
                    Array.isArray(roundsService.rooms)
                    ? roundsService.rooms
                    : [];
                const currentRooms =
                    Array.isArray(auditService.rooms)
                    ? auditService.rooms
                    : [];

                function addRows(rows) {
                    for (let i = 0; i < rows.length; ++i) {
                        const row = rows[i] || {};
                        const team =
                            String(
                                row.team
                                || row.branch
                                || ""
                            ).trim();

                        if (team && !seen[team]) {
                            seen[team] = true;
                            teams.push(team);
                        }
                    }
                }

                addRows(liveRounds);
                addRows(currentRooms);
                return teams;
            }

            anchors {
                left: parent.left
                right: parent.right
                top: fixedTop.bottom
                bottom: actionBay.top
                leftMargin: 18
                rightMargin: 18
                topMargin: 8
                bottomMargin: 10
            }

            onEventActivated: function(event) {
                hospitalContextService.captureReport(
                    event
                );
            }
        }

        HospitalRoundsView {
            id: roundsView

            z: 700
            visible: root.operationsSurface === "rounds"
            roundsService: roundsService

            anchors {
                left: parent.left
                right: parent.right
                top: fixedTop.bottom
                bottom: actionBay.top
                leftMargin: 18
                rightMargin: 18
                topMargin: 8
                bottomMargin: 10
            }

            onRoomActivated: function(room) {
                root.openRoomFromRounds(room);
            }
        }

        HospitalSpecialistsView {
            id: specialistsView

            z: 700
            visible: root.operationsSurface === "staff"
            registryService: specialistRegistryService

            anchors {
                left: parent.left
                right: parent.right
                top: fixedTop.bottom
                bottom: actionBay.top
                leftMargin: 18
                rightMargin: 18
                topMargin: 8
                bottomMargin: 10
            }

            onSpecialistSelected: function(specialist) {
                hospitalContextService.captureSpecialist(
                    specialist
                );
            }
        }

        Rectangle {
            id: actionBay

            height: 54
            anchors {
                left: parent.left
                right: parent.right
                bottom: bottomStop.top
                leftMargin:
                    root.operationsOpen ? 18 : 62
                rightMargin: 18
                bottomMargin: 8
            }

                color: Colors.dark
                border.width: 1
                border.color: Colors.cyan

                RectangularShadow {
                    anchors.fill: parent
                    spread: 3
                    z: -1
                    opacity: 0.28
                    color: Colors.cyan
                }

                Row {
                    anchors.centerIn: parent
                    spacing: 22

                    GohuText {
                        id: refreshAction

                        text: patientService.refreshing ? "READING" : "LOCAL REFRESH"
                        font.pixelSize: 10
                        color: refreshMouse.containsMouse ? Colors.orange : Colors.cyan
                        opacity: patientService.refreshing ? 0.55 : 1.0

                        layer.enabled: true
                        layer.effect: DropShadow {
                            radius: 5
                            samples: 7
                            opacity: refreshMouse.containsMouse ? 0.52 : 0.28
                            color: refreshAction.color
                            transparentBorder: true
                        }

                        MouseArea {
                            id: refreshMouse
                            anchors.fill: parent
                            anchors.margins: -8
                            hoverEnabled: true
                            enabled: !patientService.refreshing
                            cursorShape: Qt.PointingHandCursor

                            onClicked: floorService.discover()
                        }
                    }

                    GohuText {
                        id: auditAction

                        text: auditService.visibleRunning
                              ? "AUDIT // RUNNING"
                              : root.selectedRoomTeam.length > 0
                                && root.auditedRoomTeam !== root.selectedRoomTeam
                              ? "AUDIT"
                              : auditService.available
                              ? "AUDIT // " + auditService.status
                              : "AUDIT"
                        font.pixelSize: 10
                        color: auditMouse.containsMouse
                               ? Colors.orange
                               : auditService.available
                               ? Colors.magenta
                               : auditService.lastError
                               ? Colors.red
                               : Colors.cyan
                        opacity: auditService.visibleRunning ? 0.60 : 1.0

                        layer.enabled: true
                        layer.effect: DropShadow {
                            radius: 5
                            samples: 7
                            opacity: auditMouse.containsMouse
                                     ? 0.52
                                     : auditService.available
                                     ? 0.42
                                     : auditService.lastError
                                     ? 0.44
                                     : 0.28
                            color: auditAction.color
                            transparentBorder: true
                        }

                        MouseArea {
                            id: auditMouse
                            anchors.fill: parent
                            anchors.margins: -8
                            hoverEnabled: true
                            enabled: !auditService.running && auditService.repository.length > 0
                            cursorShape: Qt.PointingHandCursor

                            onClicked: root.runAuditForCurrentRoom()
                        }
                    }

                    GohuText {
                        id: githubAction

                        text: githubService.refreshing
                              ? "GITHUB // READING"
                              : githubService.available
                              ? "GITHUB // SYNCED"
                              : "GITHUB"
                        font.pixelSize: 10
                        color: githubMouse.containsMouse
                               ? Colors.orange
                               : githubService.available
                               ? Colors.magenta
                               : Colors.cyan
                        opacity: githubService.refreshing ? 0.60 : 1.0

                        layer.enabled: true
                        layer.effect: DropShadow {
                            radius: 5
                            samples: 7
                            opacity: githubMouse.containsMouse
                                     ? 0.52
                                     : githubService.available
                                     ? 0.42
                                     : 0.28
                            color: githubAction.color
                            transparentBorder: true
                        }

                        MouseArea {
                            id: githubMouse
                            anchors.fill: parent
                            anchors.margins: -8
                            hoverEnabled: true
                            enabled: !githubService.refreshing && githubService.repoSlug.length > 0
                            cursorShape: Qt.PointingHandCursor

                            onClicked: githubService.refresh()
                        }
                    }


                }

                GohuText {
                    anchors {
                        right: parent.right
                        bottom: parent.bottom
                        rightMargin: 8
                        bottomMargin: 5
                    }

                    text: auditService.visibleRunning
                          ? "PX AUDIT RUNNING // " + auditService.repository
                          : auditService.available
                          ? "AUDIT " + auditService.status
                            + " // " + String(auditService.workflowCount) + " WORKFLOWS"
                            + " // " + String(auditService.runCount) + " RECENT RUNS"
                            + " // " + String(auditService.rooms.length) + " ROOMS"
                          : auditService.lastError
                          ? "AUDIT ERROR // " + auditService.lastError
                          : floorService.bedPath.length === 0
                          ? "LOCAL BED OFFLINE"
                          : githubService.refreshing
                          ? (
                              floorService.bedIsLive
                              ? "LOCAL LIVE // PX → GITHUB READING"
                              : "LOCAL BED // PX → GITHUB READING"
                            )
                          : githubService.available
                          ? (
                              floorService.bedIsLive
                              ? "LOCAL LIVE // GITHUB AVAILABLE"
                              : "LOCAL BED // GITHUB AVAILABLE"
                            )
                          : githubService.lastError
                          ? (
                              floorService.bedIsLive
                              ? "LOCAL LIVE // PX/GITHUB OFFLINE"
                              : "LOCAL BED // PX/GITHUB OFFLINE"
                            )
                          : (
                              floorService.bedIsLive
                              ? "LOCAL LIVE // PX/GITHUB NOT REQUESTED"
                              : "LOCAL BED // PX/GITHUB NOT REQUESTED"
                            )
                    font.pixelSize: 8
                    color: Colors.magenta

                    layer.enabled: true
                    layer.effect: DropShadow {
                        radius: 8
                        samples: 7
                        opacity: 0.56
                        color: Colors.magenta
                        transparentBorder: true
                    }
                }
            }

        // AppControl / CPU++ selector scrollbar geometry.
        Rectangle {
            id: scrollRail

            width: 10

            anchors {
                top: hospitalScroll.top
                bottom: hospitalScroll.bottom
                right: parent.right
                topMargin: 0
                bottomMargin: 0
                rightMargin: 3
            }

            color: Colors.cyan

            readonly property bool scrollable:
                hospitalScroll.contentHeight
                > hospitalScroll.height

            opacity: 0.0
            visible: false
            z: 300

            property real maxContentY:
                Math.max(
                    0,
                    hospitalScroll.contentHeight
                    - hospitalScroll.height
                )

            property real handleTravel:
                Math.max(
                    0,
                    height - scrollThumb.height
                )

            function setScrollFromHandleY(handleY) {
                if (maxContentY <= 0 || handleTravel <= 0)
                    return;

                const clampedY =
                    Math.max(
                        0,
                        Math.min(handleTravel, handleY)
                    );

                hospitalScroll.contentY =
                    (clampedY / handleTravel) * maxContentY;
            }

            RectangularShadow {
                anchors.fill: parent
                spread: 2
                z: -1
                opacity: 0.24
                color: parent.color
            }

            Rectangle {
                id: scrollThumb

                width: 6
                anchors.horizontalCenter: parent.horizontalCenter

                height:
                    scrollRail.scrollable
                    ? Math.max(
                        30,
                        parent.height
                        * Math.min(
                            1.0,
                            hospitalScroll.visibleArea.heightRatio
                        )
                    )
                    : 42

                y: {
                    if (!scrollRail.scrollable)
                        return 0;

                    const ratio =
                        Math.max(
                            0.0,
                            Math.min(
                                1.0,
                                Number(
                                    hospitalScroll.visibleArea.heightRatio
                                    || 0
                                )
                            )
                        );

                    const maxPosition =
                        Math.max(0.0, 1.0 - ratio);

                    const position =
                        Math.max(
                            0.0,
                            Math.min(
                                maxPosition,
                                Number(
                                    hospitalScroll.visibleArea.yPosition
                                    || 0
                                )
                            )
                        );

                    if (maxPosition <= 0
                            || scrollRail.handleTravel <= 0)
                        return 0;

                    return (
                        position / maxPosition
                    ) * scrollRail.handleTravel;
                }

                color: Colors.magenta
                opacity: 1.0

                RectangularShadow {
                    anchors.fill: parent
                    spread: 2
                    z: -1
                    opacity: 0.28
                    color: Colors.magenta
                }
            }

            MouseArea {
                id: scrollMouse

                anchors.fill: parent
                hoverEnabled: true
                acceptedButtons: Qt.LeftButton
                enabled: scrollRail.scrollable
                cursorShape: scrollRail.scrollable
                             ? Qt.SizeVerCursor
                             : Qt.ArrowCursor

                property real dragOffset: 0

                onPressed: function(mouse) {
                    const handleTop = scrollThumb.y;
                    const handleBottom =
                        scrollThumb.y
                        + scrollThumb.height;

                    dragOffset =
                        mouse.y >= handleTop
                        && mouse.y <= handleBottom
                        ? mouse.y - handleTop
                        : scrollThumb.height / 2;

                    scrollRail.setScrollFromHandleY(
                        mouse.y - dragOffset
                    );
                }

                onPositionChanged: function(mouse) {
                    if (pressed)
                        scrollRail.setScrollFromHandleY(
                            mouse.y - dragOffset
                        );
                }

                onWheel: function(wheel) {
                    const step =
                        wheel.angleDelta.y > 0
                        ? -90
                        : 90;

                    hospitalScroll.contentY =
                        Math.max(
                            0,
                            Math.min(
                                scrollRail.maxContentY,
                                hospitalScroll.contentY
                                + step
                            )
                        );

                    wheel.accepted = true;
                }
            }
        }
    }
}
