import QtQuick
import Quickshell
import Quickshell.Io
import "CelestialVisualInstallPolicy.js" as Install
import "../../widgets/weather/StationMagickAnnualAtlasPolicy.js" as Atlas

// M7b // Separate year-bounded on-demand actor. Does NOT modify M5 chart
// owner, WEATHER forecast cache, or COSMOS sources. No automatic execution.
Scope {
    id: annual
    property bool active: false
    property int year: 2026
    property string timezoneId: "UTC"
    readonly property string home: String(Quickshell.env("HOME")||"")
    readonly property string kernelPath: Install.resolveKernel(
        String(Quickshell.env("POST_APOLLO_CELESTIAL_KERNEL")||""),home)
    readonly property string pythonExecutable: Install.resolvePython(
        String(Quickshell.env("POST_APOLLO_CELESTIAL_PYTHON")||""),home)
    readonly property bool configured: kernelPath!=="" && pythonExecutable!==""
    readonly property string key: active&&configured&&
        Atlas.dayCount(year)>0&&timezoneId.length>0
        ? kernelPath+"|"+pythonExecutable+"|"+year+"|"+timezoneId:""
    property string inflight: ""
    property var atlas: Atlas.fail("CALCULATE YEAR TO LOAD JPL")
    property bool ready: false
    property bool failed: false
    property string errorText: ""
    readonly property bool loading: runYear.running
    readonly property string statusText:
        !configured ? "JPL LOCAL INSTALLATION UNAVAILABLE" :
        loading ? "CALCULATING ANNUAL EPHEMERIS" :
        failed ? errorText : ready ? "JPL YEAR VERIFIED" :
        "CALCULATE YEAR TO LOAD"

    function clear() {
        if(runYear.running)runYear.running=false;
        inflight="";
        atlas=Atlas.fail("CALCULATE YEAR TO LOAD JPL");
        ready=false;failed=false;errorText="";
    }
    function calculate() {
        if(key===""||runYear.running)return false;
        clear();
        inflight=key;
        runYear.command=[
            pythonExecutable,"-B",
            Quickshell.configDir+"/scripts/weather/celestial_annual_calendar.py",
            "--kernel",kernelPath,
            "--year",String(year),
            "--timezone",timezoneId
        ];
        runYear.running=true;
        return true;
    }
    function accept(raw) {
        if(!active||inflight===""||inflight!==key)return;
        try {
            const text=String(raw||"");
            if(text.length<100||text.length>262144)
                throw new Error("unexpected annual response length");
            const parsed=JSON.parse(text);
            const result=Atlas.validate(parsed,year,timezoneId);
            if(!result.ready)throw new Error(result.reason);
            atlas=result;
            ready=true;failed=false;errorText="";
        } catch(e) {
            atlas=Atlas.fail("INVALID ANNUAL ATLAS");
            ready=false;failed=true;errorText="ANNUAL JPL RESPONSE INVALID";
        }
    }
    Process {
        id: runYear
        command: []
        stdout: StdioCollector {
            onStreamFinished: annual.accept(text)
        }
        onExited: function(code,status){
            if(!annual.active||annual.inflight===""||annual.inflight!==annual.key)return;
            if(code!==0){annual.ready=false;annual.failed=true;
                annual.errorText="ANNUAL BACKEND UNAVAILABLE // CHECK JPL + ZONE";}
            else if(!annual.ready){annual.failed=true;
                if(annual.errorText==="")annual.errorText="NO VERIFIED YEAR RETURNED";}
        }
    }
    onKeyChanged: clear()
    onActiveChanged: if(!active)clear()
}
