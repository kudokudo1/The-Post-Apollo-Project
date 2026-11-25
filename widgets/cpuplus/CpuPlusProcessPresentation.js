// PROC presentation: completed, bounded same-user census, not an application
// grouping, live process identity, unique RAM total or control authority.
function project(report,validate) {
    if(!report||report.kind!=="census"||report.status!=="COMPLETE"
        ||typeof report.text!=="string"||report.text.length>65536)return null;
    try {
        if(!validate("census",report.text))return null;
        const records=report.text.trim().split("\n").map(x=>JSON.parse(x));
        const end=records.pop();
        if(records.length<1||records.length>6||end.samples!==records.length)return null;
        const count=v=>Number.isSafeInteger(v)&&v>=0;
        const rate=v=>v===null||typeof v==="number"&&Number.isFinite(v)&&v>=0;
        for(const sample of records){
            if(!count(sample.tsMs)||!count(sample.focusMatches)||sample.focusMatches>sample.observed
                ||!sample.coverage||!sample.previousCoverage)return null;
            for(const cover of [sample.coverage,sample.previousCoverage]){
                if(!count(cover.examinedPidEntries)||!count(cover.unreadableOrExited)
                    ||cover.unreadableOrExited>cover.examinedPidEntries||typeof cover.truncated!=="boolean")return null;
            }
            const ids=new Set();
            for(const row of sample.rows){
                if(!count(row.pid)||row.pid===0||ids.has(row.pid)||!count(row.startTicks)
                    ||!count(row.rssKiB)||!count(row.threads)||typeof row.name!=="string"||row.name.length>64
                    ||!rate(row.cpuPct)||!rate(row.readBps)||!rate(row.writeBps))return null;
                ids.add(row.pid);
            }
        }
        const first=records[0],last=records[records.length-1];
        const rows=last.rows.map(row=>{
            // Match only the same PID/start ticks within this capture; top-N
            // selection means missing baseline is unavailable, never zero.
            const before=records.length>1?first.rows.find(x=>x.pid===row.pid&&x.startTicks===row.startTicks):null;
            return {pid:row.pid,name:row.name.replace(/[\x00-\x1f\x7f]/g,"?"),startTicks:row.startTicks,
                rssKiB:row.rssKiB,threads:row.threads,cpuPct:row.cpuPct,readBps:row.readBps,writeBps:row.writeBps,
                change:before?row.rssKiB-before.rssKiB:null};
        });
        return {observed:last.observed,cpuMeasured:last.cpuMeasured,ioMeasured:last.ioMeasured,
            samples:records.length,tsMs:last.tsMs,limited:records.some(x=>x.coverage.truncated||x.previousCoverage.truncated),
            skipped:last.coverage.unreadableOrExited,rows};
    }catch(_){return null;}
}
function rank(view,order){
    if(!view)return [];
    const key=order==="CPU"?"cpuPct":order==="WRITE"?"writeBps":"rssKiB";
    return view.rows.slice().sort((a,b)=>{
        if(a[key]===null)return b[key]===null?a.pid-b.pid:1;
        if(b[key]===null)return -1;
        return b[key]-a[key]||a.pid-b.pid;
    });
}
function gib(k){return (k/1048576).toFixed(3)+" GiB";}
function change(k){return k===null?"N/A":(k>0?"+":"")+(k/1024).toFixed(1)+" MiB";}
function rate(v){return v===null?"N/A":(v/1024).toFixed(1)+" KiB/s";}
