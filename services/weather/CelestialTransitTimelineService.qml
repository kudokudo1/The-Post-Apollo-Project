import QtQuick
import Quickshell
import Quickshell.Io
import "CelestialVisualInstallPolicy.js" as Install
import "../../widgets/weather/StationMagickTransitTimelinePolicy.js" as Timeline

// M8g // Explicit one-shot M8f JPL search, not a daemon or automatic watcher.
// Private event and observer data cross stdin ONLY; no user data in argv,
// logs, filesystem, cache, settings, notifications or the network.
Scope {
    id: finder
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
    readonly property string statusText: !configured?"LOCAL SKYFIELD/JPL NOT CONFIGURED"
        : loading?"SEARCHING VERIFIED JPL TRANSITS"
        : failed?errorText
        : ready?"SOURCE-VERIFIED CONTACTS"
        :"SELECT UTC RANGE AND PLANET PAIR"

    function clearState() {
        if(calculator.running)calculator.running=false;
        pending=null;received=false;ready=false;failed=false;
        errorText="";result=null;
    }
    function search(startDate,span,natalBody,transitBody,step) {
        if(!active||!configured||calculator.running)return false;
        const req=Timeline.request(natalChart,startDate,span,natalBody,transitBody,step);
        clearState();
        if(!req){
            failed=true;errorText="COMPLETE NATAL CHART + VALID UTC RANGE REQUIRED";
            return false;
        }
        pending=req;
        calculator.command=[
            pythonExecutable,"-B",
            Quickshell.configDir+"/scripts/weather/celestial_transit_timeline.py",
            "--kernel",kernelPath
        ];
        calculator.running=true;
        return true;
    }
    function accept(raw) {
        if(!active||!pending)return;
        try{
            const text=String(raw||"");
            if(text.length<100||text.length>65536)
                throw new Error("bounded output rejected");
            const source=JSON.parse(text);
            const checked=Timeline.validate(source,pending,natalChart);
            if(!checked.ready)throw new Error("source validation rejected");
            result=checked;ready=true;received=true;failed=false;errorText="";
        }catch(e) {
            ready=false;result=null;received=false;failed=true;
            errorText="JPL TRANSIT RESPONSE INVALID";
        }
    }
    Process {
        id:calculator
        command:[]
        stdinEnabled:true
        onStarted:{
            if(!finder.active||!finder.pending){
                calculator.running=false;return;
            }
            calculator.write(JSON.stringify(finder.pending)+"\n");
        }
        stdout: StdioCollector {
            onStreamFinished: finder.accept(text)
        }
        onExited:function(exitCode,exitStatus){
            if(!finder.active||!finder.pending)return;
            if(exitCode!==0){
                finder.ready=false;finder.result=null;finder.failed=true;
                finder.errorText="JPL TRANSIT SEARCH UNAVAILABLE";
            }else if(!finder.received){
                finder.ready=false;finder.failed=true;
                finder.errorText="NO VERIFIED CONTACT TIMELINE RETURNED";
            }
            finder.pending=null;
        }
    }
    onActiveChanged:if(!active)clearState()
    onNatalChartChanged:clearState()
    onKernelPathChanged:clearState()
    onPythonExecutableChanged:clearState()
}
