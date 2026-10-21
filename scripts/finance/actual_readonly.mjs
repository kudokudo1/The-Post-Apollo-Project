// FinanceW / Actual Budget read-only normalization.
// This module has no imports from Actual, no persistence, and no write methods.
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

export function normalizeSnapshot({month, budget, accounts, balances}) {
  if (!validMonth(month)) throw new Error("invalid-month");
  if (!budget || !Array.isArray(budget.categoryGroups)
      || !Array.isArray(accounts) || !(balances instanceof Map)) {
    throw new Error("unexpected-actual-data-shape");
  }
  const categoryRows = [];
  for (const group of budget.categoryGroups) {
    if (!group || !Array.isArray(group.categories)) {
      throw new Error("unexpected-category-group");
    }
    if (group.is_income) continue;
    for (const category of group.categories) {
      if (!category || typeof category.name !== "string"
          || typeof category.id !== "string") {
        throw new Error("unexpected-category");
      }
      categoryRows.push({
        id: category.id,
        name: category.name,
        group: String(group.name || ""),
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
        name: account.name,
        balanceCents: cents(balances.get(account.id), "account-balance")
      };
    });
  return {
    schemaVersion: 1,
    source: "actual-budget",
    readOnly: true,
    month,
    toBudgetCents: cents(budget.toBudget, "toBudget"),
    accounts: accountRows,
    categories: categoryRows
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
  for (const account of accounts) {
    if (!account.offbudget && !account.closed) {
      balances.set(account.id, await api.getAccountBalance(account.id));
    }
  }
  return normalizeSnapshot({month, budget, accounts, balances});
}
