import QtQuick
import Quickshell
import qs.services.notifications
import "HospitalReportArrivalPolicy.js" as ReportPolicy

// Consumes only successful, existing Hospital Room Report refreshes.
// No PX operations, background polling, report-body read or Room mutations.
Scope {
    id: producer
    required property var reportService
    required property string roomId
    required property string repository
    property var seenByRoom: ReportPolicy.initial()

    function receive() {
        const room = String(producer.roomId || "").trim();
        const patient = String(producer.repository || "").trim();
        if (!NotificationsService.historyReady || !room || !patient
                || String(producer.reportService.roomId || "").trim() !== room
                || producer.reportService.lastError)
            return;

        const decision = ReportPolicy.advance(
            producer.seenByRoom, room, producer.reportService.reports);
        producer.seenByRoom = decision.state;
        if (decision.addedCount < 1)
            return;

        const count = decision.addedCount;
        NotificationsService.pushRich({
            "source": "HOSPITAL",
            "sourceId": "hospital",
            "category": "internal",
            "severity": "normal",
            "title": "HOSPITAL // NEW ROOM REPORT" + (count === 1 ? "" : "S"),
            "message": count + " newly listed Room report"
                       + (count === 1 ? " is" : "s are")
                       + " available. Review Hospital Reports for content,"
                       + " authority and next actions. // ROOM " + room,
            "tags": ["hospital", "room", "reports", "record-arrival"],
            "context": {
                "repository": patient,
                "roomId": room,
                "eventType": "room-reports-newly-listed",
                "origin": "apollo",
                "domain": "hospital",
                "reportCount": count,
                "verification": "listed by successful Room reports refresh only"
            }
        });
    }
    Connections {
        target: producer.reportService
        function onReportsRefreshed() { producer.receive(); }
    }
}
