.pragma library

// CPU++ exact Clock navigation is a *view request*, never a write or alarm
// action. Numeric identities are the only values permitted across this seam.
// The Clock/Angel owners independently verify durable favorite membership
// immediately before changing their existing UI view.
function deny(reason) {
    return {ok:false,kind:"",id:"",reason:reason};
}
function plan(row) {
    if (!row || typeof row !== "object" || Array.isArray(row)
            || row.isFavorite !== true || typeof row.key !== "string")
        return deny("UNSUPPORTED_RESOURCE");
    if (row.owner === "clock-alarm" && row.provider === "clock-alarm"
            && row.category === "CLOCK" && row.menu === "ALARMS"
            && row.kind === "alarm" && row.readOnly === true) {
        const match = /^fav1:local:clock-alarm:alarm:([1-9][0-9]{0,14})$/.exec(row.key);
        if (!match || row.resourceId !== match[1]
                || !Number.isSafeInteger(Number(match[1])))
            return deny("INVALID_ALARM_ID");
        return {ok:true,kind:"alarm",id:match[1],reason:""};
    }
    // Angel stars are owned by the existing FavoritesDefaultStore, including
    // number values with significant leading zeros. A pinned-only number
    // cannot be promoted to a favorite navigation request.
    if (row.owner === "angel" && row.provider === "angel"
            && row.category === "NEW" && row.kind === "number"
            && row.readOnly === false) {
        const match = /^fav1:local:angel:number:([0-9]{1,8})$/.exec(row.key);
        if (!match || row.resourceId !== match[1])
            return deny("INVALID_ANGEL_NUMBER");
        return {ok:true,kind:"angel",id:match[1],reason:""};
    }
    return deny("UNSUPPORTED_RESOURCE");
}
