#!/usr/bin/env python3
"""Paired real Quickshell jumps; validated row readiness, not frame presentation."""
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import statistics
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[2]
if os.environ.get("POST_APOLLO_GIT_MAP_SMOKE")!="CI_DISPOSABLE_ONLY":
    raise SystemExit("Disposable CI only")
sys.path.insert(0,str(ROOT/"scripts"))
import git_map_history_index as index

# Frozen page() from pre-batch main 56fe8929; the rest of the helper is identical.
OLD_PAGE="def page(conn, snapshot, start):\n    m = manifest_for(conn, snapshot)\n    if type(start) is not int or start < 0 or start % PAGE or start >= m[\"total\"]:\n        raise ValueError(\"page outside indexed range\")\n    stop = min(start + PAGE, m[\"total\"])\n    rows = [dict(row) for row in conn.execute(\n        \"SELECT * FROM commits WHERE ordinal>=? AND ordinal<? ORDER BY ordinal\",\n        (start,stop))]\n    if len(rows) != stop-start or any(row[\"ordinal\"] != start+i for i,row in enumerate(rows)):\n        raise ValueError(\"incomplete page\")\n    for row in rows:\n        row[\"parents\"] = [dict(edge) for edge in conn.execute(\"\"\"\n            SELECT e.position, e.parent_sha AS sha, p.ordinal, e.parent_lane AS lane\n            FROM edges e JOIN commits p ON p.sha=e.parent_sha\n            WHERE e.child=? ORDER BY e.position LIMIT ?\n            \"\"\", (row[\"ordinal\"], MAX_PARENTS+1))]\n        if len(row[\"parents\"]) > MAX_PARENTS:\n            raise ValueError(\"invalid edge count\")\n    boundary = conn.execute(\"SELECT frontier FROM boundaries WHERE ordinal=?\", (start,)).fetchone()\n    if boundary is None:\n        raise ValueError(\"missing boundary\")\n    return {\"schema\":SCHEMA, \"snapshot\":snapshot, \"repoId\":m[\"repoId\"],\n            \"start\":start, \"total\":m[\"total\"], \"rows\":rows,\n            \"frontier\":json.loads(boundary[0]), \"end\":stop==m[\"total\"]}\n\n\n"
source=(ROOT/"scripts/git_map_history_index.py").read_text()
a,b=source.index("def page("),source.index("def locate(")
assert "One bounded ancestry query per page" in source[a:b], "requires #2664"
baseline=source[:a]+OLD_PAGE+source[b:]
with tempfile.TemporaryDirectory(prefix="git-map-latency-") as tmp:
    base=Path(tmp)
    scene=base/"scene"
    scene.mkdir()
    shutil.copytree(ROOT/"components",scene/"components")
    for folder,files in (
        ("services/git",("GitMapPageBridge.qml","GitMapViewportPolicy.js")),
        ("widgets/git",("GitMapVirtualViewport.qml",)),
    ):
        dest=scene/folder
        dest.mkdir(parents=True)
        for name in files:
            shutil.copy2(ROOT/folder/name,dest/name)
    shutil.copy2(ROOT/"tests/git/fixtures/GitMapLatencyNative.qml",scene/"smoke.qml")
    scripts=scene/"scripts"
    scripts.mkdir()
    helper=scripts/"git_map_history_index.py"
    directory=base/"index"
    directory.mkdir(mode=0o700)
    db=directory/index.NAME
    def rows():
        for i in range(100000):
            sha=format(i+1,"040x")
            yield sha,[format(i+2,"040x")] if i<99999 else [],i,"Fixture","Commit "+str(i)
    with sqlite3.connect(db) as conn:
        manifest=index.fill(conn,rows(),snapshot="a"*32,repo_id="b"*64,
                            roots_digest="c"*64,shallow=False)
    conn.close()
    db.chmod(0o600)
    env=os.environ.copy()
    for key in ("HOME","XDG_CACHE_HOME","XDG_CONFIG_HOME","XDG_STATE_HOME","XDG_DATA_HOME","XDG_RUNTIME_DIR"):
        d=base/key
        d.mkdir(mode=0o700)
        env[key]=str(d)
    env.update(QT_QPA_PLATFORM="offscreen",QT_QUICK_BACKEND="software",
               LIBGL_ALWAYS_SOFTWARE="1",QS_DISABLE_FILE_WATCHER="1",
               WAYLAND_DISPLAY="",DISPLAY="",MAP_BENCH_MANIFEST=json.dumps(manifest),
               MAP_BENCH_DIRECTORY=str(directory))
    samples={"before":[],"after":[]}
    for order in (("before","after"),("after","before"),("before","after")):
        for label in order:
            helper.write_text(baseline if label=="before" else source)
            result=subprocess.run(["qs","-p",str(scene/"smoke.qml"),"--no-color"],
                                  cwd=scene,env=env,text=True,stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT,timeout=45)
            print(result.stdout)
            lines=re.findall(r"GIT_MAP_LATENCY_PASS (\[[0-9, ]+\])",result.stdout)
            if (result.returncode or len(lines)!=1 or any(x in result.stdout for x in
                    ("GIT_MAP_LATENCY_FAIL","Binding loop detected","TypeError:","ReferenceError:"))):
                raise SystemExit("Native jump fixture failed")
            values=json.loads(lines[0])
            assert len(values)==12 and all(type(v) is int and v>=0 for v in values)
            samples[label].extend(values)
    for label,values in samples.items():
        print("G4d native",label,"raw ms:",values)
        print("G4d native",label,"median ms:",statistics.median(values),
              "p95 ms:",sorted(values)[int(.95*len(values)+.999999)-1])
    print("Native data readiness: 36 uncached jumps per variant; exact visible row SHA, extent and delegate bounds checked.")
    print("Offscreen software Qt; no physical display frame or workstation latency claim.")
