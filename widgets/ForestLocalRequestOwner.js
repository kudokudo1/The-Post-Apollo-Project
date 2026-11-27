// UI1: original local SEND/STOP event custody for the real host interface.
// No provider, process, network, mock response, grant or storage here.
// Host is independently owned. null submit result = explicit no-dispatch
// refusal; Runtime's HELD/REFUSED are non-acceptance and never attach.
// Accepted result = {accepted:true, correlation: opaque object}; the
// eventual IPC owner must bind it to the original Runtime operation.
// Uncertain/malformed results are held, not permission to retry.
// Every Tree/model/host/view withdrawal must be observed by the mounted owner.
function createLocalRequestOwner() {
    let current = null, active = null, lastEpoch = 0, pending = false;
    let status = "HELD";
    function bounded(s, max) {
        if (typeof s !== "string" || !s || s.length > max || s.indexOf("\x00") !== -1)
            return false;
        try { return encodeURIComponent(s).replace(/%[0-9a-fA-F]{2}|[^%]/g,"x").length <= max; }
        catch (_) { return false; }
    }
    function validHost(h) {
        return !!h && typeof h.submit === "function" &&
            typeof h.stop === "function" && typeof h.withdraw === "function";
    }
    function validPresentation(p) {
        return !!p && ["observe","attach","receive","withdraw","state"].every(k => typeof p[k] === "function");
    }
    function retireRecord(record) {
        // Clear the original before calling out: synchronous callbacks
        // must never see the retired operation as a new current operation.
        try { record.presentation.withdraw(record.epoch); } catch (_) {}
        try { record.host.withdraw(record.correlation); } catch (_) {}
    }
    function withdraw() {
        const old = current, original = active;
        current = null;
        active = null;
        status = "HELD";
        if (old) {
            try { old.presentation.observe(null); } catch (_) {}
        }
        if (original) retireRecord(original);
    }
    function observe(host, epoch, model, presentation) {
        if (current && current.host === host && current.epoch === epoch
                && current.model === model && current.presentation === presentation)
            return true;
        withdraw();
        if (pending || !validHost(host) || !validPresentation(presentation)
                || !Number.isSafeInteger(epoch) || epoch <= lastEpoch || !bounded(model,256))
            return false;
        lastEpoch = epoch;
        current = {host,epoch,model,presentation,used:false};
        try { presentation.observe(epoch); }
        catch (_) { withdraw(); return false; }
        if (!current || current.epoch !== epoch) return false;
        status = "READY";
        return true;
    }
    function submit(model, draft, epoch) {
        const view = current;
        if (!view || pending || active || view.used || status !== "READY"
                || epoch !== view.epoch || model !== view.model || !bounded(draft,4096))
            return false;
        // Mark before crossing owner seam; no second submit from a
        // synchronous callback, even if view changes during acceptance.
        view.used = true;
        pending = true;
        status = "SUBMITTING";
        let result;
        try { result = view.host.submit(model,draft,epoch); }
        catch (_) {
            pending = false;
            if (current === view) status = "UNKNOWN_HOLD";
            return false;
        }
        pending = false;
        if (result === null) {
            if (current === view) { view.used = false; status = "READY"; }
            return false;
        }
        // Runtime currently returns these explicit non-acceptance states.
        // Neither permits a second attempt from this view: REFUSED can
        // also follow a delivery refusal, so do not infer no effect.
        if (result === "HELD" || result === "REFUSED") {
            if (current === view) status = result;
            return false;
        }
        if (!result || result.accepted !== true || !result.correlation
                || typeof result.correlation !== "object") {
            if (current === view) status = "UNKNOWN_HOLD";
            return false;
        }
        const original = {host:view.host, epoch:view.epoch, presentation:view.presentation,
            correlation:result.correlation, stopRequested:false, terminal:false};
        if (current !== view) { retireRecord(original); return false; }
        active = original;
        let attached = false;
        try { attached = view.presentation.attach(epoch,draft); } catch (_) {}
        if (current !== view || active !== original) return false;
        if (!attached) {
            active = null;
            status = "UNKNOWN_HOLD";
            retireRecord(original);
            return false;
        }
        status = "ACCEPTED";
        return true;
    }
    function stop() {
        const original = active;
        if (!original || original.stopRequested || original.terminal)
            return false;
        original.stopRequested = true;
        status = "STOP_REQUESTED";
        try { return original.host.stop(original.correlation) === true; }
        catch (_) { if (active === original) status = "UNKNOWN_HOLD"; return false; }
    }
    function receive(epoch, correlation, snapshot) {
        const original = active;
        if (!original || original.terminal || original.epoch !== epoch
                || original.correlation !== correlation || !current || current.epoch !== epoch)
            return false;
        let received = false, state;
        try {
            received = original.presentation.receive(epoch,snapshot);
            state = original.presentation.state();
        } catch (_) {
            original.terminal = true;
            status = "UNKNOWN_HOLD";
            retireRecord(original);
            return false;
        }
        if (active !== original) return false;
        if (state && state.terminal === true) {
            original.terminal = true;
            status = state.status;
        }
        return received;
    }
    function state() {
        return {status, epoch:current ? current.epoch : null,
            canSubmit:!!current && !current.used && !pending && status === "READY",
            canStop:!!active && !active.stopRequested && !active.terminal};
    }
    return {observe,submit,stop,receive,withdraw,state};
}
