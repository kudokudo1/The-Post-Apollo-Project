// FinanceW M4s1: local backup candidate. Pure request and receipt policy.
// No restore/import authority and no automatic writes.
function exact(v,keys) {
    return v!==null && typeof v==="object" && !Array.isArray(v)
        && Object.keys(v).length===keys.length
        && keys.every(function(k){return Object.prototype.hasOwnProperty.call(v,k);});
}
function integer(v,min,max) {
    return Number.isSafeInteger(v)&&v>=min&&v<=max;
}
function id(v) {return typeof v==="string"&&/^backup-[0-9a-f]{32}\.json$/.test(v);}
function hash(v) {return typeof v==="string"&&/^[0-9a-f]{64}$/.test(v);}
function metadata(v) {
    return exact(v,["backupId","createdUtc","sourceRevision","sha256","accountCount",
                    "entryCount","connected","bankVerified","encrypted"])
        && id(v.backupId)&&hash(v.sha256)
        && typeof v.createdUtc==="string"&&/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(v.createdUtc)
        && integer(v.sourceRevision,1,Number.MAX_SAFE_INTEGER-1)
        && integer(v.accountCount,1,12)&&integer(v.entryCount,0,300)
        && v.connected===false&&v.bankVerified===false&&v.encrypted===false;
}
function validRequest(r) {
    if(!r)return false;
    if(r.action==="list")return exact(r,["action"]);
    if(r.action==="create")
        return exact(r,["action","expectedRevision","confirmBackup"])
            && integer(r.expectedRevision,1,2147483646)&&r.confirmBackup===true;
    if(r.action==="delete")
        return exact(r,["action","backupId","expectedBackupSha256","confirmDelete"])
            && id(r.backupId)&&hash(r.expectedBackupSha256)&&r.confirmDelete===true;
    return false;
}
function createCandidate(context) {
    if(!context||context.enabled!==true||context.active!==true
       ||context.busy!==false||context.ready!==true||context.dirty!==false
       ||context.localSaved!==true)return null;
    var r={action:"create",expectedRevision:context.revision,confirmBackup:true};
    return validRequest(r)?r:null;
}
function deleteCandidate(context,selected) {
    if(!context||context.enabled!==true||context.active!==true
       ||context.busy!==false||!metadata(selected))return null;
    return {action:"delete",backupId:selected.backupId,
            expectedBackupSha256:selected.sha256,confirmDelete:true};
}
function sameRequest(a,b) {
    if(!validRequest(a)||!validRequest(b)||a.action!==b.action)return false;
    if(a.action==="list")return true;
    if(a.action==="create")return a.expectedRevision===b.expectedRevision;
    return a.backupId===b.backupId&&a.expectedBackupSha256===b.expectedBackupSha256;
}
function accept(raw,code,request) {
    if(code!==0||!validRequest(request)||typeof raw!=="string"||raw.length>16384)
        return null;
    var prefix="FINANCEW_BANKING_BACKUP_RESULT ";
    var lines=raw.split(/\r?\n/);
    if(lines.length!==2||lines[1]!==""||!lines[0].startsWith(prefix))return null;
    try {
        var v=JSON.parse(lines[0].slice(prefix.length));
        if(!v||v.source!=="LOCAL_OPERATOR_BANKING_BACKUP"||v.action!==request.action
            ||v.connected!==false||v.bankVerified!==false||v.encrypted!==false)return null;
        var base=["source","action","connected","bankVerified","encrypted"];
        if(v.action==="list") {
            if(!exact(v,base.concat(["backups"]))||!Array.isArray(v.backups)
                ||v.backups.length>8)return null;
            var seen=Object.create(null);
            for(var i=0;i<v.backups.length;i++){
                var row=v.backups[i];
                if(!metadata(row)||seen[row.backupId])return null;
                seen[row.backupId]=true;
            }
            return {action:"list",rows:v.backups.slice()};
        }
        if(v.action==="create"&&exact(v,base.concat(["backup"]))&&metadata(v.backup)
           &&v.backup.sourceRevision===request.expectedRevision)
            return {action:"create",backup:v.backup};
        if(v.action==="delete"&&exact(v,base.concat(["backupId","deleted"]))
           &&v.backupId===request.backupId&&v.deleted===true)
            return {action:"delete",backupId:v.backupId};
    } catch(error) {}
    return null;
}
