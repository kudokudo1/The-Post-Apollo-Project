"use strict";

/**
 * M11y: read-only, SYNTHETIC-ONLY Ed25519 release verifier.
 *
 * This module does not launch anything, run Quickshell, use TASKS paths,
 * access an actual journal, persist trust state or install a release.
 * Trust anchor bytes and the monotonic generation floor MUST arrive from
 * an independent authenticated channel. The caller's provenance cannot be
 * established by this test module; this is NOT production authorization.
 */
const crypto = require("node:crypto");
const fs = require("node:fs");
const path = require("node:path");

const DIRECTORY_NAME = "m11y-release-copy";
const MAX_MANIFEST = 4096;
const MAX_ARTIFACT = 131072;
const ITEMS = Object.freeze({
  host: "synthetic-host.py",
  owner: "synthetic-owner.py",
  interpreter: "synthetic-interpreter.bin",
});
const SHA = /^[0-9a-f]{64}$/;
const PUBLIC_KEY_BEGIN = "-----BEGIN PUBLIC KEY-----";

class TrustRefusal extends Error {
  constructor(code) {
    super(code);
    this.name = "TrustRefusal";
  }
}
function requireSafe(ok, code) {
  if (!ok) throw new TrustRefusal(code);
}
function sha256(value) {
  return crypto.createHash("sha256").update(value).digest("hex");
}
function exactKeys(data, fields) {
  return data !== null && typeof data === "object" &&
    !Array.isArray(data) &&
    Object.keys(data).length === fields.length &&
    fields.every(key => Object.hasOwn(data, key));
}
function privateStat(st, isDir) {
  return (isDir ? st.isDirectory() : st.isFile()) &&
    st.uid === process.getuid() &&
    (st.mode & 0o077) === 0 &&
    (isDir || st.nlink === 1);
}
function readPrivateFile(parent, name, max) {
  let handle = null;
  try {
    const filename = path.join(parent, name);
    const before = fs.lstatSync(filename, { bigint: true });
    requireSafe(before.isFile() && before.uid === BigInt(process.getuid()) &&
      (before.mode & 0o077n) === 0n && before.nlink === 1n &&
      before.size > 0n && before.size <= BigInt(max),
      "UNSAFE_SYNTHETIC_FILE");
    handle = fs.openSync(filename, fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW);
    const stat = fs.fstatSync(handle, { bigint: true });
    const bytes = fs.readFileSync(handle);
    const later = fs.fstatSync(handle, { bigint: true });
    const after = fs.lstatSync(filename, { bigint: true });
    const identity = s => [s.dev, s.ino, s.size, s.mtimeNs, s.ctimeNs].join(":");
    requireSafe(identity(before) === identity(stat) &&
      identity(stat) === identity(later) &&
      identity(later) === identity(after) &&
      bytes.length === Number(stat.size) &&
      bytes.length <= max, "SYNTHETIC_FILE_CHANGED");
    return bytes;
  } catch (error) {
    if (error instanceof TrustRefusal) throw error;
    throw new TrustRefusal("SYNTHETIC_FILE_UNAVAILABLE");
  } finally {
    if (handle !== null) fs.closeSync(handle);
  }
}
function parseManifest(bytes) {
  requireSafe(Buffer.isBuffer(bytes) && bytes.length <= MAX_MANIFEST,
    "SYNTHETIC_MANIFEST_FORMAT");
  const text = bytes.toString("ascii");
  // ASCII round-trip also rejects UTF-8 and non-ASCII ambiguity.
  requireSafe(Buffer.from(text, "ascii").equals(bytes),
    "SYNTHETIC_MANIFEST_FORMAT");
  const lines = text.split("\n");
  requireSafe(lines.length === 6 && lines[5] === "" &&
    lines[0] === "M11Y-SYNTHETIC-RELEASE-V1" &&
    /^generation:[1-9][0-9]{0,9}$/.test(lines[1]) &&
    /^host:[0-9a-f]{64}$/.test(lines[2]) &&
    /^owner:[0-9a-f]{64}$/.test(lines[3]) &&
    /^interpreter:[0-9a-f]{64}$/.test(lines[4]),
    "SYNTHETIC_MANIFEST_FORMAT");
  const generation = Number(lines[1].slice("generation:".length));
  requireSafe(Number.isSafeInteger(generation) && generation <= 1000000000,
    "SYNTHETIC_MANIFEST_FORMAT");
  return {
    generation,
    digests: {
      host: lines[2].slice("host:".length),
      owner: lines[3].slice("owner:".length),
      interpreter: lines[4].slice("interpreter:".length),
    },
  };
}
/**
 * Trust boundary:
 * - trusted.publicKeyPem, trusted.expectedSpkiHash and trusted.minimumGeneration
 *   are independent inputs; NEVER read these values from releaseDir.
 * - The Ed25519 signature covers the raw canonical manifest bytes.
 * - Caller must independently persist an authenticated generation floor
 *   after acceptance; this function does not update it.
 * - Verified artifacts are returned as captured bytes. Reopening a path for
 *   execution later would reintroduce TOCTOU and is not supported here.
 */
function verifySyntheticRelease(releaseDir, trusted) {
  requireSafe(typeof releaseDir === "string" &&
    path.isAbsolute(releaseDir) &&
    path.basename(releaseDir) === DIRECTORY_NAME &&
    !releaseDir.split(path.sep).includes(".."),
    "SYNTHETIC_RELEASE_DIRECTORY_ONLY");
  requireSafe(exactKeys(trusted, [
    "publicKeyPem", "expectedSpkiHash", "minimumGeneration"
  ]) &&
    typeof trusted.publicKeyPem === "string" &&
    trusted.publicKeyPem.startsWith(PUBLIC_KEY_BEGIN) &&
    typeof trusted.expectedSpkiHash === "string" &&
    SHA.test(trusted.expectedSpkiHash) &&
    Number.isSafeInteger(trusted.minimumGeneration) &&
    trusted.minimumGeneration >= 0,
    "INDEPENDENT_TRUST_ANCHOR_REQUIRED");
  try {
    const st = fs.lstatSync(releaseDir);
    requireSafe(privateStat(st, true) && !st.isSymbolicLink(),
      "UNSAFE_SYNTHETIC_DIRECTORY");
    requireSafe(fs.realpathSync(releaseDir) === releaseDir,
      "SYNTHETIC_DIRECTORY_ALIAS");
  } catch (error) {
    if (error instanceof TrustRefusal) throw error;
    throw new TrustRefusal("SYNTHETIC_DIRECTORY_UNAVAILABLE");
  }
  let key;
  try {
    key = crypto.createPublicKey(trusted.publicKeyPem);
    requireSafe(key.type === "public" && key.asymmetricKeyType === "ed25519",
      "UNTRUSTED_RELEASE_KEY");
    const spkiDer = key.export({ type: "spki", format: "der" });
    requireSafe(sha256(spkiDer) === trusted.expectedSpkiHash,
      "TRUST_ANCHOR_FINGERPRINT_MISMATCH");
  } catch (error) {
    if (error instanceof TrustRefusal) throw error;
    throw new TrustRefusal("UNTRUSTED_RELEASE_KEY");
  }
  const payload = readPrivateFile(releaseDir, "release.manifest", MAX_MANIFEST);
  const signature = readPrivateFile(releaseDir, "release.sig", 256);
  requireSafe(signature.length === 64 && crypto.verify(null, payload, key, signature),
    "RELEASE_SIGNATURE_REFUSED");
  const manifest = parseManifest(payload);
  requireSafe(manifest.generation > trusted.minimumGeneration,
    "RELEASE_GENERATION_NOT_NEWER");
  const snapshots = {};
  for (const [role, filename] of Object.entries(ITEMS)) {
    const bytes = readPrivateFile(releaseDir, filename, MAX_ARTIFACT);
    requireSafe(sha256(bytes) === manifest.digests[role],
      "RELEASE_ARTIFACT_DIGEST_MISMATCH");
    snapshots[role] = Buffer.from(bytes);
  }
  return {
    status: "SYNTHETIC_SIGNED_CONTENT_VERIFIED",
    syntheticOnly: true,
    productionWriterAuthorized: false,
    generation: manifest.generation,
    manifestDigest: sha256(payload),
    snapshots,
  };
}

module.exports = { verifySyntheticRelease, TrustRefusal, DIRECTORY_NAME };
