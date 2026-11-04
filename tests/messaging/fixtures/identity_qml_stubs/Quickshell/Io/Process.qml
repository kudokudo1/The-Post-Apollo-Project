import QtQml

// CI fixture: Qt owns the real QObject/QML bindings, but no OS process starts.
// This stub lets the test inject stdout, process failure and delayed replies.
QtObject {
    objectName: "ciSnapshotProcess"
    property var command: []
    property bool running: false
    property bool stdinEnabled: false
    property string lastInput: ""
    signal started()
    onRunningChanged: {
        if (running) started();
    }
    function write(text) { lastInput = String(text); }
    property QtObject stdout
    property QtObject stderr
    signal exited(int exitCode, int exitStatus)

    function finishWith(output, code) {
        if (stdout) {
            stdout.text = output;
            stdout.streamFinished();
        }
        running = false;
        exited(code, 0);
    }
}
