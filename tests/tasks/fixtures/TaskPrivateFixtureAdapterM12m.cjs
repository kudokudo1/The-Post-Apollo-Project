/*
 * TASKS M12m // synthetic-only filesystem adapter.
 * This is NOT a general-purpose file writer and MUST NOT be passed live TASKS.
 * The caller creates the private test file first; no fallback/auto-create.
 */
"use strict";

const fs = require("node:fs/promises");
const constants = require("node:fs").constants;
const path = require("node:path");
const crypto = require("node:crypto");

const MAX_BYTES = 1048576;

class PrivateFixtureAdapterM12m {
    constructor(file) {
        if (typeof file !== "string" || !path.isAbsolute(file)) {
            throw new Error("ABSOLUTE_DISPOSABLE_FILE_REQUIRED");
        }
        const parent = path.dirname(file), root = path.dirname(parent);
        if (path.basename(file) !== "fixture-only.json" ||
                path.basename(parent) !== "m11e-fileview-test" ||
                !/^m12m-[A-Za-z0-9_-]+$/.test(path.basename(root)) ||
                path.dirname(root) !== "/tmp" || path.normalize(file) !== file) {
            throw new Error("M12M_PRIVATE_TEST_FIXTURE_ONLY");
        }
        this.file = file;
        this.parent = parent;
        this.root = root;
    }

    async _check() {
        for (const dir of [this.root, this.parent]) {
            const st = await fs.lstat(dir);
            if (!st.isDirectory() || st.isSymbolicLink() ||
                    st.uid !== process.geteuid() || (st.mode & 0o777) !== 0o700) {
                throw new Error("UNSAFE_FIXTURE_DIRECTORY");
            }
        }
        const st = await fs.lstat(this.file);
        if (!st.isFile() || st.isSymbolicLink() ||
                st.uid !== process.geteuid() || (st.mode & 0o777) !== 0o600 ||
                st.nlink !== 1 || st.size < 1 || st.size > MAX_BYTES) {
            throw new Error("UNSAFE_FIXTURE_SOURCE");
        }
        return st;
    }

    async readExact() {
        const st = await this._check();
        const handle = await fs.open(
            this.file, constants.O_RDONLY | (constants.O_NOFOLLOW || 0));
        try {
            const opened = await handle.stat();
            if (opened.ino !== st.ino || opened.dev !== st.dev) {
                throw new Error("SOURCE_REPLACED_AT_OPEN");
            }
            const bytes = await handle.readFile();
            const after = await handle.stat();
            const pathname = await fs.lstat(this.file);
            if (bytes.length !== st.size || opened.size !== after.size ||
                    opened.mtimeMs !== after.mtimeMs ||
                    opened.ctimeMs !== after.ctimeMs ||
                    pathname.ino !== st.ino || pathname.dev !== st.dev) {
                throw new Error("UNSTABLE_SOURCE_READ");
            }
            const decoded = new TextDecoder("utf-8", {fatal:true}).decode(bytes);
            if (!decoded) throw new Error("EMPTY_SOURCE");
            return decoded;
        } finally {
            await handle.close();
        }
    }

    async replaceAtomic(text, baseline) {
        if (typeof text !== "string" || typeof baseline !== "string") {
            throw new TypeError("TEXT_AND_BASELINE_REQUIRED");
        }
        const data = Buffer.from(text, "utf8");
        if (data.length < 1 || data.length > MAX_BYTES) {
            throw new Error("INVALID_SIZE");
        }
        if (await this.readExact() !== baseline) {
            throw new Error("BASELINE_CHANGED");
        }
        const name = ".m12m-" + crypto.randomUUID();
        const temp = path.join(this.parent, name);
        let made = false;
        try {
            const handle = await fs.open(temp, "wx", 0o600);
            made = true;
            try {
                await handle.writeFile(data);
                await handle.sync();
            } finally {
                await handle.close();
            }
            // Advisory checks only; this cannot fence same-UID outsiders.
            if (await this.readExact() !== baseline) {
                throw new Error("BASELINE_CHANGED_BEFORE_RENAME");
            }
            await fs.rename(temp, this.file);
            made = false;
            const dir = await fs.open(this.parent, constants.O_RDONLY | constants.O_DIRECTORY);
            try {
                await dir.sync();
            } finally {
                await dir.close();
            }
        } finally {
            if (made) await fs.unlink(temp).catch(() => {});
        }
    }
}

module.exports = {PrivateFixtureAdapterM12m};
