// FP1a: pure hypothetical planning. No authenticated identity or financial IO.
var ROWS=[
{id:"mine",label:"MINE",purpose:"Personal scenarios"},
{id:"shared",label:"SHARED",purpose:"Joint planning scenarios"},
{id:"mom",label:"MOM",purpose:"Separate family planning"},
{id:"granny",label:"GRANNY",purpose:"Separate family planning"},
{id:"family",label:"FAMILY",purpose:"Aggregate scenario without account access"}
];
function contexts(){return ROWS.map(function(x){return context(x.id);});}
function context(id){
    var r=ROWS.filter(function(x){return x.id===id;});
    return r.length===1?{id:r[0].id,label:r[0].label,purpose:r[0].purpose,
        authorized:false,connected:false,hasRecords:false}:null;
}
function moneyCents(value){
    if(typeof value!=="string"||!/^\d{1,8}(?:\.\d{1,2})?$/.test(value))
        return null;
    var parts=value.split(".");
    var amount=Number(parts[0])*100+Number((parts[1]||"").padEnd(2,"0"));
    return Number.isSafeInteger(amount)&&amount<=1000000000?amount:null;
}
function refuse(reason){
    return {ok:false,reason:reason,readOnly:true,persisted:false,
        source:"HYPOTHETICAL_INPUT_ONLY"};
}
function compare(input){
    if(!input||typeof input!=="object"||Array.isArray(input))
        return refuse("INVALID_INPUT");
    var required=["alternativeText","contextId","extraHours","horizonMonths",
        "hourValueText","operatingText","upfrontText"];
    var keys=Object.keys(input).sort();
    if(keys.length!==required.length||
            keys.some(function(x,i){return x!==required[i];}))
        return refuse("INVALID_INPUT_FIELDS");
    if(!context(input.contextId))return refuse("UNKNOWN_CONTEXT");
    var upfront=moneyCents(input.upfrontText);
    var operating=moneyCents(input.operatingText);
    var alternative=moneyCents(input.alternativeText);
    var timeValue=moneyCents(input.hourValueText);
    if([upfront,operating,alternative,timeValue].some(function(x){return x===null;}))
        return refuse("INVALID_MONEY");
    if(!Number.isInteger(input.extraHours)||input.extraHours<0||
            input.extraHours>168)return refuse("INVALID_TIME");
    if(!Number.isInteger(input.horizonMonths)||input.horizonMonths<1||
            input.horizonMonths>360)return refuse("INVALID_HORIZON");
    var timeMonthly=timeValue*input.extraHours;
    var optionMonthly=operating+timeMonthly;
    var optionTotal=upfront+optionMonthly*input.horizonMonths;
    var alternativeTotal=alternative*input.horizonMonths;
    if(![timeMonthly,optionMonthly,optionTotal,alternativeTotal].every(
            Number.isSafeInteger))return refuse("UNSAFE_TOTAL");
    var monthlyAdvantage=alternative-optionMonthly;
    return {ok:true,readOnly:true,persisted:false,bankDataUsed:false,
        accountsReferenced:0,source:"HYPOTHETICAL_INPUT_ONLY",
        contextId:input.contextId,horizonMonths:input.horizonMonths,
        optionTotalCents:optionTotal,alternativeTotalCents:alternativeTotal,
        optionSavingsCents:alternativeTotal-optionTotal,
        timeMonthlyCents:timeMonthly,
        breakEvenMonths:monthlyAdvantage>0
            ?Math.ceil(upfront/monthlyAdvantage):null};
}
