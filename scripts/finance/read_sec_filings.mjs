// FinanceW SEC M2. One read-only EDGAR submissions API request on selection/
// refresh. Requires an operator-supplied SEC-compliant User-Agent (not printed).
import { homedir } from "node:os";
import { join } from "node:path";
import { lstat, readFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";

export const CONTACT_FILE = join(homedir(), ".local", "share", "post-apollo",
  "finance-sec", "user-agent.txt");
export const ISSUERS = Object.freeze({
  "0000320193": "Apple",
  "0000789019": "Microsoft",
  "0001045810": "NVIDIA",
});
export const FORMS = new Set(["8-K","8-K/A","4","4/A","SC 13D","SC 13D/A",
  "SC 13G","SC 13G/A","10-Q","10-Q/A","10-K","10-K/A"]);
const MAX_RETURN = 30;
const MAX_SIZE = 9 * 1024 * 1024;
const ACC = /^\d{10}-\d{2}-\d{6}$/;
const DOC = /^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,170}$/;
const DAY = /^\d{4}-\d{2}-\d{2}$/;

export function validateAgent(raw) {
  if (typeof raw !== "string" || /[\r\n\x00-\x1F\x7F]/.test(raw)) return null;
  const text = raw.trim();
  // A named product/team and real contact address, not a synthetic UA.
  const match = text.match(/^([A-Za-z][A-Za-z0-9 ._-]{3,80})\s+([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})$/);
  if (!match || /example\.(com|org|net)$/i.test(match[2])) return null;
  return text;
}
export async function loadAgent(file = CONTACT_FILE) {
  let stat;
  try { stat = await lstat(file); }
  catch (error) {
    if (error.code === "ENOENT") throw new Error("identity-required");
    throw new Error("identity-unreadable");
  }
  if (!stat.isFile() || stat.isSymbolicLink() || stat.size < 9 ||
      stat.size > 180 || (stat.mode & 0o077) !== 0)
    throw new Error("identity-permissions");
  const agent = validateAgent(await readFile(file, "utf8"));
  if (!agent) throw new Error("identity-invalid");
  return agent;
}

function groupFor(form) {
  if (form.startsWith("8-K")) return "MATERIAL EVENT";
  if (form.startsWith("SC 13")) return "OWNERSHIP";
  if (form === "4" || form === "4/A") return "INSIDER DISCLOSURE";
  return "FINANCIAL REPORT";
}

export function normalizeSubmissions(raw, cik, retrievedAt) {
  if (!ISSUERS[cik] || !raw || typeof raw !== "object") throw new Error("invalid-sec-data");
  if (String(raw.cik) !== String(Number(cik))) throw new Error("wrong-issuer");
  const recent = raw.filings?.recent;
  const required = ["accessionNumber","filingDate","form","primaryDocument"];
  if (!recent || !required.every(k => Array.isArray(recent[k]))) throw new Error("invalid-sec-data");
  const count = recent.form.length;
  if (count > 10000 || required.some(k => recent[k].length !== count))
    throw new Error("invalid-sec-data");
  const filings = [];
  const seen = new Set();
  for (let i = 0; i < count; i++) {
    const form = recent.form[i], accession = recent.accessionNumber[i];
    const date = recent.filingDate[i], document = recent.primaryDocument[i];
    if (!FORMS.has(form) || typeof accession !== "string" || !ACC.test(accession)
        || typeof date !== "string" || !DAY.test(date)
        || typeof document !== "string" || !DOC.test(document)
        || seen.has(accession)) continue;
    seen.add(accession);
    const acceptedRaw = Array.isArray(recent.acceptanceDateTime)
      ? recent.acceptanceDateTime[i] : null;
    const acceptedAt = typeof acceptedRaw === "string"
      && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/.test(acceptedRaw)
      ? acceptedRaw.slice(0, 19) : null;
    filings.push({
      accession, form, category: groupFor(form), filedAt: date, acceptedAt,
      documentUrl: "https://www.sec.gov/Archives/edgar/data/"
        + String(Number(cik)) + "/" + accession.replaceAll("-", "") + "/" + document,
    });
  }
  filings.sort((a,b) => (b.filedAt.localeCompare(a.filedAt)
    || (b.acceptedAt || "").localeCompare(a.acceptedAt || "")));
  return { schemaVersion:1, source:"sec-edgar-submissions", readOnly:true,
    retrievedAt, cik, issuer:ISSUERS[cik], name:String(raw.name || "").slice(0,100),
    filings:filings.slice(0,MAX_RETURN), matchingInRecent:filings.length,
    scope:"issuer recent submissions only; not a market-wide SEC feed" };
}

export async function loadSec(cik, fetcher = fetch, agentLoader = loadAgent) {
  if (!ISSUERS[cik]) throw new Error("unknown-issuer");
  const agent = await agentLoader(); // Fail closed before any SEC request.
  const response = await fetcher("https://data.sec.gov/submissions/CIK" + cik + ".json", {
    method:"GET", redirect:"error",
    headers:{"User-Agent":agent, "Accept":"application/json"},
    signal:AbortSignal.timeout(12000),
  });
  if (!response.ok) throw new Error("sec-unavailable");
  const length = Number(response.headers?.get?.("content-length"));
  if (Number.isFinite(length) && length > MAX_SIZE) throw new Error("sec-response-too-large");
  const raw = await response.text();
  if (raw.length > MAX_SIZE) throw new Error("sec-response-too-large");
  return normalizeSubmissions(JSON.parse(raw), cik, new Date().toISOString());
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    const payload = await loadSec(process.argv[2] || "0000320193");
    process.stdout.write("FINANCE_SEC_SNAPSHOT " + JSON.stringify(payload) + "\n");
  } catch (error) {
    const known = ["identity-required", "identity-unreadable", "identity-permissions",
      "identity-invalid", "unknown-issuer", "sec-unavailable", "sec-response-too-large",
      "invalid-sec-data", "wrong-issuer"];
    const code = known.includes(error?.message) ? error.message : "sec-fetch-failed";
    process.stdout.write("FINANCE_SEC_ERROR " + code + "\n");
    process.exitCode = 1;
  }
}
