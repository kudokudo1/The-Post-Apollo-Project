// M4a: local preview only. No profile defaults, persistence or application.
function names(){return ["BALANCED","DEVELOPMENT","GAMING","LOCAL AI","STABILITY","CUSTOM"];}
function empty(){return {capacityGiB:null,swappiness:null};}
function capacity(v){return Number.isSafeInteger(v)&&v>=0&&v<=64&&v%4===0;}
function policy(v){return Number.isSafeInteger(v)&&v>=0&&v<=200;}
function valid(d){return d!==null&&typeof d==="object"&&!Array.isArray(d)
    &&Object.keys(d).length===2&&Object.prototype.hasOwnProperty.call(d,"capacityGiB")
    &&Object.prototype.hasOwnProperty.call(d,"swappiness")
    &&(d.capacityGiB===null||capacity(d.capacityGiB))&&(d.swappiness===null||policy(d.swappiness));}
function capture(d,key,value){
    if(!valid(d))return null;
    if(key==="capacityGiB"&&capacity(value))return {capacityGiB:value,swappiness:d.swappiness};
    if(key==="swappiness"&&policy(value))return {capacityGiB:d.capacityGiB,swappiness:value};
    return null;
}
function preview(name,d,actualKiB,actualSwappiness){
    if((name!==""&&!names().includes(name))||!valid(d))return null;
    const target=name==="CUSTOM"?d:empty();
    const actualDisk=Number.isSafeInteger(actualKiB)&&actualKiB>=0?actualKiB:null;
    const actualPolicy=policy(actualSwappiness)?actualSwappiness:null;
    return {capacity:{actual:actualDisk,target:target.capacityGiB,
        deltaKiB:actualDisk===null||target.capacityGiB===null?null:target.capacityGiB*1048576-actualDisk},
        swappiness:{actual:actualPolicy,target:target.swappiness,
        delta:actualPolicy===null||target.swappiness===null?null:target.swappiness-actualPolicy},
        canApply:false};
}
function gib(k){return k===null?"UNAVAILABLE":(k/1048576).toFixed(2)+" GiB";}
function delta(v,unit){return v===null?"N/A":(v>0?"+":"")+v.toFixed(unit==="GiB"?2:0)+(unit?" "+unit:"");}

// M5: descriptive requirements only. No executable plan, ordering or grants.
// Extended observations must be requalified independently; a profile is intent.
function applicationPreview(name,d,actualKiB,actualSwappiness,ready,busy,validDraft){
    if(name!=="CUSTOM"||!validDraft(d))return null;
    const rows=[];
    const add=(key,label,target,assessment,permission,recovery)=>{
        rows.push({key,label,target:String(target),assessment,permission,recovery});
    };
    if(d.capacityGiB!==null){
        const actual=ready&&Number.isSafeInteger(actualKiB)&&actualKiB>=0?actualKiB:null;
        const delta=actual===null?null:d.capacityGiB*1048576-actual;
        const assessment=d.capacityGiB===0?"ZERO TARGET // REMOVAL NOT SUPPORTED":
            delta===null?"OBSERVATION REQUIRED":delta===0?"OBSERVED MATCH":
            delta>0?"INCREASE CANDIDATE":"REDUCTION // PROTECTED HOLD";
        add("capacity","MANAGED DISK SWAP",d.capacityGiB+" GiB",assessment,
            "CAPACITY-SCOPED AUTHORIZATION; MANAGED ALLOCATION IDENTITY",
            "FRESH CAPACITY / OCCUPANCY / RESERVE CHECK; VERIFIED RECOVERY AND READBACK");
    }
    if(d.swappiness!==null){
        const actual=ready&&policy(actualSwappiness)?actualSwappiness:null;
        add("swappiness","SWAPPINESS",d.swappiness,actual===null?"OBSERVATION REQUIRED":actual===d.swappiness?"OBSERVED MATCH":"CHANGE CANDIDATE",
            "VM POLICY-SCOPED AUTHORIZATION","CAPTURE PREVIOUS VALUE; VERIFY READBACK AND RECOVERY");
    }
    if(d.priority!==null)add("priority","SWAP PRIORITY",d.priority.deviceHint+" / "+d.priority.value,
        "FRESH DEVICE OBSERVATION REQUIRED","DEVICE-SCOPED AUTHORIZATION; LOCATOR IS NOT IDENTITY",
        "QUALIFY DEVICE LIFECYCLE, OCCUPANCY AND PREVIOUS PRIORITY; NO FORCED WITHDRAWAL");
    if(d.zram!==null)add("zram","ZRAM ALGORITHM",d.zram.deviceHint+" / "+d.zram.algorithm,
        "FRESH DEVICE AND ALGORITHM SUPPORT REQUIRED","ZRAM-SCOPED AUTHORIZATION; PROTECTED DEVICE IDENTITY",
        "QUALIFY RESET / DATA PRESERVATION AND RECOVERY; NO IMPLICIT RESET");
    const a=d.advanced;
    if(a!==null){
        const conflict=a.background!==null&&a.writer!==null&&
            (a.background.unit!==a.writer.unit||a.background.value>=a.writer.value);
        for(const [key,label,unit] of [["cachePressure","CACHE PRESSURE",""],["background","BACKGROUND WRITEBACK",""],["writer","WRITER WRITEBACK",""],["writebackCentisecs","FLUSH INTERVAL"," cs"],["expireCentisecs","DIRTY DATA AGE"," cs"]]){
            if(a[key]===null)continue;
            const pair=key==="background"||key==="writer";
            add(key,label,pair?a[key].value+" "+a[key].unit:a[key]+unit,
                pair&&conflict?"THRESHOLDS INCOMPATIBLE OR NOT COMPARABLE":"FRESH VM OBSERVATION REQUIRED",
                "VM POLICY-SCOPED AUTHORIZATION",
                pair?"CAPTURE BOTH THRESHOLD MODES AND VALUES; QUALIFY ORDER AND RECOVERY":"CAPTURE PREVIOUS VALUE; VERIFY READBACK AND RECOVERY");
        }
    }
    return {rows, status:busy?"OPERATION BUSY // HOLD":rows.length===0?"NO TARGETS":ready?"PREVIEW ONLY // HOLD":"OBSERVATION UNAVAILABLE // HOLD",
        canApply:false};
}
