// Hospital H1 // Source-only Doctor DISPLAY NAME intent preparation.
//
// No writer, native client, socket or installed runtime is authorized here.
// A validated intent proves only that its UI input is well formed, NEVER
// that a Doctor exists, the caller has permission, or a name was committed.
// The protected issuer must independently verify all authority and state.
const INTENT_SCHEMA = "postapollo.hospital.doctor-name-intent.v1";
const ACTION = "DOCTOR_NAME_SET";
const ID_PATTERN = /^[A-Za-z0-9._:/-]{1,160}$/;

function refused(reason) {
    return {ok: false, reason: reason, intent: null};
}

function prepareNameIntent(doctorId, displayName) {
    if (typeof doctorId !== "string")
        return refused("DOCTOR_NAME_ID_TYPE_REFUSED");
    const id = doctorId.trim();
    if (!ID_PATTERN.test(id))
        return refused("DOCTOR_NAME_ID_REFUSED");

    if (typeof displayName !== "string")
        return refused("DOCTOR_NAME_TEXT_TYPE_REFUSED");
    const name = displayName.trim();
    if (Array.from(name).length > 96
            || /[\x00-\x1f\x7f]/.test(name)
            || /[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/.test(name))
        return refused("DOCTOR_NAME_TEXT_REFUSED");

    // An empty name is explicitly allowed. The protected backend's
    // existing semantics reset the friendly name to the technical ID.
    // No role/status/Room/Assignment/SQL/permission field is accepted.
    return {
        ok: true,
        reason: "",
        intent: {
            schema: INTENT_SCHEMA,
            action: ACTION,
            doctorId: id,
            name: name
        }
    };
}
