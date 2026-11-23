import QtQuick
import Quickshell
import "HospitalDoctorNameIntentPolicy.js" as NameIntentPolicy

// Hospital H1 // Candidate protected Doctor DISPLAY NAME integration.
// NOT bound into HospitalW: the existing editor stays unchanged until
// authorized native issuer, protected writer, and installed cutover pass.
// This service has NO Process, CLI, socket, shell, fallback or DB access.
Scope {
    id: root

    readonly property bool protectedNameWritesReady: false
    property bool saving: false
    property string lastError: ""
    property string lastStatus: ""
    property string pendingDoctorId: ""
    property var lastSavedDoctor: null
    property var preparedIntent: null

    signal nameSaved(var doctor)
    signal refused(string reason)

    function clearStatus() {
        if (!saving) {
            lastError = "";
            lastStatus = "";
        }
    }

    function prepareName(doctorIdValue, displayNameValue) {
        // Input validation is not permission to send anything. The issuer
        // must separately prove authenticated user, exact Doctor, scope,
        // concurrent version, signed one-use consent, and committed result.
        preparedIntent = null;
        pendingDoctorId = "";
        lastSavedDoctor = null;
        const check = NameIntentPolicy.prepareNameIntent(
            doctorIdValue, displayNameValue
        );
        if (!check.ok) {
            lastError = "HOSPITAL NATIVE HOLD // " + check.reason;
            lastStatus = "DOCTOR NAME // REFUSED";
            return false;
        }
        preparedIntent = check.intent;
        pendingDoctorId = check.intent.doctorId;
        lastError = "";
        lastStatus = "DOCTOR NAME // VALIDATED, NOT AUTHORIZED";
        return true;
    }

    function saveName(doctorIdValue, displayNameValue) {
        saving = false;
        if (!prepareName(doctorIdValue, displayNameValue)) {
            refused(lastError);
            return false;
        }

        // No activated issuer or backend receipt verifier exists in this
        // candidate. In particular, the desktop must NOT call generic
        // protected generic store bridge, invoke PX, or emit a success signal.
        lastError =
            "HOSPITAL NATIVE HOLD // PROTECTED DOCTOR NAME ISSUER NOT ENROLLED";
        lastStatus = "DOCTOR NAME // NO WRITE PERFORMED";
        refused(lastError);
        return false;
    }
}
