// Shared launching-shell resource evidence. No per-widget attribution.
// All offsets are relative to the actual lifecycle start wall-clock timestamp.
// The monotonic sample clock independently checks for wall-clock discontinuity.
function dumpResourcePlan(seconds) {
    if(!Number.isSafeInteger(seconds)||seconds<5||seconds>120)return null;
    const interval=Math.max(5,Math.ceil(seconds/12));
    return {kind:"memory",durationSeconds:seconds,intervalMs:interval*1000};
}
function dumpResourceEvidence(text,origin,seconds,policy) {
    const plan=dumpResourcePlan(seconds);
    const integer=(n,min,max)=>Number.isSafeInteger(n)&&n>=min&&n<=max;
    const num=n=>typeof n==="number"&&Number.isFinite(n)&&n>=0;
    if(!plan||!integer(origin,0,Number.MAX_SAFE_INTEGER-145000)||typeof text!=="string"||text.length>65536)return null;
    try {
        if(!policy.configuredEvidence("memory",text,plan)||!policy.summarize("memory",text))return null;
        const lines=text.trim().split("\n").map(s=>JSON.parse(s));
        const end=lines.pop();
        if(lines.length<2||lines.length>13||!integer(end.pid,2,Number.MAX_SAFE_INTEGER))return null;
        const first=lines[0],last=lines[lines.length-1];
        if(!integer(first.tsMs,origin,origin+5000)||!integer(first.monotonicMs,0,Number.MAX_SAFE_INTEGER)||
            !integer(end.monotonicMs,first.monotonicMs,Number.MAX_SAFE_INTEGER)||
            end.monotonicMs!==last.monotonicMs||
            Math.abs(end.observedMs-(end.monotonicMs-first.monotonicMs))>2)return null;
        const samples=[];
        for(let i=0;i<lines.length;i++){
            const row=lines[i],prev=i?lines[i-1]:null,m=row.memoryKiB;
            if(!integer(row.tsMs,origin,origin+seconds*1000+10000)||
                !integer(row.monotonicMs,first.monotonicMs,end.monotonicMs)||
                Math.abs((row.tsMs-first.tsMs)-(row.monotonicMs-first.monotonicMs))>250||
                !integer(row.cpuTicks,0,Number.MAX_SAFE_INTEGER)||
                !m||!["Rss","Pss","SwapPss"].every(k=>integer(m[k],0,Number.MAX_SAFE_INTEGER))||
                m.Pss>m.Rss)return null;
            if(prev&&(row.tsMs<=prev.tsMs||row.monotonicMs<=prev.monotonicMs||
                row.cpuTicks<prev.cpuTicks||Math.abs(row.sampleIntervalMs-(row.monotonicMs-prev.monotonicMs))>2||
                !num(row.cpuPct)))return null;
            const atMs=row.tsMs-origin,fromMs=prev?prev.tsMs-origin:null;
            samples.push({atMs,fromMs,cpuPct:row.cpuPct,rssKiB:m.Rss,pssKiB:m.Pss,swapPssKiB:m.SwapPss,
                withinWindow:atMs<=seconds*1000,
                intervalWithinWindow:prev!==null&&fromMs>=0&&atMs<=seconds*1000});
        }
        const overlapMs=Math.max(0,Math.min(seconds*1000,last.tsMs-origin)-Math.max(0,first.tsMs-origin));
        return {schema:"post-apollo-dump-shell-resource-v1",scope:"launching-quickshell",pid:end.pid,startTicks:end.startTicks,
            requestedMs:seconds*1000,observedMs:end.observedMs,intervalMs:plan.intervalMs,overlapMs,
            firstOffsetMs:first.tsMs-origin,lastOffsetMs:last.tsMs-origin,samples};
    } catch(_){return null;}
}
