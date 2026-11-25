import QtQuick
import "MemoryQueueSessionHost.js" as Host

// Unmounted session-scoped one-shot deadline driver. No child or authority.
// Caller supplies one immutable host snapshot per transition and explicit
// reviewed timeout policy. On timeout caller MUST invalidate the exact
// generation synchronously, stop its child and never replay.
QtObject {
    id: root
    property var hostState: null
    property var timeouts: null
    property var tickets: ({})
    property int nextTicket: 0
    readonly property int activeCount: Object.keys(tickets).length
    signal deadlineExpired(int generation, string category, int ticket)
    signal policyRejected(int generation)
    property bool ready: false
    property bool tripped: false
    property Component factory: Component {
        Timer {
            required property int generation
            required property string category
            required property int ticket
            repeat: false
            onTriggered: root.fire(generation,category,ticket)
        }
    }
    function clear() {
        const old=tickets;
        tickets=({});
        for(const key of Object.keys(old)) {
            old[key].stop();
            old[key].destroy();
        }
    }
    function validPolicy() {
        const categories=["HELLO","PUBLICATION","ACTION","HISTORY","RECOVERY","PARTIAL_FRAME"];
        return timeouts && Object.keys(timeouts).length===categories.length
            && categories.every(k=>Number.isInteger(timeouts[k]) && timeouts[k]>0 && timeouts[k]<=60000);
    }
    function sync() {
        if(!ready)return;
        const s=hostState;
        if(!s || !["HELLO","CONNECTED"].includes(s.phase)) {
            clear();
            tripped=false;
            return;
        }
        // Changing policy while connected is not a way to extend deadlines.
        if(tripped)return;
        if(!validPolicy()) {
            clear();tripped=true;policyRejected(s.generation);return;
        }
        const desired=Host.waiting(s);
        const next=Object.assign({},tickets);
        for(const key of Object.keys(next)) {
            const timer=next[key];
            if(timer.generation!==s.generation || !desired.includes(key)) {
                delete next[key];
                timer.stop();timer.destroy();
            }
        }
        for(const key of desired) {
            // Do not extend an active wait on intermediate packets, duplicate
            // callbacks, or partial bytes. Coalesced waits conservatively
            // retain their original deadline rather than extending it.
            if(next[key])continue;
            if(nextTicket>=2147483646) {
                tickets=next;clear();tripped=true;policyRejected(s.generation);return;
            }
            const timer=factory.createObject(root,{generation:s.generation,category:key,
                ticket:++nextTicket,interval:timeouts[key]});
            if(!timer) {
                tickets=next;clear();tripped=true;policyRejected(s.generation);return;
            }
            next[key]=timer;
        }
        tickets=next;
        for(const key of Object.keys(next))if(!next[key].running)next[key].start();
    }
    function fire(generation,category,ticket) {
        const current=tickets[category];
        if(tripped || !current || current.ticket!==ticket || current.generation!==generation
            || !hostState || hostState.generation!==generation || !Host.waiting(hostState).includes(category))return;
        // Latch before signal; no second timeout, no rearm while same failed
        // host remains published. The wrapper must publish failed state.
        tripped=true;clear();
        deadlineExpired(generation,category,ticket);
    }
    onHostStateChanged: sync()
    onTimeoutsChanged: {
        if(ready && hostState && ["HELLO","CONNECTED"].includes(hostState.phase)) {
            if(!tripped) {
                clear();tripped=true;policyRejected(hostState.generation);
            }
        } else sync();
    }
    Component.onCompleted: {ready=true;sync();}
    Component.onDestruction: clear()
}
