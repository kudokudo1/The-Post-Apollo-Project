#!/usr/bin/env node
// FinanceW read-only Actual probe. Run manually; no startup hooks or writers.
import {readFile, stat, mkdtemp, rm, chmod} from "node:fs/promises";
import {tmpdir} from "node:os";
import {join} from "node:path";
import {validMonth, localServerUrl, takeReadOnlySnapshot} from "./actual_readonly.mjs";

function monthNow() {
  const date = new Date();
  return date.getFullYear() + "-" + String(date.getMonth() + 1).padStart(2, "0");
}

async function protectedSecret(envName) {
  const filename = process.env[envName];
  if (!filename) throw new Error("missing-" + envName.toLowerCase());
  const info = await stat(filename);
  if (!info.isFile() || (info.mode & 0o077) !== 0) {
    throw new Error("secret-file-must-be-private");
  }
  const value = (await readFile(filename, "utf8")).replace(/[\r\n]+$/, "");
  if (!value) throw new Error("empty-secret-file");
  return value;
}

async function run() {
  // Refuse to connect to a non-local URL or emit a partial snapshot.
  const serverURL = localServerUrl(process.env.ACTUAL_SERVER_URL);
  const syncId = process.env.ACTUAL_SYNC_ID;
  if (!syncId || !/^[a-zA-Z0-9-]{8,80}$/.test(syncId)) {
    throw new Error("missing-or-invalid-sync-id");
  }
  const month = process.env.FINANCEW_MONTH || monthNow();
  if (!validMonth(month)) throw new Error("invalid-month");

  const password = await protectedSecret("ACTUAL_PASSWORD_FILE");
  const encryptionPassword = process.env.ACTUAL_ENCRYPTION_PASSWORD_FILE
    ? await protectedSecret("ACTUAL_ENCRYPTION_PASSWORD_FILE") : null;

  // Private disposable working copy, never the desktop app's live database.
  const directory = await mkdtemp(join(tmpdir(), "financew-actual-"));
  await chmod(directory, 0o700);
  let api;
  try {
    api = await import("@actual-app/api");
    await api.init({dataDir: directory, serverURL, password});
    await api.downloadBudget(syncId, encryptionPassword
      ? {password: encryptionPassword} : undefined);
    const snapshot = await takeReadOnlySnapshot(api, month);
    process.stdout.write(JSON.stringify(snapshot) + "\n");
  } finally {
    if (api) {
      try { await api.shutdown(); } catch { /* still remove cache */ }
    }
    await rm(directory, {recursive: true, force: true});
  }
}

run().catch(error => {
  // Fixed, non-sensitive status. Never print Actual's exception contents,
  // passwords, sync IDs, SQL, budget records, or local filesystem paths.
  const code = /^(invalid-|missing-|secret-|server-must-|empty-)/.test(
    String(error?.message || "")
  ) ? String(error.message).split(":")[0] : "actual-read-failed";
  process.stderr.write("FINANCEW_READ_ONLY_ERROR " + code + "\n");
  process.exitCode = 1;
});
