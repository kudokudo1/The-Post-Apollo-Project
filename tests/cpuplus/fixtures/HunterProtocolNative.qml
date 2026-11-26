import QtQuick
import Quickshell
import "services/system"

ShellRoot {
    id: root
    property var target: ({pid:3010,startTicks:10,name:"synthetic",identity:"synthetic"})
    property int index: 0
    property int received: 0
    property var modes: ["normal","nonzero","stderr","duplicate","malformed","missing","mismatch","crash"]
    function fail(reason) {
        console.error("HUNTER_PROTOCOL_FAIL // "+reason);
        Qt.quit();
    }
    HunterExecutor {
        id: engine
        // This fixture's helper only emits synthetic text and exits.
        // No real process is selected or signaled.
        function script() {
            const mode=root.modes[root.index];
            return "import json,sys,os\n"
                + "mode="+JSON.stringify(mode)+"\n"
                + "t=json.loads(sys.argv[1])[0]\n"
                + "r={'type':'result','pid':t['pid'],'name':t['name'],'status':'killed','detail':'SYNTHETIC'}\n"
                + "if mode=='mismatch': r['pid']+=1\n"
                + "print(json.dumps(r),flush=True)\n"
                + "if mode=='duplicate': print(json.dumps(r),flush=True)\n"
                + "if mode=='malformed': print('INVALID',flush=True)\n"
                + "if mode!='missing': print(json.dumps({'type':'done','count':1}),flush=True)\n"
                + "if mode=='stderr': print('unexpected',file=sys.stderr,flush=True)\n"
                + "if mode=='crash': os.abort()\n"
                + "sys.exit(7 if mode=='nonzero' else 0)\n";
        }
        onResultReady: function(result) { root.received++; }
        onFinished: {
            const positive=root.index===0;
            if (engine.running || engine.completionVerified!==positive
                    || root.received!==(positive?1:0)) {
                root.fail("correlation "+root.modes[root.index]); return;
            }
            root.index++;
            if (root.index===root.modes.length) {
                const result=JSON.stringify({type:"result",pid:root.target.pid,
                    name:root.target.name,status:"killed",detail:"SYNTHETIC"});
                const done=JSON.stringify({type:"done",count:1});
                if (engine.validatedResult(root.target,result+"\n"+done,"",0,0,true)!==null) {
                    root.fail("timeout must reject complete transcript");return;
                }
                console.log("HUNTER_PROTOCOL_PASS");
                Qt.quit();
            } else Qt.callLater(root.nextCase);
        }
    }
    function nextCase() {
        received=0;
        if (!engine.start([target])) fail("could not start synthetic helper");
    }
    Timer {
        interval: 100; running: true; repeat: false
        onTriggered: {
            if (Quickshell.env("POST_APOLLO_HUNTER_DISPOSABLE_CI") !== "1") {Qt.quit();return;}
            root.nextCase();
        }
    }
}
