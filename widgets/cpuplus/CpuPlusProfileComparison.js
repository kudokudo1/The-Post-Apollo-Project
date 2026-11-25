// Read-only comparison against explicitly captured observations. Device hints
// never establish identity; no row or warning grants execution authority.
function integer(v,low,high){return Number.isSafeInteger(v)&&v>=low&&v<=high;}
function rows(sample){
    if(!sample||!Array.isArray(sample.rows)||sample.rows.length>256)return null;
    const seen=new Set(),out=[];
    for(const r of sample.rows){
        if(!r||typeof r.name!=="string"||!r.name||seen.has(r.name)
            ||!integer(r.size,1,Number.MAX_SAFE_INTEGER)||!integer(r.priority,-32768,32767))return null;
        seen.add(r.name);out.push({name:r.name,size:r.size,priority:r.priority});
    }
    return out;
}
function matchDevice(target,observed){
    if(observed===null)return {state:"OBSERVATION UNAVAILABLE",row:null};
    const row=observed.find(r=>r.name===target.deviceHint);
    if(!row)return {state:"DEVICE NOT OBSERVED",row:null};
    if(row.size!==target.sizeKiB)return {state:"SIZE MISMATCH // RESELECT",row:null};
    return {state:"LOCATOR AND SIZE MATCH ONLY",row};
}
function result(key,label,target,actual,status,delta=null){
    return {key,label,target,actual,status,delta};
}
function numeric(key,label,target,actual,unit){
    const text=v=>v===null?"UNAVAILABLE":String(v)+(unit?" "+unit:"");
    if(target===null)return result(key,label,"NOT SET",text(actual),"NOT SET");
    if(actual===null)return result(key,label,text(target),"UNAVAILABLE","OBSERVATION UNAVAILABLE");
    return result(key,label,text(target),text(actual),target===actual?"MATCH":"DIFFERENT",target-actual);
}
function plan(draft,sample,ready,valid,algorithmPath,advancedPaths){
    if(!ready||!valid(draft))return null;
    const observed=rows(sample);
    const z=draft.zram===null?null:matchDevice(draft.zram,observed);
    const zPath=z&&z.row?algorithmPath(draft.zram.deviceHint):null;
    if(z&&z.row&&!zPath)return null;
    const needAdvanced=draft.advanced!==null;
    return {draft:JSON.parse(JSON.stringify(draft)),rows:observed,
        zramRead:!!zPath,advancedRead:needAdvanced,paths:(zPath?[zPath]:[]).concat(needAdvanced?advancedPaths():[])};
}
function compare(p,raw,readOk,parseZram,parseAdvanced,spec,validSpec){
    if(!p)return null;
    const d=p.draft, out=[];
    let z=null,a=null;
    if(readOk&&typeof raw==="string"&&raw.length<=6144){
        const lines=raw.trim().split(/\r?\n/);
        const count=(p.zramRead?1:0)+(p.advancedRead?7:0);
        if(lines.length===count){
            if(p.zramRead)z=parseZram(lines[0]);
            if(p.advancedRead)a=parseAdvanced(lines.slice(p.zramRead?1:0).join("\n"));
        }
    }
    if(d.priority===null)out.push(result("priority","SWAP PRIORITY","NOT SET","NOT CHECKED","NOT SET"));
    else{
        const m=matchDevice(d.priority,p.rows);
        const target=d.priority.deviceHint+" / "+d.priority.value;
        if(!m.row)out.push(result("priority","SWAP PRIORITY",target,"UNAVAILABLE",m.state));
        else out.push(result("priority","SWAP PRIORITY",target,String(m.row.priority),
            (m.row.priority===d.priority.value?"MATCH":"DIFFERENT")+" // LOCATOR AND SIZE ONLY",d.priority.value-m.row.priority));
    }
    if(d.zram===null)out.push(result("zram","ZRAM ALGORITHM","NOT SET","NOT CHECKED","NOT SET"));
    else{
        const m=matchDevice(d.zram,p.rows);
        const target=d.zram.deviceHint+" / "+d.zram.algorithm;
        if(!m.row)out.push(result("zram","ZRAM ALGORITHM",target,"UNAVAILABLE",m.state));
        else if(!z)out.push(result("zram","ZRAM ALGORITHM",target,"UNAVAILABLE","ALGORITHM READ UNAVAILABLE"));
        else out.push(result("zram","ZRAM ALGORITHM",target,z.actual,
            (!z.options.includes(d.zram.algorithm)?"UNSUPPORTED ALGORITHM":z.actual===d.zram.algorithm?"MATCH":"DIFFERENT")+" // LOCATOR AND SIZE ONLY"));
    }
    for(const [key,label,unit] of [["cachePressure","CACHE PRESSURE",""],["background","BACKGROUND WRITEBACK",""],["writer","WRITER WRITEBACK",""],["writebackCentisecs","FLUSH INTERVAL","cs"],["expireCentisecs","DIRTY DATA AGE","cs"]]){
        const target=d.advanced?d.advanced[key]:null;
        const observed=spec(a,key);
        const actual=validSpec(observed,observed?observed.value:null)?observed.value:null;
        if(key==="background"||key==="writer"){
            const actualText=actual!==null?actual+" "+observed.unit:a&&a[key]?a[key].mode:"UNAVAILABLE";
            if(target===null)out.push(result(key,label,"NOT SET",actualText,"NOT SET"));
            else if(actual===null)out.push(result(key,label,target.value+" "+target.unit,actualText,a?"OBSERVED PAIR NOT COMPARABLE":"OBSERVATION UNAVAILABLE"));
            else if(target.unit!==observed.unit)out.push(result(key,label,target.value+" "+target.unit,actualText,"UNIT MISMATCH // NO CONVERSION"));
            else out.push(numeric(key,label,target.value,actual,target.unit));
        }else out.push(numeric(key,label,target,actual,unit));
    }
    return {rows:out,canApply:false};
}
