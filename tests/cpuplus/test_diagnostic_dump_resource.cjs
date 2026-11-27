const fs=require("node:fs"),path=require("node:path"),vm=require("node:vm"),assert=require("node:assert/strict");
const root=path.join(__dirname,"../../services/diagnostics");
const policy=vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(root,"CpuPlusDiagnosticsPolicy.js"),"utf8"),policy);
const resource=vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(root,"DiagnosticDumpResource.js"),"utf8"),resource);
function verify(assert,R,P) {
    assert(R.dumpResourcePlan(5).intervalMs===5000);
    assert(R.dumpResourcePlan(120).intervalMs===10000);
    assert(!R.dumpResourcePlan(1)&&!R.dumpResourcePlan(121)&&!R.dumpResourcePlan("30"));
    const origin=100000;
    const plan=R.dumpResourcePlan(5);
    const memoryKiB={Rss:100,Pss:80,SwapPss:0};
    const a={event:"memory",pid:123,startTicks:456,tsMs:origin+100,monotonicMs:2000,memoryKiB,cpuTicks:10,cpuPct:null,sampleIntervalMs:null};
    const b={...a,tsMs:origin+5100,monotonicMs:7000,cpuTicks:60,cpuPct:10,sampleIntervalMs:5000};
    const end={event:"complete",pid:123,startTicks:456,workshopSchema:"post-apollo-observer-calibration-v1",calibration:plan,samples:2,observedMs:5000,monotonicMs:7000};
    const encode=rows=>rows.map(x=>JSON.stringify(x)).join("\n");
    const parse=rows=>R.dumpResourceEvidence(encode(rows),origin,5,P);
    const result=parse([a,b,end]);
    assert(result&&result.pid===123&&result.startTicks===456);
    assert(result.overlapMs===4900&&result.firstOffsetMs===100&&result.lastOffsetMs===5100);
    assert(result.samples[0].withinWindow&&!result.samples[1].withinWindow&&!result.samples[1].intervalWithinWindow);
    assert(result.samples[0].cpuPct===null&&result.samples[1].cpuPct===10);
    const host={MemTotal:100000,MemAvailable:80000,MemFree:30000,AnonPages:10000,Cached:3000,
        Shmem:100,SReclaimable:100,SUnreclaim:100,SwapTotal:10000,SwapFree:9000};
    const context={beforeKiB:host,afterKiB:{...host,MemAvailable:79000},spanMs:0.4};
    const realShape=[{...a,hostObservation:context,privateResidentKiB:30,pssPlusSwapPssKiB:80},
        {...b,hostObservation:context,privateResidentKiB:30,pssPlusSwapPssKiB:80},end];
    assert(P.summarize("memory",encode(realShape)).includes("HOST CONTEXT // 2/2 paired samples"));
    assert(parse(realShape)?.pid===123);
    assert(P.summarize("memory",encode([{...a,hostObservation:{beforeKiB:null,afterKiB:null,spanMs:0}},b,end])).includes("UNAVAILABLE"));
    assert(!parse([a,{...b,pid:124},end]));
    assert(!parse([a,{...b,startTicks:999},end]));
    assert(!parse([a,{...b,tsMs:b.tsMs+1000},end]));
    assert(!parse([a,{...b,cpuTicks:1},end]));
    assert(!parse([a,{...b,memoryKiB:{...memoryKiB,Pss:101}},end]));
    assert(!parse([a,b,{...end,monotonicMs:7001}]));
    assert(!parse([a,b]));
    assert(!parse([{...a,tsMs:origin-1},b,end]));
    assert(!R.dumpResourceEvidence("x".repeat(65537),origin,5,P));
}

verify(assert,resource,policy);
const owner=fs.readFileSync(path.join(root,"DiagnosticDumpResourceCapture.qml"),"utf8");
assert.match(owner,/"--workshop","--parent-quickshell","--duration"/);
assert.match(owner,/!stdoutSeen\|\|!exitSeen/);
assert.doesNotMatch(owner,/repeat:\s*true|running:\s*true|Component.onCompleted|sudo|pkexec/);
console.log("universal resource capture contract PASS");
