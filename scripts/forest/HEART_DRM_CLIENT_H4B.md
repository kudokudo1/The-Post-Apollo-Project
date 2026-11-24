# Heart H4b // AMD DRM client observation

DOC 1F · DEVELOPMENT ACTIVE · PRODUCTION HOLD.

## IMPLEMENTATION
Explicit existing cgroup, same-effective-UID PID and numeric DRM fd only.
Reuse I6 process identity/membership and I5 bounded reads. Check selected
fd character device major 226; read kernel fdinfo driver, PCI address,
client ID and resident VRAM. Accept standard drm-resident-vram and the
legacy AMD drm-memory-vram alias, refuse disagreement or missing metrics.
Cross-check device identity via sysfs character-device link and PCI path.
Hold process/group/device descriptors, sample client and device counters
twice, compare observable identities, boot and mount. No device open,
ioctl, enumeration of arbitrary processes or fd discovery, privilege
escalation, environment, command line, model load or inference.

Report one client's sampled resident VRAM separately from total device
VRAM and sampled device headroom. Do not add client bytes to used device
bytes or sum shared memory across clients. No public PCI/PID/fd/client IDs.
Reject missing or malformed data; no unknown-to-zero conversion.

Kernel reference:
- https://docs.kernel.org/gpu/drm-usage-stats.html
- https://docs.kernel.org/gpu/amdgpu/driver-misc.html

## HOW TO USE
After review and merge, developer-only diagnostic for an explicitly
established same-owner process/group and existing DRM fd. Use the
observe command with --cgroup, --pid and --fd. Do not run as root or
change service credentials to obtain access. System-owned Ollama is
outside this same-UID observer's ordinary operator scope.

## VERIFY
    python3 -B -m unittest discover -s tests/forest -p 'test_heart_drm_client_h4b.py' -v
Includes actual Linux non-DRM fd refusal and synthetic identity adapters
with real disposable descriptor reads. No actual AMD GPU trial.

## WATCH OUT FOR
A DRM client can share buffers or descriptors with other processes.
Client residency is not unique physical memory, exact model weight
allocation, complete GPU workload or verified Ollama device binding.
Other GPU APIs, unsupported drivers and distinct service UID remain
unobserved. Device-wide headroom is not allocatable capacity. Metadata
rechecks do not pin the remote open file description, exclude ABA,
or provide an atomic sample. One-second completed sampling window is
not a hard I/O deadline. No safe start, resource grant or production
permission. Do not derive P1 requirements/availability directly.

## NEXT / DECISIONS
AMD-only initial diagnostic, one explicitly selected client; no claim
of exhaustive attribution. Need Runtime-owned actual provider/runner
mapping and enforceable settings, conservative model demand and
operator-approved public trial. Independent Nurse2F review required.
