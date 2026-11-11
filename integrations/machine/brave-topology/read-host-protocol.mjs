/* MACHINE // one-shot, nonce-bound, ciphertext-only read-back contract. */
import {validateSealedEnvelope} from "./session-unseal.mjs";
export const READ_HOST="org.postapollo.machine_brave_read_trial";
export const READ_REQ="machine-brave-sealed-read-request-v1";
export const READ_RESP="machine-brave-sealed-read-response-v1";
const UUID4=/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const SHA256=/^[0-9a-f]{64}$/;
export function makeReadRequest(challenge,recordId){
  if(typeof challenge!=="string"||!UUID4.test(challenge)||
     typeof recordId!=="string"||!UUID4.test(recordId))
    throw new TypeError("SEALED READ REQUEST REFUSED");
  return {kind:READ_REQ,challenge,record_id:recordId,
          operator_read_requested:true};
}
export function verifyReadReply(challenge,recordId,reply){
  const fields=[
    "kind","status","challenge","record_id","sha256","envelope",
    "ciphertext_authentication_verified","origin_authenticated",
    "persistent_browser_window_binding_verified","restore_allowed",
    "safe_actions"
  ];
  if(!reply||typeof reply!=="object"||Array.isArray(reply)||
     Object.keys(reply).length!==fields.length||
     fields.some(f=>!Object.hasOwn(reply,f))||
     reply.kind!==READ_RESP||reply.status!=="sealed_record_read"||
     reply.challenge!==challenge||reply.record_id!==recordId||
     !SHA256.test(reply.sha256)||
     reply.ciphertext_authentication_verified!==false||
     reply.origin_authenticated!==false||
     reply.persistent_browser_window_binding_verified!==false||
     reply.restore_allowed!==false||
     !Array.isArray(reply.safe_actions)||reply.safe_actions.length)
    throw new TypeError("SEALED READ RESPONSE REFUSED");
  validateSealedEnvelope(reply.envelope);
  return {envelope:reply.envelope,sha256:reply.sha256,
          restore_allowed:false,safe_actions:[]};
}
