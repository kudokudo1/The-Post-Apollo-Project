// K8d: visual/draft-only resource editor. No actuation, defaults or host assumptions.
function cards() {
    return [
        {key:"cpu",title:"CPU",scope:"PRIORITY / LEADER THREAD; QUOTA / GROUP",controls:[
            {key:"quota",title:"QUOTA DRAFT",min:10,max:100,step:5,unit:"% OF ONE CPU",initial:75},
            {key:"nice",title:"PRIORITY / NICE",min:-20,max:19,step:1,unit:"NICE",initial:0}
        ],note:"AFFINITY // CURRENT LEADER MASK ONLY; EXPANSION UNVERIFIED"},
        {key:"memory",title:"MEMORY",scope:"RLIMIT_AS / VIRTUAL ADDRESS SPACE",controls:[
            {key:"virtual",title:"ADDRESS SPACE",min:128,max:8192,step:128,unit:"MiB",initial:2048}
        ],note:"NOT AN RSS OR PHYSICAL RAM CAP"},
        {key:"swap",title:"SWAP",scope:"CGROUP / SHARED-GROUP BUDGET",controls:[
            {key:"budget",title:"SWAP BUDGET",min:0,max:8192,step:1,unit:"MiB",initial:1024}
        ],note:"CGROUP MEMBERSHIP AND DELEGATION UNVERIFIED; ZERO IS NOT SWAP PURGE"},
        {key:"disk",title:"DISK I/O",scope:"I/O PRIORITY / THREAD; BANDWIDTH / GROUP",controls:[
            {key:"read",title:"READ DRAFT",min:1,max:512,step:1,unit:"MiB/s",initial:64},
            {key:"write",title:"WRITE DRAFT",min:1,max:512,step:1,unit:"MiB/s",initial:64}
        ],note:"NO VERIFIED DEVICE OR CONTROLLER"},
        {key:"threads",title:"THREADS",scope:"CGROUP / TASK COUNT",controls:[
            {key:"tasks",title:"TASK COUNT",min:1,max:512,step:1,unit:"TASKS",initial:64}
        ],note:"SHARED CGROUP, NOT A PER-PID THREAD CAP"},
        {key:"gpu",title:"GPU",scope:"READ-ONLY OBSERVATION",controls:[],
            note:"NO VERIFIED PER-PROCESS GPU / VRAM CONTROL"},
        {key:"network",title:"NETWORK",scope:"NAMESPACE OBSERVATION",controls:[],
            note:"NO VERIFIED PER-PROCESS BANDWIDTH CONTROL"}
    ];
}
function find(key) {
    var rows=cards();
    for(var i=0;i<rows.length;i++) if(rows[i].key===key) return rows[i];
    return null;
}
function identity(target) {
    if(!target||!Number.isSafeInteger(Number(target.pid))||Number(target.pid)<=1
            ||!Number.isSafeInteger(Number(target.startTicks))||Number(target.startTicks)<=0
            ||typeof target.comm!=="string"||!target.comm) return "";
    return JSON.stringify([Number(target.pid),Number(target.startTicks),target.comm]);
}
function priorityPresets() {
    return [{key:"normal",label:"NORMAL",nice:0},
        {key:"background",label:"BACKGROUND",nice:10},
        {key:"lowest",label:"LOWEST",nice:19}];
}
function hasValue(previous,key,field) {
    var entry=previous[key];
    return !!entry && !!entry.values && Object.prototype.hasOwnProperty.call(entry.values,field);
}
function stagePriorityPreset(previous,key) {
    var presets=priorityPresets();
    for(var i=0;i<presets.length;i++)
        if(presets[i].key===key) return stageValue(previous,"cpu","nice",presets[i].nice);
    return previous;
}
function stageMode(previous,key,mode) {
    var spec=find(key);
    if(!spec||!spec.controls.length||["off","manual","auto","hold"].indexOf(mode)<0)
        return previous;
    var result=Object.assign({},previous);
    var existing=result[key]||{mode:"hold",values:{}};
    result[key]={mode:mode,values:Object.assign({},existing.values)};
    return result;
}
function stageValue(previous,key,field,value) {
    if(key==="swap"&&field==="budget") return stageSwap(previous,"budget",value);
    var spec=find(key);
    if(!spec) return previous;
    var control=null;
    for(var i=0;i<spec.controls.length;i++)
        if(spec.controls[i].key===field) control=spec.controls[i];
    if(!control||typeof value!=="number"||!isFinite(value)) return previous;
    var normalized=Math.max(control.min,Math.min(control.max,value));
    normalized=control.min+Math.round((normalized-control.min)/control.step)*control.step;
    normalized=Math.max(control.min,Math.min(control.max,normalized));
    var result=Object.assign({},previous);
    var existing=result[key]||{mode:"hold",values:{}};
    var values=Object.assign({},existing.values);
    values[field]=normalized;
    result[key]={mode:"manual",values:values};
    return result;
}
function mode(previous,key) {
    return previous[key]?previous[key].mode:(key==="cpu"||key==="disk"||key==="swap"?"manual":"hold");
}
function value(previous,key,field) {
    var spec=find(key);
    if(!spec) return null;
    for(var i=0;i<spec.controls.length;i++) if(spec.controls[i].key===field) {
        var selected=previous[key]&&previous[key].values;
        return selected&&Object.prototype.hasOwnProperty.call(selected,field)
            ?selected[field]:spec.controls[i].initial;
    }
    return null;
}
// Parse Linux Cpus_allowed_list, never derive CPU IDs from a count.
function cpuIds(mask) {
    if(typeof mask!=="string"||!mask||mask.length>4096) return [];
    var result=[];
    var parts=mask.split(",");
    for(var i=0;i<parts.length;i++) {
        if(!/^\d+(?:-\d+)?$/.test(parts[i])) return [];
        var bounds=parts[i].split("-"),lo=Number(bounds[0]),hi=Number(bounds[bounds.length-1]);
        if(!Number.isSafeInteger(lo)||!Number.isSafeInteger(hi)||lo<0||hi<lo||hi>1048575||hi-lo>4095) return [];
        for(var cpu=lo;cpu<=hi;cpu++) {
            if(result.length>=4096||result.indexOf(cpu)>=0) return [];
            result.push(cpu);
        }
    }
    return result.sort((a,b)=>a-b);
}
function stageAffinity(previous,allowed,selected) {
    if(!Array.isArray(allowed)||!Array.isArray(selected)||!selected.length
        ||selected.some(x=>!Number.isSafeInteger(x)||allowed.indexOf(x)<0)
        ||new Set(selected).size!==selected.length) return previous;
    var result=Object.assign({},previous);
    var entry=previous.cpu||{mode:"manual",values:{}};
    result.cpu={mode:"manual",values:Object.assign({},entry.values,{affinity:selected.slice().sort((a,b)=>a-b)})};
    return result;
}
function affinitySelection(previous,allowed) {
    var entry=previous.cpu,selected=entry&&entry.values&&entry.values.affinity;
    return Array.isArray(selected)&&selected.length&&selected.every(x=>allowed.indexOf(x)>=0)
        ?selected.slice():allowed.slice();
}
function dropAffinity(previous) {
    if(!hasValue(previous,"cpu","affinity")) return previous;
    var result=Object.assign({},previous),entry=previous.cpu;
    var values=Object.assign({},entry.values);
    delete values.affinity;
    if(!Object.keys(values).length&&entry.mode==="manual") delete result.cpu;
    else result.cpu={mode:entry.mode,values:values};
    return result;
}
function ioPriority(previous) {
    var entry=previous.disk, p=entry&&entry.values&&entry.values.ioPriority;
    return p || {kind:"best_effort",level:4};
}
function stageIoPriority(previous,kind,level) {
    if(kind!=="best_effort"&&kind!=="idle") return previous;
    if(kind==="best_effort"&&(!Number.isInteger(level)||level<0||level>7)) return previous;
    var result=Object.assign({},previous);
    var entry=previous.disk||{mode:"manual",values:{}};
    var priority=kind==="idle"?{kind:kind}:{kind:kind,level:level};
    result.disk={mode:"manual",values:Object.assign({},entry.values,{ioPriority:priority})};
    return result;
}
// A finite zero and the kernel's "max" token are different requests.
function swapChoice(previous) {
    var entry=previous.swap, values=entry&&entry.values;
    if(values&&values.swapKind==="uncapped") return {kind:"uncapped"};
    if(values&&values.swapKind==="budget") return {kind:"budget",mib:values.budget};
    return {kind:"preview",mib:1024};
}
function stageSwap(previous,kind,mib) {
    if(kind!=="budget"&&kind!=="uncapped") return previous;
    if(kind==="budget"&&(!Number.isSafeInteger(mib)||mib<0||mib>8192)) return previous;
    var result=Object.assign({},previous);
    var values=kind==="budget"?{swapKind:kind,budget:mib}:{swapKind:kind};
    result.swap={mode:"manual",values:values};
    return result;
}
function summary(previous) {
    var lines=[];
    var rows=cards();
    for(var i=0;i<rows.length;i++) {
        var spec=rows[i],entry=previous[spec.key];
        if(!entry) continue;
        var description=spec.title+" // "+entry.mode.toUpperCase();
        if(entry.mode==="manual") {
            var fields=[];
            for(var j=0;j<spec.controls.length;j++) {
                var c=spec.controls[j];
                // Priority and quota are different kernel operations. Never
                // turn a placeholder value into a requested CPU setting.
                if(spec.key==="swap"||((spec.key==="cpu"||spec.key==="disk")&&!hasValue(previous,spec.key,c.key))) continue;
                fields.push(c.title+" "+value(previous,spec.key,c.key)+" "+c.unit);
            }
            if(spec.key==="cpu"&&hasValue(previous,"cpu","affinity")) fields.push("AFFINITY "+entry.values.affinity.join(","));
            if(spec.key==="disk"&&hasValue(previous,"disk","ioPriority")) {
                var p=entry.values.ioPriority;
                fields.push(p.kind==="idle"?"I/O PRIORITY IDLE":"I/O PRIORITY BEST EFFORT "+p.level);
            }
            if(spec.key==="swap") {
                var swap=swapChoice(previous);
                if(swap.kind==="uncapped") fields.push("NO CAP // memory.swap.max=max");
                else if(swap.kind==="budget") fields.push("SWAP BUDGET "+swap.mib+" MiB");
            }
            description+=" // "+(fields.length?fields.join(" · "):"NO "+spec.key.toUpperCase()+" VALUES SELECTED");
        }
        if(entry.mode==="auto") description+=" // POLICY NOT DEFINED";
        lines.push(description);
    }
    return lines;
}
