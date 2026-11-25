// FinanceW Simple M3d5b3 // NON-ACTIVATED protected writer bridge contract.
// This is a PURE policy/trace model. No filesystem, Actual API, credentials,
// process spawning, UI signal, command framing, request ID, or finance write.
// Even a positive review is NOT an authorization or executable transport.
import {
  prepareOfflineCategorizedReview,recheckOfflineCategorizedReview
} from "./simple_m3d2_offline_review.mjs";
import {inspectM3d5b2WriterOutcome}
  from "./simple_m3d5b2_disposable_transport.mjs";

const pinnedWriterEndpoint="http://127.0.0.1:5006";
const key=/^[0-9a-f]{64}$/;
const fingerprint=/^[0-9a-f]{64}$/;
const viewOf=v=>({
  snapshot:v?.snapshot,candidate:v?.candidate,proposal:v?.proposal,
  selectedCategoryId:v?.selectedCategoryId
});
const blocked=reason=>Object.freeze({
  ok:false,reviewMatched:false,canSave:false,writeAllowed:false,
  dispatchAllowed:false,requestIssued:false,canRetry:false,reason
});

// The read side can default to 5007 while the M3b writer pins 5006.
// Require the trusted reader's *explicit observed endpoint*, plus the
// protected writer's separately established source-key witness. A UI
// snapshot hash on its own does not prove where a network connection went.
// Values are caller-supplied for this pure model and confer no authority.
export function inspectM3d5b3SourceCompatibility({
  readerEndpoint,writerEndpoint,readerSourceKey,writerSourceKey
}={}) {
  if(typeof readerEndpoint!=="string" || !readerEndpoint
      ||typeof writerEndpoint!=="string" || !writerEndpoint)
    return blocked("explicit-endpoint-witness-required");
  if(readerEndpoint!==writerEndpoint)
    return blocked("read-write-endpoint-mismatch");
  if(writerEndpoint!==pinnedWriterEndpoint)
    return blocked("protected-writer-endpoint-unapproved");
  if(typeof readerSourceKey!=="string" || !key.test(readerSourceKey)
      ||typeof writerSourceKey!=="string" || !key.test(writerSourceKey))
    return blocked("source-key-unverified");
  if(readerSourceKey!==writerSourceKey)
    return blocked("read-write-source-mismatch");
  return Object.freeze({
    ok:true,canSave:false,writeAllowed:false,dispatchAllowed:false,
    requestIssued:false,reason:"source-witnesses-match-non-authoritative"
  });
}

// An M3d5b1 confirmation returns a fingerprint but destroys the random
// requestId and whole command. Do NOT derive a new ID from the hash, invent
// a new one, or reinterpret its confirmation phrase as write permission.
// This is the exact remaining bridge gap that M3d5b4 must eventually solve
// under independent security review and authorized durable custody.
export function inspectM3d5b3PreDispatch({
  view,previousReview,controllerConfirmation,
  readerEndpoint,writerEndpoint,writerSourceKey
}={}) {
  const current=prepareOfflineCategorizedReview(viewOf(view));
  if(!current.ok || current.canSave!==false
      ||current.writeAllowed!==false
      ||current.requiresFreshActualPreflight!==true)
    return blocked(current.reason||"offline-review-invalid");
  if(!previousReview)return blocked("prior-review-required");
  const rechecked=recheckOfflineCategorizedReview({
    previous:previousReview,...viewOf(view)
  });
  if(!rechecked.ok || rechecked.canSave!==false
      ||rechecked.writeAllowed!==false)
    return blocked(rechecked.reason||"stale-review");
  const source=inspectM3d5b3SourceCompatibility({
    readerEndpoint,writerEndpoint,
    readerSourceKey:view?.snapshot?.sourceKey,writerSourceKey
  });
  if(!source.ok)return source;
  if(!controllerConfirmation || controllerConfirmation.ok!==true
      ||controllerConfirmation.phase!=="confirmed-but-dispatch-disabled"
      ||controllerConfirmation.reason!=="request-identity-issued-and-discarded"
      ||controllerConfirmation.canSave!==false
      ||controllerConfirmation.writeAllowed!==false
      ||typeof controllerConfirmation.fingerprint!=="string"
      ||!fingerprint.test(controllerConfirmation.fingerprint))
    return blocked("independent-confirmation-missing");
  // The confirmation result is intentionally NOT sufficient as durable
  // transport authority. A hash can't prove its hidden request ID, nor be
  // used to construct an identical M3b command after process restart.
  if("requestId" in controllerConfirmation
      ||"action" in controllerConfirmation
      ||"command" in controllerConfirmation
      ||"previewFields" in controllerConfirmation)
    return blocked("executable-confirmation-fields-forbidden");
  return Object.freeze({
    ok:false,reviewMatched:true,canSave:false,writeAllowed:false,
    dispatchAllowed:false,requestIssued:false,canRetry:false,
    reason:"durable-request-id-not-exported"
  });
}

// Synthetic failure matrix only. Stage and journal evidence are test inputs,
// NOT actual persisted records or financial attestation. No result from this
// function is an Actual commit; all scenarios remain non-retryable.
export function classifyM3d5b3SyntheticRecovery({
  phase="unknown",failure="none",journal="unknown",
  stdout="",exitCode=null,readback="unknown"
}={}) {
  const noRetry={canRetry:false,dispatchAllowed:false,
    productionWrite:false,syntheticOnly:true};
  if(!["before-reservation","sealed-dry-run",
        "writer-attempted","writer-exited"].includes(phase)
      ||!["none","process-crash","timeout","aborted"].includes(failure)
      ||!["absent","sealed","attempted","committed","corrupt","unknown"]
        .includes(journal))
    return {...noRetry,state:"blocked",reason:"invalid-synthetic-evidence"};
  // Crash before an intent was reserved is not a financial write witness.
  if(phase==="before-reservation")
    return {...noRetry,state:"not-dispatched",reason:"no-writer-custody"};
  // A test-only reservation can never be promoted to an attempted real write.
  if(phase==="sealed-dry-run")
    return {...noRetry,state:"not-dispatched",reason:"sealed-disposable-only"};
  if(journal==="corrupt" || journal==="unknown" || journal==="absent"
      ||journal==="sealed")
    return {...noRetry,state:"uncertain",reason:"writer-journal-not-proven"};
  if(journal==="attempted" || phase==="writer-attempted"
      ||failure!=="none")
    return {...noRetry,state:"uncertain",reason:"attempted-or-interrupted"};
  const result=inspectM3d5b2WriterOutcome({stdout,exitCode});
  if(journal==="committed" && result.state==="committed"
      && readback==="matching") {
    // This is only a self-consistent fictional scenario, not a real commit.
    return {...noRetry,state:"synthetic-evidence-consistent",
      reason:"future-locked-writer-readback-required"};
  }
  return {...noRetry,state:"uncertain",
    reason:"writer-ack-or-readback-unverified"};
}
