// Real local response presentation for the existing ConversationFeed.
// No execution, authorization, process, network, journal, timer or fake reply.
// UI1 owns the feed and independently observes every view incarnation change.
// Runtime owns accepted submit, original operation correlation and snapshots.
// Never derive currentness or admission authority from a received snapshot.
function createPresentation(feed) {
    let observed = null, epoch = null, scope = "", used = false;
    let prompt = "", text = "", sequence = 0, status = "IDLE";
    let localOutcome = "UNKNOWN_HOLD";
    let admitted = false, terminal = false, baseline = "", stopFrozen = false;
    const ranks = {PREPARED:1, LOCAL_RESERVED:2, GENERATING:3,
        STOP_REQUESTED:4, LOCAL_COMMITTED:5, UNKNOWN_HOLD:5};
    const keys = ["sequence","status","text","local_outcome","provisional","native_admitted"];
    function validEpoch(v) { return Number.isSafeInteger(v) && v > 0; }
    function bounded(s, max, allowEmpty) {
        if (typeof s !== "string" || s.length > max || (!allowEmpty && !s) || s.indexOf("\x00") !== -1)
            return false;
        try { return encodeURIComponent(s).replace(/%[0-9a-fA-F]{2}|[^%]/g,"x").length <= max; }
        catch (_) { return false; }
    }
    function sameFeed() { return feed && scope !== "" && feed.effectiveScope === scope; }
    function readyFeed() {
        return feed && feed.visible && feed.conversation !== null && !!feed.conversation
            && typeof feed.effectiveScope === "string" && feed.effectiveScope.length > 0
            && feed.streamingTailEnabled && !feed.showComposer && !feed.sendEnabled
            && !feed.richMessageActions && !feed.loading && feed.error === "";
    }
    function current(v) {
        return epoch !== null && observed === epoch && v === epoch
            && sameFeed() && readyFeed();
    }
    function outgoing() { return {direction:"outgoing",body:prompt}; }
    function clearRows() {
        // A retired original must never clear a replacement scope.
        if (sameFeed()) {
            feed.clearStreamingTail();
            feed.messages = [];
        }
    }
    function retire() {
        clearRows(); terminal = true; status = "WITHDRAWN";
        prompt = ""; text = ""; baseline = "";
        localOutcome = "UNKNOWN_HOLD"; admitted = false;
    }
    function observe(v) {
        const next = validEpoch(v) ? v : null;
        if (epoch !== null && next !== epoch) retire();
        observed = next;
    }
    function attach(v, exactPrompt) {
        // Called only AFTER independently accepted original submit. This
        // method is display attachment, not permission or provider admission.
        if (used || !validEpoch(v) || observed !== v || !readyFeed()
                || !bounded(exactPrompt,4096,false) || feed.messages.length !== 0)
            return false;
        used = true; epoch = v; scope = feed.effectiveScope;
        prompt = exactPrompt; status = "SUBMITTED";
        feed.clearStreamingTail();
        feed.messages = [outgoing()];
        return true;
    }
    function hold() {
        if (sameFeed()) {
            feed.clearStreamingTail();
            feed.messages = [outgoing()];
        }
        text = ""; baseline = ""; terminal = true; status = "UNKNOWN_HOLD";
        localOutcome = "UNKNOWN_HOLD";
        return false;
    }
    function validSnapshot(s) {
        if (!s || typeof s !== "object" || Array.isArray(s)
                || Object.keys(s).length !== keys.length
                || !keys.every(k=>Object.prototype.hasOwnProperty.call(s,k))
                || !Number.isSafeInteger(s.sequence) || s.sequence <= sequence
                || typeof s.status !== "string"
                || !Object.prototype.hasOwnProperty.call(ranks,s.status)
                || !bounded(s.text,16000,true)
                || typeof s.provisional !== "boolean" || typeof s.native_admitted !== "boolean"
                || (admitted && !s.native_admitted)
                || (ranks[status] && ranks[s.status] < ranks[status]))
            return false;
        if (s.status === "UNKNOWN_HOLD")
            return s.text === "" && !s.provisional
                && ["UNKNOWN_HOLD","ABORTED_LOCAL","COMMITTED_LOCAL"].indexOf(s.local_outcome)>=0;
        if (s.status === "LOCAL_COMMITTED")
            return s.native_admitted && s.local_outcome === "COMMITTED_LOCAL"
                && !s.provisional && !!s.text && s.text.indexOf(text) === 0;
        if (s.local_outcome !== "UNKNOWN_HOLD")
            return false;
        if (s.status === "PREPARED" || s.status === "LOCAL_RESERVED")
            return !s.text && !s.provisional;
        if (s.status === "GENERATING" && !s.native_admitted)
            return false;
        return s.provisional === !!s.text && (!s.text || s.native_admitted)
            && s.text.indexOf(text) === 0;
    }
    // UI1 calls this for the original view BEFORE calling host.stop. This is
    // a presentation fence, not proof of accepted cancellation or provider idle.
    function requestStop(v) {
        if (terminal || stopFrozen || !current(v)) return false;
        stopFrozen = true; status = "STOP_REQUESTED";
        return true;
    }
    function receive(v,s) {
        // Stale/duplicate packets do not advance or damage current display.
        if (epoch === null || v !== epoch || observed !== epoch || terminal)
            return false;
        if (!current(v)) { retire(); return false; }
        if (s && Number.isSafeInteger(s.sequence) && s.sequence <= sequence)
            return false;
        // In-flight pre-STOP snapshots can arrive after the owner fence.
        // Do not grow or erase the visible partial in response to them.
        if (stopFrozen && s && ["PREPARED","LOCAL_RESERVED","GENERATING"].indexOf(s.status)>=0)
            return false;
        if (!validSnapshot(s)) return hold();
        if (s.status === "UNKNOWN_HOLD") {
            hold();
            sequence = s.sequence; admitted = s.native_admitted;
            localOutcome = s.local_outcome;
            return true;
        }
        if (s.status === "STOP_REQUESTED") stopFrozen = true;
        // Only the original independently correlated commit-won terminal
        // can replace the frozen text. STOP alone never settles the attempt.
        const show = !stopFrozen || s.status === "LOCAL_COMMITTED";
        if (show && s.text) {
            if (!baseline) {
                baseline = s.text;
                feed.messages = [outgoing(),{direction:"incoming",body:baseline}];
            }
            // Retain the original incoming row; replace only its display text.
            if (!feed.updateStreamingTail(scope,s.text)) return hold();
        }
        if (show) text = s.text;
        sequence = s.sequence; status = s.status;
        localOutcome = s.local_outcome;
        admitted = s.native_admitted;
        terminal = status === "LOCAL_COMMITTED";
        return true;
    }
    function withdraw(v) {
        if (v !== epoch || epoch === null) return false;
        retire(); observed = null; return true;
    }
    function displayLabel() {
        // Labels describe only observed presentation, never provider idle,
        // durable protected storage, or permission for another request.
        switch (status) {
        case "IDLE": return "NO RESPONSE YET";
        case "SUBMITTED": return "REQUEST ACCEPTED";
        case "PREPARED": return "REQUEST PREPARED";
        case "LOCAL_RESERVED": return "LOCAL TURN RESERVED";
        case "GENERATING": return "GENERATING // PROVISIONAL";
        case "STOP_REQUESTED": return "STOP REQUESTED // OUTCOME PENDING";
        case "LOCAL_COMMITTED": return "RESPONSE COMPLETE // LOCAL";
        case "WITHDRAWN": return "VIEW WITHDRAWN";
        case "UNKNOWN_HOLD":
            if (localOutcome === "ABORTED_LOCAL")
                return "LOCAL TURN ABORTED // PROVIDER STATE UNKNOWN";
            if (localOutcome === "COMMITTED_LOCAL")
                return "LOCAL TURN COMMITTED // RESPONSE UNAVAILABLE";
            return "OUTCOME UNKNOWN // NO AUTOMATIC RETRY";
        default: return "OUTCOME UNKNOWN // NO AUTOMATIC RETRY";
        }
    }
    function state() {
        return {status:status,sequence:sequence,terminal:terminal,
            nativeAdmitted:admitted,localOutcome:localOutcome,
            provisional:!!text && status !== "LOCAL_COMMITTED",
            displayLabel:displayLabel()};
    }
    return {observe,attach,receive,requestStop,withdraw,state};
}
