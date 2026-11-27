// KillStore-owned priority custody. Values are observations, not grants.
function nice(n) { return Number.isInteger(n) && n>=-20 && n<=19; }
function key(pid,birth,comm) {
    return JSON.stringify([pid,birth,comm]);
}
function snapshot(s) {
    return !!s && nice(s.nice) && Number.isSafeInteger(s.uid) && s.uid>0
        && (s.scheduler===0 || s.scheduler===3)
        && Number.isSafeInteger(s.soft) && s.soft>=-1
        && Number.isSafeInteger(s.hard) && s.hard>=-1
        && (s.hard===-1 || (s.soft>=0 && s.soft<=s.hard));
}
function equal(a,b) {
    return snapshot(a) && snapshot(b) && a.nice===b.nice && a.uid===b.uid
        && a.scheduler===b.scheduler && a.soft===b.soft && a.hard===b.hard;
}
function reversible(original,current,target,soft) {
    return nice(original) && nice(current) && nice(target)
        && Number.isInteger(soft) && soft>=1 && soft<=40
        && Math.min(original,current,target)>=20-soft;
}
function request(record,operation,target) {
    if (!record || !snapshot(record.current) || !nice(record.original)
        || (record.state!=="observed" && record.state!=="managed")
        || (operation!=="apply" && operation!=="restore")
        || (operation==="restore" && (record.state!=="managed" || target!==record.original))
        || target===record.current.nice
        || !reversible(record.original,record.current.nice,target,record.current.soft)) return null;
    return {operation:operation,original:record.original,expected:record.current.nice,
        target:target,expectedSoft:record.current.soft,expectedSnapshot:record.current};
}
function unavailable(prior, uncertain) {
    // Never recapture an unknown mutation or replace an owned baseline.
    return {state:uncertain || (prior && (prior.state==="managed" || prior.state==="unknown"))
        ? "unknown" : "unavailable", original:prior ? prior.original : null,
        current:prior ? prior.current : null};
}
function consume(prior,req,raw) {
    const capture=req.operation==="capture";
    let result;
    try {
        if (typeof raw!=="string" || raw.length>32768) return unavailable(prior,!capture);
        result=JSON.parse(raw);
    } catch(error) { return unavailable(prior,!capture); }
    if (!result || result.schema!=="post-apollo-kill-priority-v1"
        || result.serial!==req.serial || result.pid!==req.pid
        || result.startTicks!==req.startTicks || result.comm!==req.comm
        || result.operation!==req.operation) return unavailable(prior,!capture);
    if (capture) {
        if (result.state!=="observed" || result.attempted!==false || !snapshot(result.before))
            return unavailable(prior,false);
        if (prior && prior.state==="unknown") return prior;
        if (prior && prior.state==="managed") return equal(prior.current,result.before) ? prior : unavailable(prior,true);
        return {state:"observed",original:result.before.nice,current:result.before};
    }
    if (result.state==="refused" && result.attempted===false) {
        // A refused operation may mean the baseline changed. Do not silently retry.
        return unavailable(prior,false);
    }
    if (!prior || !equal(prior.current,result.before) || !equal(req.expectedSnapshot,result.before)
        || !snapshot(result.after) || result.after.nice!==req.target
        || !equal(Object.assign({},result.before,{nice:req.target}),result.after)
        || result.original!==prior.original || result.original!==req.original
        || result.attempted!==true
        || result.state!==(req.operation==="restore"?"restored":"applied"))
        return unavailable(prior,true);
    return {state:req.target===prior.original?"observed":"managed",
        original:prior.original,current:result.after};
}
