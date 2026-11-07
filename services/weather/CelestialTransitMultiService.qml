import QtQuick
import Quickshell
import Quickshell.Io
import "CelestialVisualInstallPolicy.js" as Install
import "../../widgets/weather/StationMagickTransitMultiPolicy.js" as Multi

// M8h // The only new process is one explicit, cancellable local JPL search.
// Birth/event coordinates travel via stdin; argv contains kernel path only.
// No stored charts, GPS polling, downloads, user cache or auto refresh.
Scope {
    id: multiSource
    property bool active: false
    property var natalChart: null
    readonly property string home: String(Quickshell.env("HOME")||"")
    readonly property string kernelPath: Install.resolveKernel(
        String(Quickshell.env("POST_APOLLO_CELESTIAL_KERNEL")||""),home)
    readonly property string pythonExecutable: Install.resolvePython(
        String(Quickshell.env("POST_APOLLO_CELESTIAL_PYTHON")||""),home)
    readonly property bool configured: kernelPath!==""&&pythonExecutable!==""
    property var pending: null
    property bool received: false
    property bool ready: false
    property bool failed: false
    property string errorText: ""
    property var result: null
    readonly property bool loading: calculator.running
    readonly property string statusText: !configured
        ? "LOCAL JPL / SKYFIELD UNAVAILABLE"
        : loading ? "CALCULATING MULTI-PLANET EVENTS"
        : failed ? errorText
        : ready ? "SOURCE-VERIFIED MULTI-TRANSIT EVENTS"
        : "SELECT UP TO THREE TRANSIT PLANETS"

    function clearState() {
        if(calculator.running)calculator.running=false;
        pending=null;received=false;ready=false;failed=false;
        errorText="";result=null;
    }
    function search(startDate,days,natalBody,moving,aspects,step) {
        if(!active||!configured||calculator.running)return false;
        const req=Multi.request(natalChart,startDate,days,
                                natalBody,moving,aspects,step);
        clearState();
        if(!req){
            failed=true;errorText="COMPLETE NATAL CHART / UTC / BODY FILTER REQUIRED";
            return false;
        }
        pending=req;
        calculator.command=[
            pythonExecutable,"-B",
            Quickshell.configDir+"/scripts/weather/celestial_transit_multi.py",
            "--kernel",kernelPath
        ];
        calculator.running=true;
        return true;
    }
    function accept(raw) {
        if(!active||!pending)return;
        try{
            const source=String(raw||"");
            if(source.length<100||source.length>125000)
                throw new Error("bounded multi-transit output required");
            const checked=Multi.validate(JSON.parse(source),pending,natalChart);
            if(!checked.ready)throw new Error("source mismatch");
            result=checked;ready=true;received=true;failed=false;errorText="";
        }catch(e){
            result=null;ready=false;received=false;failed=true;
            errorText="MULTI-JPL RESPONSE REJECTED";
        }
    }
    Process {
        id:calculator
        command:[]
        stdinEnabled:true
        onStarted:{
            if(!multiSource.active||!multiSource.pending){
                calculator.running=false;return;
            }
            calculator.write(JSON.stringify(multiSource.pending)+"\n");
        }
        stdout: StdioCollector {
            onStreamFinished:multiSource.accept(text)
        }
        onExited:function(exitCode,exitStatus) {
            if(!multiSource.active||!multiSource.pending)return;
            if(exitCode!==0){
                multiSource.ready=false;multiSource.result=null;
                multiSource.failed=true;
                multiSource.errorText="MULTI-JPL COMPUTATION UNAVAILABLE";
            }else if(!multiSource.received){
                multiSource.ready=false;multiSource.failed=true;
                multiSource.errorText="NO VERIFIED MULTI-TRANSIT RESPONSE";
            }
            multiSource.pending=null;
        }
    }
    onActiveChanged:if(!active)clearState()
    onNatalChartChanged:clearState()
    onKernelPathChanged:clearState()
    onPythonExecutableChanged:clearState()
}
