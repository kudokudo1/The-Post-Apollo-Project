/* Strict read-only native Sway co-observation; never a pairing certificate. */
export const FOCUS_HOST_NAME = "org.postapollo.machine_brave_focus_observe";
export const FOCUS_REQUEST_KIND = "machine-brave-native-focus-observe-request-v1";
export const FOCUS_RESPONSE_KIND = "machine-brave-native-focus-observation-v1";
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const SAFE_LABEL = /^[^\u0000-\u001f\u007f]{1,128}$/;

export function makeFocusObserveRequest(challenge) {
  if (typeof challenge !== "string" || !UUID.test(challenge)) {
    throw new TypeError("INVALID FOCUS CHALLENGE");
  }
  // The browser-local window ID is deliberately not sent to the host.
  return {kind: FOCUS_REQUEST_KIND, challenge};
}

export function checkFocusObserveResponse(challenge, response) {
  if (typeof challenge !== "string" || !UUID.test(challenge)
      || !response || typeof response !== "object"
      || Array.isArray(response)) {
    throw new TypeError("FOCUS OBSERVATION REJECTED");
  }
  const keys = [
    "kind", "status", "challenge", "read_only",
    "host_brave_focus_observed", "host_focus_stable_two_reads",
    "observed_output", "observed_workspace", "browser_window_id",
    "extension_origin_argument_observed", "extension_origin_authenticated",
    "browser_to_sway_identity_verified",
    "private_window_exclusion_verified_by_host",
    "restart_session_identity_verified", "session_capture_allowed",
    "restore_allowed", "safe_actions",
  ];
  if (Object.keys(response).length !== keys.length
      || keys.some(key => !Object.hasOwn(response, key))
      || response.kind !== FOCUS_RESPONSE_KIND
      || response.challenge !== challenge
      || response.read_only !== true
      || response.browser_window_id !== null
      || response.extension_origin_argument_observed !== true
      || response.extension_origin_authenticated !== false
      || response.browser_to_sway_identity_verified !== false
      || response.private_window_exclusion_verified_by_host !== false
      || response.restart_session_identity_verified !== false
      || response.session_capture_allowed !== false
      || response.restore_allowed !== false
      || !Array.isArray(response.safe_actions)
      || response.safe_actions.length !== 0) {
    throw new TypeError("FOCUS OBSERVATION REJECTED");
  }
  const observed = response.status === "host_brave_focus_observed_unverified";
  const absent = response.status === "no_host_focus_candidate";
  if ((!observed && !absent)
      || response.host_brave_focus_observed !== observed
      || response.host_focus_stable_two_reads !== observed
      || (observed && (!SAFE_LABEL.test(response.observed_output)
                   || !SAFE_LABEL.test(response.observed_workspace)))
      || (absent && (response.observed_output !== null
                  || response.observed_workspace !== null))) {
    throw new TypeError("FOCUS OBSERVATION REJECTED");
  }
  return {
    status: response.status,
    output: observed ? response.observed_output : null,
    workspace: observed ? response.observed_workspace : null,
    browser_to_sway_identity_verified: false,
    restore_allowed: false,
    safe_actions: [],
  };
}
