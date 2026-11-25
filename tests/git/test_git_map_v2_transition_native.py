#!/usr/bin/env python3
"""Disposable real V2 host: interrupted locked page/locate across repository switch.

Reuses the exact V2 disposable adapter from test_git_map_v2_native.py;
production QML, installed cache and repository are untouched.
"""
import fcntl
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

ROOT=Path(__file__).resolve().parents[2]
if os.environ.get("POST_APOLLO_GIT_MAP_SMOKE")!="CI_DISPOSABLE_ONLY":
    raise SystemExit("Disposable CI only")
def adapt(scene,base):
    # Adapt only disposable QML copies to the versioned process interface.
    # Keep actual host/controller/viewport logic and independent kernel probe.
    def patch(path,old,new):
        f=scene/path
        text=f.read_text()
        assert text.count(old)==1,(path,old)
        f.write_text(text.replace(old,new))
    host="widgets/git/GitMapControlHost.qml"
    bridge="services/git/GitMapPageBridge.qml"
    lease="widgets/git/GitMapGenerationLease.qml"
    viewport="widgets/git/GitMapVirtualViewport.qml"
    controller="widgets/git/GitMapCustodyController.qml"
    (scene/"scripts/git_map_v2_manager_fixture.py").write_text("""import json,os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import git_map_isolated_candidate as v2
assert os.environ.get("POST_APOLLO_GIT_MAP_SMOKE")=="CI_DISPOSABLE_ONLY"
action,repo=sys.argv[1:]
assert action in ("lookup","build")
print(json.dumps(getattr(v2,action)(Path(repo),Path(os.environ["XDG_CACHE_HOME"])),separators=(",",":")))
""")
    patch(host,'Quickshell.shellPath("scripts/git_map_index_manager.py")','Quickshell.shellPath("scripts/git_map_v2_manager_fixture.py")')
    patch(host,'value.schema === "post-apollo-git-map-cache-v1"','value.schema === "post-apollo-git-map-custody-v2" && value.reclamationAllowed===false')
    patch(host,'value.directory.startsWith("/")','value.directory.startsWith(Quickshell.env("XDG_CACHE_HOME")+"/post-apollo-git-map-custody-v2/") && typeof value.device==="string" && /^[0-9]{1,20}$/.test(value.device) && typeof value.inode==="string" && /^[0-9]{1,20}$/.test(value.inode)')
    patch(host,'''Quickshell.shellPath("scripts/git_map_history_index.py"),
                     "locate",pendingResult.directory,pendingResult.manifest.snapshot,anchor.sha''','''Quickshell.shellPath("scripts/git_map_v2_reader_candidate.py"),
                     "--base",Quickshell.env("XDG_CACHE_HOME"),"--device",pendingResult.device,"--inode",pendingResult.inode,"locate",pendingResult.repoId,pendingResult.key,pendingResult.manifest.snapshot,anchor.sha''')
    patch(host,'''Quickshell.shellPath("scripts/git_map_history_index.py"),
            "search",activeDirectory,s.snapshot,"--",query,String(start)''','''Quickshell.shellPath("scripts/git_map_v2_reader_candidate.py"),
            "--base",Quickshell.env("XDG_CACHE_HOME"),"--device",activeLease.generation.device,"--inode",activeLease.generation.inode,"search",s.repoId,activeLease.generation.key,s.snapshot,"--",query,String(start)''')
    patch(host,'''        if (action==="search") { finishSearch(result); schedule(); return; }''','''        if (action==="locate" || action==="search") {
            const g=action==="locate" ? pendingResult : (activeLease ? activeLease.generation : null);
            result=result && g && result.schema==="post-apollo-git-map-reader-v2-candidate"
                && result.status==="READY" && result.repoId===g.repoId && result.key===g.key
                && result.snapshot===g.manifest.snapshot && result.device===g.device && result.inode===g.inode
                && result.reclamationAllowed===false
                && (action==="locate" ? pendingLease && pendingLease.held : activeLease && activeLease.held)
                ? result.result : null;
            if (!result) {
                invalidateV2Selection();
                return;
            }
        }
        if (action==="search") { finishSearch(result); schedule(); return; }''')
    patch(host,"    function handleCustodyLoss() {",'''    function invalidateV2Selection() {
        custodyLost=true;
        repoEpoch++;
        searchEpoch++;
        activeRepo="";
        activeDirectory="";
        searchRequest=null;
        lastMatch=null;
        lookupQueued=false;
        buildQueued=false;
        clearPending();
        const old=activeLease;
        activeLease=null;
        if (old && custodyController) custodyController.release(old);
        statusText="CUSTODY LOST // REOPEN TO RECHECK";
    }
    function handleCustodyLoss() {''')
    patch(host,"        const previousLease=activeLease;",'''        candidate.v2Generation=result;
        const previousLease=activeLease;''')
    patch(host,"        requestsEnabled: root.operatorActive && root.fullVisible",'''        requestsEnabled: root.operatorActive && root.fullVisible
        v2Lease: root.activeLease
        onV2Fault: function(g) { Qt.callLater(()=>{ if (root.activeLease && g && root.activeLease.generation.device===g.device && root.activeLease.generation.inode===g.inode && root.activeLease.generation.manifest.snapshot===g.manifest.snapshot) root.invalidateV2Selection(); }); }''')
    patch(viewport,"    property alias requestsEnabled: bridge.requestsEnabled",'''    property alias requestsEnabled: bridge.requestsEnabled
    property alias v2Generation: bridge.v2Generation
    property alias v2Lease: bridge.v2Lease
    signal v2Fault(var g)''')
    patch(viewport,"    GitMap.GitMapPageBridge { id: bridge }","    GitMap.GitMapPageBridge { id: bridge; onV2Fault: function(g) { root.v2Fault(g); } }")
    patch(bridge,"    property var state: null",'''    property var state: null
    property var v2Generation: null
    property var v2Lease: null
    property var activeEvidence: null
    property bool v2ReadRefused: false
    onV2GenerationChanged: v2ReadRefused=false
    function sameGeneration(a,b) {
        return a && b && a.directory===b.directory && a.repoId===b.repoId
            && a.key===b.key && a.manifest.snapshot===b.manifest.snapshot
            && a.device===b.device && a.inode===b.inode;
    }
    signal v2Fault(var g)''')
    patch(bridge,"        if (!requestsEnabled || !state || faulted || busy || worker.running) return;","        if (!requestsEnabled || !state || faulted || busy || worker.running || v2ReadRefused) return;")
    patch(bridge,"        activeRequest = request;",'''        if (!v2Generation || !v2Lease || !v2Lease.held
                || !sameGeneration(v2Lease.generation,v2Generation) || v2Generation.directory!==directory
                || v2Generation.manifest.snapshot!==request.snapshot) {
            v2ReadRefused=true;
            v2Fault(v2Generation);
            return;
        }
        activeEvidence=v2Generation;
        activeRequest = request;''')
    patch(controller,'same.generation.manifest.snapshot!==g.manifest.snapshot','same.generation.manifest.snapshot!==g.manifest.snapshot || same.generation.device!==g.device || same.generation.inode!==g.inode')
    patch(bridge,'''Quickshell.shellPath("scripts/git_map_history_index.py"),
                     "page", activeDirectory, request.snapshot, String(request.start)''','''Quickshell.shellPath("scripts/git_map_v2_reader_candidate.py"),
                     "--base",Quickshell.env("XDG_CACHE_HOME"),"--device",activeEvidence.device,"--inode",activeEvidence.inode,"page",request.repoId,
                     activeDirectory.split("/").pop(),request.snapshot,String(request.start)''')
    patch(bridge,'''try { accepted = Policy.accept(state,request,JSON.parse(output)); }''','''try {
                    const reply=JSON.parse(output);
                    if (reply.schema==="post-apollo-git-map-reader-v2-candidate" && reply.status==="READY"
                            && reply.repoId===request.repoId && reply.key===activeDirectory.split("/").pop()
                            && reply.snapshot===request.snapshot && reply.device===activeEvidence.device && reply.inode===activeEvidence.inode
                            && v2Lease && v2Lease.held && sameGeneration(v2Lease.generation,activeEvidence) && reply.reclamationAllowed===false)
                        accepted=Policy.accept(state,request,reply.result);
                }''')
    patch(bridge,"            state = accepted || Policy.fail(state,request);",'''            state = accepted || Policy.fail(state,request);
            if (!accepted && v2Lease && v2Lease.held && sameGeneration(v2Lease.generation,activeEvidence)) {
                v2ReadRefused=true;
                v2Fault(activeEvidence);
            }''')
    patch(lease,'''Quickshell.shellPath("scripts/git_map_reader_candidate.py"),
            generation.repoId,generation.key,generation.manifest.snapshot''','''Quickshell.shellPath("scripts/git_map_v2_reader_candidate.py"),
            "--base",Quickshell.env("XDG_CACHE_HOME"),"--device",generation.device,"--inode",generation.inode,"hold",generation.repoId,generation.key,generation.manifest.snapshot''')
    patch(lease,'"post-apollo-git-map-reader-candidate-v1"','"post-apollo-git-map-reader-v2-candidate"')
    patch(lease,"m.snapshot!==g.manifest.snapshot || m.reclamationAllowed!==false","m.snapshot!==g.manifest.snapshot || m.device!==g.device || m.inode!==g.inode || m.reclamationAllowed!==false")
    # The transition probe checks inode locks and has no old reader executable string.


for mode in ("page","locate"):
    with tempfile.TemporaryDirectory(prefix="git-map-v2-transition-") as tmp:
        base=Path(tmp)
        scene=base/"scene"
        scene.mkdir()
        shutil.copytree(ROOT/"components",scene/"components")
        for folder,names in (
            ("services/git",("GitMapPageBridge.qml","GitMapViewportPolicy.js")),
            ("widgets/git",("GitMapVirtualViewport.qml","GitMapControlHost.qml","GitMapCustodyController.qml","GitMapGenerationLease.qml")),
            ("scripts",("git_map_history_index.py","git_map_index_manager.py","git_map_reader_candidate.py","git_map_isolated_candidate.py","git_map_v2_reader_candidate.py")),
        ):
            dest=scene/folder
            dest.mkdir(parents=True)
            for name in names: shutil.copy2(ROOT/folder/name,dest/name)
        shutil.copy2(ROOT/"tests/git/fixtures/GitMapTransitionNative.qml",scene/"smoke.qml")
        shutil.copy2(ROOT/"tests/git/fixtures/git_map_transition_probe.py",scene/"probe.py")
        adapt(scene,base)
        control=base/"control"
        control.mkdir(mode=0o700)
        helper=scene/"scripts/git_map_history_index.py"
        original=helper.read_text()
        anchor="def page(conn, snapshot, start):" if mode=="page" else "def locate(conn, snapshot, sha):"
        assert original.count(anchor)==1
        delay="""    import time
    control=Path(os.environ["MAP_TRANSITION_CONTROL"])
    if CONDITION and not (control/"started").exists():
        (control/"started").touch()
        deadline=time.monotonic()+4
        while not (control/"release").exists():
            if time.monotonic()>=deadline:
                raise ValueError("fixture release timeout")
            time.sleep(.01)
"""
        delay=delay.replace("CONDITION","start==256" if mode=="page" else "True")
        helper.write_text(original.replace(anchor,anchor+"\n"+delay.rstrip("\n")))
        repo=base/"repo"
        other=base/"other"
        for directory in (repo,other):
            directory.mkdir()
            subprocess.run(["git","-C",str(directory),"init","-b","main"],check=True,capture_output=True)
        lines=[]
        for i in range(1,301):
            lines.extend(["commit refs/heads/main",f"mark :{i}",
                f"committer Fixture <fixture@example.invalid> {1700000000+i} +0000",
                "data 1","x"])
            if i>1: lines.append(f"from :{i-1}")
            lines.append("")
        subprocess.run(["git","-C",str(repo),"fast-import","--quiet"],
            input=("\n".join(lines)+"\n").encode(),check=True,capture_output=True)
        subprocess.run(["git","-C",str(repo),"reset","--hard","HEAD"],check=True,capture_output=True)
        subprocess.run(["git","-C",str(other),"-c","user.name=Fixture",
            "-c","user.email=fixture@example.invalid","commit","--allow-empty",
            "-m","other repository"],check=True,capture_output=True)
        before={directory:(
            subprocess.check_output(["git","-C",str(directory),"rev-parse","HEAD"]).strip(),
            subprocess.check_output(["git","-C",str(directory),"status","--porcelain"])
        ) for directory in (repo,other)}
        env=os.environ.copy()
        for key in ("HOME","XDG_CACHE_HOME","XDG_CONFIG_HOME","XDG_STATE_HOME","XDG_DATA_HOME","XDG_RUNTIME_DIR"):
            d=base/key
            d.mkdir(mode=0o700)
            env[key]=str(d)
        env.update(QT_QPA_PLATFORM="offscreen",QT_QUICK_BACKEND="software",
            LIBGL_ALWAYS_SOFTWARE="1",QS_DISABLE_FILE_WATCHER="1",WAYLAND_DISPLAY="",DISPLAY="",
            MAP_MANAGED_REPO=str(repo),MAP_OTHER_REPO=str(other),MAP_TRANSITION_MODE=mode,
            MAP_TRANSITION_CONTROL=str(control),POST_APOLLO_GIT_MAP_SMOKE="CI_DISPOSABLE_ONLY")
        result=subprocess.run(["qs","-p",str(scene/"smoke.qml"),"--no-color"],cwd=scene,
            env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=45)
        print(result.stdout)
        required=("GIT_MAP_TRANSITION_PASS "+mode,
            "GIT_MAP_TRANSITION_KERNEL_PAIR_PASS","GIT_MAP_TRANSITION_KERNEL_FINAL_PASS")
        assert result.returncode==0 and all(x in result.stdout for x in required),result.stdout
        assert not any(x in result.stdout for x in (
            "GIT_MAP_TRANSITION_FAIL","Binding loop detected","TypeError:","ReferenceError:")),result.stdout
        cache=Path(env["XDG_CACHE_HOME"])/"post-apollo-git-map-custody-v2"
        assert cache.is_dir() and not (cache.parent/"post-apollo-git-map-v1").exists()
        generations=[p for p in cache.glob("*/*") if p.is_dir() and not p.name.startswith(".")]
        assert len(generations)>=2,generations
        for path in generations:
            assert (path/"history.custody-v2.sqlite3").is_file()
            assert not (path/"history.sqlite3").exists()
        def all_released():
            for path in generations:
                fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
                try:
                    try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
                    except BlockingIOError: return False
                finally: os.close(fd)
            return True
        deadline=time.monotonic()+5
        while not all_released():
            assert time.monotonic()<deadline,"V2 owner exit left custody held"
            time.sleep(.02)
        for directory in (repo,other):
            now=(subprocess.check_output(["git","-C",str(directory),"rev-parse","HEAD"]).strip(),
                 subprocess.check_output(["git","-C",str(directory),"status","--porcelain"]))
            if mode=="page" or directory==other:
                assert now==before[directory],"unexpected repository mutation"
            else:
                assert now[0]!=before[directory][0] and now[1]==before[directory][1]
        print("GIT_MAP_V2_TRANSITION_PASS",mode,flush=True)
