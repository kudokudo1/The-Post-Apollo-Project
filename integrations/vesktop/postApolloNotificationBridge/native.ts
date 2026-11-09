// Vencord native helper: opt-in, generic desktop notification only.
// No shell, network, stored messages, tokens, arbitrary command/path
// selection or raw text forwarding.
import { execFile } from "node:child_process";
import type { IpcMainInvokeEvent } from "electron";
import { notificationArgs } from "./identity";

const sent = new Map<string, number>();
let minuteStart = 0;
let minuteCount = 0;
const PER_MINUTE = 12;

export async function emit(_event: IpcMainInvokeEvent,
                           raw: unknown): Promise<{ status: string }> {
    const args = notificationArgs(raw);
    if (!args) return { status: "INVALID" };
    const messageId = (raw as { messageId: string }).messageId;
    const now = Date.now();
    if (now - minuteStart >= 60000) {
        minuteStart = now;
        minuteCount = 0;
    }
    if (minuteCount >= PER_MINUTE || sent.has(messageId))
        return { status: "RATE_LIMITED_OR_DUPLICATE" };
    minuteCount += 1;
    sent.set(messageId, now);
    // Only bounded, in-process deduplication. Nothing saved to disk.
    if (sent.size > 128) {
        const oldest = sent.keys().next().value;
        if (oldest !== undefined) sent.delete(oldest);
    }
    return new Promise(resolve => {
        // execFile never goes through the shell; all arguments were validated
        // by the pure policy helper before reaching this call.
        execFile("notify-send", args,
            { timeout: 2500, windowsHide: true, maxBuffer: 4096 },
            error => resolve({ status: error ? "NOTIFY_UNAVAILABLE" : "DELIVERED" }));
    });
}
