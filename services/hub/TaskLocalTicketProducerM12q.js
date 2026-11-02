.pragma library
// TASKS M12q: pure, disabled-production ticket plan/readback policy.
// No I/O, no callbacks, no privileged service. In QML this module may only
// be entered through ApolloHubTodoStore.ticketProducerEnabled (literal false).
// CONFIRMED means exact source readback in the test contract, NOT an
// authenticated writer, cross-resource atomicity, or hostile-UID isolation.

var ROUTES = {
    HUB:["addTask","renameTask","setTaskDone","removeTask"],
    DETAILS:["updateTaskDetails"],
    PLANNER:["addTask","updateTaskDetails"],
    PROJECTS:["createProject","renameProject","deleteProject","assignTaskProject"]
};
function copy(value) { return JSON.parse(JSON.stringify(value)); }
function recognized(surface,method) {
    return Object.prototype.hasOwnProperty.call(ROUTES,surface)
        && ROUTES[surface].indexOf(method) >= 0;
}
function shape(args,keys) {
    if(!args || typeof args !== "object" || Array.isArray(args)) return false;
    var actual=Object.keys(args).sort(), wanted=keys.slice().sort();
    return JSON.stringify(actual) === JSON.stringify(wanted);
}
function mutate(policy,doc,method,args,nowMs) {
    if(method==="addTask" && shape(args,["title"]))
        return policy.create(doc,args.title,nowMs);
    if(method==="renameTask" && shape(args,["id","title"]))
        return policy.update(doc,args.id,"rename",args.title,nowMs,false);
    if(method==="setTaskDone" && shape(args,["id","done"]))
        return policy.update(doc,args.id,"done",args.done,nowMs,false);
    if(method==="removeTask" && shape(args,["id","confirmed"]))
        return policy.update(doc,args.id,"delete",null,nowMs,args.confirmed);
    if(method==="updateTaskDetails" &&
            shape(args,["id","priority","description","dueDate"]))
        return policy.updateDetails(doc,args.id,args.priority,
                                    args.description,args.dueDate,nowMs);
    if(method==="createProject" && shape(args,["name"]))
        return policy.createProject(doc,args.name,nowMs);
    if(method==="renameProject" && shape(args,["id","name"]))
        return policy.renameProject(doc,args.id,args.name,nowMs);
    if(method==="deleteProject" && shape(args,["id","confirmed"]))
        return policy.deleteProject(doc,args.id,nowMs,args.confirmed);
    if(method==="assignTaskProject" && shape(args,["taskId","projectId"]))
        return policy.assignProject(doc,args.taskId,args.projectId,nowMs);
    return {ok:false,reason:"INVALID_OPERATION_ARGUMENTS"};
}
function refusal(reason) {
    return {admitted:false,ticketId:"",state:"BLOCKED",reason:reason,
            disposition:"KEEP_DRAFT"};
}
function makeTicketId(session,sequence) {
    if(typeof session!=="string" || !/^[A-Za-z0-9]{8,36}$/.test(session)
            || typeof sequence!=="number" ||
            !isFinite(sequence) || Math.floor(sequence)!==sequence
            || sequence<1 || sequence>999999999) return "";
    return "m12o-local-"+session+"-"+sequence;
}
function plan(policy,doc,surface,method,args,nowMs,session,sequence) {
    if(!policy || typeof policy.validate!=="function" ||
            typeof policy.parse!=="function" ||
            typeof policy.view!=="function" ||
            !recognized(surface,method))
        return refusal("UNSUPPORTED_ROUTE");
    var ticketId=makeTicketId(session,sequence);
    if(!ticketId || typeof nowMs!=="number" ||
            !isFinite(nowMs) || Math.floor(nowMs)!==nowMs || nowMs<1)
        return refusal("INVALID_REQUEST_IDENTITY");
    try {
        if(!policy.validate(doc).ok) return refusal("INVALID_BASELINE");
        var base=copy(doc);
        var mutation=mutate(policy,base,method,args,nowMs);
        if(!mutation || mutation.ok!==true)
            return refusal(mutation && mutation.reason || "POLICY_REFUSED");
        if(!policy.validate(mutation.document).ok)
            return refusal("INVALID_CANDIDATE");
        var expectedRaw=JSON.stringify(mutation.document,null,2)+"\n";
        // QML/Node-compatible UTF-8 byte count. Reject malformed surrogate
        // pairs rather than guessing a file size from UTF-16 .length.
        var bytes=unescape(encodeURIComponent(expectedRaw)).length;
        if(!bytes || bytes>1048576) return refusal("FILE_TOO_LARGE");
        var parsed=policy.parse(expectedRaw);
        if(!parsed || parsed.ok!==true ||
                JSON.stringify(parsed.document)!==JSON.stringify(mutation.document))
            return refusal("INVALID_SERIALIZATION");
        var baseline=policy.view(base.tasks.length?"ready":"empty",base,"");
        var expected=policy.view(parsed.document.tasks.length?"ready":"empty",
                                 parsed.document,"");
        if(JSON.stringify(expected)===JSON.stringify(baseline))
            return refusal("UNCHANGED_VIEW");
        return {
            admitted:true,ticketId:ticketId,state:"WRITING",
            surface:surface,method:method,
            baseline:copy(baseline),expected:copy(expected),
            expectedDocument:copy(parsed.document),expectedRaw:expectedRaw,
            reason:"",disposition:"KEEP_DRAFT"
        };
    } catch(e) { return refusal("POLICY_OR_SERIALIZATION_EXCEPTION"); }
}
function saved(stage) {
    if(!stage || stage.admitted!==true || stage.state!=="WRITING")
        return {state:"REVIEW_REQUIRED",reason:"UNEXPECTED_SAVED_HINT"};
    var next=copy(stage);next.state="VERIFYING";return next;
}
function verify(policy,stage,actualRaw) {
    if(!stage || stage.admitted!==true || stage.state!=="VERIFYING" ||
            typeof actualRaw!=="string")
        return {confirmed:false,state:"REVIEW_REQUIRED",reason:"INVALID_READBACK_STATE"};
    if(actualRaw!==stage.expectedRaw)
        return {confirmed:false,state:"REVIEW_REQUIRED",reason:"SOURCE_BYTES_MISMATCH"};
    try {
        var decoded=policy.parse(actualRaw);
        if(!decoded || decoded.ok!==true)
            return {confirmed:false,state:"REVIEW_REQUIRED",reason:"INVALID_READBACK_SOURCE"};
        var observed=policy.view(decoded.document.tasks.length?"ready":"empty",
                                 decoded.document,"");
        if(JSON.stringify(observed)!==JSON.stringify(stage.expected))
            return {confirmed:false,state:"REVIEW_REQUIRED",reason:"EXPECTED_VIEW_MISMATCH"};
        return {confirmed:true,state:"CONFIRMED",ticketId:stage.ticketId,
                evidence:"SYNTHETIC_READBACK_RECEIPT",
                document:copy(decoded.document),snapshot:copy(observed)};
    } catch(e) {
        return {confirmed:false,state:"REVIEW_REQUIRED",reason:"READBACK_EXCEPTION"};
    }
}
