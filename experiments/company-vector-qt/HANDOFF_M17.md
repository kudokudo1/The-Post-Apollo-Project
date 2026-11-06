# 🏥 Company Network M17 // QtLocation QML bundle completion

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Company Network vector renderer integration
STAFF ROLE // Nurse 2, external / Hospital-compatible
PROVIDER // OPEN AI // CHATGPT
CONNECTION // External; no live Hospital registration verified
ASSIGNMENT // Extend merged M16's incomplete QtLocation shared-library bundle with its QML import module
PHASE // Draft PR; live Fedora runtime integration unverified
SCOPE // Isolated bundled files, M15 launcher preflight, synthetic tests, CI and handoff

## IMPLEMENTATION

Operator inspection confirmed:
- Fedora Silverblue host: Qt6Core, Qt6Quick, Qt6Positioning, Qt6PositioningQuick 6.11.2.
- Host is missing both libQt6Location.so.6 and /usr/lib64/qt6/qml/QtLocation.
- Fedora 44 Toolbox postapollo-vector44: qt6-qtlocation 6.11.2 and all four QtLocation QML module files:
  libdeclarative_locationplugin.so, MapView.qml, plugins.qmltypes, qmldir.
- The existing Company Qt app imports QtLocation and QtPositioning in main.qml and the Toolbox already renders Post-Apollo's real online vector style.

M16 PR #1339 is already merged. Its staging helper previously copied only libQt6Location.so.6. M17 updates it in place, retaining the explicit check/stage/remove CLI and user-local lab destination, but now stages FIVE tightly enumerated files under:

  ~/postapollo-vector-lab/qtlocation-runtime/lib64/libQt6Location.so.6
  ~/postapollo-vector-lab/qtlocation-runtime/qml/QtLocation/libdeclarative_locationplugin.so
  ~/postapollo-vector-lab/qtlocation-runtime/qml/QtLocation/MapView.qml
  ~/postapollo-vector-lab/qtlocation-runtime/qml/QtLocation/plugins.qmltypes
  ~/postapollo-vector-lab/qtlocation-runtime/qml/QtLocation/qmldir

M17 uses a v2 integrity manifest with SHA256 hashes of all five files and checks the declared QML module/plugin before accepting any bundle. It checks root-owned RPM source files and their package ownership/integrity from inside Toolbox before staging. No entire Toolbox Qt runtime is copied.

M15's native bridge now sets child-only QML_IMPORT_PATH and QML2_IMPORT_PATH to the bundle's qml directory first, followed by MapLibre's existing qml prefix. It verifies every QML artifact and runs ldd on the bundled plugin as well as previously checked native components before launching. The existing QtPositioning QML module stays on the host. M13 fixed-path launcher and explicit online consent are unchanged.

## HOW TO USE

After this PR is reviewed and safely available in the user's Quickshell checkout without overwriting uncommitted work:

Read-only check inside Toolbox:

  toolbox run -c postapollo-vector44 bash -lc 'python3 "$HOME/.config/quickshell/experiments/company-vector-qt/CompanyQtLocationBundleM16.py" check'

Only after operator explicitly approves local writes to the isolated lab:

  toolbox run -c postapollo-vector44 bash -lc 'python3 "$HOME/.config/quickshell/experiments/company-vector-qt/CompanyQtLocationBundleM16.py" stage'

On Fedora HOST, read-only:

  python3 ~/.config/quickshell/experiments/company-vector-qt/CompanyVectorHostBridge.py --probe

Only after a separate local installation approval:

  python3 ~/.config/quickshell/experiments/company-vector-qt/install_host_bridge_m15.py install

Then Company → Coverage → VECTOR VIEW → OFFLINE TEST; ONLINE STREETS requires separate disclosure approval. CLOSE VECTOR should terminate the native child.

After stopping Company, an approved staged-bundle rollback can use:

  toolbox run -c postapollo-vector44 bash -lc 'python3 "$HOME/.config/quickshell/experiments/company-vector-qt/CompanyQtLocationBundleM16.py" remove'

The M15 bridge installation is reversed separately with the M15 installer.

## VERIFY

- Operator screenshot: native MapLibre and Post-Apollo styled-online map visually render at multiple scales; upstream 3/3 native tests had passed.
- Operator shell: all host Qt modules needed except QtLocation present, Toolbox QtLocation module files present.
- M17: deterministic unprivileged tests for five-file staged bundle, malicious extras, symlinks, altered manifests/QML data, plugin ldd, runtime path and missing-plugin fail closed.
- CI status must be read on the current PR. Native host launch, QtLocation plugin loading and Stage Director containment have not been demonstrated.

## WATCH OUT FOR

- A matching Qt version and ldd closure do not prove QML plugin loading. Actual native Company window focus/render/close/no-orphan verification remains mandatory.
- The old M16 *library-only* bundle manifest v1 is intentionally rejected. If the user has independently staged that version already, do not overwrite or remove it without a reviewed migration and explicit operator approval.
- The QtLocation QML plugin may have dependencies beyond the selected five files. If runtime reports a missing dependent module, verify it before expanding the bundle. Never blindly copy Toolbox /usr/lib64 into the host.
- No local staging, package installation, desktop config mutation or Quickshell restart was performed.
- Stage Director containment remains another worker's responsibility.

## CHECKLIST

- [x] Confirm missing host QtLocation QML module from operator logs
- [x] Recheck M16 merge and current Company branch ownership
- [x] Extend QtLocation stage with complete four-file QML module
- [x] Extend host manifest and QML plugin dependency preflight
- [x] Update tests and CI contracts
- [ ] GitHub CI and code review
- [ ] Specific operator approval for local bundle staging
- [ ] Host probe reports READY
- [ ] Separate M15 bridge installation approval
- [ ] Live Company launch/close and orphan/focus verification
- [ ] Stage Director containment review
- [ ] Operator final acceptance

## NEXT

Review and test M17 repository PR. Once CI passes, obtain approval for the precise owner-local staging action, sync safely without resetting dirty Quickshell worktree, run the staged runtime from Toolbox and perform host read-only probe. Any host ABI/QML loading failures remain blockers to investigate.

## DECISIONS

Preserve M13 single-PID and online consent, M14 MapLibre build, M15 fixed trust boundary and v2 bundle manifest, plus the old Company Coverage map. No unapproved local write, merge or production activation.
