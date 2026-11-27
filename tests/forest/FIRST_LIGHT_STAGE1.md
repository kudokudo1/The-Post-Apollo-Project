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
release-assets.githubusercontent.com fixed release asset path prefix,
or exact candidate R2 host and digest path for a blob. Public historical
redirect evidence: github.com/ollama/ollama/issues/11428 and /18716.
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
size/digest before system zstd decompression. Streaming bounded tar
regular-file extraction only, no executable mode, no devices/hardlinks,
no path traversal; internal symlink descriptors validated but never
materialized. Per-file size/hash inventory derived; publish only fixed
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
