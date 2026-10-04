import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: historyService

    property var events: []
    property int maxEvents: 1000
    property string lastError: ""

    signal eventRecorded(var event)

    FileView {
        id: historyFile

        path: Quickshell.dataPath("hospital-history.json")
        atomicWrites: true

        adapter: JsonAdapter {
            id: historyAdapter

            property int schemaVersion: 1
            property var events: []
        }

        onAdapterUpdated: writeAdapter()
        onLoaded: historyService.hydrate()
        onLoadFailed: historyService.hydrate()

        onSaveFailed: function(error) {
            historyService.lastError =
                "HISTORY SAVE // " + String(error);
        }
    }

    function hydrate() {
        events = Array.isArray(historyAdapter.events)
                 ? historyAdapter.events.slice()
                 : [];
        lastError = "";
    }

    function nowIso() {
        return new Date().toISOString();
    }

    function record(eventType, team, state, details) {
        const event = {
            schemaVersion: 1,
            recordedAt: nowIso(),
            eventType: String(eventType || ""),
            team: String(team || ""),
            state: String(state || ""),
            details: details || {}
        };

        const next = events.slice();
        next.push(event);

        events = next.slice(-maxEvents);
        historyAdapter.events = events.slice();

        eventRecorded(event);
        return event;
    }

    function forTeam(team) {
        const wanted = String(team || "");

        return events.filter(function(event) {
            return String(event.team || "") === wanted;
        });
    }

    function latestForTeam(team) {
        const matches = forTeam(team);
        return matches.length > 0
               ? matches[matches.length - 1]
               : null;
    }

    function clear() {
        events = [];
        historyAdapter.events = [];
        lastError = "";
    }
}
