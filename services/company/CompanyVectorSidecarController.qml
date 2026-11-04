import QtQuick
import Quickshell
import Quickshell.Io

// Explicit, attached native Qt child. Separate from Coverage presentation,
// hub storage and the real company identity/permission model.
Item {
    id: controller
    visible: false
    readonly property bool running: vectorRunner.running
    property string status: "RUNTIME NOT CHECKED"
    property bool requestedStop: false
    property string output: ""

    function launch(online) {
        if (vectorRunner.running) return false;
        output="";
        requestedStop=false;
        status="LAUNCHING";
        vectorRunner.command = ["/usr/bin/python3",
            Quickshell.shellPath("services/company/CompanyVectorSidecarLaunch.py"),
            online ? "online" : "offline"];
        vectorRunner.running=true;
        return true;
    }

    function stop() {
        if (!vectorRunner.running) return false;
        requestedStop=true;
        status="CLOSING";
        // Quickshell Process sends SIGTERM. The Python wrapper execv()
        // replaces itself with Qt, so there is no detached subprocess.
        vectorRunner.running=false;
        return true;
    }

    Process {
        id: vectorRunner
        running: false
        stdout: StdioCollector {
            onStreamFinished: controller.output=String(text || "")
        }
        onStarted: controller.status="STARTED / NATIVE WINDOW UNVERIFIED"
        onExited: function(code, state) {
            if (controller.requestedStop) {
                controller.status="CLOSED";
                controller.requestedStop=false;
                return;
            }
            var result=null;
            try { result=JSON.parse(controller.output); } catch(e) {}
            if (result && result.status==="NOT_INSTALLED")
                controller.status="NOT INSTALLED";
            else if (result && result.status==="LAUNCH_FAILED")
                controller.status="LAUNCH FAILED";
            else
                controller.status="EXITED / CHECK NATIVE INSTALL";
        }
    }
}
