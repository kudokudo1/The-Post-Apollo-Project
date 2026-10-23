// FinanceW compact spreadsheet stepping. Pure integer-cents calculations.
// This module never executes writes or opens finance authorization.
function normalizeStepperAmount(text){
    const raw=String(text===null || text===undefined ? "" : text).trim().replace(/^\$/,"");
    if(!/^\d{1,9}(?:\.\d{1,2})?$/.test(raw))return null;
    const parts=raw.split(".");
    const cents=Number(parts[0])*100+Number((parts[1]||"").padEnd(2,"0"));
    return Number.isSafeInteger(cents)&&cents>=0&&cents<=99999999999?cents:null;
}
function stepAmount(text,centsDelta,allowZero){
    const cents=normalizeStepperAmount(text);
    if(cents===null || !Number.isSafeInteger(centsDelta))return null;
    const result=cents+centsDelta;
    if(!Number.isSafeInteger(result)||result>99999999999
            || result<(allowZero?0:1))return null;
    return (result/100).toFixed(2);
}
