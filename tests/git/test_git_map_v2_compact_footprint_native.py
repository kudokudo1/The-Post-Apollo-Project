#!/usr/bin/env python3
"""Paired V2 Python vs compact holder PSS in two retained GitW hosts.
CI only; no installed desktop or system-wide claim.
"""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import statistics
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[2]
if os.environ.get("POST_APOLLO_GIT_MAP_SMOKE")!="CI_DISPOSABLE_ONLY":
    raise SystemExit("Disposable CI only")
sys.path.insert(0,str(ROOT/"scripts"))
import git_map_isolated_candidate as v2
import git_map_history_index as index

def process_stat(pid):
    # /proc/PID/stat comm may contain spaces or parentheses.
    fields=(Path("/proc")/str(pid)/"stat").read_text().rsplit(")",1)[1].split()
    return int(fields[1]), int(fields[19])

def descendants(root):
    tree={}
    for path in Path("/proc").iterdir():
        if not path.name.isdecimal(): continue
        pid=int(path.name)
        try: tree[pid]=process_stat(pid)
        except (OSError,ValueError,IndexError): continue
    if root not in tree: raise ValueError("shell exited")
    selected={root:tree[root][1]}
    while True:
        new={pid:start for pid,(parent,start) in tree.items()
             if parent in selected and pid not in selected}
        if not new: return selected
        selected.update(new)

def sample(root,mode,binary):
    expected_helpers=1
    before=descendants(root)
    rows=[]
    for pid,start in sorted(before.items()):
        path=Path("/proc")/str(pid)
        cmd=(path/"cmdline").read_bytes().split(b"\0")
        helper=(Path(os.readlink(path/"exe"))==binary if mode=="compact"
                else any(x.endswith(b"/scripts/git_map_v2_reader_candidate.py") for x in cmd))
        if helper:
            assert Path(os.readlink(path/"exe"))==(binary if mode=="compact" else Path(sys.executable).resolve())
        values={}
        for line in (path/"smaps_rollup").read_text().splitlines():
            key,_,rest=line.partition(":")
            if key in ("Rss","Pss","SwapPss"): values[key]=int(rest.split()[0])
        assert set(values)=={"Rss","Pss","SwapPss"}
        assert process_stat(pid)[1]==start,"process identity changed"
        rows.append(dict(pid=pid,helper=helper,**values))
    assert descendants(root)==before,"process tree changed"
    assert sum(row["helper"] for row in rows)==expected_helpers,rows
    # No transient page/build/witness processes may contaminate retained sample.
    assert len(rows)==1+expected_helpers,rows
    return {"rows":rows,"Pss":sum(row["Pss"] for row in rows),
            "SwapPss":sum(row["SwapPss"] for row in rows)}

def exclusive(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: return False
        return True
    finally: os.close(fd)

with tempfile.TemporaryDirectory(prefix="git-map-footprint-") as tmp:
    base=Path(tmp)
    scene=base/"scene"
    scene.mkdir()
    shutil.copytree(ROOT/"components",scene/"components")
    for folder,names in (
        ("services/git",("GitMapPageBridge.qml","GitMapViewportPolicy.js")),
        ("widgets/git",("GitMapVirtualViewport.qml","GitMapControlHost.qml","GitMapCustodyController.qml","GitMapGenerationLease.qml")),
        ("scripts",("git_map_history_index.py","git_map_index_manager.py","git_map_reader_candidate.py","git_map_isolated_candidate.py","git_map_v2_reader_candidate.py","git_map_compact_holder.c")),
    ):
        dest=scene/folder
        dest.mkdir(parents=True)
        for name in names: shutil.copy2(ROOT/folder/name,dest/name)
    shutil.copy2(ROOT/"tests/git/fixtures/GitMapFootprintNative.qml",scene/"smoke.qml")
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
            "--base",Quickshell.env("XDG_CACHE_HOME"),"--device",generation.device,"--inode",generation.inode].concat(Quickshell.env("MAP_COMPACT_HOLDER")==="yes" ? ["--compact-hold"] : []).concat(["hold",generation.repoId,generation.key,generation.manifest.snapshot])''')
    patch(lease,'"post-apollo-git-map-reader-candidate-v1"','"post-apollo-git-map-reader-v2-candidate"')
    patch(lease,"m.snapshot!==g.manifest.snapshot || m.reclamationAllowed!==false","m.snapshot!==g.manifest.snapshot || m.device!==g.device || m.inode!==g.inode || m.reclamationAllowed!==false")
    binary=scene/"scripts/git_map_compact_holder"
    subprocess.run(["cc","-std=c11","-O2","-Wall","-Wextra","-Werror",str(binary)+".c","-o",str(binary)],check=True)
    repo=base/"repo"
    repo.mkdir()
    def git(*args,**kw):
        return subprocess.run(["git","-C",str(repo),*args],check=True,capture_output=True,**kw)
    git("init","-b","main")
    lines=[]
    for i in range(1,1001):
        lines.extend(["commit refs/heads/main",f"mark :{i}",
                      f"committer Fixture <fixture@example.invalid> {1700000000+i} +0000",
                      "data 1","x"])
        if i>1: lines.append(f"from :{i-1}")
        lines.append("")
    git("fast-import","--quiet",input=("\n".join(lines)+"\n").encode())
    git("reset","--hard","HEAD")
    head=git("rev-parse","HEAD").stdout
    worktree=git("status","--porcelain").stdout
    cache=base/"cache"
    receipt=v2.build(repo,cache)
    assert receipt["manifest"]["total"]==1000,receipt
    directory=Path(receipt["directory"])
    db=directory/v2.NAME
    digest=hashlib.sha256(db.read_bytes()).hexdigest()
    samples={"python":[],"compact":[]}
    for pair,order in enumerate((("python","compact"),("compact","python"),("python","compact"))):
        for mode in order:
            env=os.environ.copy()
            for key in ("HOME","XDG_CONFIG_HOME","XDG_STATE_HOME","XDG_DATA_HOME","XDG_RUNTIME_DIR"):
                path=base/f"{pair}-{mode}-{key}"
                path.mkdir(mode=0o700)
                env[key]=str(path)
            env.update(XDG_CACHE_HOME=str(cache),QT_QPA_PLATFORM="offscreen",
                       QT_QUICK_BACKEND="software",LIBGL_ALWAYS_SOFTWARE="1",
                       QS_DISABLE_FILE_WATCHER="1",WAYLAND_DISPLAY="",DISPLAY="",
                       MAP_FOOTPRINT_REPO=str(repo),MAP_FOOTPRINT_MODE="on",
                       MAP_COMPACT_HOLDER="yes" if mode=="compact" else "no")
            # Verify the exact prebuilt snapshot is visible through the same
            # executable and environment as the host, before launching QML.
            lookup=subprocess.run([sys.executable,"-I","-B",
                str(scene/"scripts/git_map_v2_manager_fixture.py"),"lookup",str(repo)],
                env=env,text=True,capture_output=True,timeout=5,check=True)
            assert json.loads(lookup.stdout)==receipt,(lookup.stdout,receipt)
            logfile=base/f"{pair}-{mode}.log"
            with logfile.open("w") as log:
                p=subprocess.Popen(["qs","-p",str(scene/"smoke.qml"),"--no-color"],cwd=scene,
                                   env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                try:
                    deadline=time.monotonic()+25
                    expected="GIT_MAP_FOOTPRINT_READY "+receipt["manifest"]["snapshot"]
                    while expected not in logfile.read_text():
                        assert "GIT_MAP_FOOTPRINT_FAIL" not in logfile.read_text(),logfile.read_text()
                        assert p.poll() is None,logfile.read_text()
                        assert time.monotonic()<deadline,logfile.read_text()
                        time.sleep(.05)
                    time.sleep(.3)
                    values=[]
                    for _ in range(3):
                        assert not exclusive(directory)
                        values.append(sample(p.pid,mode,binary))
                        time.sleep(.15)
                    print("GIT_MAP_V2_COMPACT_RAW",pair,mode,json.dumps(values),flush=True)
                    samples[mode].append(statistics.median(x["Pss"] for x in values))
                    assert not any(x in logfile.read_text() for x in
                        ("GIT_MAP_FOOTPRINT_FAIL","Binding loop detected","TypeError:","ReferenceError:"))
                finally:
                    try: os.killpg(p.pid,signal.SIGKILL)
                    except ProcessLookupError: pass
                    p.wait(timeout=5)
                    deadline=time.monotonic()+5
                    while not exclusive(directory):
                        assert time.monotonic()<deadline,"owner exit left lock"
                        time.sleep(.02)
    assert hashlib.sha256(db.read_bytes()).hexdigest()==digest
    assert git("rev-parse","HEAD").stdout==head and git("status","--porcelain").stdout==worktree
    print("GIT_MAP_V2_COMPACT_PAIR_MEDIANS_KIB",json.dumps(samples),flush=True)
    print("GIT_MAP_V2_COMPACT_PAIRED_DELTA_KIB",
          json.dumps([b-a for a,b in zip(samples["python"],samples["compact"])]),flush=True)
    assert not (cache/"post-apollo-git-map-v1").exists()
    assert len([p for p in (cache/v2.ROOT_NAME).glob("*/*") if p.is_dir()])==1
    print("GIT_MAP_V2_COMPACT_FOOTPRINT_PASS; no deletion",flush=True)
