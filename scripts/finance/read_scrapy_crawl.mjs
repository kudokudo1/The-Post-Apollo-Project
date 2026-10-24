// FinanceW Research M1: read and normalize one local Scrapy export.
// No crawler launch, network access, write path, or live financial records.
import { homedir } from "node:os";
import { join } from "node:path";
import { lstat, readFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";

export const CRAWL_FILE = join(
  homedir(), ".local", "share", "post-apollo", "finance-crawler", "crawl-records.json"
);
const MAX_BYTES = 262144;
const MAX_PAGES = 6;
const EXPECTED_HOST = "quotes.toscrape.com";

function cleanText(value, max) {
  return typeof value === "string" ? value.trim().slice(0, max) : "";
}

function approvedUrl(value) {
  if (typeof value !== "string" || value.length > 400) return null;
  try {
    const u = new URL(value);
    if (u.protocol !== "https:" || u.hostname !== EXPECTED_HOST
        || u.username || u.password || u.port) return null;
    u.hash = "";
    return u.href;
  } catch (error) {
    return null;
  }
}

export function normalizePage(record) {
  if (!record || typeof record !== "object"
      || record.schemaVersion !== 1 || record.source !== "finance-demo-scrapy"
      || record.readOnly !== true) return null;
  const url = approvedUrl(record.url);
  const title = cleanText(record.title, 150);
  const observedAt = cleanText(record.observedAt, 45);
  if (!url || !title || !Number.isFinite(Date.parse(observedAt))) return null;
  if (!Array.isArray(record.links) || record.links.length > 32
      || !Array.isArray(record.snippets) || record.snippets.length > 3) return null;

  const unique = new Set();
  for (const raw of record.links) {
    const link = approvedUrl(raw);
    if (link) unique.add(link);
  }
  const snippets = record.snippets.map(s => cleanText(s, 240)).filter(Boolean);
  return {
    url, title, observedAt,
    snippet: snippets.join(" ").slice(0, 450),
    links: Array.from(unique).slice(0, 32),
  };
}

export function normalizeCrawl(raw) {
  if (!Array.isArray(raw) || raw.length > 6) throw new Error("invalid-export");
  const pages = [], seen = new Set();
  for (const record of raw) {
    const page = normalizePage(record);
    if (!page) throw new Error("invalid-page");
    if (seen.has(page.url)) throw new Error("duplicate-page");
    seen.add(page.url);
    pages.push(page);
  }
  return {
    schemaVersion: 1, source: "finance-demo-scrapy", readOnly: true,
    status: pages.length ? "snapshot" : "empty",
    pageCount: pages.length,
    linkCount: pages.reduce((n, page) => n + page.links.length, 0),
    pages
  };
}

export async function readCrawl(file = CRAWL_FILE) {
  let st;
  try {
    st = await lstat(file);
  } catch (error) {
    if (error && error.code === "ENOENT") throw new Error("missing-export");
    throw new Error("unreadable-export");
  }
  if (!st.isFile() || st.isSymbolicLink() || st.size < 2 || st.size > MAX_BYTES)
    throw new Error("unsafe-export");
  const value = JSON.parse(await readFile(file, "utf8"));
  return normalizeCrawl(value);
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    process.stdout.write("FINANCE_CRAWL_SNAPSHOT " + JSON.stringify(await readCrawl()) + "\n");
  } catch (error) {
    const kind = ["missing-export", "unsafe-export", "invalid-export", "invalid-page",
                  "duplicate-page"].includes(error.message) ? error.message : "unreadable-export";
    process.stdout.write("FINANCE_CRAWL_ERROR " + kind + "\n");
    process.exitCode = 1;
  }
}
