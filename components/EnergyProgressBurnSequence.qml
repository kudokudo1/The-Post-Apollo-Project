import QtQuick

// Presentation only. External owner supplies the arm clock and verified
// backend outcome. This component cannot arm, confirm, delete or retry.
Item {
    id: sequence
    property bool armed: false
    property bool armReady: false
    property real armProgress: 0
    property string operationStage: ""
    property bool verified: false
    property string idleCaption: ""
    property bool reducedMotion: false
    readonly property bool terminal: operationStage === "result" || operationStage === "error"
    readonly property bool verifiedResult: operationStage === "result" && verified
    readonly property bool operationVisible: operationStage === "working" || terminal
    readonly property bool ashVisible: !operationVisible && armed
    readonly property bool receiptReady: terminal && (verifiedResult
        ? burnFace.phase === "success" && burnFace.fireState.repair >= 1
        : burnFace.phase === "failure" && (burnFace.finishFrom <= 0 || !burnFace.fireState.active))
    readonly property string burnPhase: terminal && !verifiedResult ? "failure"
        : verifiedResult && (travel >= .9 || reducedMotion) ? "success"
        : operationVisible ? "running" : "idle"
    readonly property real burnFraction: burnFace.displayedFraction
    readonly property real ashFraction: ashFace.displayedFraction
    readonly property string ashPhase: ashFace.phase
    property real travel: 0

    // Visual pacing only: an instantaneous verified backend result still
    // receives a readable sweep, never an invented backend percentage.
    onOperationStageChanged: {
        if(operationStage === "" || operationStage === "clicked") {
            travelAnimation.stop();
            travel=0;
        } else if(operationStage === "working" || verifiedResult) {
            if(!travelAnimation.running && travel<.9)
                travelAnimation.start();
        } else {
            travelAnimation.stop();
        }
    }
    NumberAnimation {
        id: travelAnimation
        target: sequence
        property: "travel"
        to: .9
        duration: 1800
        easing.type: Easing.Linear
    }
    EnergyProgressFace {
        id: ashFace
        anchors.fill: parent
        variant: "flamethrower"
        fireMode: "ash-trail"
        energyColor: Colors.orange
        chassisColor: sequence.operationStage === "clicked" ? Colors.magenta : Colors.red
        reducedMotion: sequence.reducedMotion
        progressMode: "timed"
        progress: sequence.armProgress
        phase: sequence.ashVisible ? (sequence.armReady ? "ready" : "running") : "idle"
        visible: sequence.ashVisible
        caption: sequence.idleCaption
    }
    EnergyProgressFace {
        id: burnFace
        anchors.fill: parent
        variant: "flamethrower"
        fireMode: "burn-away"
        remainingAsh: true
        energyColor: Colors.orange
        chassisColor: Colors.red
        reducedMotion: sequence.reducedMotion
        progressMode: "timed"
        progress: sequence.travel
        phase: sequence.burnPhase
        visible: sequence.operationVisible
        caption: sequence.verifiedResult ? "VERIFIED // FINISHING"
            : sequence.terminal ? "PARTIAL // UNVERIFIED" : "BURNING..."
    }
    GohuText {
        anchors.fill: parent
        anchors.margins: 6
        visible: !sequence.ashVisible && !sequence.operationVisible
        color: Colors.white
        font.pixelSize: 10
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
        text: sequence.idleCaption
    }
}
