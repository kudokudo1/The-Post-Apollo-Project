import assert from "node:assert/strict";
import {
  makeProbeRequest, checkProbeResponse, NATIVE_HOST_NAME,
  REQUEST_KIND, RESPONSE_KIND
} from "../../integrations/machine/brave-topology/native-probe-protocol.mjs";

const nonce = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
assert.equal(NATIVE_HOST_NAME, "org.postapollo.machine_brave_probe");
assert.deepEqual(makeProbeRequest(nonce), {
  kind: REQUEST_KIND, challenge: nonce
});

const good = {
  kind: RESPONSE_KIND,
  status: "transport_observed",
  challenge: nonce,
  read_only: true,
  extension_origin_argument_observed: true,
  extension_origin_authenticated: false,
  browser_window_identity_verified: false,
  sway_window_identity_verified: false,
  browser_session_identity_verified: false,
  incognito_exclusion_verified_by_host: false,
  tab_content_captured: false,
  session_capture_allowed: false,
  restore_allowed: false,
  safe_actions: []
};
assert.deepEqual(checkProbeResponse(nonce, good), {
  status: "transport_observed",
  window_identity_verified: false,
  session_restorable: false,
  safe_actions: []
});

for (const bad of [null, 42, {}, "x", [],
  {...good, challenge: "00000000-0000-4000-8000-000000000124"},
  {...good, status: "verified"},
  {...good, extension_origin_authenticated: true},
  {...good, browser_window_identity_verified: true},
  {...good, sway_window_identity_verified: true},
  {...good, browser_session_identity_verified: true},
  {...good, incognito_exclusion_verified_by_host: true},
  {...good, tab_content_captured: true},
  {...good, session_capture_allowed: true},
  {...good, restore_allowed: true},
  {...good, safe_actions: ["restore"]},
  {...good, url: "https://PRIVATE.example"},
  {...good, window_id: 1234},
  {...good, saved_session: {}}
]) {
  assert.throws(() => checkProbeResponse(nonce, bad),
                /PROBE RESPONSE REJECTED/);
}
for (const bad of ["", null, true, 123, nonce.toUpperCase(),
  "00000000000040008000000000000123", "other"]) {
  assert.throws(() => makeProbeRequest(bad), /INVALID PROBE CHALLENGE/);
}
const responseClone = structuredClone(good);
checkProbeResponse(nonce, good);
assert.deepEqual(good, responseClone);
console.log("MACHINE Brave // optional native probe challenge and no-identity contract PASS");
