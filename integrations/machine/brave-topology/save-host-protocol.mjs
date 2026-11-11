/* MACHINE // strict one-shot encrypted save host contract. */
export const SAVE_HOST = "org.postapollo.machine_brave_save_trial";
export const SAVE_REQUEST_KIND = "machine-brave-sealed-save-request-v1";
export const SAVE_RESPONSE_KIND = "machine-brave-sealed-save-response-v1";
const UUID4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const SHA256 = /^[0-9a-f]{64}$/;
export function makeSealedSaveRequest(challenge,envelope) {
  if (typeof challenge !== "string" || !UUID4.test(challenge) ||
      !envelope || typeof envelope !== "object" ||
      envelope.kind !== "machine-brave-sealed-session-v1" ||
      !Object.hasOwn(envelope,"ciphertext")) {
    throw new TypeError("SEALED SAVE REQUEST REFUSED");
  }
  return {
    kind:SAVE_REQUEST_KIND,challenge,
    operator_save_requested:true,envelope
  };
}
export function checkSealedSaveResponse(challenge,reply) {
  const keys=[
    "kind","status","challenge","record_id","sha256",
    "ciphertext_authentication_verified","origin_authenticated",
    "persistent_browser_window_binding_verified","restore_allowed",
    "safe_actions"
  ];
  if (typeof challenge !== "string" || !UUID4.test(challenge) ||
      !reply || typeof reply !== "object" || Array.isArray(reply) ||
      Object.keys(reply).length !== keys.length ||
      keys.some(k=>!Object.hasOwn(reply,k)) ||
      reply.kind !== SAVE_RESPONSE_KIND ||
      reply.status !== "sealed_record_saved" ||
      reply.challenge !== challenge ||
      !UUID4.test(reply.record_id) ||
      !SHA256.test(reply.sha256) ||
      reply.ciphertext_authentication_verified !== false ||
      reply.origin_authenticated !== false ||
      reply.persistent_browser_window_binding_verified !== false ||
      reply.restore_allowed !== false ||
      !Array.isArray(reply.safe_actions) || reply.safe_actions.length) {
    throw new TypeError("SEALED SAVE RESPONSE REFUSED");
  }
  return {status:"sealed_record_saved",record_id:reply.record_id,
          sha256:reply.sha256,restore_allowed:false,safe_actions:[]};
}
