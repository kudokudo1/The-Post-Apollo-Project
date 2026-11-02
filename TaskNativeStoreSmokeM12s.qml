//@ pragma DataDir $BASE/post-apollo-m12s-fixture
//@ pragma StateDir $BASE/post-apollo-m12s-state
import QtQuick
import Quickshell
import qs.services.hub

// TASKS M12s // Native *real store* smoke, never imported by shell.qml.
// This is not a ticket activation test. It loads the existing production
// singleton under a separately overridden per-shell data directory.
// Only explicit operator clicks can create/update the disposable task file.
// The source guards below refuse any write if the intended DataDir and
// explicit disposable-run environment marker are missing.
Scope {
    id: smoke

    readonly property string exactExpectedSuffix:
        "/post-apollo-m12s-fixture"
    readonly property string storePath: ApolloHubTodoStore.storagePath
    readonly property bool isolatedPath:
        Quickshell.dataDir.endsWith(exactExpectedSuffix)
        && storePath === Quickshell.dataDir + "/apollo-hub-todo-v1.json"
    readonly property bool operatorFixtureMode:
        Quickshell.env("POST_APOLLO_M12S_DISPOSABLE") === "1"
    readonly property bool guardedPath:
        isolatedPath && operatorFixtureMode
    readonly property bool flagsSafe:
        !ApolloHubTodoStore.guardedWriterEnabled
        && !ApolloHubTodoStore.ticketProducerEnabled
        && !ApolloHubTodoStore.independentlyAuthenticatedTicketReceipt
    readonly property bool canEditFixture:
        guardedPath && flagsSafe
        && (ApolloHubTodoStore.storageState === "empty"
            || ApolloHubTodoStore.storageState === "ready")

    property string lastAction: "NO ACTION"
    property bool actionRequested: false

    // Deliberately no startup mutations and no new FileView/Process.
    function testDisabledTicketRefusal() {
        if (!guardedPath || !flagsSafe) {
            lastAction = "REFUSED // UNSAFE FIXTURE OR FLAGS";
            return;
        }
        var attempt = ApolloHubTodoStore.submit(
            "HUB", "addTask", {args:{title:"M12S_DISABLED_TICKET_TEST"}});
        if (attempt && attempt.admitted === false
                && attempt.reason === "M12Q_DISABLED_NO_WRITER")
            lastAction = "PASS // TICKET ADMISSION REFUSED";
        else
            lastAction = "FAIL // UNEXPECTED TICKET OUTCOME";
    }

    function testLegacyWrite() {
        if (!canEditFixture) {
            lastAction = "REFUSED // NOT ISOLATED OR NOT READY";
            return;
        }
        // Only this explicit click may write to the test-only DataDir.
        var accepted = ApolloHubTodoStore.addTask("M12S_SYNTHETIC_TASK");
        actionRequested = accepted;
        lastAction = accepted
            ? "REQUESTED // WAIT FOR SAVED STATE"
            : "REFUSED // LEGACY STAGE";
    }

    function testReload() {
        if (!canEditFixture) {
            lastAction = "REFUSED // NOT READY";
            return;
        }
        lastAction = ApolloHubTodoStore.reloadFromDisk()
            ? "RELOAD REQUESTED // CHECK SNAPSHOT"
            : "REFUSED // RELOAD BLOCKED";
    }

    PanelWindow {
        id: testWindow
        visible: true
        implicitWidth: 640
        implicitHeight: 385
        focusable: true
        exclusiveZone: 0
        anchors { left: true; top: true }
        color: "#1B0623"

        Rectangle {
            anchors.fill: parent
            color: "#1B0623"
            border.color: "#55CFCA"
            border.width: 2

            Column {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 8

                Text {
                    text: "TASKS // M12s REAL STORE NATIVE SMOKE"
                    font.pixelSize: 16
                    font.bold: true
                    color: "#C74EC7"
                }
                Text {
                    text: "DISPOSABLE DATA ONLY // NEVER LIVE TASKS"
                    font.pixelSize: 12
                    color: "#F2BE4E"
                }
                Text {
                    width: parent.width
                    text: "ISOLATION // " + (smoke.guardedPath ? "VALID" : "INVALID / READ-ONLY")
                          + " // GATES " + (smoke.flagsSafe ? "DISABLED" : "UNSAFE")
                    font.pixelSize: 13
                    color: smoke.guardedPath && smoke.flagsSafe
                           ? "#9ece6a" : "#F2BE4E"
                }
                Text {
                    width: parent.width
                    wrapMode: Text.WrapAnywhere
                    text: "DATA DIR // " + Quickshell.dataDir
                    font.pixelSize: 11
                    color: "#DCF3FA"
                }
                Text {
                    width: parent.width
                    wrapMode: Text.WrapAnywhere
                    text: "SOURCE // " + smoke.storePath
                    font.pixelSize: 11
                    color: "#DCF3FA"
                }
                Text {
                    width: parent.width
                    text: "STORE // " + ApolloHubTodoStore.storageState
                          + " // ERROR " + (ApolloHubTodoStore.errorCode || "NONE")
                    font.pixelSize: 12
                    color: "#55CFCA"
                }
                Text {
                    width: parent.width
                    text: "TASKS // " + (ApolloHubTodoStore.snapshot.total || 0)
                          + " TOTAL // " + (ApolloHubTodoStore.snapshot.remaining || 0)
                          + " OPEN"
                    font.pixelSize: 12
                    color: "#DCF3FA"
                }
                Text {
                    width: parent.width
                    wrapMode: Text.WrapAnywhere
                    text: "RESULT // " + smoke.lastAction
                    font.pixelSize: 12
                    color: "#F2BE4E"
                }
                Row {
                    spacing: 10
                    Rectangle {
                        width: 175; height: 34
                        color: "#1B0623"; border.color: "#55CFCA"
                        Text {
                            anchors.centerIn: parent
                            text: "CHECK TICKET OFF"; color: "#DCF3FA"
                            font.pixelSize: 11
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: smoke.testDisabledTicketRefusal()
                        }
                    }
                    Rectangle {
                        width: 175; height: 34
                        color: "#1B0623"; border.color: "#ED981A"
                        Text {
                            anchors.centerIn: parent
                            text: "ADD FIXTURE TASK"; color: "#DCF3FA"
                            font.pixelSize: 11
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: smoke.testLegacyWrite()
                        }
                    }
                    Rectangle {
                        width: 175; height: 34
                        color: "#1B0623"; border.color: "#55CFCA"
                        Text {
                            anchors.centerIn: parent
                            text: "RELOAD FIXTURE"; color: "#DCF3FA"
                            font.pixelSize: 11
                        }
                        MouseArea {
                            anchors.fill: parent
                            onClicked: smoke.testReload()
                        }
                    }
                }
                Text {
                    width: parent.width
                    wrapMode: Text.WordWrap
                    text: "This panel uses ApolloHubTodoStore itself. "
                          + "The disabled ticket check cannot write. "
                          + "The ADD button uses the original legacy method "
                          + "only under the explicit disposable path guard."
                    font.pixelSize: 11
                    color: "#DCF3FA"
                }
                Text {
                    width: parent.width
                    text: "NO AUTOMATIC RETRY // NO PRODUCTION TICKET ENABLEMENT"
                    font.pixelSize: 10
                    color: "#F2BE4E"
                }
            }
        }
    }
}
