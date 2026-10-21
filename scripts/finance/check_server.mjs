#!/usr/bin/env node
// Credential-free, loopback-only reachability check for the LIVE indicator.
// Authentication is separately verified by read_budget.mjs.
import {readActualServerURL} from "./source_config.mjs";

try {
  const url = await readActualServerURL();
  const response = await fetch(url + "/", {
    redirect: "manual", // never follow a redirect outside localhost
    signal: AbortSignal.timeout(3000)
  });
  // The embedded or standalone server may redirect to its login page.
  process.exitCode = response.status >= 200 && response.status < 400 ? 0 : 1;
} catch {
  process.exitCode = 1;
}
