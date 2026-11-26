#!/usr/bin/env python3
"""Native geometry and selection smoke for the actual compact SYSTEM rail."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
if os.environ.get("POST_APOLLO_MEMORY_UI_SMOKE")!="CI_DISPOSABLE_ONLY":
    raise SystemExit("Disposable CI only")
source=(ROOT/"widgets/CpuPlusW.qml").read_text()
block=source.split("readonly property var systemSubModes: [",1)[1].split("]",1)[0]
choices=[dict(name=n,key=k,symbol=s) for n,k,s in re.findall(r'\{ name: "([^"]+)", key: "([^"]+)", symbol: "([^"]+)" \}',block)]
assert [x["key"] for x in choices]==["ALL","CPU","MEMORY","GPU","STORAGE","NETWORK","SWAP"]
scene=r'''import QtQuick
import QtQuick.Window
import Quickshell
import "components"
import "widgets/cpuplus"
ShellRoot {
    id: root
    property int requests: 0
    Window {
        width: 260; height: 120; visible: true
        CpuPlusSystemTargetStrip {
            id: rail
            width: 140
            choices: CHOICES
            onTargetRequested: function(key) { root.requests++; selectedKey=key; }
        }
    }
    function check(ok, msg) {
        if (!ok) { console.error("SYSTEM_TARGET_FAIL // "+msg); Qt.quit(); }
        return ok;
    }
    function find(key) {
        return rail.children.find(item=>item.objectName==="cpuplusSystemTarget-"+key);
    }
    Timer {
        interval: 400; running: true; repeat: false
        onTriggered: {
            if (!root.check(rail.implicitHeight>=72,"wrapped layout")) return;
            for (const choice of rail.choices) {
                const b=root.find(choice.key);
                if (!root.check(!!b,"missing "+choice.key)) return;
                if (!root.check(b.width===36&&b.height===36&&b.labelItem.visible
                    &&b.labelItem.width>0&&b.labelItem.height>0&&b.labelItem.text===choice.symbol
                    &&b.labelItem.font.pixelSize===24,"visible glyph geometry "+choice.key)) return;
                if (!root.check(b.idleForegroundColor===Colors.resourceColor(choice.key)
                    &&b.idleBorderColor===Colors.resourceColor(choice.key)
                    &&b.hoverFillColor===Colors.yellow&&b.hoverForegroundColor===Colors.orange
                    &&b.hoverBorderColor===Colors.orange&&b.pressedFillColor===Colors.magenta
                    &&b.pressedForegroundColor===Colors.black&&b.selectedFillColor===Colors.yellow
                    &&b.selectedForegroundColor===Colors.magenta,"canonical state colors "+choice.key)) return;
            }
            const all=root.find("ALL"), cpu=root.find("CPU");
            if (!root.check(all.selected&&all.accentColor===Colors.white&&root.requests===0,"initial ALL")) return;
            cpu.leftClicked(null);
            if (!root.check(rail.selectedKey==="CPU"&&cpu.selected&&!all.selected&&root.requests===1,"selection route")) return;
            console.log("SYSTEM_TARGET_NATIVE_PASS");
            Qt.quit();
        }
    }
}
'''.replace("CHOICES",json.dumps(choices,ensure_ascii=False))
with tempfile.TemporaryDirectory(prefix="cpu-system-target-") as folder:
    base=Path(folder); config=base/"scene"; config.mkdir()
    shutil.copytree(ROOT/"components",config/"components")
    dest=config/"widgets/cpuplus"; dest.mkdir(parents=True)
    shutil.copy2(ROOT/"widgets/cpuplus/CpuPlusSystemTargetStrip.qml",dest/"CpuPlusSystemTargetStrip.qml")
    (config/"smoke.qml").write_text(scene)
    env=dict(os.environ,QT_QPA_PLATFORM="offscreen",QT_QUICK_BACKEND="software",
             LIBGL_ALWAYS_SOFTWARE="1",QS_DISABLE_FILE_WATCHER="1",WAYLAND_DISPLAY="",DISPLAY="")
    for name in ("HOME","XDG_CACHE_HOME","XDG_CONFIG_HOME","XDG_STATE_HOME","XDG_DATA_HOME","XDG_RUNTIME_DIR"):
        p=base/name; p.mkdir(mode=0o700); env[name]=str(p)
    result=subprocess.run(["qs","-p",str(config/"smoke.qml"),"--no-color"],cwd=config,env=env,
        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=15)
    print(result.stdout)
    if result.returncode or "SYSTEM_TARGET_NATIVE_PASS" not in result.stdout or "SYSTEM_TARGET_FAIL" in result.stdout:
        raise SystemExit("Native SYSTEM target regression")
