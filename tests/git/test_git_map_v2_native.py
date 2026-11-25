#!/usr/bin/env python3
import os
import fcntl
import time
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[2]
if os.environ.get("POST_APOLLO_GIT_MAP_SMOKE")!="CI_DISPOSABLE_ONLY":
    raise SystemExit("Disposable CI only")
with tempfile.TemporaryDirectory(prefix="git-map-v2-native-") as tmp:
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
        for name in names:
            shutil.copy2(ROOT/folder/name,dest/name)
    shutil.copy2(ROOT/"tests/git/fixtures/GitMapSharedCustodyNative.qml",scene/"smoke.qml")
    shutil.copy2(ROOT/"tests/git/fixtures/git_map_shared_custody_probe.py",scene/"probe.py")
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
    patch(host,"        if (!candidate.activate(result.directory,result.manifest,anchor)) {",'''        candidate.v2Generation=result;
        if (!candidate.activate(result.directory,result.manifest,anchor)) {''')
    patch(host,"        requestsEnabled: root.operatorActive && root.fullVisible",'''        requestsEnabled: root.operatorActive && root.fullVisible
        v2Lease: root.activeLease
        onV2Fault: Qt.callLater(root.invalidateV2Selection)''')
    patch(viewport,"    property alias requestsEnabled: bridge.requestsEnabled",'''    property alias requestsEnabled: bridge.requestsEnabled
    property alias v2Generation: bridge.v2Generation
    property alias v2Lease: bridge.v2Lease
    signal v2Fault()''')
    patch(viewport,"    GitMap.GitMapPageBridge { id: bridge }","    GitMap.GitMapPageBridge { id: bridge; onV2Fault: root.v2Fault() }")
    patch(bridge,"    property var state: null",'''    property var state: null
    property var v2Generation: null
    property var v2Lease: null
    property var activeEvidence: null
    signal v2Fault()''')
    patch(bridge,"        activeRequest = request;",'''        if (!v2Generation || !v2Lease || !v2Lease.held
                || v2Lease.generation!==v2Generation || v2Generation.directory!==directory
                || v2Generation.manifest.snapshot!==request.snapshot) {
            v2Fault();
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
                            && v2Lease && v2Lease.held && v2Lease.generation===activeEvidence && reply.reclamationAllowed===false)
                        accepted=Policy.accept(state,request,reply.result);
                }''')
    patch(bridge,"            state = accepted || Policy.fail(state,request);",'''            state = accepted || Policy.fail(state,request);
            if (!accepted && v2Lease && v2Lease.held && v2Lease.generation===activeEvidence) {
                requestsEnabled=false;
                v2Fault();
            }''')
    patch(lease,'''Quickshell.shellPath("scripts/git_map_reader_candidate.py"),
            generation.repoId,generation.key,generation.manifest.snapshot''','''Quickshell.shellPath("scripts/git_map_v2_reader_candidate.py"),
            "--base",Quickshell.env("XDG_CACHE_HOME"),"--device",generation.device,"--inode",generation.inode,"hold",generation.repoId,generation.key,generation.manifest.snapshot''')
    patch(lease,'"post-apollo-git-map-reader-candidate-v1"','"post-apollo-git-map-reader-v2-candidate"')
    patch(lease,"m.snapshot!==g.manifest.snapshot || m.reclamationAllowed!==false","m.snapshot!==g.manifest.snapshot || m.device!==g.device || m.inode!==g.inode || m.reclamationAllowed!==false")
    patch("probe.py",'b"/scripts/git_map_reader_candidate.py"','b"/scripts/git_map_v2_reader_candidate.py"')
    # Test-only delay inside the real CLI search, after v2.read acquired
    # its shared lock. An external witness controls release, not a guessed delay.
    control=base/"inflight"
    control.mkdir(mode=0o700)
    helper=scene/"scripts/git_map_history_index.py"
    source=helper.read_text()
    anchor="def search(conn, snapshot, query, start):"
    assert source.count(anchor)==1
    source=source.replace(anchor, """def search(conn, snapshot, query, start):
    if query == "commit 20":
        import time
        control=Path(os.environ["MAP_SHARED_INFLIGHT_DIR"])
        (control/"started").touch()
        deadline=time.monotonic()+3
        while not (control/"release").exists():
            if time.monotonic()>=deadline:
                raise ValueError("fixture release timeout")
            time.sleep(.01)
    return fixture_original_search(conn,snapshot,query,start)


def fixture_original_search(conn, snapshot, query, start):""")
    helper.write_text(source)
    repo=base/"repo"
    repo.mkdir()
    for args in [("init","-b","main")]+[("commit","--allow-empty","-m",f"commit {i}") for i in range(40)]:
        subprocess.run(["/usr/bin/git","-C",str(repo),"-c","user.name=Fixture",
            "-c","user.email=fixture@example.invalid",*args],check=True,
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    env=os.environ.copy()
    for key in ("HOME","XDG_CACHE_HOME","XDG_CONFIG_HOME","XDG_STATE_HOME","XDG_DATA_HOME","XDG_RUNTIME_DIR"):
        d=base/key
        d.mkdir(mode=0o700)
        env[key]=str(d)
    env.update(QT_QPA_PLATFORM="offscreen",QT_QUICK_BACKEND="software",
               LIBGL_ALWAYS_SOFTWARE="1",QS_DISABLE_FILE_WATCHER="1",WAYLAND_DISPLAY="",DISPLAY="",
               MAP_MANAGED_REPO=str(repo),MAP_SHARED_INFLIGHT_DIR=str(control))
    result=subprocess.run(["qs","-p",str(scene/"smoke.qml"),"--no-color"],cwd=scene,env=env,
                          text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=45)
    print(result.stdout)
    if result.stdout.count("SHARED_CUSTODY_KERNEL_WITNESS_PASS")!=4:
        raise SystemExit("Missing integrated kernel witness")
    if "SHARED_CUSTODY_INFLIGHT_LOCK_PASS" not in result.stdout:
        raise SystemExit("Missing independent finite reader witness")
    cache=Path(env["XDG_CACHE_HOME"])/"post-apollo-git-map-custody-v2"
    assert not (cache.parent/"post-apollo-git-map-v1").exists(),"unexpected legacy fallback"
    generations=[p for p in cache.glob("*/*") if p.is_dir() and not p.name.startswith(".")]
    assert len(generations)==2,generations
    for g in generations:
        assert (g/"history.custody-v2.sqlite3").is_file()
        assert not (g/"history.sqlite3").exists()
    print("GIT_MAP_V2_NATIVE_NAMESPACE_PASS")
    def all_released():
        for path in cache.glob("*/*"):
            if not path.is_dir() or path.name.startswith("."): continue
            fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
            try:
                try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
                except BlockingIOError: return False
            finally: os.close(fd)
        return True
    deadline=time.monotonic()+5
    while not all_released():
        if time.monotonic()>=deadline: raise SystemExit("Integrated owner exit left locks held")
        time.sleep(.02)
    print("SHARED_CUSTODY_ALL_RELEASED")
    print("GIT_MAP_V2_NATIVE_OWNER_RELEASE_PASS")
    if (result.returncode or "GIT_MAP_SHARED_CUSTODY_PASS" not in result.stdout
            or any(x in result.stdout for x in ("GIT_MAP_SHARED_CUSTODY_FAIL","Binding loop detected","TypeError:","ReferenceError:"))):
        raise SystemExit("Native managed Git map fixture failed")
