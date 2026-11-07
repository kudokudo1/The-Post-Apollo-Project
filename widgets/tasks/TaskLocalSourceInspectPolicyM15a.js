.pragma library

// TASKS M15a // User-clicked, one-shot, local JSON STRUCTURE inspection.
// Only bounded status/count metadata. A check is not a save acknowledgment.
// This policy never activates an encrypted checkpoint or changes source bytes.
var STATUS = {
    SOURCE_STRUCTURALLY_READABLE: {
        title: "LOCAL SOURCE // STRUCTURE READABLE",
        explanation: "An independent read opened the existing local JSON and recognized its basic TASKS structure. This is not a full policy-parity audit, proof of who wrote it, a current revision receipt, or a guarantee it is durable."
    },
    SOURCE_MISSING: {
        title: "LOCAL SOURCE // FILE ABSENT",
        explanation: "The saved JSON file was not found at the app's current source path. No replacement or blank file was created."
    },
    SOURCE_PERMISSION_REVIEW: {
        title: "LOCAL SOURCE // PERMISSIONS NEED REVIEW",
        explanation: "The source appears readable by other local accounts. The inspector did not open its task contents or change file permissions."
    },
    SOURCE_INVALID_JSON: {
        title: "LOCAL SOURCE // JSON INVALID",
        explanation: "The file could not be parsed as bounded JSON. The source was not repaired or replaced."
    },
    SOURCE_INVALID_STRUCTURE: {
        title: "LOCAL SOURCE // STRUCTURE INVALID",
        explanation: "The JSON parsed but its basic TASKS document structure is inconsistent. No task data was changed."
    },
    SOURCE_UNSUPPORTED_VERSION: {
        title: "LOCAL SOURCE // VERSION UNSUPPORTED",
        explanation: "The saved document declares a version outside the recognized v1/v2/v3 structural check. It was not migrated."
    },
    SOURCE_TOO_LARGE: {
        title: "LOCAL SOURCE // SIZE NOT ACCEPTED",
        explanation: "The source exceeds the bounded inspection size or is empty. It was not opened or modified."
    },
    SOURCE_CHANGED: {
        title: "LOCAL SOURCE // CHANGED DURING READ",
        explanation: "The file changed while it was being checked. Results cannot be used as a stable observation."
    },
    SOURCE_UNSAFE: {
        title: "LOCAL SOURCE // PATH OR FILE UNSAFE",
        explanation: "The source or parent directory failed ownership, file-type or symlink checks. The inspector did not follow an unsafe source."
    },
    SOURCE_PATH_REFUSED: {
        title: "LOCAL SOURCE // PATH REFUSED",
        explanation: "The requested path did not match the required absolute TASKS JSON filename. No source content was read."
    },
    SOURCE_UNAVAILABLE: {
        title: "LOCAL SOURCE // CHECK UNAVAILABLE",
        explanation: "The inspector could not obtain a reliable result. The saved file is not verified."
    }
};
var FIELDS = [
    "protocol","kind","status","sourcePresent","taskCount","projectCount",
    "readOnly","writerAuthenticated","savedAcknowledged",
    "sourceRevisionVerified","encryptedDraftRecoveryEnabled",
    "writeAuthorized","restoreAuthorized","draftClearAuthorized",
    "keyReleaseAuthorized"
];
var DENIED = [
    "writerAuthenticated","savedAcknowledged","sourceRevisionVerified",
    "encryptedDraftRecoveryEnabled","writeAuthorized","restoreAuthorized",
    "draftClearAuthorized","keyReleaseAuthorized"
];
function result(title, explanation, count, state) {
    return {
        state: state, title:title, explanation:explanation,
        countLabel:count,
        proof:"ONE-TIME STRUCTURAL CHECK // SAVE AND WRITER NOT AUTHENTICATED",
        draftDisposition:"KEEP UNSAVED DRAFT",
        lastConfirmedDisplay:"KEEP LAST CONFIRMED VIEW",
        writeAuthorized:false, savedAcknowledged:false,
        canReplay:false, canRestore:false, canClearDraft:false,
        canReleaseKey:false, sourceRevisionVerified:false
    };
}
function notChecked() {
    return result("LOCAL SOURCE // NOT CHECKED",
        "Click CHECK LOCAL SOURCE to inspect the current saved JSON read-only. Nothing is scanned automatically.",
        "TASKS COUNTS // NOT INSPECTED", "NOT_CHECKED");
}
function checking() {
    return result("LOCAL SOURCE // CHECKING",
        "A one-time read-only source check is running. No draft, task file or key is being written.",
        "TASKS COUNTS // NOT CONFIRMED", "CHECKING");
}
function stale() {
    return result("LOCAL SOURCE // RECHECK REQUIRED",
        "A new TASKS write was requested since this inspection. The earlier observation must not be treated as current.",
        "TASKS COUNTS // STALE", "STALE");
}
function unverified() {
    return result("LOCAL SOURCE // RESULT UNVERIFIED",
        "The source inspector did not return one valid, safely bounded response. No claim about saved data can be made.",
        "TASKS COUNTS // NOT VERIFIED", "REFUSED");
}
function view(report) {
    if (!report || typeof report !== "object" || Array.isArray(report))
        return unverified();
    var keys=Object.keys(report).sort();
    if (JSON.stringify(keys)!==JSON.stringify(FIELDS.slice().sort())
            || report.protocol!==1
            || report.kind!=="TASKS_LOCAL_SOURCE_CHECK_M15A"
            || report.readOnly!==true
            || typeof report.sourcePresent!=="boolean"
            || typeof report.status!=="string"
            || !Object.prototype.hasOwnProperty.call(STATUS,report.status))
        return unverified();
    for(var i=0;i<DENIED.length;i++)
        if(report[DENIED[i]]!==false)return unverified();
    var good=report.status==="SOURCE_STRUCTURALLY_READABLE";
    if (good) {
        if (report.sourcePresent!==true
                || typeof report.taskCount!=="number"
                || !isFinite(report.taskCount)
                || Math.floor(report.taskCount)!==report.taskCount
                || report.taskCount<0 || report.taskCount>200
                || typeof report.projectCount!=="number"
                || !isFinite(report.projectCount)
                || Math.floor(report.projectCount)!==report.projectCount
                || report.projectCount<0 || report.projectCount>30)
            return unverified();
    } else if (report.taskCount!==null || report.projectCount!==null
               || report.status==="SOURCE_MISSING" && report.sourcePresent!==false
               || report.status==="SOURCE_PERMISSION_REVIEW" &&
                   report.sourcePresent!==true)
        return unverified();
    var item=STATUS[report.status];
    return result(item.title,item.explanation,
        good ? ("STRUCTURAL COUNTS // TASKS "+report.taskCount+
                " · PROJECTS "+report.projectCount)
             : "TASKS COUNTS // NOT EXPOSED",
        report.status);
}
