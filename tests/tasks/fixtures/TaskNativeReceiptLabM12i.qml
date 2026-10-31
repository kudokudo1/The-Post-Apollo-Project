import QtQuick
import Quickshell
import Quickshell.Io

// M12i STANDALONE DISPOSABLE native lab. Never import from shell.qml.
// Exactly one test-only FileView. The Python host never writes JSON.
// The UI's onSaved is a hint; actual bytes and SQLite receipt are checked
// independently by TaskNativeReceiptHostM12i.py.
Scope {
    id: lab
    property string fixturePath: ""
    property string writerId: ""
    property bool bootstrapFixture: false
    property bool attached: false
    property bool fileLoaded: false
    property bool connected: false
    property bool busy: false
    property bool freezeQueued: false
    property string phase: "UNVERIFIED"
    property string fileState: "UNLOADED"
    property string status: "NOT_STARTED"
    property int epoch: -1
    property int counter: -1
    property int settledCount: 0
    property int requestId: 1
    property int awaitingId: -1
    property string awaitingKind: ""
    property string pendingStage: ""
    property string pendingRaw: ""
    property int pendingEpoch: -1
    readonly property bool liveTasksAuthorized: false
    readonly property bool productionWriterAuthorized: false
    readonly property bool independentNativeStageAttributionProven: false
    readonly property bool actualNativeReceiptAcceptanceRecorded: false
    readonly property bool canIncrement:
        connected && fileLoaded && !busy && !freezeQueued &&
        phase === "JSON_ACTIVE" && fileState === "READY" &&
        pendingStage === ""

    function reject(code) {
        status = "RECOVERY_REVIEW / " + code;
        phase = "RECOVERY_REVIEW";
        fileState = "RECOVERY_REVIEW";
        attached = false;
        connected = false;
        busy = false;
        freezeQueued = true;
        pendingStage = "";
        pendingRaw = "";
        pendingEpoch = -1;
        awaitingId = -1;
        awaitingKind = "";
        if (host.running) host.running = false;
    }

    function startTest() {
        if (attached || host.running || busy) return false;
        if (!/^\/.+\/m11e-fileview-test\/fixture-only\.json$/.test(fixturePath)
                || !/^[A-Za-z0-9][A-Za-z0-9._:-]{7,95}$/.test(writerId)) {
            reject("DISPOSABLE_FIXTURE_REQUIRED");
            return false;
        }
        attached = true;
        busy = true;
        connected = false;
        fileLoaded = false;
        fileState = "LOADING";
        phase = "UNVERIFIED";
        status = "CONNECTING";
        counter = -1;
        settledCount = 0;
        epoch = -1;
        requestId = 1;
        awaitingId = 0;
        awaitingKind = "hello";
        pendingStage = "";
        pendingRaw = "";
        pendingEpoch = -1;
        freezeQueued = false;
        var command = ["python3", "-B", "-I",
            Quickshell.shellPath("tests/tasks/fixtures/TaskNativeReceiptHostM12i.py"),
            "--db", fixturePath.slice(0, fixturePath.lastIndexOf("/") + 1)
                 + "handoff-test.db",
            "--writer-id", writerId];
        if (bootstrapFixture) command.push("--bootstrap-fixture");
        host.exec(command);
        return true;
    }

    function send(kind, data) {
        if (!connected || !host.running || busy || requestId > 60) return false;
        var message = {requestId:requestId, kind:kind};
        if (kind === "reserve") message.stageId = data.stageId;
        else if (kind === "verify") {
            message.stageId = data.stageId;
            message.epoch = data.epoch;
        } else if (kind === "freeze") message.epoch = epoch;
        else if (kind !== "status") return false;
        awaitingId = requestId;
        awaitingKind = kind;
        requestId++;
        busy = true;
        host.write(JSON.stringify(message) + "\n");
        return true;
    }

    function increment() {
        if (!canIncrement) return false;
        pendingStage = "m12i-native-stage-" + requestId;
        fileState = "RESERVING";
        if (!send("reserve",{stageId:pendingStage})) {
            reject("RESERVE_SEND_FAILED"); return false;
        }
        return true;
    }

    function freeze() {
        if (!connected || phase !== "JSON_ACTIVE" || freezeQueued)
            return false;
        freezeQueued = true;
        if (!busy && pendingStage === "" && !send("freeze",{})) {
            reject("FREEZE_SEND_FAILED"); return false;
        }
        return true;
    }

    function stop() {
        status = "STOPPED / FUTURE OWNER MUST REVIEW";
        phase = "RECOVERY_REVIEW";
        fileState = "RECOVERY_REVIEW";
        freezeQueued = true;
        connected = false;
        attached = false;
        pendingStage = "";
        pendingRaw = "";
        pendingEpoch = -1;
        if (host.running) host.running = false;
    }

    function afterSettlement() {
        pendingStage = "";
        pendingRaw = "";
        pendingEpoch = -1;
        fileState = "READY";
        if (freezeQueued && phase === "JSON_ACTIVE" &&
                !send("freeze",{}))
            reject("FREEZE_AFTER_SETTLEMENT_FAILED");
    }

    function acceptLine(line) {
        if (!busy || awaitingId < 0 || line.length > 4096) {
            reject("UNEXPECTED_HOST_LINE"); return;
        }
        try {
            var msg = JSON.parse(line);
            var keys = ["protocol","requestId","kind","ok","status",
                "phase","epoch","pending","stageId","payload","actualSha256",
                "productionWriterAuthorized","nativeStageAttributionProven",
                "realTasksAccessAuthorized"];
            if (!msg || typeof msg !== "object" || Array.isArray(msg) ||
                    Object.keys(msg).length !== keys.length)
                throw new Error("BAD_HOST_SHAPE");
            for (var i=0; i<keys.length; i++)
                if (!Object.prototype.hasOwnProperty.call(msg,keys[i]))
                    throw new Error("MISSING_HOST_FIELD");
            if (msg.protocol !== 1 || msg.requestId !== awaitingId ||
                    msg.kind !== awaitingKind || typeof msg.ok !== "boolean" ||
                    typeof msg.status !== "string" || msg.status.length > 80 ||
                    typeof msg.pending !== "boolean" ||
                    (msg.epoch !== null &&
                     (!Number.isSafeInteger(msg.epoch) || msg.epoch < 0)) ||
                    (msg.stageId !== null && typeof msg.stageId !== "string") ||
                    (msg.payload !== null && typeof msg.payload !== "string") ||
                    (msg.actualSha256 !== null &&
                     (typeof msg.actualSha256 !== "string" ||
                      !/^[a-f0-9]{64}$/.test(msg.actualSha256))) ||
                    msg.productionWriterAuthorized !== false ||
                    msg.nativeStageAttributionProven !== false ||
                    msg.realTasksAccessAuthorized !== false ||
                    ["JSON_ACTIVE","FREEZE_REQUESTED","JSON_QUIESCED",
                     "RECOVERY_REVIEW","UNVERIFIED"].indexOf(msg.phase) < 0)
                throw new Error("UNSAFE_HOST_FRAME");
            var kind = awaitingKind;
            awaitingId = -1;
            awaitingKind = "";
            busy = false;
            phase = msg.phase;
            epoch = msg.epoch === null ? -1 : msg.epoch;
            if (!msg.ok) {
                reject("HOST_REFUSED_" + msg.status); return;
            }
            connected = true;
            status = "SYNTHETIC_HOST_READY";
            if (kind === "hello") {
                if (phase !== "JSON_ACTIVE" || msg.pending) {
                    reject("FRESH_OWNER_RECOVERY_REQUIRED"); return;
                }
            } else if (kind === "reserve") {
                if (phase !== "JSON_ACTIVE" || !msg.pending ||
                        msg.stageId !== pendingStage ||
                        fileState !== "RESERVING" ||
                        typeof msg.payload !== "string" ||
                        msg.payload.length > 2048)
                    throw new Error("INVALID_RESERVED_STAGE");
                var doc = JSON.parse(msg.payload);
                if (doc.fixture !== "M11E_SYNTHETIC_ONLY" ||
                        doc.marker !== "sample" ||
                        !Number.isSafeInteger(doc.counter) ||
                        doc.counter !== counter + 1 ||
                        doc.revision !== doc.counter)
                    throw new Error("BAD_FIXTURE_PAYLOAD");
                pendingRaw = msg.payload;
                pendingEpoch = epoch;
                fileState = "SAVING";
                fixtureFile.setText(pendingRaw);
            } else if (kind === "verify") {
                if (phase !== "JSON_ACTIVE" || msg.pending ||
                        msg.stageId !== pendingStage ||
                        fileState !== "SETTLING" ||
                        msg.actualSha256 === null ||
                        epoch !== pendingEpoch)
                    throw new Error("BAD_STAGE_RECEIPT");
                counter++;
                settledCount++;
                status = "TEST_RECEIPT_SETTLED_UI_UNACKNOWLEDGED";
                afterSettlement();
            } else if (kind === "freeze") {
                if (!freezeQueued || phase !== "FREEZE_REQUESTED" ||
                        msg.pending)
                    throw new Error("FREEZE_REFUSED");
                fileState = "FROZEN";
                status = "TEST_FROZEN";
            }
        } catch(e) {reject("INVALID_HOST_RESPONSE");}
    }

    FileView {
        id: fixtureFile
        path: lab.attached ? lab.fixturePath : ""
        atomicWrites: true
        blockWrites: false
        watchChanges: false
        printErrors: false
        onLoaded: {
            if (!lab.attached) return;
            if (lab.fileState === "LOADING") {
                try {
                    var doc=JSON.parse(fixtureFile.text());
                    if (doc.fixture !== "M11E_SYNTHETIC_ONLY" ||
                            doc.marker !== "sample" ||
                            !Number.isSafeInteger(doc.counter) ||
                            doc.revision !== doc.counter)
                        throw new Error("INVALID_TEST_FILE");
                    lab.counter = doc.counter;
                    lab.fileLoaded = true;
                    lab.fileState = "READY";
                } catch(e) {lab.reject("BAD_INITIAL_FIXTURE");}
            } else if (lab.fileState === "VERIFYING") {
                // UI-level check is helpful but NOT a trusted OS readback.
                if (fixtureFile.text() !== lab.pendingRaw) {
                    lab.reject("QML_DEFERRED_READBACK_MISMATCH");
                } else {
                    lab.fileState = "SETTLING";
                    if (!lab.send("verify",{
                        stageId:lab.pendingStage,epoch:lab.pendingEpoch
                    })) lab.reject("VERIFY_SEND_FAILED");
                }
            } else lab.reject("UNEXPECTED_FILE_RELOAD");
        }
        onLoadFailed: function(error) {if (lab.attached) lab.reject("FILE_LOAD_FAILED");}
        onSaved: {
            if (lab.fileState !== "SAVING" || lab.pendingStage === "") {
                lab.reject("UNEXPECTED_SAVED_HINT"); return;
            }
            lab.fileState="VERIFYING";
            var callbackStage=lab.pendingStage;
            var callbackEpoch=lab.pendingEpoch;
            // M11g-established native requirement: defer reload until
            // FileView saved() unwinds. Stage correlation here is only local.
            Qt.callLater(function() {
                if (lab.attached && lab.connected &&
                        lab.fileState === "VERIFYING" &&
                        lab.pendingStage === callbackStage &&
                        lab.pendingEpoch === callbackEpoch &&
                        lab.pendingRaw !== "")
                    fixtureFile.reload();
            });
        }
        onSaveFailed: function(error) {lab.reject("FILE_SAVE_FAILED");}
    }

    Process {
        id: host
        stdinEnabled: true
        stdout: SplitParser {
            splitMarker: "\n"
            onRead: function(line) {lab.acceptLine(line);}
        }
        stderr: StdioCollector {}
        onExited: function(code, exitStatus) {
            lab.connected=false;
            lab.busy=false;
            lab.freezeQueued=true;
            lab.attached=false;
            lab.fileState="RECOVERY_REVIEW";
            lab.phase="RECOVERY_REVIEW";
            if (lab.status !== "STOPPED / FUTURE OWNER MUST REVIEW")
                lab.status="HOST_EXITED_REVIEW_REQUIRED";
        }
    }

    PanelWindow {
        visible: true
        implicitWidth: 590
        implicitHeight: 375
        focusable: true
        exclusiveZone: 0
        anchors { left: true; top: true }
        color: "#1B0623"
        Rectangle {
            anchors.fill: parent
            color: "#1B0623"
            border.color: "#55CFCA"
            Column {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 7
                Text {
                    text: "M12i // NATIVE STAGE RECEIPT LAB"
                    color: "#C74EC7"
                    font.pixelSize: 15
                    font.bold: true
                }
                Text {
                    text: "DISPOSABLE ONLY // NO PRODUCTION WRITER OR TRUST CLAIM"
                    color: "#F2BE4E"
                    font.pixelSize: 11
                }
                Text {text: "Private fixture file";color: "#55CFCA";font.pixelSize: 11}
                Rectangle {
                    width: parent.width;height: 30
                    color: "#1B0623";border.color: "#55CFCA"
                    TextInput {
                        id: pathField
                        anchors.fill: parent;anchors.margins: 6
                        text: "";color: "#DCF3FA";selectByMouse: true
                        font.pixelSize: 11
                        onTextChanged: lab.fixturePath = text.trim()
                    }
                }
                Text {text: "Synthetic writer ID";color: "#55CFCA";font.pixelSize: 11}
                Rectangle {
                    width: parent.width;height: 30
                    color: "#1B0623";border.color: "#55CFCA"
                    TextInput {
                        anchors.fill: parent;anchors.margins: 6
                        text: "";color: "#DCF3FA";selectByMouse: true
                        font.pixelSize: 11
                        onTextChanged: lab.writerId = text.trim()
                    }
                }
                Flow {
                    spacing: 6;width: parent.width
                    Repeater {
                        model: ["NEW TEST","EXISTING","INCREMENT","FREEZE","STOP"]
                        Rectangle {
                            required property string modelData
                            width: 104;height: 28
                            color: area.pressed ? "#C74EC7" : "#1B0623"
                            border.color: "#55CFCA"
                            Text {
                                anchors.centerIn: parent
                                text: modelData
                                color: "#DCF3FA";font.pixelSize: 10
                            }
                            MouseArea {
                                id: area
                                anchors.fill: parent
                                onClicked: {
                                    if (modelData === "NEW TEST") {
                                        lab.bootstrapFixture=true;
                                        lab.startTest();
                                    } else if (modelData === "EXISTING") {
                                        lab.bootstrapFixture=false;
                                        lab.startTest();
                                    } else if (modelData === "INCREMENT")
                                        lab.increment();
                                    else if (modelData === "FREEZE")
                                        lab.freeze();
                                    else if (modelData === "STOP")
                                        lab.stop();
                                }
                            }
                        }
                    }
                }
                Text {
                    width:parent.width;wrapMode:Text.WordWrap
                    text: "PHASE: "+lab.phase+" // FILE: "+lab.fileState+
                          " // COUNTER: "+lab.counter+" // RECEIPTS: "+lab.settledCount
                    color:"#DCF3FA";font.pixelSize:11
                }
                Text {
                    width:parent.width;wrapMode:Text.WordWrap
                    text:"STATUS: "+lab.status
                    color:"#55CFCA";font.pixelSize:11
                }
                Text {
                    width:parent.width;wrapMode:Text.WordWrap
                    text:"NATIVE STAGE ATTRIBUTION: NOT PROVEN. "+
                         "Host independently rereads synthetic bytes. "+
                         "Durable receipt is not a production authorization."
                    color:"#F2BE4E";font.pixelSize:10
                }
            }
        }
    }
}
