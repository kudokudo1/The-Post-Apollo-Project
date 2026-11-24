# Forest I4 // Passive Linux process observations

PATIENT: The-Post-Apollo-Project · ROOM: Spirit measurement infrastructure
ROLE: Forest Core DOC, external Hospital-compatible · PRODUCTION HOLD.

## IMPLEMENTATION
Operator continued from I3 #2435, still open at base inspection; I4 is
independent of its unmerged code. I1 #2426 and I2 #2430 merged but their
independent reviews remain outstanding. I4 adds a bounded, opt-in,
read-only Linux diagnostic of one existing numeric PID. No new service,
process launch/stop, inference request, provider/network call, protected
storage access or persistent file write in the observer.

Read fixed /proc/PID/stat and status using a pinned directory descriptor
with relative no-follow opens, strict byte bounds and start-tick checks
within and across samples. Parse only memory counters (RSS, lifetime HWM,
anonymous/file/shared RSS, reported swap), user/system CPU ticks and
thread count. No process search, arbitrary path, command line, environment,
exe read, prompt or private contents. PID and raw process identity are not
printed. At most 20 samples, 100–500 ms interval, 9.5 seconds scheduled
sleep maximum (kernel scheduling/read time can add delay). On process
exit, malformed counters, changed observed instance or interrupt, discard
partial aggregate. Unknown RSS prevents a sampled maximum. Sampled RSS
max and increase are separate from kernel lifetime HWM; CPU ticks are
not free CPUs. Missing fields remain null.

## HOW TO USE
After source review and operator merge/acceptance, from repository root,
a local operator may explicitly select an already-running permitted PID:

    python3 -B scripts/forest/process_observation_i4.py observe --pid "$PID" --samples 5 --interval-ms 250

Set PID to the exact existing process to inspect, not an inferred model
runner. No sudo or privilege escalation; unavailable measurements stay
unavailable. Do not launch a workload just to produce a result.
I4 does not discover Ollama runner PIDs or identify a model from a PID.
Existing P0/P2C continue separate host and device-wide diagnostics.

## VERIFY
python3 -B -m unittest discover -s tests/forest -p 'test_process_observation_i4.py' -v

19 focused tests including live Linux self and disposable child with
24 MiB allocation/touched pages, exited process refusal and strict
negative cases. Existing P0/P2C/I2/P1 regression suites run separately.
The child is launched only in the test harness, never by observer.
Native Linux CI is not Fedora workstation acceptance or inference.

## WATCH OUT FOR
Linux VmRSS/VmHWM are approximate, per-process and may include shared
pages. RSS is not PSS, cgroup aggregate, total runtime memory or private
allocation. HWM is lifetime, not trial-specific peak. Sampled maxima
can miss between-sample peaks; elapsed time is observed sample window,
not inference timing. CPU ticks measure cumulative work, not a required
thread budget. Proc descriptor/start-tick consistency is not authenticated
executable identity, exact model/runner mapping, namespace or exec proof.
No verified complete workload coverage, no model or accelerator
attribution, no calibration requirement or available capacity derived.
Do not feed this output automatically into I3/P1 requirements.
Shared GPU/cgroup/runner lifecycle observations, independently verified
identity and actual measurement methodology remain future integration.
ForestW context/cache request #7132402465 accepted as design dependency:
requested context, reported effective limit, consumed tokens, reserved
capacity, cache state/ownership and durable Forest knowledge remain
separate. No automatic cache eviction, context resize or model unload.

## NEXT / DECISIONS
Independent review and operator merge. Then bound exact process-group /
cgroup memory observations and accelerator measurement scope, evaluate
whether actual runtime/runner identity can be independently established
without new privilege. Actual workload calibration requires separately
reviewed conservative preflight, precise workload and explicit approval.
No native inference, workstation change, live authority or new scheduler.
