# First Light manifest-only evidence proposal (offline implementation)

Both Stage 1 manual staging intents remain spent. Nurse 2F is sole
operator-facing dispatch coordinator (#7224114032, #7224126906).
Second run 46039275672 failed at BLOB_DESCRIPTOR after pinned manifest
fetch and validation; the exact rejected field remains unknown.
Stage1b #3113 only improves fixed refusal categories, not acceptance.

## Proposed evidence route — NOT authorized or implemented

A separate reviewed public metadata-only operation, not the Stage 1
workflow or a third staging attempt. Exactly one HTTPS GET to the
existing registry manifest URL `https://registry.ollama.ai/v2/library/granite3.3/manifests/2b`.
Fixed request headers, no redirects, credentials, cookies, proxy, URL
input, retry, model blobs or release archive. Hosted-only, clean
environment/null stdin/closed nonstdio descriptors, fixed timeout and
bounded transfer; refuse unknown, non-200, compressed content, invalid
length or >65536 bytes. Hold the bounded body in memory; compare the
unchanged raw SHA256 07bd1f170855240f9e162bf54ea494a8bc1c73d8cbd1365d7fccbeb7d2504947
before parsing. No raw body, paths, digests, arbitrary fields or URLs
in output. No file persistence, artifact publishing, provider startup
or model invocation. No adapter, manual workflow, dispatch permission
or actual retrieval is added in this patch. Nurse/Spirit/Heart review
the specific method and future execution separately.

## Offline evidence module

`first_light_manifest_evidence.classify(raw)` accepts bytes only, checks
the existing pin and cap, rejects duplicate JSON keys, nonstandard
constants and exponent overflow to nonfinite floats before invoking
the unchanged strict Stage 1 parser to report
its fixed first refusal category. Its independent observation of a
bounded config and up to 16 layers reports only fixed role labels,
required-key presence, counts of unknown keys, from/name value-type
classes (not content), digest-format boolean, fixed size class,
duplicate-valid-digest flag, and bounded size aggregate and cap flags.
Unknown media values never appear. No source or descriptor values
authorize requests. These roles are predetermined diagnostic labels,
not an acceptance allowlist or manifest qualification. Aggregate is
null if any size is invalid. No individual size/digest or metadata
string is emitted. This is classification, not a policy relaxation.

Tests exercise synthetic bytes with patched fixture SHA only, pin-first
refusal before JSON, optional/unknown fields including urls, unknown
media, strict parser refusal, invalid sizes/digests, aggregate cap,
duplicate keys, explicit nonfinite literals and exponent overflow (including
nested metadata), finite noninteger refusal, shape/size limits and no
file/network I/O. The offline
workflow executes only these synthetic tests. Actual pinned bytes are
not available; no evidence of exact rejected field or manifest role
structure yet. Future actual evidence adapter must be separately
reviewed; no need to rerun original Stage 1 to learn the predicate.
