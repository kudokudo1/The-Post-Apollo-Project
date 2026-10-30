"use strict";

/** M11y synthetic-only signed deployment manifest and trust-anchor regression. */
const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");
const { verifySyntheticRelease, TrustRefusal } =
  require("./fixtures/TaskSignedReleaseVerifierM11y.cjs");

const FILES = Object.freeze({
  host: "synthetic-host.py",
  owner: "synthetic-owner.py",
  interpreter: "synthetic-interpreter.bin",
});
const DATA = Object.freeze({
  host: Buffer.from("# M11Y SYNTHETIC HOST ONLY\nx=1\n"),
  owner: Buffer.from("# M11Y SYNTHETIC OWNER ONLY\nx=2\n"),
  interpreter: Buffer.from("M11Y_SYNTHETIC_BINARY_ONLY\n"),
});
function sha256(value) {
  return crypto.createHash("sha256").update(value).digest("hex");
}
function createFixture() {
  const parent = fs.mkdtempSync(path.join(os.tmpdir(), "task-m11y-"));
  fs.chmodSync(parent, 0o700);
  const dir = path.join(parent, "m11y-release-copy");
  fs.mkdirSync(dir, { mode: 0o700 });
  const { publicKey, privateKey } = crypto.generateKeyPairSync("ed25519");
  const pem = publicKey.export({ type: "spki", format: "pem" });
  const fingerprint = sha256(publicKey.export({ type: "spki", format: "der" }));
  const trust = { publicKeyPem: pem, expectedSpkiHash: fingerprint, minimumGeneration: 6 };
  const file = (name, bytes) => {
    fs.writeFileSync(path.join(dir, name), bytes, { mode: 0o600 });
    fs.chmodSync(path.join(dir, name), 0o600);
  };
  function manifest(generation = 7, override = {}) {
    return Buffer.from(
      "M11Y-SYNTHETIC-RELEASE-V1\n" +
      "generation:" + generation + "\n" +
      "host:" + (override.host || sha256(DATA.host)) + "\n" +
      "owner:" + (override.owner || sha256(DATA.owner)) + "\n" +
      "interpreter:" + (override.interpreter || sha256(DATA.interpreter)) + "\n");
  }
  function resign(payload = manifest()) {
    file("release.manifest", payload);
    file("release.sig", crypto.sign(null, payload, privateKey));
  }
  for (const [key, name] of Object.entries(FILES)) file(name, DATA[key]);
  resign();
  return { dir, parent, file, trust, manifest, resign,
    cleanup() { fs.rmSync(parent, { recursive: true, force: true }); } };
}
function withFixture(fn) {
  const fx = createFixture();
  try { fn(fx); } finally { fx.cleanup(); }
}
function refused(fx, code, trust = fx.trust, dir = fx.dir) {
  assert.throws(() => verifySyntheticRelease(dir, trust),
    e => e instanceof TrustRefusal && e.message === code);
}

test("valid independent test key, signature, three captured artifacts", () =>
  withFixture(fx => {
    const out = verifySyntheticRelease(fx.dir, fx.trust);
    assert.equal(out.status, "SYNTHETIC_SIGNED_CONTENT_VERIFIED");
    assert.equal(out.syntheticOnly, true);
    assert.equal(out.productionWriterAuthorized, false);
    assert.equal(out.generation, 7);
    assert.equal(out.manifestDigest, sha256(fx.manifest()));
    assert.deepEqual(Object.keys(out.snapshots), Object.keys(FILES));
    for (const role of Object.keys(FILES)) {
      assert.deepEqual(out.snapshots[role], DATA[role]);
    }
  }));

test("absent or self-reported trust anchor never becomes release authority", () =>
  withFixture(fx => {
    refused(fx, "INDEPENDENT_TRUST_ANCHOR_REQUIRED", {});
    refused(fx, "INDEPENDENT_TRUST_ANCHOR_REQUIRED", {
      publicKeyPem: fx.trust.publicKeyPem, expectedSpkiHash: fx.trust.expectedSpkiHash,
    });
    fx.file("trusted-key.pem", Buffer.from(fx.trust.publicKeyPem));
    // Untrusted adjacent key exists, but the API requires an external anchor.
    refused(fx, "INDEPENDENT_TRUST_ANCHOR_REQUIRED", null);
  }));

test("same-folder attacker key plus signed replacement cannot replace pinned external key", () =>
  withFixture(fx => {
    const impostor = crypto.generateKeyPairSync("ed25519");
    const signed = fx.manifest();
    fx.file("release.sig", crypto.sign(null, signed, impostor.privateKey));
    fx.file("trusted-key.pem", Buffer.from(
      impostor.publicKey.export({ type: "spki", format: "pem" })));
    refused(fx, "RELEASE_SIGNATURE_REFUSED");
    const alteredTrust = { ...fx.trust,
      publicKeyPem: impostor.publicKey.export({ type: "spki", format: "pem" }) };
    refused(fx, "TRUST_ANCHOR_FINGERPRINT_MISMATCH", alteredTrust);
  }));

test("edited signed manifest and signature bit flips are refused", () =>
  withFixture(fx => {
    fx.file("release.manifest", Buffer.from(fx.manifest().toString().replace(
      "generation:7", "generation:8")));
    refused(fx, "RELEASE_SIGNATURE_REFUSED");
    fx.resign();
    const signature = fs.readFileSync(path.join(fx.dir, "release.sig"));
    signature[0] ^= 0x01;
    fx.file("release.sig", signature);
    refused(fx, "RELEASE_SIGNATURE_REFUSED");
  }));

test("validly signed older generation is denied by independent floor", () =>
  withFixture(fx => {
    fx.resign(fx.manifest(6));
    refused(fx, "RELEASE_GENERATION_NOT_NEWER");
    fx.resign(fx.manifest(5));
    refused(fx, "RELEASE_GENERATION_NOT_NEWER");
    fx.resign(fx.manifest(7));
    const trust = { ...fx.trust, minimumGeneration: 7 };
    refused(fx, "RELEASE_GENERATION_NOT_NEWER", trust);
  }));

test("same-generation replay needs externally maintained floor and is refused when advanced", () =>
  withFixture(fx => {
    assert.equal(verifySyntheticRelease(fx.dir, fx.trust).generation, 7);
    // Simulates external state update. This verifier deliberately stores nothing.
    const advanced = { ...fx.trust, minimumGeneration: 7 };
    refused(fx, "RELEASE_GENERATION_NOT_NEWER", advanced);
  }));

test("edited host, owner and interpreter bytes never pass signed digest", () =>
  withFixture(fx => {
    for (const role of Object.keys(FILES)) {
      const file = path.join(fx.dir, FILES[role]);
      const original = fs.readFileSync(file);
      fx.file(FILES[role], Buffer.concat([original, Buffer.from("TAMPER")]));
      refused(fx, "RELEASE_ARTIFACT_DIGEST_MISMATCH");
      fx.file(FILES[role], original);
    }
  }));

test("captured signed snapshots do not change when pathname replaced afterward", () =>
  withFixture(fx => {
    const captured = verifySyntheticRelease(fx.dir, fx.trust);
    const replacement = path.join(fx.dir, "replacement.tmp");
    fs.writeFileSync(replacement, "MALICIOUS", { mode: 0o600 });
    fs.renameSync(replacement, path.join(fx.dir, FILES.host));
    assert.deepEqual(captured.snapshots.host, DATA.host);
    refused(fx, "RELEASE_ARTIFACT_DIGEST_MISMATCH");
  }));

test("symlink, hardlink and loose artifact permissions fail closed", () =>
  withFixture(fx => {
    const host = path.join(fx.dir, FILES.host);
    const original = fs.readFileSync(host);
    fs.unlinkSync(host);
    fs.symlinkSync(path.join(fx.dir, FILES.owner), host);
    refused(fx, "UNSAFE_SYNTHETIC_FILE");
    fs.unlinkSync(host);
    fx.file(FILES.host, original);
    const link = path.join(fx.dir, "other-link");
    fs.linkSync(host, link);
    refused(fx, "UNSAFE_SYNTHETIC_FILE");
    fs.unlinkSync(link);
    fs.chmodSync(host, 0o644);
    refused(fx, "UNSAFE_SYNTHETIC_FILE");
    fs.chmodSync(host, 0o600);
    fs.chmodSync(fx.dir, 0o755);
    refused(fx, "UNSAFE_SYNTHETIC_DIRECTORY");
  }));

test("symlinked directory and unexpected directory name fail", () =>
  withFixture(fx => {
    const copied = path.join(fx.parent, "copied");
    fs.renameSync(fx.dir, copied);
    fs.symlinkSync(copied, fx.dir, "dir");
    refused(fx, "UNSAFE_SYNTHETIC_DIRECTORY");
    refused(fx, "SYNTHETIC_RELEASE_DIRECTORY_ONLY", fx.trust, fx.parent);
  }));

test("duplicate or noncanonical signed manifest fields refused even with valid signature", () =>
  withFixture(fx => {
    const invalid = Buffer.from(fx.manifest().toString().replace(
      "host:", "host:" + "0".repeat(64) + "\nhost:"));
    fx.resign(invalid);
    refused(fx, "SYNTHETIC_MANIFEST_FORMAT");
    fx.resign(Buffer.concat([fx.manifest(), Buffer.from("\n")]));
    refused(fx, "SYNTHETIC_MANIFEST_FORMAT");
    fx.resign(Buffer.from(fx.manifest().toString().replace(
      "generation:7", "generation:07")));
    refused(fx, "SYNTHETIC_MANIFEST_FORMAT");
  }));

test("wrong key algorithm, fingerprints, malformed signature and file denied", () =>
  withFixture(fx => {
    refused(fx, "TRUST_ANCHOR_FINGERPRINT_MISMATCH",
      { ...fx.trust, expectedSpkiHash: "f".repeat(64) });
    const rsa = crypto.generateKeyPairSync("rsa", { modulusLength: 2048 });
    refused(fx, "UNTRUSTED_RELEASE_KEY",
      { ...fx.trust, publicKeyPem: rsa.publicKey.export({ type: "spki", format: "pem" }) });
    fx.file("release.sig", Buffer.from("short"));
    refused(fx, "RELEASE_SIGNATURE_REFUSED");
  }));

test("static production guard and absence of real TASKS or script execution", () => {
  const root = path.resolve(__dirname, "../..");
  const verifier = fs.readFileSync(path.join(
    __dirname, "fixtures/TaskSignedReleaseVerifierM11y.cjs"), "utf8");
  const store = fs.readFileSync(path.join(root,
    "services/hub/ApolloHubTodoStore.qml"), "utf8");
  const shell = fs.readFileSync(path.join(root, "shell.qml"), "utf8");
  for (const value of ["apollo-hub-todo-v1.json", "Quickshell.dataDir",
                       "TaskJsonGateCandidateM11l", "TaskJsonGateHostBridgeM11m"]) {
    assert.equal(verifier.includes(value), false);
  }
  assert.equal(verifier.includes("child_process"), false);
  assert.ok(store.includes("readonly property bool guardedWriterEnabled: false"));
  assert.equal((store.match(/\bFileView\s*\{/g) || []).length, 1);
  assert.equal(store.includes("TaskSignedReleaseVerifierM11y"), false);
  assert.equal(shell.includes("TaskSignedReleaseVerifierM11y"), false);
});
