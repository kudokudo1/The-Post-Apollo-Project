// UI2 S6a: unmounted, local presentation gesture lifetime only.
// One latch per independent control target (e.g. browsed Tree preferences
// or composer selection). No roster, policy, provider or permission source.
// A token is a caller-owned local selection correlation, not an identity
// credential. The host must observe EVERY target/revision/visibility change,
// including an A -> B -> A transition, before a gesture can complete.
// Successful finish means only that this local gesture is still current;
// it cannot authorize SEND, a model invocation, a preference write or I/O.
function createTargetLatch() {
    let observed = null;
    let active = null;

    function valid(token) {
        if (typeof token !== "string" || token.length > 128)
            return false;
        const match = /^[A-Za-z0-9][A-Za-z0-9._:/-]*$/.exec(token);
        return match !== null && match[0] === token;
    }

    function observe(token) {
        const next = valid(token) ? token : null;
        if (next !== observed || next === null) {
            active = null;
            observed = next;
        }
    }

    function begin(current) {
        if (!valid(current) || current !== observed)
            return null;
        // Identity-only, non-serializable handle. Supersedes prior gesture.
        active = Object.freeze({});
        return active;
    }

    function finish(ticket, current) {
        // A delayed release from an old gesture must not clear a new one.
        if (active === null || ticket !== active)
            return false;
        active = null; // single-use, even if currentness check fails
        return valid(current) && current === observed;
    }

    function cancel(ticket) {
        if (active === null || ticket !== active)
            return false;
        active = null;
        return true;
    }

    function clear() {
        observed = null;
        active = null;
    }

    return {observe, begin, finish, cancel, clear};
}
