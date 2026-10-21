// Single source selection used by both the budget API and header health check.
// A missing file preserves the original desktop-integrated port 5007.
import {readFile} from "node:fs/promises";
import {homedir} from "node:os";
import {join} from "node:path";
import {localServerUrl} from "./actual_readonly.mjs";

export async function readActualServerURL({
  path = join(homedir(), ".config", "financew", "actual-server-url"),
  env = process.env
} = {}) {
  if (env.ACTUAL_SERVER_URL) return localServerUrl(env.ACTUAL_SERVER_URL);
  let raw;
  try {
    raw = await readFile(path, "utf8");
  } catch (error) {
    if (error.code === "ENOENT") return localServerUrl();
    throw new Error("invalid-local-server-url");
  }
  // A single URL, not a list of destinations or credentials.
  if (!raw || !/^\S+\s*$/.test(raw)) {
    throw new Error("invalid-local-server-url");
  }
  return localServerUrl(raw.trim());
}
