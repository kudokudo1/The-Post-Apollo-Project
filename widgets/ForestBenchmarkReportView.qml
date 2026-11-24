import QtQuick
import "../components"
import "../services/forest/ForestBenchmarkReportPolicy.js" as Reports

// Two operator-pasted P2B metadata reports. No runner, file opener, network,
// task text, persistence, or model selection. Imported values are unverified.
Item {
    id: pane
    property var reportA: null
    property var reportB: null
    property string importStatus: "NO REPORTS"
    function importReport(slot) {
        if (slot !== "A" && slot !== "B")
            return;
        const parsed = Reports.parseReport(reportInput.text);
        if (slot === "A") reportA = parsed;
        else reportB = parsed;
        reportInput.clear();
        importStatus = parsed ? slot + " // IMPORTED, UNVERIFIED" : slot + " // INVALID OR INCOMPLETE REPORT";
    }
    function clearReports() {
        reportA = null;
        reportB = null;
        reportInput.clear();
        importStatus = "NO REPORTS";
    }
    onVisibleChanged: if (!visible) clearReports()

    Flickable {
        id: scroll
        anchors.fill: parent
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        contentHeight: body.implicitHeight
        Column {
            id: body
            width: scroll.width
            spacing: 5
            GohuText {
                width: parent.width
                text: "BENCH // P2B REPORT COMPARISON"
                color: Colors.magenta
                font.pixelSize: 11
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: "Paste a complete P2B JSON report into A or B. Imported, not verified; no benchmark is run."
                color: Colors.orange
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }
            Rectangle {
                width: parent.width
                height: 26
                color: Colors.dark
                border.width: 1
                border.color: Colors.cyan
                clip: true
                TextInput {
                    id: reportInput
                    anchors.fill: parent
                    anchors.margins: 5
                    color: Colors.cyan
                    font.pixelSize: 10
                    maximumLength: 8193
                    selectByMouse: true
                    Accessible.name: "Paste one P2B metadata JSON report"
                }
                GohuText {
                    anchors.centerIn: parent
                    visible: reportInput.text.length === 0
                    text: "PASTE REPORT JSON"
                    color: Colors.orange
                    font.pixelSize: 9
                }
            }
            Row {
                width: parent.width
                spacing: 3
                Repeater {
                    model: ["IMPORT A","IMPORT B","CLEAR"]
                    delegate: Rectangle {
                        required property string modelData
                        width: (body.width - 6) / 3
                        height: 23
                        color: Colors.dark
                        border.width: 1
                        border.color: Colors.cyan
                        Accessible.name: modelData
                        GohuText {
                            anchors.centerIn: parent
                            text: parent.modelData
                            color: Colors.cyan
                            font.pixelSize: 9
                        }
                        MouseArea {
                            anchors.fill: parent
                            cursorShape: Qt.PointingHandCursor
                            onClicked: {
                                if (parent.modelData === "CLEAR") pane.clearReports();
                                else pane.importReport(parent.modelData === "IMPORT A" ? "A" : "B");
                            }
                        }
                    }
                }
            }
            GohuText {
                width: parent.width
                text: pane.importStatus
                color: Colors.orange
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }
            Repeater {
                model: [pane.reportA, pane.reportB]
                delegate: GohuText {
                    required property var modelData
                    required property int index
                    width: body.width
                    text: (index === 0 ? "A // " : "B // ") + (modelData
                        ? modelData.model + " / " + modelData.scenario.toUpperCase()
                          + " / OLLAMA " + modelData.ollama_version : "NO REPORT")
                    textFormat: Text.PlainText
                    color: Colors.cyan
                    font.pixelSize: 10
                    wrapMode: Text.WrapAnywhere
                }
            }
            GohuText {
                width: parent.width
                text: Reports.comparison(pane.reportA,pane.reportB)
                color: Colors.orange
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }
            GohuText {
                width: parent.width
                text: "FIXED P2B // CTX 2048 / OUTPUT CAP 32 / THINK OFF / ONE REQUEST"
                color: Colors.cyan
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }
            Repeater {
                model: [
                    {label:"FIRST VISIBLE CONTENT", key:"first_visible_content_ms", unit:"ms"},
                    {label:"GENERATION RATE (PROVIDER)", key:"provider_generated_tokens_per_second", unit:"tok/s"},
                    {label:"CLIENT COMPLETE", key:"client_complete_ms", unit:"ms"},
                    {label:"RESPONSE HEADERS", key:"headers_latency_ms", unit:"ms"},
                    {label:"PROVIDER LOAD", key:"provider_load_ms", unit:"ms"},
                    {label:"PROMPT EVAL", key:"provider_prompt_eval_ms", unit:"ms"},
                    {label:"GENERATION EVAL", key:"provider_eval_ms", unit:"ms"},
                    {label:"PROVIDER TOTAL", key:"provider_total_ms", unit:"ms"},
                    {label:"PROMPT TOKENS", key:"provider_prompt_eval_count", unit:"tokens"},
                    {label:"CACHED PROMPT TOKENS", key:"provider_prompt_cached_count", unit:"tokens"},
                    {label:"GENERATED TOKENS", key:"provider_eval_count", unit:"tokens"}
                ]
                delegate: Column {
                    required property var modelData
                    width: body.width
                    spacing: 2
                    GohuText {
                        width: parent.width
                        text: parent.modelData.label
                        color: Colors.magenta
                        font.pixelSize: 9
                        wrapMode: Text.WordWrap
                    }
                    Row {
                        width: parent.width
                        spacing: 4
                        GohuText {
                            width: (parent.width - 4) / 2
                            text: "A " + Reports.metric(pane.reportA ? pane.reportA[parent.parent.modelData.key] : null,
                                parent.parent.modelData.unit)
                            color: Colors.cyan
                            font.pixelSize: 9
                            wrapMode: Text.WrapAnywhere
                        }
                        GohuText {
                            width: (parent.width - 4) / 2
                            text: "B " + Reports.metric(pane.reportB ? pane.reportB[parent.parent.modelData.key] : null,
                                parent.parent.modelData.unit)
                            color: Colors.cyan
                            font.pixelSize: 9
                            wrapMode: Text.WrapAnywhere
                        }
                    }
                }
            }
            GohuText {
                width: parent.width
                text: "NO QUALITY SCORE, HARDWARE PROOF, OR SPEED WINNER // IMPORTED REPORTS ONLY"
                color: Colors.orange
                font.pixelSize: 9
                wrapMode: Text.WordWrap
            }
        }
    }
}
