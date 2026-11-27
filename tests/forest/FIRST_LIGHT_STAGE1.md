# First Light Stage 1 // hosted public artifact feasibility

Operator scope authorized in Hospital #2161 7220022441, Heart 7219990494.
**Exact completed job review before any dispatch.** No native inference,
provider startup, workstation/self-hosted access, protected data or production.

Manual-only workflow forest-first-light-stage1.yml on reviewed main,
public repo, standard ubuntu-24.04 x64, first attempt only; one bounded job,
15 minute Actions limit and 720s helper outer timeout, 660s internal
deadline. One dispatch only under this authorization; concurrency
serializes jobs but is not a durable once-only grant. No dispatch by
this PR, no schedule/push/PR acquisition, no rerun or automatic retry.
Before dispatch verify exact integrated revision, transitive code and
checkout action pin; avoid a main revision race. If reviewed revision
cannot be selected exactly, do not dispatch. Required reviewed_sha input
must equal github.sha; mismatch skips the acquisition job. This is a
revision check, not an approval verifier. No secrets or write token
to verifier; contents read for pinned checkout, persist-credentials false.
Clean env, closed extra FDs, no provider or downloaded executable run.
Standard GitHub public runners advertised free, estimated one job up to
15 runner minutes and <=2.99 GB public artifact content (plus manifest,
TLS/HTTP and checkout overhead), not a confirmed cost or speed guarantee.

Fixed initial sources: GitHub Ollama v0.32.14 linux-amd64 release archive
1421191399 bytes; registry.ollama.ai/v2/library/granite3.3/manifests/2b
and digest-addressed blobs under that repository from the verified raw
manifest. Exact SHA256 pins in helper. One HTTPS redirect only:
release-assets.githubusercontent.com exact upstream repository 658928958
namespace and UUID-shaped path, signed filename ollama-linux-amd64.tar.zst,
or exact candidate R2 host and digest path for a blob. Public historical
redirect evidence: github.com/ollama/ollama/issues/11428 and /18716.
Release API metadata: https://api.github.com/repos/ollama/ollama/releases/assets/517039292
(release 371138535, asset 517039292, exact name/size/digest); the actual
opaque CDN UUID is not available in that metadata and is NOT claimed pinned.
Actual redirect/auth behavior not verified; unexpected redirect or
challenge refuses, no bearer token exchange, broad host fallback or retry.
This is direct TLS client destination restriction, not independent
kernel-enforced network isolation. Spirit must review actual source
policy and whether runner scope is eligible before dispatch. If provider
needs different acquisition endpoints, return HOLD rather than widening.

Actual runner preflight: hosted environment/OS/arch/image metadata,
read-only visible cgroup-v2 non-root ancestry, unified mount root and memory/disk availability, no
extra FDs, owned 0700 empty temp scope, >= archive + 1.56GB model cap +
6GiB extraction cap + 2GiB free reserve. Refuse unknowns; environment
metadata and visible ancestry are feasibility observations, not independent
host attestation or preventive model capacity proof. Standard runner
advertised 14GB disk; actual free space can be less. No cleanup of other
runner content. Exact manifest digest before blobs, every config/layer
byte/size/digest verified, no external descriptor URLs. Archive exact
size/digest before system zstd decompression. Bounded seekable decompressed tar spool replaces regular-file extraction;
no member materialized. Read regular member bytes for hashes, reject
unsupported types, traversal, repeated normalized names and invalid links.
Check physical end offset for at least two zero terminator blocks and all
remaining bounded padding zero, including buffered bytes. No extra disk
allocation beyond the 6GiB decompressed cap. Per-file size/hash inventory derived; publish only fixed
aggregate digest/counts, main binary hash and aggregate public runner
measurements in job log. No upload. Per-member hashes are derived, not
independent expected binary pins; no materialized runtime layout or
model demand/placement claim. Strict parser may refuse valid archive
features not supported here. Temporary scope removed by owned trap;
runner death/timeout cleanup not independently witnessed, no secure
erasure claim. Refuse unknown or mismatch, no partial success.

Offline tests included in manual job before acquisition. They exercise
fixed source/redirect rules, manifest pins and descriptor limits, safe
archive member hashing and unsafe path/link/device refusals; no network.
No actual staging, inference, resource admission, model trial, source
authentication or native release claimed. Stage 2 requires separate
operator approval and independent evidence.

## Corrected source / review limits

Trusted public runner acquisition requires exact independent Spirit/Nurse
review of GitHub-hosted eligibility and the reviewed client policy. The
runtime process environment is scrubbed and no token is passed; no claim
of independently verified absence of every runner credential or network
route. The actual CDN UUID and anonymous registry redirect availability
remain unresolved until separately reviewed; do not dispatch if the
source policy cannot be accepted. No extra source fetch or broadened
allowlist. Template/config role evidence is not separately emitted; use
the same verified manifest for later authorized qualification. Offline
PR/push workflow runs synthetic verifier tests only, no acquisition.


## Original attempt and FD launcher correction

Hospital #7222390290 single intent is SPENT. Original manual run
46027506290 attempt 1, exact 4971212b, raw job 140602601999: six offline
tests pass; STAGE1_HOLD INHERITED_FD exit 2 before any artifact fetch.
No FD target/type known, no credential exposure inferred. Never retry
or rerun that exercise. Any second staging exercise requires distinct
operator authorization after corrected exact review and fresh custody.

Preserve the existing clean environment, null stdin, GNU timeout
process-group boundary (720s + 10s), job deadline and all artifact/source/
disk policies. Add fixed first_light_stage1_launcher.py between timeout
and verifier. It requires the same exact environment key set and fixed
PATH/LANG, validates null stdin and open stdout/stderr, closes every
actual nonstdio FD in its single-threaded process, verifies no extra FD
remains, then execve the fixed reviewed sibling with same PID/group,
not another worker or an arbitrary executable. No FD target, value,
credential or untrusted error detail logged. Original verifier independently
checks extra FDs again before acquisition; only EBADF for the already
closed enumeration FD is tolerated, unknown errors refuse. No change
to preflight ordering or acquisition authority. This is descriptor
hygiene, not full credential/host/egress isolation.

Offline-only workflow runs actual fixed launcher with --offline-witness
under timeout and clean env/null stdin; this execs only the fixed test
entrypoint which calls the real verifier FD guard, never staging.
Tests pass actual inheritable file, pipe, socket and high FD through
raw and corrected exec, assert raw refusal, no inherited FD in corrected
child, original parent descriptors remain usable; extra environment/
nonnull stdin refuse. --offline-wait is a fixed no-acquisition witness
for timeout exit 124 and original process reap, not a stage mode.
No offline path calls stage.run/fetch, no actual artifact download
or native provider. The original timeout behavior is unchanged;
offline witness does not prove cleanup under runner death or actual
acquisition capacity. Exact Spirit/Heart/Nurse correction reviews and
a separate operator decision required before a new staging exercise.


## Second original attempt: manifest descriptor refusal

Hospital #7224005423 second intent SPENT; run 46039275672 attempt 1,
exact a1b697191e939a3483028ac8c0ebdce9773b69e7; raw 140642552500:
9/9 offline PASS, STAGE1_HOLD BLOB_DESCRIPTOR, exit 2. FD and other
preflight checks precede acquisition. The fixed manifest SHA and size
check precede descriptor parsing. For this accepted flow, blob targets
are derived only from validated digest strings, so the observed code
is consistent with pinned manifest descriptor predicate failure before
the blob loop. Raw manifest structure was not retained in job output;
do not assert an exact rejected field. Zero uploaded artifacts does not
mean zero network acquisition. Both prior intents remain spent.

Ollama v0.32.14 manifest/layer.go documents optional from and name
fields; a public secondary example of granite3.3:2b locally stored
manifest includes from. These are plausible explanations, not evidence
of the exact pinned registry bytes. No schema relaxation based on this
example. Recover exact public pinned descriptor metadata via separately
reviewed read-only evidence; verify the existing SHA before deciding
a narrow policy. This diagnostic-only change preserves every acceptance
predicate, fixed source and size limit. Fixed refusal classes distinguish
descriptor object/keys, media type, digest format, size, and redirect
digest; never print raw keys, values, paths, digests or signed URLs.
Synthetic offline fixtures exercise optional fields, URL override,
missing keys, wrong types, invalid digest, zero/oversized sizes and
pin-first refusal. No acquisition in CI. No additional staging exercise,
retry or inference authorized; Nurse 2F sole operator-facing dispatch
coordinator. Runtime owns diagnosis/source, Heart evidence, Spirit
schema/security review. See Nurse incident #7224114032/#7224126906.
