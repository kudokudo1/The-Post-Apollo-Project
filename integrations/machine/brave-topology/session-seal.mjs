/* MACHINE // Explicit, selected-tab encryption. No Brave APIs or storage.
 * This module never returns plaintext tabs. A future receiver gets only an
 * AES-GCM envelope whose tag is appended by WebCrypto. No key export.
 */
export const SEALED_KIND = "machine-brave-sealed-session-v1";
export const PLAINTEXT_KIND = "machine-brave-selected-session-v1";
export const MAX_SELECTED_TABS = 48;
export const MAX_URL = 2048;
export const MAX_PLAINTEXT_BYTES = 98304;
export const PBKDF2_ITERATIONS = 600000;

function refuse() {
  throw new TypeError("SEALED SESSION REFUSED");
}
function urlRisk(value) {
  if (typeof value !== "string" || !value || value.length > MAX_URL ||
      /[\u0000-\u001f\u007f]/.test(value)) return "excluded";
  try {
    const parsed = new URL(value);
    if (!["https:", "http:"].includes(parsed.protocol) ||
        !parsed.hostname || parsed.username || parsed.password) return "excluded";
    return parsed.search || parsed.hash ? "sensitive" : "candidate";
  } catch {
    return "excluded";
  }
}
export function classifySelectableUrl(url) {
  return urlRisk(url);
}
function b64url(bytes) {
  let binary = "";
  for (let i = 0; i < bytes.length; i += 8192) {
    binary += String.fromCharCode(...bytes.subarray(i, i + 8192));
  }
  return btoa(binary).replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/, "");
}
export async function sealSelectedSession({label, tabs, passphrase, includeSensitive=false},
                                           cryptoApi=globalThis.crypto) {
  if (typeof label !== "string" ||
      !/^[A-Za-z][A-Za-z0-9 _.-]{0,47}$/.test(label) ||
      typeof passphrase !== "string" ||
      passphrase.length < 16 || passphrase.length > 1024 ||
      typeof includeSensitive !== "boolean" ||
      !Array.isArray(tabs) || !tabs.length || tabs.length > MAX_SELECTED_TABS ||
      !cryptoApi || !cryptoApi.subtle || !cryptoApi.getRandomValues) refuse();
  const ordered = [];
  const used = new Set();
  let originalActive = 0;
  for (const tab of tabs) {
    if (!tab || typeof tab !== "object" || Array.isArray(tab) ||
        Object.keys(tab).sort().join(",") !==
        "index,pinned,url,wasActive" ||
        !Number.isSafeInteger(tab.index) || tab.index < 0 ||
        used.has(tab.index) || typeof tab.pinned !== "boolean" ||
        typeof tab.wasActive !== "boolean") refuse();
    used.add(tab.index);
    const risk = urlRisk(tab.url);
    if (risk === "excluded" || (risk === "sensitive" && !includeSensitive)) refuse();
    if (tab.wasActive) originalActive++;
    ordered.push({source_position: tab.index, url: tab.url,
                  pinned: tab.pinned, was_active: tab.wasActive});
  }
  if (originalActive > 1) refuse();
  ordered.sort((a,b) => a.source_position-b.source_position);
  const payload = {
    kind: PLAINTEXT_KIND, version: 1,
    saved_at_utc: new Date().toISOString(),
    window_label: label,
    tabs: ordered,
    browser_sway_identity_verified: false,
    restore_allowed: false
  };
  let text;
  try {
    text = new TextEncoder().encode(JSON.stringify(payload));
    if (text.byteLength > MAX_PLAINTEXT_BYTES) refuse();
    const salt = cryptoApi.getRandomValues(new Uint8Array(16));
    const nonce = cryptoApi.getRandomValues(new Uint8Array(12));
    let keyBytes = new TextEncoder().encode(passphrase);
    let material;
    try {
      material = await cryptoApi.subtle.importKey(
        "raw", keyBytes, "PBKDF2", false, ["deriveKey"]);
    } finally {
      keyBytes.fill(0);
    }
    const key = await cryptoApi.subtle.deriveKey(
      {name:"PBKDF2",hash:"SHA-256",salt,iterations:PBKDF2_ITERATIONS},
      material,{name:"AES-GCM",length:256},false,["encrypt"]);
    const ciphertext = new Uint8Array(await cryptoApi.subtle.encrypt({
      name:"AES-GCM",iv:nonce,
      additionalData:new TextEncoder().encode(SEALED_KIND),
      tagLength:128
    },key,text));
    if (ciphertext.length > 131072) refuse();
    return {
      kind:SEALED_KIND, version:1, algorithm:"AES-256-GCM",
      kdf:"PBKDF2-HMAC-SHA256", iterations:PBKDF2_ITERATIONS,
      salt:b64url(salt),nonce:b64url(nonce),aad:SEALED_KIND,
      ciphertext:b64url(ciphertext)
    };
  } catch {
    refuse();
  } finally {
    if (text) text.fill(0);
  }
}
