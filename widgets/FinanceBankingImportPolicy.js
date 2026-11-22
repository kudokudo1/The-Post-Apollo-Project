// Banking M1 // Offline, in-memory CSV review. No Actual, provider, or storage access.
// Minimal normalized date, description and signed amount; all amounts in integer cents.
var MAX_CSV_CHARS=65536;
var MAX_IMPORT_ROWS=200;
var MAX_SESSION_ROWS=500;
var ACCOUNT_CHOICES=[
    {id:"cashapp",name:"Cash App"},
    {id:"chime",name:"Chime"},
    {id:"paypal",name:"PayPal"},
    {id:"bank",name:"Other Bank"}
];

function accounts() {
    return ACCOUNT_CHOICES.map(function(a){return {id:a.id,name:a.name};});
}
function money(cents) {
    if(!Number.isSafeInteger(cents))return "INVALID";
    return (cents<0?"-$":"$")+(Math.abs(cents)/100).toFixed(2);
}
function canonicalDate(value) {
    var s=String(value||"").trim(),m,y,mo,d;
    if((m=/^(\d{4})-(\d{2})-(\d{2})$/.exec(s))) {
        y=Number(m[1]);mo=Number(m[2]);d=Number(m[3]);
    } else if((m=/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(s))) {
        y=Number(m[3]);mo=Number(m[1]);d=Number(m[2]);
    } else return null;
    if(y<1900||y>2100||mo<1||mo>12||d<1||d>31)return null;
    var date=new Date(Date.UTC(y,mo-1,d));
    if(date.getUTCFullYear()!==y||date.getUTCMonth()!==mo-1||date.getUTCDate()!==d)
        return null;
    return String(y).padStart(4,"0")+"-"+String(mo).padStart(2,"0")+"-"+String(d).padStart(2,"0");
}
function signedCents(input) {
    var s=String(input===undefined||input===null?"":input).trim();
    if(!s)return null;
    var parens=s.charAt(0)==="("&&s.charAt(s.length-1)===")";
    if(parens)s=s.slice(1,-1).trim();
    if(s.charAt(0)==="$")s=s.slice(1).trim();
    var negative=s.charAt(0)==="-";
    if(negative||s.charAt(0)==="+")s=s.slice(1).trim();
    if(s.charAt(0)==="$")s=s.slice(1).trim();
    if(parens&&negative)return null;
    if(!/^(?:\d{1,7}|\d{1,3}(?:,\d{3})+)(?:\.\d{1,2})?$/.test(s))
        return null;
    var parts=s.replace(/,/g,"").split(".");
    var cents=Number(parts[0])*100+Number((parts[1]||"").padEnd(2,"0"));
    if(!Number.isSafeInteger(cents)||cents<=0||cents>999999999)return null;
    return parens||negative?-cents:cents;
}
// RFC-4180 style double-quote escaping. Reject suspicious quote placement,
// malformed lines, and excessive input rather than guessing account data.
function csvRows(text) {
    if(typeof text!=="string"||!text||text.length>MAX_CSV_CHARS)
        return {ok:false,error:"CSV MISSING OR OVER 64K CHARACTERS"};
    var source=text.charCodeAt(0)===0xFEFF?text.slice(1):text;
    if(/[\u0000-\u0008\u000B\u000C\u000E-\u001F]/.test(source))
        return {ok:false,error:"CSV CONTAINS CONTROL CHARACTERS"};
    var rows=[],row=[],field="",inside=false,afterQuote=false,atStart=true;
    function append() {
        row.push(field);field="";atStart=true;afterQuote=false;
    }
    function flush() {
        append();
        if(row.some(function(c){return c.trim()!=="";}))rows.push(row);
        row=[];
    }
    for(var i=0;i<source.length;++i) {
        var ch=source[i];
        if(inside) {
            if(ch==='"') {
                if(source[i+1]==='"'){field+='"';++i;}
                else {inside=false;afterQuote=true;}
            } else field+=ch;
        } else if(afterQuote) {
            if(ch===",")append();
            else if(ch==="\n"||ch==="\r") {
                flush();
                if(ch==="\r"&&source[i+1]==="\n")++i;
            } else return {ok:false,error:"INVALID CSV QUOTE SEQUENCE"};
        } else if(ch==='"') {
            if(!atStart)return {ok:false,error:"QUOTE INSIDE UNQUOTED FIELD"};
            inside=true;atStart=false;
        } else if(ch===",")append();
        else if(ch==="\n"||ch==="\r") {
            flush();
            if(ch==="\r"&&source[i+1]==="\n")++i;
        } else {field+=ch;atStart=false;}
        if(field.length>1000||rows.length>MAX_IMPORT_ROWS+1)
            return {ok:false,error:"CSV FIELD OR ROW LIMIT EXCEEDED"};
    }
    if(inside)return {ok:false,error:"UNCLOSED CSV QUOTE"};
    if(field||row.length||afterQuote)flush();
    return {ok:true,rows:rows};
}
function normalizedHeader(s) {
    return String(s||"").trim().toLowerCase().replace(/[\s_\-]+/g," ");
}
function headerIndex(names,alternatives) {
    for(var i=0;i<alternatives.length;i++) {
        var n=names.indexOf(alternatives[i]);
        if(n>=0)return n;
    }
    return -1;
}
// Explicit import for one selected manual source: never infers a connected account.
function parseCsv(text,sourceId) {
    var account=ACCOUNT_CHOICES.find(function(a){return a.id===sourceId;});
    if(!account)return {ok:false,error:"CHOOSE A VALID MANUAL SOURCE"};
    var parsed=csvRows(text);
    if(!parsed.ok)return parsed;
    var lines=parsed.rows;
    if(lines.length<2)return {ok:false,error:"CSV NEEDS A HEADER AND AT LEAST ONE ROW"};
    if(lines.length>MAX_IMPORT_ROWS+1)return {ok:false,error:"IMPORT LIMIT: 200 ROWS"};
    var names=lines[0].map(normalizedHeader);
    if(new Set(names).size!==names.length)
        return {ok:false,error:"DUPLICATE COLUMN HEADER"};
    var dateCol=headerIndex(names,["date","transaction date","posted date","completed date"]);
    var descCol=headerIndex(names,["description","details","name","merchant","payee","activity"]);
    var amountCol=headerIndex(names,["amount","net amount","net","total"]);
    var debitCol=headerIndex(names,["debit","withdrawal","outflow"]);
    var creditCol=headerIndex(names,["credit","deposit","inflow"]);
    if(dateCol<0||descCol<0||(amountCol<0&&(debitCol<0||creditCol<0)))
        return {ok:false,error:"CSV REQUIRES DATE, DESCRIPTION, AND AMOUNT (OR DEBIT/CREDIT)"};
    if(amountCol>=0&&(debitCol>=0||creditCol>=0))
        return {ok:false,error:"AMBIGUOUS AMOUNT AND DEBIT/CREDIT COLUMNS"};
    var output=[],fingerprints={};
    for(var i=1;i<lines.length;++i) {
        var cols=lines[i],line=i+1;
        if(cols.length!==names.length)
            return {ok:false,error:"CSV COLUMN COUNT MISMATCH ON ROW "+line};
        var date=canonicalDate(cols[dateCol]);
        var desc=String(cols[descCol]||"").trim();
        if(!date||!desc||desc.length>160)
            return {ok:false,error:"INVALID DATE OR DESCRIPTION ON ROW "+line};
        var amount=null;
        if(amountCol>=0)amount=signedCents(cols[amountCol]);
        else {
            var debit=String(cols[debitCol]||"").trim();
            var credit=String(cols[creditCol]||"").trim();
            if(Boolean(debit)===Boolean(credit))
                return {ok:false,error:"EXACTLY ONE DEBIT/CREDIT REQUIRED ON ROW "+line};
            amount=signedCents(debit||credit);
            if(amount!==null)amount=(debit?-1:1)*Math.abs(amount);
        }
        if(amount===null)
            return {ok:false,error:"INVALID SIGNED AMOUNT ON ROW "+line};
        var fingerprint=sourceId+"\u001f"+date+"\u001f"+desc.toLowerCase()+"\u001f"+amount;
        if(fingerprints[fingerprint])
            return {ok:false,error:"IDENTICAL ROWS REQUIRE MANUAL REVIEW; ROW "+line};
        fingerprints[fingerprint]=true;
        output.push({sourceId:sourceId,sourceName:account.name,date:date,
                     description:desc,amountCents:amount,fingerprint:fingerprint});
    }
    return {ok:true,mode:"MANUAL SESSION",sourceName:account.name,rows:output,
            rowsCount:output.length,connected:false,persisted:false};
}
function dayNumber(date) {
    var m=/^(\d{4})-(\d{2})-(\d{2})$/.exec(date||"");
    if(!m)return null;
    var v=Date.UTC(Number(m[1]),Number(m[2])-1,Number(m[3]))/86400000;
    return Number.isFinite(v)?v:null;
}
function transferHint(s) {
    return /\b(transfer|xfer|cash\s?app|paypal|chime|ach|withdrawal)\b/i.test(s);
}
function suggestedPairs(rows,confirmed) {
    if(!Array.isArray(rows)||!Array.isArray(confirmed))return [];
    var used={},out=[];
    confirmed.forEach(function(pair){
        if(Array.isArray(pair)&&pair.length===2) {
            used[pair[0]]=true;used[pair[1]]=true;
        }
    });
    for(var i=0;i<rows.length;i++) {
        var a=rows[i];
        if(used[a.id]||a.amountCents>=0)continue;
        var options=[];
        for(var j=0;j<rows.length;j++) {
            var b=rows[j];
            if(used[b.id]||b.amountCents<=0||a.sourceId===b.sourceId
               ||a.amountCents!==-b.amountCents)continue;
            var distance=Math.abs(dayNumber(a.date)-dayNumber(b.date));
            if(distance<=3&&(transferHint(a.description)||transferHint(b.description)))
                options.push(b);
        }
        // Ambiguous equal-size transfers are never auto-paired.
        if(options.length===1) {
            var b=options[0],otherDebits=rows.filter(function(d){
                return !used[d.id]&&d.amountCents<0&&d.sourceId!==b.sourceId
                    &&d.amountCents===-b.amountCents
                    &&Math.abs(dayNumber(d.date)-dayNumber(b.date))<=3
                    &&(transferHint(d.description)||transferHint(b.description));
            });
            if(otherDebits.length===1) {
                used[a.id]=true;used[b.id]=true;
                out.push({fromId:a.id,toId:b.id,fromSource:a.sourceName,
                    toSource:b.sourceName,date:a.date,amountCents:-a.amountCents});
            }
        }
    }
    return out;
}
// Conservatively, every debit remains spending until the user explicitly confirms
// an unambiguous cross-account pair. Credits are not automatically called income.
function review(rows,confirmed) {
    if(!Array.isArray(rows)||!Array.isArray(confirmed)||rows.length>MAX_SESSION_ROWS)
        return {ok:false,error:"INVALID SESSION"};
    var byId={},seen={},credits=0,debits=0,excluded=0;
    for(var i=0;i<rows.length;i++) {
        var r=rows[i];
        if(!r||typeof r.id!=="string"||!r.id||byId[r.id]||
           !Number.isSafeInteger(r.amountCents)||r.amountCents===0||
           !ACCOUNT_CHOICES.some(function(a){return a.id===r.sourceId;}))
            return {ok:false,error:"INVALID SESSION ROW"};
        byId[r.id]=r;
        if(r.amountCents<0)debits+=-r.amountCents;
        else credits+=r.amountCents;
        if(!Number.isSafeInteger(debits)||!Number.isSafeInteger(credits))
            return {ok:false,error:"SESSION AMOUNT OVERFLOW"};
        if(r.fingerprint&&seen[r.fingerprint])
            return {ok:false,error:"DUPLICATE ROW ALREADY IMPORTED"};
        if(r.fingerprint)seen[r.fingerprint]=true;
    }
    var locked={};
    for(var p=0;p<confirmed.length;p++) {
        var pair=confirmed[p];
        if(!Array.isArray(pair)||pair.length!==2||pair[0]===pair[1]||
           locked[pair[0]]||locked[pair[1]])return {ok:false,error:"INVALID CONFIRMED PAIR"};
        var a=byId[pair[0]],b=byId[pair[1]];
        if(!a||!b||a.sourceId===b.sourceId||
           a.amountCents>=0||b.amountCents<=0||a.amountCents!==-b.amountCents)
            return {ok:false,error:"INVALID CONFIRMED TRANSFER"};
        locked[pair[0]]=true;locked[pair[1]]=true;excluded+=-a.amountCents;
    }
    return {ok:true,mode:"MANUAL SESSION",debitsCents:debits,
        creditsCents:credits,confirmedTransferOutCents:excluded,
        spendingLikeDebitsCents:debits-excluded,confirmedPairs:confirmed.length,
        candidates:suggestedPairs(rows,confirmed),connected:false,persisted:false};
}
