# Social PHONE FaceTime Audio V3: partial BlueFerry call status

**Patient:** kudokudo1/The-Post-Apollo-Project  
**Staff:** external Hospital-compatible PHONE DOC, no verified live Room/Assignment/Session  
**Base:** current main; V2 PR #2003 merged; issue #1999 tracks true audio-route acceptance.

## IMPLEMENTATION

Operator supplied live read-only BlueFerry observations: service active, local configuration present, session D-Bus owner present, Python D-Bus available, and GetStatus returned valid API v2 JSON with daemon=true and string phone_audio_route. The calls_state field was not a string. Its precise raw type/presence remains unknown.

The original PhoneAudioControls._project converts a missing/nonstring/unknown calls_state into UNKNOWN. V2 PhoneFaceTimeAudioRouteProbe._blueferry_ready incorrectly classified that single unknown call field as the whole daemon unavailable, resulting in misleading BLUEFERRY STATUS UNAVAILABLE.

V3 separates an observed, valid BlueFerry GetStatus from optional cellular-call HFP fields. A valid read-only provider self-report with UNKNOWN/missing callsState or callsEnabled produces PHONE_CALL_STATUS_UNREPORTED with phoneBackendObserved true, cellularHfpReadyReported false, and every native FaceTime, recording, personal-data, route-mutation, provider-authentication and microphone/speaker flag false. An actually inaccessible/invalid daemon still produces PHONE_BRIDGE_UNAVAILABLE; a valid call status that explicitly fails readiness still produces PHONE_CALLS_NOT_READY.

The shared FaceTime Audio panel now says BLUEFERRY RESPONDING // Cellular call state was not reported in a recognized format, instead of misleadingly implying the entire daemon is unreachable. This does not touch cellular Calls1, PipeWire config, Apple invite handling, permissions, Favorites/Notes SAVE or any local machine.

## HOW TO USE

After independent review, merge and separately authorized local Quickshell deployment, open Social > PHONE > CALLS > FT AUDIO > CHECK AUDIO ROUTE. Expect the new partial-status explanation if the operator-observed missing/nonstring call field persists.

Only a real consenting iPhone FaceTime Audio call with the PC selected manually from the iPhone audio route picker can establish actual speaker/microphone routing. A known Bluetooth HFP profile, even with responding BlueFerry, cannot.

## VERIFY

Current parser and QML source tests now include explicit real-GetStatus-shaped API v2 fixtures with missing/null/boolean/list/future-version call status, missing callsEnabled and the provider-observed-but-no-HFP-authorization outcome. The dedicated FaceTime V2 workflow reruns legacy URL-invite security, cellular audio control and locked Personal editor regressions. Exact PR head CI green is required; source tests do not establish live audio routing.

## WATCH OUT FOR

The value was demonstrated not to be a string, but the live diagnostic did not establish whether the key was missing, null, numeric, boolean or an unsupported structure. Do not print the raw JSON, phone IDs, config file or private fields. The existing daemon can be healthy for messages/media while its optional cellular calling backend lacks readiness evidence.

V3 makes no native FaceTime client, call setup, C3e/C5 consent, signed Personal save, profile mutation or Bluetooth action. Provider self-report never equals independently authenticated iPhone/Apple connection.

## CHECKLIST

- [x] Validate live operator result and re-open actual mainline source.
- [x] Correct partial status classification in PHONE-owned observer.
- [x] Add explicit partial-status QML and regression coverage.
- [ ] Verify exact-head CI, independent review, operator-authorized merge.
- [ ] Separately authorized live desktop update and real consenting call test.

## NEXT

Verify CI and review draft. After authorized desktop deployment, recheck the FaceTime Audio status, then inspect only call-field presence and primitive types to identify whether this is optional backend reporting or a provider compatibility change. Do not restart services or weaken trust checks to dismiss the warning.

## DECISIONS

External Hospital-compatible PHONE DOC, no live registration claimed. Source and test changes only; no merge, local machine action, real iPhone call or private data write; operator retains final acceptance.
