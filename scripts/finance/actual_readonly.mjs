// FinanceW / Actual Budget read-only normalization.
// This module has no imports from Actual, no persistence, and no write methods.
import {summarizeFunding} from "./funding_reconciliation.mjs";
import {summarizeIncomeCandidates} from "./income_categorization_preview.mjs";
export function validMonth(month) {
  return typeof month === "string"
      && /^(?:19|20)\d{2}-(?:0[1-9]|1[0-2])$/.test(month);
}

export function localServerUrl(value) {
  const raw = value || "http://127.0.0.1:5007";
  let url;
  try { url = new URL(raw); } catch { throw new Error("invalid-local-server-url"); }
  if (url.protocol !== "http:"
      || !["localhost", "127.0.0.1", "[::1]"].includes(url.hostname)
      || url.username || url.password || url.search || url.hash
      || (url.pathname !== "/" && url.pathname !== "")) {
    throw new Error("server-must-be-loopback-http");
  }
  return url.origin;
}

function cents(value, label) {
  if (!Number.isSafeInteger(value)) {
    throw new Error("invalid-financial-field:" + label);
  }
  return value;
}

export function normalizeSnapshot({month, budget, accounts, balances,
                                   transactionSets = new Map(), payees = []}) {
  if (!validMonth(month)) throw new Error("invalid-month");
  if (!budget || !Array.isArray(budget.categoryGroups)
      || !Array.isArray(accounts) || !(balances instanceof Map)) {
    throw new Error("unexpected-actual-data-shape");
  }
  const categoryRows = [];
  const groupRows = [];
  for (const group of budget.categoryGroups) {
    if (!group || !Array.isArray(group.categories)) {
      throw new Error("unexpected-category-group");
    }
    if (group.is_income) continue;
    // Stable identifiers, not display names, are needed for future category
    // management. A malformed group fails closed rather than guessing IDs.
    if (typeof group.id !== "string" || !group.id
        || typeof group.name !== "string" || !group.name.trim())
      throw new Error("unexpected-category-group-identity");
    groupRows.push({id:group.id,name:group.name});
    for (const category of group.categories) {
      if (!category || typeof category.name !== "string"
          || typeof category.id !== "string") {
        throw new Error("unexpected-category");
      }
      categoryRows.push({
        id: category.id,
        name: category.name,
        group: group.name,
        groupId: group.id,
        budgetedCents: cents(category.budgeted, "budgeted"),
        spentCents: cents(category.spent, "spent"),
        availableCents: cents(category.balance, "balance")
      });
    }
  }
  const accountRows = accounts.filter(account => !account.offbudget && !account.closed)
    .map(account => {
      if (!account || typeof account.id !== "string"
          || typeof account.name !== "string" || !balances.has(account.id)) {
        throw new Error("unexpected-account");
      }
      return {
        id: account.id,
        name: account.name,
        balanceCents: cents(balances.get(account.id), "account-balance")
      };
    });
  if (!(transactionSets instanceof Map) || !Array.isArray(payees))
    throw new Error("unexpected-transactions-shape");
  const activeAccounts = accounts.filter(account => !account.offbudget && !account.closed);
  const payeeNames = new Map();
  for (const payee of payees) {
    if (!payee || typeof payee.id !== "string"
               || typeof payee.name !== "string")
      throw new Error("unexpected-payee");
    payeeNames.set(payee.id, payee.name);
  }
  const transactionRows = [];
  for (const account of activeAccounts) {
    const items = transactionSets.get(account.id) || [];
    if (!Array.isArray(items))
      throw new Error("unexpected-transactions");
    for (const item of items) {
      if (!item || typeof item.id !== "string" || !item.id
                || typeof item.date !== "string"
                || !/^\d{4}-\d{2}-\d{2}$/.test(item.date)
                || !item.date.startsWith(month + "-")
                || (item.account !== undefined && item.account !== account.id))
        throw new Error("unexpected-transaction");
      const payeeKey = item.payee_id || item.payee || "";
      const payeeName = payeeNames.get(payeeKey)
            || (typeof item.imported_payee === "string" ? item.imported_payee : "")
            || (item.transfer_id ? "TRANSFER" : "TRANSACTION");
      transactionRows.push({
        id: item.id,
        accountId: account.id,
        editable: !item.transfer_id && !item.is_parent && !item.is_child
          && !item.parent_id && !(Array.isArray(item.subtransactions)
                   && item.subtransactions.length)
          && (!item.imported_id || String(item.imported_id).startsWith("financew-")),
        date: item.date,
        account: account.name,
        description: payeeName,
        amountCents: cents(item.amount, "transaction-amount"),
        cleared: item.cleared === true
      });
    }
  }
  // The page previews at most 24 latest entries. Do not sum split entries:
  // API returns parent transaction amounts and nested split details.
  transactionRows.sort((a, b) => b.date.localeCompare(a.date));
  return {
    schemaVersion: 1,
    source: "actual-budget",
    readOnly: true,
    month,
    toBudgetCents: cents(budget.toBudget, "toBudget"),
    accounts: accountRows,
    categories: categoryRows,
    categoryGroups: groupRows,
    funding: summarizeFunding({month,budget,accounts,balances,transactionSets}),
    incomeReview: summarizeIncomeCandidates({month,budget,accounts,transactionSets}),
    transactionsCount: transactionRows.length,
    transactions: transactionRows.slice(0, 24)
  };
}

export async function takeReadOnlySnapshot(api, month) {
  if (!validMonth(month)) throw new Error("invalid-month");
  // The only API calls allowed in the snapshot path are getters.
  const [budget, accounts] = await Promise.all([
    api.getBudgetMonth(month),
    api.getAccounts()
  ]);
  if (!Array.isArray(accounts)) throw new Error("unexpected-accounts");
  const balances = new Map();
  const transactionSets = new Map();
  const from = month + "-01";
  const until = month + "-31"; // Inclusive end, per Actual API documentation.
  const payees = await api.getPayees();
  for (const account of accounts) {
    if (!account.offbudget && !account.closed) {
      balances.set(account.id, await api.getAccountBalance(account.id));
      transactionSets.set(account.id, await api.getTransactions(account.id, from, until));
    }
  }
  return normalizeSnapshot({month, budget, accounts, balances, transactionSets, payees});
}
