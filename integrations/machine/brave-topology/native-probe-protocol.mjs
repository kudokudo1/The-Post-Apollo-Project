/* Pure request/reply validation. A transport round trip proves no window identity. */
export const NATIVE_HOST_NAME = "org.postapollo.machine_brave_probe";
export const REQUEST_KIND = "machine-brave-native-transport-request-v1";
export const RESPONSE_KIND = "machine-brave-native-transport-probe-v1";
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;

export function makeProbeRequest(challenge) {
  if (typeof challenge !== "string" || !UUID.test(challenge)) {
    throw new TypeError("INVALID PROBE CHALLENGE");
  }
  return {kind: REQUEST_KIND, challenge};
}

export function checkProbeResponse(challenge, report) {
  if (typeof challenge !== "string" || !UUID.test(challenge)
      || !report || typeof report !== "object"
      || Array.isArray(report)) {
    throw new TypeError("PROBE RESPONSE REJECTED");
  }
  const keys = [
    "kind", "status", "challenge", "read_only",
    "extension_origin_argument_observed", "extension_origin_authenticated",
    "browser_window_identity_verified", "sway_window_identity_verified",
    "browser_session_identity_verified", "incognito_exclusion_verified_by_host",
    "tab_content_captured", "session_capture_allowed", "restore_allowed",
    "safe_actions"
  ];
  if (Object.keys(report).length !== keys.length
      || keys.some(k => !Object.hasOwn(report, k))
      || report.kind !== RESPONSE_KIND
      || report.status !== "transport_observed"
      || report.challenge !== challenge
      || report.read_only !== true
      || report.extension_origin_argument_observed !== true
      || report.extension_origin_authenticated !== false
      || report.browser_window_identity_verified !== false
      || report.sway_window_identity_verified !== false
      || report.browser_session_identity_verified !== false
      || report.incognito_exclusion_verified_by_host !== false
      || report.tab_content_captured !== false
      || report.session_capture_allowed !== false
      || report.restore_allowed !== false
      || !Array.isArray(report.safe_actions)
      || report.safe_actions.length !== 0) {
    throw new TypeError("PROBE RESPONSE REJECTED");
  }
  // No data from the host is persisted or forwarded.
  return {
    status: "transport_observed",
    window_identity_verified: false,
    session_restorable: false,
    safe_actions: [],
  };
}
