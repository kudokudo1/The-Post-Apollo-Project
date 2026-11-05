# 🏥 Company Network M15 // Single-PID native host bridge

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Company Network vector renderer integration
PROVIDER // OPEN AI // CHATGPT
CONNECTION // External / Hospital-compatible; no live registration
ASSIGNMENT // Prepare reversible M13 VECTOR VIEW host launch against M14's existing Fedora build
PHASE // Draft; host ABI and launch unverified
SCOPE // Native bridge, opt-in installer, synthetic tests, controller status labels only

## IMPLEMENTATION

The operator built MapLibre Native Qt 3.0 in Fedora 44 Toolbox using Qt 6.11.2, passed the upstream three-test suite, and visually verified Qt Widgets and the Company styled-online map. M14 merged. This does **not** prove Qt 6.11.2 is present on the Silverblue host.

M13's CompanyVectorSidecarLaunch.py checks an exact owner-only entry point at ~/.local/libexec/post-apollo/company-vector-probe, then uses execv(). M15 supplies an **uninstalled** CompanyVectorHostBridge.py for that path. It validates owner-only non-symlinked source binaries/libraries, checks host Qt6Core/Quick/Location/Positioning 6.11.2 via pkg-config, uses ldd to check executable dependencies, then calls os.execve() to replace its own PID with the native Qt Company executable. No Toolbox process wrapper, daemon, detached child, or Quickshell graphics changes.

Allowed arguments: none (offline synthetic), --styled-online (explicit online), --probe (read-only). Unknown arguments, missing Qt, or unsafe paths fail closed. The installer script defaults to read-only check. Explicit install atomically publishes an owner-only 0700 script and refuses overwrite; explicit remove deletes only a byte-identical bridge. M13 controller now recognizes host runtime refusal statuses.

## HOW TO USE

After M15 files are safely available in the local checkout without disturbing uncommitted work, run read-only:

- python3 ~/.config/quickshell/experiments/company-vector-qt/install_host_bridge_m15.py check
- python3 ~/.config/quickshell/experiments/company-vector-qt/CompanyVectorHostBridge.py --probe

Only after specific local installation approval, run:

- python3 ~/.config/quickshell/experiments/company-vector-qt/install_host_bridge_m15.py install

Then Company → Coverage → VECTOR VIEW → OFFLINE TEST or ONLINE STREETS → CLOSE VECTOR. Rollback after specific approval:

- python3 ~/.config/quickshell/experiments/company-vector-qt/install_host_bridge_m15.py remove

No local file installation or Quickshell restart was performed in this conversation.

## VERIFY

- GitHub M13 launcher/controller and M14 helper inspected on main.
- Nine fake-path tests passed under an unprivileged user in an isolated container. No actual graphics process was launched by tests.
- GitHub M15 CI is pending.
- Real host Qt ABI, Wayland focus/geometry, SIGTERM, native sidecar launch, status timing and Stage Director containment are unverified.

## WATCH OUT FOR

- Host Qt does not necessarily equal Toolbox Qt. Without matching Qt 6.11.2 public development metadata on the host, return HOST_QT_UNVERIFIED. Never silently install host packages or disable the check.
- Qt private modules are version coupled. pkg-config plus ldd are not sufficient for native acceptance, and Stage Director is a separate workstream.
- Existing Company map, old streets and hub storage remain untouched. Online OpenFreeMap requests disclose viewport and IP only after explicit online consent.
- Do not copy the upstream Qt Widgets demo over the Company binary.

## CHECKLIST

- [x] M14 source and visual evidence reviewed
- [x] Fixed-path M13 semantics checked
- [x] Direct-exec host bridge and owner-only installer implemented
- [x] Nine fake-environment tests passed
- [ ] M15 GitHub CI and draft review
- [ ] Read-only Fedora host ABI preflight
- [ ] Specific operator authorization for local installation
- [ ] Test Company open/close, visibility, and no orphan
- [ ] Stage Director handoff
- [ ] Operator final acceptance

## NEXT

Verify GitHub M15 checks. Then read-only test the actual Fedora host Qt versions. If not compatible, keep the feature uninstalled and prepare a separately authorized isolated runtime integration rather than bypassing ABI checks.

## DECISIONS

Preserve M13 trust, explicit online consent, direct Process lifecycle, synthetic offline default and the existing Company map. Do not merge/activate or install locally without the required next authorization.
