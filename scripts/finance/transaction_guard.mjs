// FinanceW D9: policy and transaction execution, injectable fake Actual API.
// Never retried automatically. No filesystem, credentials or side-effects until
// an injected recordAttempt callback succeeds.
export class TransactionRefusal extends Error {
  constructor(code) { super(code); this.code = code; }
}
const reject = code => { throw new TransactionRefusal(code); };
const idPattern = /^[a-zA-Z0-9-]{4,80}$/;
const hexPattern = /^[0-9a-f]{32}$/;
const own = (o, k) => Object.prototype.hasOwnProperty.call(o, k);

export function validTransactionDate(date, month) {
  if (typeof month !== "string" || !/^20\d{2}-(0[1-9]|1[0-2])$/.test(month)
      || typeof date !== "string"
      || !/^20\d{2}-(0[1-9]|1[0-2])-\d{2}$/.test(date)
      || !date.startsWith(month + "-")) return false;
  const [y,m,d] = date.split("-").map(Number);
  const parsed = new Date(Date.UTC(y, m - 1, d));
  return parsed.getUTCFullYear() === y && parsed.getUTCMonth() === m - 1
      && parsed.getUTCDate() === d;
}

export function validateTransactionCommand(input) {
  if (!input || typeof input !== "object" || Array.isArray(input))
    reject("invalid-command");
  const allowed = new Set(["action", "requestId", "accountId", "month",
    "date", "description", "amountCents", "transactionId", "original"]);
  if (Object.keys(input).some(k => !allowed.has(k))) reject("unexpected-fields");
  const {action,requestId,accountId,month,date,description,amountCents} = input;
  if (!["create", "update"].includes(action)) reject("invalid-action");
  if (typeof requestId !== "string" || !hexPattern.test(requestId))
    reject("invalid-request-id");
  if (typeof accountId !== "string" || !idPattern.test(accountId))
    reject("invalid-account-id");
  if (!validTransactionDate(date, month)) reject("invalid-date");
  if (!Number.isSafeInteger(amountCents) || amountCents === 0
      || Math.abs(amountCents) > 99999999999)
    reject("invalid-amount");
  if (typeof description !== "string"
      || !description.trim() || description.trim().length > 120)
    reject("invalid-description");
  if (action === "create") {
    if (own(input,"transactionId") || own(input,"original"))
      reject("unexpected-edit-fields");
  } else {
    if (typeof input.transactionId !== "string"
        || !idPattern.test(input.transactionId))
      reject("invalid-transaction-id");
    const orig = input.original;
    if (!orig || typeof orig !== "object"
        || Array.isArray(orig) || Object.keys(orig).sort().join(",") !== "amountCents,date")
      reject("invalid-original");
    if (!validTransactionDate(orig.date,month)
        || !Number.isSafeInteger(orig.amountCents)
        || orig.amountCents === 0)
      reject("invalid-original");
  }
  return {...input, description: description.trim()};
}

function rejectSplitOrTransfer(row) {
  // A simple editor must not break both sides of a transfer or a split.
  if ((row.imported_id && !String(row.imported_id).startsWith("financew-"))
      || row.transfer_id || row.is_parent || row.is_child
      || row.parent_id || (Array.isArray(row.subtransactions)
                          && row.subtransactions.length))
    reject("unsupported-complex-transaction");
}

function stableUuidFromHex(hex) {
  // Same ID on any manual investigation/recovery attempt. Not an auth secret.
  return [hex.slice(0,8),hex.slice(8,12),"4"+hex.slice(13,16),
    "8"+hex.slice(17,20),hex.slice(20,32)].join("-");
}

export async function executeTransaction({api, input, recordAttempt}) {
  const cmd = validateTransactionCommand(input);
  if (!api || typeof recordAttempt !== "function")
    reject("missing-write-guards");
  const accounts = await api.getAccounts();
  if (!Array.isArray(accounts) || !accounts.some(a => a && a.id === cmd.accountId
      && !a.offbudget && !a.closed)) reject("stale-account");
  const rows = await api.getTransactions(cmd.accountId,
    cmd.month + "-01", cmd.month + "-31");
  if (!Array.isArray(rows)) reject("invalid-ledger");

  if (cmd.action === "create") {
    // Block matching amount+day even if the payee label is different or stale.
    // This intentionally errs toward false positives over duplicate money.
    if (rows.some(r => r && r.date === cmd.date && r.amount === cmd.amountCents))
      reject("possible-duplicate");
    const importedId = "financew-" + cmd.requestId;
    if (rows.some(r => r && r.imported_id === importedId))
      reject("already-exists");
    await recordAttempt(cmd);
    const ids = await api.addTransactions(cmd.accountId, [{
      id: stableUuidFromHex(cmd.requestId), account: cmd.accountId,
      date: cmd.date, amount: cmd.amountCents, payee_name: cmd.description,
      imported_id: importedId, cleared: false
    }], false, false);
    if (!Array.isArray(ids) || ids.length !== 1 || !ids[0])
      reject("uncertain-write");
    await api.sync();
    const after = await api.getTransactions(cmd.accountId,
      cmd.month + "-01", cmd.month + "-31");
    if (!Array.isArray(after) || !after.some(t => t && t.id === ids[0]
        && t.date === cmd.date && t.amount === cmd.amountCents))
      reject("uncertain-write");
    return {status: "committed"};
  }

  const matching = rows.filter(r => r && r.id === cmd.transactionId);
  if (matching.length !== 1) reject("stale-transaction");
  const old = matching[0];
  rejectSplitOrTransfer(old);
  if (old.date !== cmd.original.date || old.amount !== cmd.original.amountCents
      || (old.account !== undefined && old.account !== cmd.accountId))
    reject("stale-transaction");
  // Preserve the existing payee: editing its label requires a distinct
  // payee-ID workflow. Refuse text edits rather than silently dropping them.
  await recordAttempt(cmd);
  await api.updateTransaction(cmd.transactionId, {
    date: cmd.date, amount: cmd.amountCents
  });
  await api.sync();
  const after = await api.getTransactions(cmd.accountId,
    cmd.month + "-01", cmd.month + "-31");
  if (!Array.isArray(after) || !after.some(r => r && r.id === cmd.transactionId
      && r.date === cmd.date && r.amount === cmd.amountCents))
    reject("uncertain-write");
  return {status: "committed"};
}
