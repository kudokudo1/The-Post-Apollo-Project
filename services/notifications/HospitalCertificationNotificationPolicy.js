.pragma library

// Only certification transitions recorded by HospitalCertificationService.
// This policy never reads or publishes underlying evidence, raw failures,
// unverified Room status polls, or remote implementation outcomes.
function classify(previousState, nextState, eventType) {
    const from = String(previousState || "").toUpperCase();
    const to = String(nextState || "").toUpperCase();
    const event = String(eventType || "").toUpperCase();
    if (!from || from === to)
        return null;
    if (to === "VERIFIED" && event === "CANDIDATE_VERIFIED")
        return {
            title: "ROOM EVIDENCE VERIFIED",
            message: "Hospital certification recorded candidate verification."
                     + " This is not production integration.",
            severity: "normal", kind: "candidate-verified"
        };
    if (to === "CERTIFIED" && event === "CERTIFICATION_GRANTED"
            && from === "VERIFIED")
        return {
            title: "ROOM CERTIFICATION RECORDED",
            message: "Hospital certification granted for this Room's verified candidate."
                     + " Post-op integration is still separate.",
            severity: "normal", kind: "certification-granted"
        };
    if (to === "BLOCKED" && event === "CERTIFICATION_BLOCKED")
        return {
            title: "ROOM CERTIFICATION BLOCKED",
            message: "Hospital certification entered BLOCKED."
                     + " Review the Room for authoritative details.",
            severity: "warning", kind: "certification-blocked"
        };
    if (to === "REOPENED" && event === "CERTIFICATION_REOPENED")
        return {
            title: "ROOM CERTIFICATION REOPENED",
            message: "Hospital certification recorded a reopened case."
                     + " Previous approval is not assumed to remain valid.",
            severity: "normal", kind: "certification-reopened"
        };
    return null;
}
