#!/usr/bin/env node
"use strict";
/*
 * C2b disposable integration proof. NOT a production broker or public IPC.
 * Requires GitHub Actions, private HOME, private D-Bus and a marker.
 * Uses ONLY a synthetic key and a fake NASA provider implemented in process.
 * No network operations, QML secret exposure or host credentials.
 */
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const cp = require("node:child_process");
const crypto = require("node:crypto");

const SERVICE = "post-apollo-connections-c2b-fake-only";
const LABEL = "Post-Apollo C2b disposable synthetic NASA key";
const NONCE = /^[0-9a-f]{32}$/;
const OPERATION = "fires.hotspots.read";
const SCOPE = "nasa-firms";
const SOURCE = "VIIRS_NOAA21_NRT";
const BOUNDS = "-79.1,37.8,-78.8,38.0";
const FAKE_KEY = /^C2BFAKE-[a-f0-9]{40}$/;

function environmentSafe() {
    const home = process.env.HOME || "";
    const root = path.dirname(home);
    if (process.platform !== "linux"
            || process.env.GITHUB_ACTIONS !== "true"
            || process.env.POST_APOLLO_C2B_FAKE_ONLY !== "1"
            || !process.env.DBUS_SESSION_BUS_ADDRESS
            || path.basename(home) !== "home"
            || path.dirname(root) !== os.tmpdir()
            || !/^postapollo-c2b-ci-[A-Za-z0-9]+$/.test(path.basename(root)))
        return false;
    try {
        for (const dir of [root, home]) {
            const st = fs.lstatSync(dir);
            if (!st.isDirectory() || st.isSymbolicLink()
                    || (st.mode & 0o077) !== 0
                    || (typeof process.getuid === "function"
                        && st.uid !== process.getuid())) return false;
        }
        const marker = path.join(root, ".c2b-private-bus");
        const st = fs.lstatSync(marker);
        return st.isFile() && !st.isSymbolicLink()
            && (st.mode & 0o077) === 0
            && (typeof process.getuid !== "function"
                || st.uid === process.getuid())
            && fs.readFileSync(marker, "utf8").trim() === "C2B_DISPOSABLE_ONLY";
    } catch (error) { return false; }
}

function attrs(nonce) {
    return ["post-apollo-test", SERVICE, "nonce", nonce];
}

function secretTool(args, input) {
    const result = cp.spawnSync("secret-tool", args, {
        input, encoding:"utf8", timeout:12000, maxBuffer:4096,
        // No inherited stdout/stderr and no key in argv or environment.
        stdio:["pipe","pipe","pipe"]
    });
    if (result.error || result.status !== 0) return null;
    return result.stdout;
}

function lookup(nonce) {
    const result = secretTool(["lookup", ...attrs(nonce)]);
    return typeof result === "string" ? result.trim() : null;
}

function seed(nonce) {
    if (lookup(nonce) !== null) return "REFUSED_EXISTING_SYNTHETIC_ITEM";
    const fake = "C2BFAKE-" + crypto.randomBytes(20).toString("hex");
    if (!FAKE_KEY.test(fake)) return "REFUSED_SYNTHETIC_KEY_GENERATION";
    if (secretTool(["store", "--label=" + LABEL, ...attrs(nonce)], fake + "\n") === null)
        return "REFUSED_SYNTHETIC_STORE";
    return "C2B_SYNTHETIC_KEY_STORED";
}

function fakeProvider(secret, source, bounds, days) {
    // This is an in-process fake, not an HTTP adapter. No fetch, curl, URL,
    // request header, or outbound socket is constructed from the key.
    if (!FAKE_KEY.test(secret) || source !== SOURCE
            || bounds !== BOUNDS || days !== 1)
        return {ok:false,reason:"REFUSED_FAKE_PROVIDER_INPUT"};
    return {ok:true, source:SOURCE, bounds:BOUNDS, simulated:true,
            observations:[
                {latitude:37.91,longitude:-79.02,confidence:"synthetic"},
                {latitude:37.94,longitude:-78.97,confidence:"synthetic"}
            ]};
}

function exercise(nonce) {
    // The host-managed identities and approvals in this function are only
    // an in-process SIMULATION. They are not trusted Linux peer credentials.
    const authorizedActor = Object.freeze({name:"weather-earth",profile:"test-profile"});
    const impostor = Object.freeze({name:"weather-earth",profile:"test-profile"});
    const granted = new Map();
    const now = 1793800000000;
    const expiry = now + 60000;

    function approve(actor, consent, operation, until) {
        if (!consent || actor !== authorizedActor || operation !== OPERATION
                || !(until > now) || until > now + 120000)
            return null;
        const token = crypto.randomBytes(32).toString("hex");
        granted.set(token,{actor,provider:SCOPE,operation,until,revoked:false});
        return token;
    }
    function revoke(token) {
        const g = granted.get(token);
        if (!g) return false;
        g.revoked = true;
        return true;
    }
    function perform(actor, token, provider, operation, when) {
        const g = typeof token === "string" ? granted.get(token) : null;
        if (!g || g.revoked || g.actor !== actor || actor !== authorizedActor
                || g.provider !== provider || provider !== SCOPE
                || g.operation !== operation || operation !== OPERATION
                || when >= g.until)
            return {ok:false,reason:"REFUSED_SCOPE_OR_AUTHORITY"};
        granted.delete(token);  // One-shot and non-replayable.
        const secret = lookup(nonce);  // Key retrieved only after grant check.
        if (!secret || !FAKE_KEY.test(secret))
            return {ok:false,reason:"REFUSED_SYNTHETIC_KEY_UNAVAILABLE"};
        const output = fakeProvider(secret,SOURCE,BOUNDS,1);
        if (!output.ok) return {ok:false,reason:"REFUSED_FAKE_PROVIDER"};
        return {ok:true,simulated:true,provider:"NASA FIRMS TEST ONLY",
                source:output.source,bounds:output.bounds,
                observations:output.observations};
    }

    if (approve(authorizedActor,false,OPERATION,expiry) !== null)
        return "REFUSED_MISSING_CONSENT_GATE";
    if (approve(impostor,true,OPERATION,expiry) !== null)
        return "REFUSED_UNTRUSTED_CALLER_GATE";
    if (approve(authorizedActor,true,"mail.send",expiry) !== null)
        return "REFUSED_CROSS_SCOPE_GRANT_GATE";
    const token = approve(authorizedActor,true,OPERATION,expiry);
    if (!token) return "REFUSED_EXPECTED_GRANT";
    const invalidRequests = [
        perform(impostor,token,SCOPE,OPERATION,now+1),
        perform(authorizedActor,"fake-token",SCOPE,OPERATION,now+1),
        perform(authorizedActor,token,"proton-mail",OPERATION,now+1),
        perform(authorizedActor,token,SCOPE,"mail.read",now+1),
        perform(authorizedActor,token,SCOPE,OPERATION,expiry)
    ];
    if (invalidRequests.some(x => x.ok))
        return "REFUSED_UNAUTHORIZED_FAKE_ACTION";
    const result = perform(authorizedActor,token,SCOPE,OPERATION,now+1);
    if (!result.ok || !result.simulated || result.source !== SOURCE
            || result.observations.length !== 2
            || JSON.stringify(result).includes("C2BFAKE"))
        return "REFUSED_FAKE_PROVIDER_RETRIEVAL";
    if (perform(authorizedActor,token,SCOPE,OPERATION,now+2).ok)
        return "REFUSED_REPLAY_GATE";
    const revoked = approve(authorizedActor,true,OPERATION,expiry);
    if (!revoked || !revoke(revoked)
            || perform(authorizedActor,revoked,SCOPE,OPERATION,now+3).ok)
        return "REFUSED_REVOCATION_GATE";
    const expired = approve(authorizedActor,true,OPERATION,expiry);
    if (!expired || perform(authorizedActor,expired,SCOPE,OPERATION,expiry).ok)
        return "REFUSED_EXPIRY_GATE";
    return "C2B_FAKE_NASA_SCOPE_AND_KEYRING_PASS";
}

function cleanup(nonce) {
    if (secretTool(["clear",...attrs(nonce)]) === null)
        return "REFUSED_TEST_ITEM_CLEAR";
    if (lookup(nonce) !== null)
        return "REFUSED_TEST_ITEM_CLEANUP_UNVERIFIED";
    return "C2B_SYNTHETIC_ITEM_CLEARED";
}

function run(argv) {
    if (!environmentSafe()) return "REFUSED_C2B_DISPOSABLE_GUARD";
    if (argv.length !== 4 || !NONCE.test(argv[3]))
        return "REFUSED_C2B_ARGS";
    if (argv[2] === "--seed") return seed(argv[3]);
    if (argv[2] === "--exercise") return exercise(argv[3]);
    if (argv[2] === "--missing") return lookup(argv[3]) === null
        ? "C2B_MISSING_KEY_REFUSED" : "REFUSED_EXPECTED_MISSING_KEY";
    if (argv[2] === "--cleanup") return cleanup(argv[3]);
    return "REFUSED_C2B_MODE";
}

const result = run(process.argv);
process.stdout.write(result + "\n");
if (!result.startsWith("C2B_")) process.exitCode = 1;
