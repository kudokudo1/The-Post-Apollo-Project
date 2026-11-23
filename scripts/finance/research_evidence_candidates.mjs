// FinanceW Research M6: transform EXISTING bounded SEC/crawl snapshots into
// review candidates. No provider call, disk access, account identity or writer.
// An SEC index entry is NOT document inspection. The demo crawl is NEVER
// eligible for direct attachment to an investigation.
import { validEvidence, validInvestigation } from "./research_investigations.mjs";

export class CandidateRefusal extends Error {}
const refuse = code => { throw new CandidateRefusal(code); };
const SEC_ISSUERS = Object.freeze({
  "0000320193": "Apple",
  "0000789019": "Microsoft",
  "0001045810": "NVIDIA"
});
const FORMS = new Set([
  "8-K","8-K/A","4","4/A","SC 13D","SC 13D/A",
  "SC 13G","SC 13G/A","10-Q","10-Q/A","10-K","10-K/A"
]);
const ACCESSION = /^\d{10}-\d{2}-\d{6}$/;
const DOCUMENT = /^(?:xslF345X\d{2}\/)?[A-Za-z0-9][A-Za-z0-9_.-]{0,170}$/;
const DATE = /^\d{4}-\d{2}-\d{2}$/;
const UTC = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?Z$/;
const isObj = v => v !== null && typeof v === "object" && !Array.isArray(v);
const validUtc = v => typeof v === "string" && UTC.test(v)
  && !Number.isNaN(Date.parse(v));
// Scrapy's Python datetime.now(timezone.utc).isoformat() emits
// e.g. "2026-11-23T14:42:00.123456+00:00", while the SEC read bridge
// emits JS Date.toISOString() with "Z" and millisecond precision.
// Both are valid timestamp formats; neither is an authenticated source.
const CRAWL_ISO = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})$/;
const validCrawlTime = v => typeof v === "string" && CRAWL_ISO.test(v)
  && !Number.isNaN(Date.parse(v));
function safeHttps(value,host,max=1000) {
  if(typeof value!=="string" || value.length>max) return null;
  try {
    const u=new URL(value);
    if(u.protocol!=="https:" || u.hostname!==host || u.port
      || u.username || u.password || u.hash || u.search)
      return null;
    return u.href;
  } catch { return null; }
}
function validateSec(snapshot, selectedCik) {
  if(!isObj(snapshot) || snapshot.schemaVersion!==1
      || snapshot.source!=="sec-edgar-submissions" || snapshot.readOnly!==true
      || !Object.hasOwn(SEC_ISSUERS,snapshot.cik)
      || snapshot.issuer!==SEC_ISSUERS[snapshot.cik]
      || (selectedCik!==undefined && selectedCik!==snapshot.cik)
      || !validUtc(snapshot.retrievedAt)
      || !Array.isArray(snapshot.filings) || snapshot.filings.length>30)
    refuse("INVALID_SEC_SNAPSHOT");
  const seen=new Set();
  for(const filing of snapshot.filings) {
    if(!isObj(filing) || !ACCESSION.test(filing.accession)
        || !FORMS.has(filing.form) || !DATE.test(filing.filedAt)
        || !DOCUMENT.test(filing.primaryDocument)
        || typeof filing.category!=="string" || filing.category.length>80
        || !Array.isArray(filing.items) || filing.items.length>12
        || !filing.items.every(s=>typeof s==="string" && /^[1-9]\.\d{2}$/.test(s))
        || (filing.acceptedAt!==null && typeof filing.acceptedAt!=="string")
        || seen.has(filing.accession))
      refuse("INVALID_SEC_FILING");
    const expected="https://www.sec.gov/Archives/edgar/data/"
      +String(Number(snapshot.cik))+"/"
      +filing.accession.replaceAll("-","")+"/"+filing.primaryDocument;
    if(filing.documentUrl!==expected
        || safeHttps(filing.documentUrl,"www.sec.gov")!==filing.documentUrl)
      refuse("INVALID_SEC_URL");
    seen.add(filing.accession);
  }
}
function validateCrawl(snapshot) {
  if(!isObj(snapshot) || snapshot.schemaVersion!==1
    || snapshot.source!=="finance-demo-scrapy" || snapshot.readOnly!==true
    || !Array.isArray(snapshot.pages) || snapshot.pages.length>6
    || snapshot.pageCount!==snapshot.pages.length
    || !Number.isSafeInteger(snapshot.linkCount)
    || snapshot.linkCount<0 || snapshot.linkCount>192)
    refuse("INVALID_DEMO_SNAPSHOT");
  let linkCount=0;
  const seen=new Set();
  for(const page of snapshot.pages) {
    if(!isObj(page) || safeHttps(page.url,"quotes.toscrape.com")!==page.url
      || typeof page.title!=="string" || page.title.trim()!==page.title
      || page.title.length===0 || page.title.length>150
      || typeof page.snippet!=="string" || page.snippet.length>450
      || !validCrawlTime(page.observedAt) || !Array.isArray(page.links)
      || page.links.length>32 || seen.has(page.url)
      || !page.links.every(link=>
        safeHttps(link,"quotes.toscrape.com")===link))
      refuse("INVALID_DEMO_PAGE");
    linkCount+=page.links.length;
    seen.add(page.url);
  }
  if(linkCount!==snapshot.linkCount) refuse("INVALID_DEMO_COUNT");
}
function secCandidates(snapshot) {
  validateSec(snapshot);
  return snapshot.filings.map(filing=>{
    const title=(snapshot.issuer+" // "+filing.form+" // "+filing.filedAt).slice(0,160);
    return {
      key:"sec:"+snapshot.cik+":"+filing.accession,
      kind:"sec-index",
      sourceLabel:"SEC EDGAR // INDEX",
      title,
      summary:"SEC submissions index lists "+filing.form+" filed "
        +filing.filedAt+". Filing contents have not been inspected by this preview.",
      url:filing.documentUrl,
      observedAt:snapshot.retrievedAt,
      eligibleForDraft:true,
      reviewed:false,
      authenticatedProvenance:false,
      notice:"REVIEW OFFICIAL FILING BEFORE CITING // NO AUTO SAVE"
    };
  });
}
function demoCandidates(snapshot) {
  validateCrawl(snapshot);
  return snapshot.pages.map((page,i)=>({
    key:"demo:"+i+":"+page.url,
    kind:"demo-crawl",
    sourceLabel:"DEMO CRAWL // SAVED SNAPSHOT",
    title:page.title,
    summary:"DEMONSTRATION PAGE ONLY // NOT FINANCIAL EVIDENCE",
    url:page.url,
    observedAt:page.observedAt,
    eligibleForDraft:false,
    reviewed:false,
    authenticatedProvenance:false,
    notice:"DEMO SOURCE // DIRECT RESEARCH ATTACHMENT BLOCKED"
  }));
}
export function previewEvidenceCandidates({
  secSnapshot=null,crawlSnapshot=null,selectedCik=undefined
} = {}) {
  // Missing sources are explicitly absent, not misrepresented as empty success.
  if(selectedCik!==undefined
      && (!Object.hasOwn(SEC_ISSUERS,selectedCik) || secSnapshot===null))
    refuse("INVALID_ISSUER_SELECTION");
  if(secSnapshot!==null) validateSec(secSnapshot,selectedCik);
  if(crawlSnapshot!==null) validateCrawl(crawlSnapshot);
  const sec=secSnapshot===null?[]:secCandidates(secSnapshot);
  const demo=crawlSnapshot===null?[]:demoCandidates(crawlSnapshot);
  return {
    schemaVersion:1,
    readOnly:true,
    secPresent:secSnapshot!==null,
    demoPresent:crawlSnapshot!==null,
    counts:{sec:sec.length,demo:demo.length,attachablePreview:sec.length},
    candidates:[...sec,...demo],
    notice:"PREVIEW ONLY // NO AUTOMATIC SOURCE VERIFICATION OR STORAGE"
  };
}
export function prepareCandidateAttachDraft(candidate,investigation) {
  // This prepares a form value ONLY. It never grants permission or sends it.
  if(!isObj(candidate) || candidate.kind!=="sec-index"
    || candidate.eligibleForDraft!==true || candidate.reviewed!==false
    || candidate.authenticatedProvenance!==false
    || typeof candidate.key!=="string"
    || !/^sec:\d{10}:\d{10}-\d{2}-\d{6}$/.test(candidate.key)
    || typeof candidate.title!=="string"
    || typeof candidate.summary!=="string"
    || typeof candidate.url!=="string"
    || !validUtc(candidate.observedAt) || !validInvestigation(investigation))
    refuse("INVALID_CANDIDATE_DRAFT");
  const [_,cik,accession]=candidate.key.split(":");
  const expectedPrefix="https://www.sec.gov/Archives/edgar/data/"
    +String(Number(cik))+"/"+accession.replaceAll("-","")+"/";
  if(!Object.hasOwn(SEC_ISSUERS,cik)
    || !candidate.url.startsWith(expectedPrefix)
    || safeHttps(candidate.url,"www.sec.gov")!==candidate.url
    || !validEvidence({
      id:"preview",source:"manual",title:candidate.title,
      summary:candidate.summary,url:candidate.url,
      observedAt:candidate.observedAt,reviewed:false
    }) || investigation.evidence.length>=40
    || investigation.evidence.some(e=>e.url===candidate.url))
    refuse("CANDIDATE_REVIEW_REQUIRED");
  return {
    action:"attach",investigationId:investigation.id,
    title:candidate.title,summary:candidate.summary,url:candidate.url
  };
}
