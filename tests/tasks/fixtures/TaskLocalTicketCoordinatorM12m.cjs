/*
 * TASKS M12m // isolated, non-production local ticket coordinator.
 *
 * This is a model of one logical in-application writer and its acknowledgment
 * rules. It is deliberately NOT imported by shell.qml or ApolloHubTodoStore.
 * The injected store is a DISPOSABLE adapter, never the live TASKS file.
 * No signatures, same-UID writer isolation or native FileView callbacks.
 */
"use strict";

function copy(value) {
    return JSON.parse(JSON.stringify(value));
}

const FINAL = new Set(["CONFIRMED", "REJECTED", "BLOCKED", "REVIEW_REQUIRED"]);

class LocalTicketCoordinatorM12m {
    constructor({store, policy, onStatus = () => {}}) {
        if (!store || typeof store.readExact !== "function" ||
                typeof store.replaceAtomic !== "function" ||
                !policy || typeof policy.parse !== "function" ||
                typeof policy.validate !== "function" ||
                typeof onStatus !== "function") {
            throw new TypeError("EXPLICIT_DISPOSABLE_ADAPTER_AND_POLICY_REQUIRED");
        }
        this.store = store;
        this.policy = policy;
        this.onStatus = onStatus;
        this.phase = "DETACHED";
        this.confirmed = null;
        this.confirmedBytes = null;
        this.lastDraft = null;
        this.error = null;
        this.tickets = [];
        this.queue = [];
        this.sequence = 0;
        this.draining = false;
    }

    snapshot() {
        return copy({
            phase: this.phase,
            error: this.error,
            confirmed: this.confirmed,
            lastDraft: this.lastDraft,
            tickets: this.tickets.map(t => ({
                ticketId: t.ticketId, state: t.state, reason: t.reason
            }))
        });
    }

    _emit(ticket) {
        if (ticket) {
            try {
                this.onStatus({
                    ticketId: ticket.ticketId, state: ticket.state, reason: ticket.reason
                });
            } catch (_) {
                // UI observer is not the persistence authority.
            }
        }
    }

    async attach() {
        if (this.phase !== "DETACHED") {
            throw new Error("ATTACH_ONCE_ONLY");
        }
        this.phase = "LOADING";
        try {
            const raw = await this.store.readExact();
            if (typeof raw !== "string" || !raw.length) {
                throw new Error("SOURCE_MISSING_OR_EMPTY");
            }
            const parsed = this.policy.parse(raw);
            if (!parsed || parsed.ok !== true) {
                throw new Error("UNSUPPORTED_OR_INVALID_SOURCE");
            }
            this.confirmedBytes = raw;
            this.confirmed = copy(parsed.document);
            this.phase = "READY";
            return true;
        } catch (_) {
            // No empty-list promotion and no implicit retry. A new instance
            // and an explicit recovery decision are required.
            this.phase = "RECOVERY_REVIEW";
            this.error = "SOURCE_ATTACH_UNVERIFIED";
            return false;
        }
    }

    submit(mutation) {
        const ticket = {
            ticketId: "m12m-local-" + String(++this.sequence).padStart(6, "0"),
            state: "QUEUED", reason: null, finish: null
        };
        const completion = new Promise(resolve => {
            ticket.finish = resolve;
        });
        this.tickets.push(ticket);
        if (this.phase !== "READY" || typeof mutation !== "function") {
            this._finish(ticket, this.phase === "READY" ? "REJECTED" : "BLOCKED",
                         this.phase === "READY" ? "INVALID_MUTATION" : "WRITES_NOT_READY");
            return {ticketId: ticket.ticketId, completion};
        }
        this.queue.push({ticket, mutation});
        this._emit(ticket);
        // Deferring the worker ensures every caller has its ticket before
        // the first state transition. Queue order is FIFO.
        Promise.resolve().then(() => this._drain());
        return {ticketId: ticket.ticketId, completion};
    }

    _finish(ticket, state, reason) {
        if (FINAL.has(ticket.state)) {
            return;
        }
        ticket.state = state;
        ticket.reason = reason || null;
        this._emit(ticket);
        ticket.finish({ticketId: ticket.ticketId, state, reason: ticket.reason});
    }

    _stopQueued() {
        for (const item of this.queue.splice(0)) {
            this._finish(item.ticket, "BLOCKED", "RECOVERY_REVIEW");
        }
    }

    _review(ticket, reason) {
        this.error = reason;
        this.phase = "RECOVERY_REVIEW";
        this._finish(ticket, "REVIEW_REQUIRED", reason);
        this._stopQueued();
    }

    async _drain() {
        if (this.draining) return;
        this.draining = true;
        try {
            while (this.queue.length && this.phase === "READY") {
                const {ticket, mutation} = this.queue.shift();
                ticket.state = "PREPARING";
                this._emit(ticket);
                let proposed, serialized, parsed;
                try {
                    const result = mutation(copy(this.confirmed));
                    if (!result || result.ok !== true) {
                        this._finish(ticket, "REJECTED", "POLICY_REFUSED");
                        continue;
                    }
                    proposed = result.document;
                    if (!this.policy.validate(proposed).ok) {
                        this._finish(ticket, "REJECTED", "INVALID_CANDIDATE");
                        continue;
                    }
                    serialized = JSON.stringify(proposed, null, 2) + "\n";
                    parsed = this.policy.parse(serialized);
                    if (!parsed || parsed.ok !== true || serialized === this.confirmedBytes) {
                        this._finish(ticket, "REJECTED", "INVALID_OR_UNCHANGED");
                        continue;
                    }
                } catch (_) {
                    this._finish(ticket, "REJECTED", "MUTATION_EXCEPTION");
                    continue;
                }

                this.lastDraft = copy(parsed.document);
                this.phase = "WRITING";
                ticket.state = "WRITING";
                this._emit(ticket);
                try {
                    // Re-check the file right before replacing it. This
                    // detects ordinary external edits, not malicious races.
                    const baseline = await this.store.readExact();
                    if (baseline !== this.confirmedBytes) {
                        this._review(ticket, "EXTERNAL_SOURCE_CHANGED");
                        break;
                    }
                    await this.store.replaceAtomic(serialized, baseline);
                    ticket.state = "VERIFYING";
                    this._emit(ticket);
                    const observed = await this.store.readExact();
                    if (observed !== serialized) {
                        this._review(ticket, "READBACK_MISMATCH");
                        break;
                    }
                    const observedDocument = this.policy.parse(observed);
                    if (!observedDocument || observedDocument.ok !== true) {
                        this._review(ticket, "READBACK_INVALID");
                        break;
                    }

                    // Confirmation means exact independent readback after
                    // the fixture adapter returned. NOT writer origin proof.
                    this.confirmed = copy(observedDocument.document);
                    this.confirmedBytes = observed;
                    this.lastDraft = null;
                    this.phase = "READY";
                    this._finish(ticket, "CONFIRMED", null);
                } catch (_) {
                    // A failed/throwing replace may have written bytes before
                    // failing. Never auto-retry or promote pending UI.
                    this._review(ticket, "WRITE_OUTCOME_UNCERTAIN");
                    break;
                }
            }
        } finally {
            this.draining = false;
        }
    }
}

module.exports = {LocalTicketCoordinatorM12m};
