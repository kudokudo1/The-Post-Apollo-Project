import QtQuick
import Quickshell
import Quickshell.Io
import "CelestialVisualInstallPolicy.js" as Install
import "../../widgets/weather/StationMagickTransitMatrixPolicy.js" as Matrix

// M8k // One deliberately requested private multi-natal/moving-body calculation.
// Same installed kernel/Python as M8h. Private input via stdin, never argv/logs.
Scope {
    id:matrixSource
    property bool active:false
    property var natalChart:null
    readonly property string home:String(Quickshell.env("HOME")||"")
    readonly property string kernelPath:Install.resolveKernel(
        String(Quickshell.env("POST_APOLLO_CELESTIAL_KERNEL")||""),home)
    readonly property string pythonExecutable:Install.resolvePython(
        String(Quickshell.env("POST_APOLLO_CELESTIAL_PYTHON")||""),home)
    readonly property bool configured:kernelPath!==""&&pythonExecutable!==""
    property var pending:null
    property bool received:false
    property bool ready:false
    property bool failed:false
    property string errorText:""
    property var result:null
    readonly property bool loading:runner.running
    readonly property string statusText:!configured?"LOCAL JPL / SKYFIELD UNAVAILABLE":
        loading?"CALCULATING VERIFIED JPL MATRIX":
        failed?errorText:
        ready?"VERIFIED NATAL × TRANSIT EVENTS":
        "SELECT 1-3 NATAL AND 1-3 TRANSIT BODIES"
    function clearState(){
        if(runner.running)runner.running=false;
        pending=null;received=false;ready=false;failed=false;
        errorText="";result=null;
    }
    function search(day,span,natals,moving,aspects,cadence){
        if(!active||!configured||runner.running)return false;
        const req=Matrix.request(natalChart,day,span,natals,moving,aspects,cadence);
        clearState();
        if(!req){
            failed=true;
            errorText="REDUCE PLANETS / RANGE OR VERIFY NATAL DATA";
            return false;
        }
        pending=req;
        runner.command=[
            pythonExecutable,"-B",
            Quickshell.configDir+"/scripts/weather/celestial_transit_matrix.py",
            "--kernel",kernelPath
        ];
        runner.running=true;
        return true;
    }
    function accept(raw){
        if(!active||!pending)return;
        try{
            const text=String(raw||"");
            if(text.length<100||text.length>125000)
                throw new Error("bounded output rejected");
            const checked=Matrix.validate(JSON.parse(text),pending,natalChart);
            if(!checked.ready)throw new Error("source mismatch");
            result=checked;received=true;ready=true;failed=false;errorText="";
        }catch(e){
            result=null;ready=false;received=false;failed=true;
            errorText="JPL MATRIX SOURCE INVALID";
        }
    }
    Process {
        id:runner
        command:[]
        stdinEnabled:true
        onStarted:{
            if(!matrixSource.active||!matrixSource.pending){
                runner.running=false;return;
            }
            runner.write(JSON.stringify(matrixSource.pending)+"\n");
        }
        stdout:StdioCollector {
            onStreamFinished:matrixSource.accept(text)
        }
        onExited:function(exitCode,exitStatus){
            if(!matrixSource.active||!matrixSource.pending)return;
            if(exitCode!==0){
                matrixSource.ready=false;matrixSource.result=null;
                matrixSource.failed=true;
                matrixSource.errorText="JPL MATRIX CALCULATION UNAVAILABLE";
            }else if(!matrixSource.received){
                matrixSource.ready=false;matrixSource.failed=true;
                matrixSource.errorText="NO VERIFIED MATRIX RESPONSE";
            }
            matrixSource.pending=null;
        }
    }
    onActiveChanged:if(!active)clearState()
    onNatalChartChanged:clearState()
    onKernelPathChanged:clearState()
    onPythonExecutableChanged:clearState()
}
