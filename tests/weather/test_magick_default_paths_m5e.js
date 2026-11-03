"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");

const root=path.resolve(__dirname,"../..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
const policy=read("services/weather/CelestialVisualInstallPolicy.js");
const service=read("services/weather/CelestialVisualService.qml");
const station=read("widgets/weather/WeatherStationW.qml");
const pane=read("widgets/weather/StationMagickSubjectPane.qml");
const ctx=vm.createContext({});
vm.runInContext(policy.replace(/^\.pragma library\s*/m,""),ctx);

test("normal desktop startup discovers the existing one-time MAGICK install",()=>{
    const home="/var/home/mapple";
    assert.equal(ctx.resolveKernel("",home),
        "/var/home/mapple/.local/share/post-apollo/magick/de440s.bsp");
    assert.equal(ctx.resolvePython("",home),
        "/var/home/mapple/.local/share/post-apollo/magick/venv/bin/python");
    assert.equal(ctx.pathSource("","",home),"home-installation");
    assert.equal(ctx.resolveKernel(undefined,home),ctx.resolveKernel("",home));
    assert.equal(ctx.resolvePython(null,home),ctx.resolvePython("",home));
    assert.equal(ctx.resolveKernel("",home+"/"),ctx.resolveKernel("",home));
});

test("explicit kernel and Python development overrides take precedence",()=>{
    const home="/var/home/mapple";
    assert.equal(ctx.resolveKernel("/kernels/test.bsp",home),"/kernels/test.bsp");
    assert.equal(ctx.resolvePython("/opt/skyfield/bin/python",home),
                 "/opt/skyfield/bin/python");
    assert.equal(ctx.pathSource("/kernels/test.bsp","",home),"environment-override");
    assert.equal(ctx.pathSource("","python3",home),"environment-override");
    assert.equal(ctx.resolveKernel("   /kernels/fallback.bsp  ",home),
                 "/kernels/fallback.bsp");
    assert.equal(ctx.resolvePython("  python3  ",home),"python3");
});

test("unknown HOME does not invent a root path or download a kernel",()=>{
    for (const invalid of ["",undefined,"relative/home","/","/x\nbad",null]) {
        assert.equal(ctx.resolveKernel("",invalid),"");
        assert.equal(ctx.resolvePython("",invalid),"python3");
        assert.equal(ctx.pathSource("","",invalid),"unconfigured");
    }
    assert.equal(ctx.resolveKernel("/external.bsp",""),"/external.bsp");
    assert.equal(ctx.resolvePython("/venv/python",""),"/venv/python");
});

test("single root-owned JPL service uses the policy without launch-file editing",()=>{
    assert.match(service,/import "CelestialVisualInstallPolicy.js" as Install/);
    assert.match(service,/Quickshell\.env\("HOME"\)/);
    assert.match(service,/Quickshell\.env\("POST_APOLLO_CELESTIAL_KERNEL"\)/);
    assert.match(service,/Quickshell\.env\("POST_APOLLO_CELESTIAL_PYTHON"\)/);
    assert.match(service,/Install\.resolveKernel\(kernelOverride, installHome\)/);
    assert.match(service,/Install\.resolvePython\(pythonOverride, installHome\)/);
    assert.match(service,/property string kernelPath:/);
    assert.match(service,/property string pythonExecutable:/);
    assert.match(service,/calculation\.running=true/);
    assert.match(service,/onCurrentKeyChanged: clearState\(\)/);
    assert.match(pane,/onClicked: magickPane\.celestialSource\.refresh\(\)/);
    assert.equal((station.match(/WeatherServices\.CelestialVisualService\s*\{/g)||[]).length,1);
    assert.equal((service.match(/Process\s*\{/g)||[]).length,1);
    for(const banned of ["Timer {","FileView {","XMLHttpRequest","curl ","wget ",
                         "pip install","pkill ","swaymsg","Component.onCompleted: refresh()"])
        assert.equal(policy.includes(banned),false,"unexpected side effect in path policy: "+banned);
    assert.equal(service.includes("Timer {"),false);
    assert.equal(service.includes("onActiveChanged: refresh()"),false);
});
