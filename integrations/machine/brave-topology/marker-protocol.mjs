/* Title-marker witness. A transient title match is not session authority. */
export const HOST_NAME = "org.postapollo.machine_brave_title_marker";
export const REQUEST_KIND = "machine-brave-marker-observe-request-v1";
export const RESPONSE_KIND = "machine-brave-marker-observe-response-v1";
export const TITLE_PREFIX = "MACHINE WINDOW CHECK ";
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const SAFE = /^[^\u0000-\u001f\u007f]{1,128}$/;

export function validChallenge(value) {
  return typeof value === "string" && UUID.test(value);
}

export function markerRequest(challenge) {
  if (!validChallenge(challenge)) throw new TypeError("INVALID MARKER");
  return {kind: REQUEST_KIND, challenge};
}

export function checkMarkerReply(challenge, reply) {
  const keys = [
    "kind", "status", "challenge", "read_only_host",
    "marker_unique_and_stable", "sway_container_id",
    "output", "workspace", "browser_window_id",
    "extension_origin_authenticated", "host_private_window_exclusion_verified",
    "persistent_window_identity_verified", "session_capture_allowed",
    "restore_allowed", "safe_actions"
  ];
  if (!validChallenge(challenge) || !reply
      || typeof reply !== "object" || Array.isArray(reply)
      || Object.keys(reply).length !== keys.length
      || keys.some(k => !Object.hasOwn(reply, k))
      || reply.kind !== RESPONSE_KIND
      || reply.challenge !== challenge
      || reply.read_only_host !== true
      || reply.browser_window_id !== null
      || reply.extension_origin_authenticated !== false
      || reply.host_private_window_exclusion_verified !== false
      || reply.persistent_window_identity_verified !== false
      || reply.session_capture_allowed !== false
      || reply.restore_allowed !== false
      || !Array.isArray(reply.safe_actions) || reply.safe_actions.length) {
    throw new TypeError("MARKER REPLY REJECTED");
  }
  const matched = reply.status === "transient_title_marker_observed";
  if ((!matched && reply.status !== "marker_not_observed")
      || reply.marker_unique_and_stable !== matched
      || (matched && (typeof reply.sway_container_id !== "number"
          || !Number.isSafeInteger(reply.sway_container_id)
          || reply.sway_container_id <= 0
          || typeof reply.output !== "string" || !SAFE.test(reply.output)
          || typeof reply.workspace !== "string" || !SAFE.test(reply.workspace)))
      || (!matched && (reply.sway_container_id !== null
          || reply.output !== null || reply.workspace !== null))) {
    throw new TypeError("MARKER REPLY REJECTED");
  }
  return {
    status: reply.status,
    conId: matched ? reply.sway_container_id : null,
    output: matched ? reply.output : null,
    workspace: matched ? reply.workspace : null,
    sessionRestorable: false,
    safeActions: [],
  };
}
