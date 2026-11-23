// FinanceW Research M5: pure, read-only evidence metadata health diagnostics.
// This module never reads a file, opens a URL, verifies a site, or changes a record.
// Source labels and local "reviewed" flags are NOT proof of authenticated provenance.
import { validateCollection } from "./research_investigations.mjs";

const MAX_FINDINGS = 100;
const DAY_MS = 86400000;
const isoUtc = value => typeof value === "string"
  && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?Z$/.test(value)
  && Number.isFinite(Date.parse(value));
const own = (value,key) => Object.prototype.hasOwnProperty.call(value,key);
const exact = (value, keys) => value && typeof value === "object"
  && !Array.isArray(value) && Object.keys(value).length === keys.length
  && keys.every(k=>own(value,k));

export class AuditRefusal extends Error {}
function refuse(code) { throw new AuditRefusal(code); }
function validSnapshot(doc) {
  return exact(doc,["schemaVersion","revision","investigations"])
    && doc.schemaVersion === 1
    && Number.isSafeInteger(doc.revision) && doc.revision >= 0
    && doc.revision < Number.MAX_SAFE_INTEGER
    && validateCollection(doc.investigations);
}

// Validated date is provided by the caller: no ambient Date.now() or auto refresh.
// Counts are complete; finding details are capped to avoid huge diagnostic output.
// Details deliberately contain identifiers and codes only, not sensitive research text.
export function auditResearchSnapshot(doc, {asOf, staleDays = 180} = {}) {
  if (!validSnapshot(doc)) refuse("INVALID_RESEARCH_SNAPSHOT");
  if (!isoUtc(asOf) || !Number.isSafeInteger(staleDays)
      || staleDays < 1 || staleDays > 3650) refuse("INVALID_AUDIT_OPTIONS");
  const now = Date.parse(asOf);
  const metrics = {
    caseCount:doc.investigations.length,
    evidenceCount:0,
    emptyCases:0,
    manualEvidence:0,
    manuallyMarkedReviewed:0,
    manualReviewPending:0,
    declaredSecEvidence:0,
    demoEvidence:0,
    reusedUrlsWithinCase:0,
    oldObservations:0,
    futureObservations:0,
    provenanceVerifiedByAudit:0
  };
  const findings=[];
  let findingsTotal=0;
  function flag(code, investigationId, evidenceId=null) {
    findingsTotal++;
    if (findings.length < MAX_FINDINGS)
      findings.push({code, investigationId, evidenceId});
  }

  for (const item of doc.investigations) {
    if (item.evidence.length === 0) {
      metrics.emptyCases++;
      flag("CASE_HAS_NO_EVIDENCE",item.id);
    }
    // Reusing a citation in a *different* case can be legitimate.
    const seenUrls=new Set();
    for (const evidence of item.evidence) {
      metrics.evidenceCount++;
      const url=new URL(evidence.url).href; // M1 has already validated HTTPS.
      if (seenUrls.has(url)) {
        metrics.reusedUrlsWithinCase++;
        flag("REPEATED_SOURCE_URL_IN_CASE",item.id,evidence.id);
      }
      seenUrls.add(url);

      const observed=Date.parse(evidence.observedAt);
      if (observed > now) {
        metrics.futureObservations++;
        flag("OBSERVATION_IN_FUTURE",item.id,evidence.id);
      } else if (now-observed > staleDays*DAY_MS) {
        metrics.oldObservations++;
        flag("OBSERVATION_OLDER_THAN_WINDOW",item.id,evidence.id);
      }

      if (evidence.source === "manual") {
        metrics.manualEvidence++;
        if (evidence.reviewed === true) {
          // Self-declared local review only; no remote provenance established.
          metrics.manuallyMarkedReviewed++;
        } else {
          metrics.manualReviewPending++;
          flag("MANUAL_REVIEW_PENDING",item.id,evidence.id);
        }
      } else if (evidence.source === "sec-edgar-submissions") {
        // Describes the record's label; no SEC fetching or URL verification.
        metrics.declaredSecEvidence++;
      } else if (evidence.source === "finance-demo-scrapy") {
        metrics.demoEvidence++;
        flag("DEMO_SOURCE_NOT_FINANCIAL_EVIDENCE",item.id,evidence.id);
      }
    }
  }
  return {
    schemaVersion:1,
    sourceRevision:doc.revision,
    assessedAt:asOf,
    staleDays,
    metrics,
    findingsTotal,
    findings,
    omittedFindings:findingsTotal-findings.length,
    status:findingsTotal ? "local-flags-present" : "no-local-flags",
    notice:"METADATA CHECK ONLY // NO WEB FETCH // NO SOURCE AUTHENTICATION"
  };
}
