import QtQuick
import "../../components"

// Weather's original M6c service snapshot and routing policy remain the owner.
// This adapter feeds the SAME reusable in-widget diagnostics popup now used
// by Finance. No new WeatherService, provider fetch, timer or cache writer.
DiagnosticsServicePopup {
    id: diagnosticsPane
    property var snapshot: null

    heading: "PROVIDER HEALTH // DIAGNOSTICS"
    displayedState: snapshot ? snapshot.currentState : "NO SERVICE"
    providerLabel: snapshot ? snapshot.providerLabel : "NONE"
    currentAge: snapshot ? snapshot.currentAge : "--"
    locationLabel: snapshot ? snapshot.location : "UNAVAILABLE"
    showLocation: true
    serviceRows: snapshot
        ? [snapshot.primary, snapshot.fallback, snapshot.aqi] : []
    reason: snapshot ? snapshot.reason : "NO SERVICE DATA"
    reasonHeading: "REASON // CURRENT ROUTING"
    ageHeading: "LAST PROVIDER SUCCESS // "
    footnote: "READ ONLY // PROVIDER STATUS IS SESSION-LOCAL. "
              + "CACHE AGE COMES FROM THE SAVED SAMPLE. "
              + "NO EXTRA FETCHES FROM THIS PANEL."
}
