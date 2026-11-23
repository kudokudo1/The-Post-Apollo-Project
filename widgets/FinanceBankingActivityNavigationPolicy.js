// Banking M4n // Pure account-scoped navigation over an existing validated
// provider projection. Never creates, edits or connects an account.
// Return 1-based UI filter index (0 belongs to the explicit ALL selector).
// Fail closed when the account is absent, in another provider, or malformed.
function accountFilterIndex(details,providerId,accountId) {
    if(!details||details.ok!==true
       ||details.connected!==false||details.persisted!==false
       ||details.providerId!==providerId
       ||typeof accountId!=="string"||accountId.length===0
       ||!Array.isArray(details.allAccounts)||details.allAccounts.length>12)
        return -1;
    var seen=Object.create(null),result=-1;
    for(var i=0;i<details.allAccounts.length;i++) {
        var account=details.allAccounts[i];
        if(!account||typeof account.id!=="string"||account.id.length===0
           ||typeof account.providerId!=="string"
           ||account.providerId!==providerId
           ||Object.prototype.hasOwnProperty.call(seen,account.id))
            return -1;
        seen[account.id]=true;
        if(account.id===accountId)result=i+1;
    }
    return result;
}
