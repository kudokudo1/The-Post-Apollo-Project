import QtQuick
import Quickshell
import Quickshell.Io
import "CelestialVisualInstallPolicy.js" as Install
import "../../widgets/weather/StationMagickNatalRequestPolicy.js" as Request
import "../../widgets/weather/StationMagickNatalWheelPolicy.js" as Wheel

// M8b // One user-triggered local Python/JPL calculation with private stdin.
// No birth details in argv, URLs, environment variables, files or logs.
// Clears results and kills in-flight process when the owning pane goes away.
Scope {
    id: natalService
    property bool active: false
    readonly property string installHome: String(Quickshell.env("HOME")||"")
    readonly property string kernelPath: Install.resolveKernel(
        String(Quickshell.env("POST_APOLLO_CELESTIAL_KERNEL")||""),installHome)
    readonly property string pythonExecutable: Install.resolvePython(
        String(Quickshell.env("POST_APOLLO_CELESTIAL_PYTHON")||""),installHome)
    readonly property bool configured: kernelPath!==""&&pythonExecutable!==""
    property bool ready: false
    property bool failed: false
    property string errorText: ""
    property var chartData: null
    // Only short-lived memory. Reset on completion, cancellation or navigation.
    property var pending: null
    property bool received: false
    readonly property bool loading: calculator.running
    readonly property string statusText: !configured
        ? "LOCAL JPL INSTALLATION UNAVAILABLE"
        : loading ? "CALCULATING PRIVATE NATAL CHART"
        : failed ? errorText : ready ? "SOURCE-VERIFIED NATAL CHART"
        : "ENTER UTC EVENT DETAILS"

    function clearState(){
        if(calculator.running) calculator.running=false;
        pending=null;received=false;chartData=null;
        ready=false;failed=false;errorText="";
    }
    function calculate(draft) {
        if(!active||!configured||calculator.running)return false;
        const req=Request.fromDraft(draft);
        if(!req){
            clearState();failed=true;
            errorText="TROPICAL UTC EVENT INPUT REQUIRED";return false;
        }
        clearState();
        pending=req;
        calculator.command=[
            pythonExecutable,"-B",
            Quickshell.configDir+"/scripts/weather/celestial_natal_chart.py",
            "--kernel",kernelPath
        ];
        // No PII is embedded in command-line args.
        calculator.running=true;
        return true;
    }
    function accept(raw){
        if(!active||!pending)return;
        try {
            const text=String(raw||"");
            if(text.length<100||text.length>16384)
                throw new Error("unexpected result size");
            const value=JSON.parse(text);
            const chart=Wheel.validate(value);
            if(!chart.ready||!Request.matches(value,pending))
                throw new Error("source chart or request mismatch");
            chartData=value;
            ready=true;failed=false;errorText="";
            received=true;
        }catch(e){
            chartData=null;ready=false;failed=true;
            errorText="JPL NATAL RESPONSE INVALID";
        }
    }
    Process {
        id: calculator
        command: []
        stdinEnabled: true
        onStarted: {
            if(!natalService.active||!natalService.pending) {
                calculator.running=false;return;
            }
            // Python consumes exactly one bounded JSON *line* from stdin.
            calculator.write(JSON.stringify(natalService.pending)+"\n");
        }
        stdout: StdioCollector {
            onStreamFinished: natalService.accept(text)
        }
        onExited: function(exitCode,exitStatus) {
            if(!natalService.active||!natalService.pending)return;
            if(exitCode!==0){
                natalService.chartData=null;natalService.ready=false;
                natalService.failed=true;
                natalService.errorText="NATAL JPL / UTC / HOUSE CALCULATION UNAVAILABLE";
            }else if(!natalService.received){
                natalService.ready=false;natalService.failed=true;
                natalService.errorText="NO VERIFIED NATAL CHART RETURNED";
            }
            // Keep the computed chart, forget the input payload.
            natalService.pending=null;
        }
    }
    onActiveChanged: if(!active)clearState()
    onKernelPathChanged: clearState()
    onPythonExecutableChanged: clearState()
}
