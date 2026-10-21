import assert from "node:assert/strict";
import {test} from "node:test";
import {mkdtemp, writeFile, rm} from "node:fs/promises";
import {tmpdir} from "node:os";
import {join} from "node:path";
import {readActualServerURL} from "../../scripts/finance/source_config.mjs";

test("missing local selection retains desktop embedded server", async () => {
  const dir = await mkdtemp(join(tmpdir(), "financew-config-tests-"));
  try {
    assert.equal(await readActualServerURL({
      path: join(dir, "missing"), env: {}
    }), "http://127.0.0.1:5007");
  } finally {
    await rm(dir, {recursive:true, force:true});
  }
});

test("new localhost server is selected only after explicit file configuration", async () => {
  const dir = await mkdtemp(join(tmpdir(), "financew-config-tests-"));
  const path = join(dir, "server-url");
  try {
    await writeFile(path, "http://127.0.0.1:5006\n", {mode:0o600});
    assert.equal(await readActualServerURL({path,env:{}}),
      "http://127.0.0.1:5006");
    assert.equal(await readActualServerURL({
      path,env:{ACTUAL_SERVER_URL:"http://localhost:5008"}
    }), "http://localhost:5008");
    for (const invalid of ["https://example.com", "http://10.0.0.1:5006",
      "http://127.0.0.1:5006/?password=abc", "two words", "",
      "http://127.0.0.1:5006\nhttp://127.0.0.1:5007\n"]) {
      await writeFile(path, invalid, {mode:0o600});
      await assert.rejects(()=>readActualServerURL({path,env:{}}));
    }
  } finally {
    await rm(dir, {recursive:true,force:true});
  }
});

test("source checker is limited to local unauthenticated health probes", async () => {
  const {readFile} = await import("node:fs/promises");
  const script = await readFile(
    new URL("../../scripts/finance/check_server.mjs", import.meta.url),
    "utf8");
  assert.match(script,/readActualServerURL\(/);
  assert.match(script,/redirect: "manual"/);
  assert.match(script,/AbortSignal\.timeout\(3000\)/);
  for (const forbidden of ["ACTUAL_PASSWORD", "actual-password",
    "ACTUAL_SYNC_ID", "getTransactions", "downloadBudget", "setBudgetAmount"]) {
    assert.ok(!script.includes(forbidden), forbidden);
  }
});

test("installer never copies budgets, migrates credentials, or changes source selection", async () => {
  const {readFile} = await import("node:fs/promises");
  const installer = await readFile(
    new URL("../../scripts/finance/install_standalone_server.sh", import.meta.url),
    "utf8");
  assert.match(installer, /ACTUAL_HOSTNAME=127\.0\.0\.1/);
  assert.match(installer, /ACTUAL_PORT=5006/);
  assert.match(installer, /@actual-app\/sync-server@26\.10\.0/);
  assert.match(installer, /systemctl --user enable --now/);
  assert.match(installer, /if \[\[ "\$\{EUID\}" -eq 0 \]\]/);
  for (const forbidden of ["rm -rf", "actual-password", "actual-sync-id",
      "actual-server-url", "rsync", "cp -", "mv -"]) {
    assert.ok(!installer.includes(forbidden), forbidden);
  }
});
