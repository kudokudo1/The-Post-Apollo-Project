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
