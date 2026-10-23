.pragma library
// M5a scheduling guard over the existing v3 task snapshot. Never performs IO.
function find(snapshot, id) {
    if (!snapshot || !Array.isArray(snapshot.items) || typeof id !== "string")
        return null;
    for (var i = 0; i < snapshot.items.length; i++)
        if (snapshot.items[i] && snapshot.items[i].id === id)
            return snapshot.items[i];
    return null;
}
function signature(task) {
    if (!task || typeof task.id !== "string") return null;
    return {id:task.id,title:task.title,done:task.done,
        priority:task.priority,description:task.description,
        dueDate:task.dueDate === null ? null : task.dueDate,
        projectId:task.projectId === undefined ? null : task.projectId};
}
function same(a,b) {
    return !!a && !!b && a.id===b.id && a.title===b.title
        && a.done===b.done && a.priority===b.priority
        && a.description===b.description && a.dueDate===b.dueDate
        && a.projectId===b.projectId;
}
function validDate(s) {
    if (typeof s !== "string" || !/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(s))
        return false;
    var y=Number(s.slice(0,4)), m=Number(s.slice(5,7)),
        d=Number(s.slice(8,10));
    if (y<1 || y>9999 || m<1 || m>12 || d<1) return false;
    var at=new Date(0);
    at.setUTCFullYear(y,m,0);
    return d<=at.getUTCDate();
}
function writable(snapshot) {
    return !!snapshot && snapshot.writable === true
        && (snapshot.state === "ready" || snapshot.state === "empty")
        && Array.isArray(snapshot.items);
}
function proposal(snapshot, original, targetDate) {
    if (!writable(snapshot)) return {ok:false,reason:"STORAGE LOCKED"};
    if (!original || typeof original.id !== "string")
        return {ok:false,reason:"SELECT TASK"};
    if (targetDate !== null && !validDate(targetDate))
        return {ok:false,reason:"INVALID DATE"};
    var current=signature(find(snapshot,original.id));
    if (!current) return {ok:false,reason:"TASK REMOVED"};
    if (!same(current,original)) return {ok:false,reason:"TASK CHANGED // CANCEL & RESELECT"};
    if (current.dueDate === targetDate) return {ok:false,reason:"DATE UNCHANGED"};
    return {ok:true,reason:"",id:current.id,
        priority:current.priority,description:current.description,
        targetDate:targetDate,
        expected:{id:current.id,title:current.title,done:current.done,
            priority:current.priority,description:current.description,
            dueDate:targetDate,projectId:current.projectId}};
}
function verified(snapshot,expected) {
    if (!snapshot || (snapshot.state!=="ready" && snapshot.state!=="empty"))
        return false;
    return same(signature(find(snapshot,expected && expected.id)),expected);
}
function canCreate(snapshot,title) {
    if (!writable(snapshot)) return false;
    if (typeof title!=="string") return false;
    var clean=title.trim();
    return clean.length>0 && clean.length<=160
        && !/[\x00-\x1f\x7f]/.test(clean);
}
function created(snapshot,ids,title) {
    if (!snapshot || (snapshot.state!=="ready" && snapshot.state!=="empty")
        || !Array.isArray(snapshot.items) || !Array.isArray(ids))
        return false;
    return snapshot.items.some(function(row) {
        return row && row.title===title && ids.indexOf(row.id)===-1;
    });
}
