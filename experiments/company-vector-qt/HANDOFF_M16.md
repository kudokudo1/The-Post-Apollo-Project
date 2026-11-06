# 🏥 Company Network M16 // Isolated QtLocation Runtime

PATIENT // kudokudo1/The-Post-Apollo-Project
ROOM // Company Network vector renderer integration
STAFF ROLE // Nurse 2 (external continuation)
PROVIDER // OPEN AI // CHATGPT
CONNECTION // EXTERNAL / HOSPITAL-COMPATIBLE, NOT REGISTERED
ASSIGNMENT // Provide opt-in one-library QtLocation runtime bundle for M15 direct-host launcher
PHASE // GitHub draft, no local deployment

## IMPLEMENTATION

Operator output proves Toolbox qt6-qtlocation 6.11.2-1.fc44.x86_64 provides /usr/lib64/libQt6Location.so.6.11.2 and its Toolbox dependencies resolve. Host reports Qt6Core/Qt6Quick 6.11.2 and Qt6Positioning loaded, but the Company executable and QMapLibreLocation fail to find libQt6Location.so.6 on the host. Toolbox linkability is not proof of host ABI safety.

This milestone introduces CompanyQtLocationBundleM16.py to stage only the verified Fedora RPM QtLocation ELF library into an owner-only path under ~/postapollo-vector-lab/qtlocation-runtime/lib64/. The file is stored as libQt6Location.so.6, alongside a version and SHA256 manifest. No host package install, Quickshell reload, or MapLibre rebuild occurs.

An explicit stage action is required for any library write. The default check is read-only; remove refuses checksum mismatches, symlinks and unexpected files. M15 CompanyVectorHostBridge.py checks user ownership, no symlinks, version/hash integrity, host Core/Quick public version metadata, exact host Positioning library version, and four ldd runtime dependency checks before direct exec. The QtLocation bundle is prepended only to this child process's LD_LIBRARY_PATH. The existing M13 launcher and online consent remain in place.

## HOW TO USE

After PR review and safe synchronization that preserves existing local Quickshell modifications:

1. Read-only inside Toolbox:
   toolbox run -c postapollo-vector44 bash -lc 'python3 "$HOME/.config/quickshell/experiments/company-vector-qt/CompanyQtLocationBundleM16.py" check'

2. Only with specific approval to write the owner-local lab, stage inside Toolbox:
   toolbox run -c postapollo-vector44 bash -lc 'python3 "$HOME/.config/quickshell/experiments/company-vector-qt/CompanyQtLocationBundleM16.py" stage'

3. Host preflight, read-only:
   python3 ~/.config/quickshell/experiments/company-vector-qt/CompanyVectorHostBridge.py --probe

4. Only with separate approval, install M15 fixed-path launcher:
   python3 ~/.config/quickshell/experiments/company-vector-qt/install_host_bridge_m15.py install

5. Test Company → Coverage → VECTOR VIEW → OFFLINE TEST; ONLINE STREETS requires separate explicit disclosure consent. CLOSE VECTOR should stop the child, with no orphan.

6. After stopping the native app and with local removal approval, rollback:
   toolbox run -c postapollo-vector44 bash -lc 'python3 "$HOME/.config/quickshell/experiments/company-vector-qt/CompanyQtLocationBundleM16.py" remove'

No user-machine actions have been performed in this ChatGPT conversation.

## VERIFY

Toolbox QtLocation 6.11.2 and no missing dependencies in operator's Toolbox ldd output. GitHub M15 merge verified. M16 synthetic tests and CI are distinct from host runtime acceptance; local host/plugin/UI behavior has not been tested.

## WATCH OUT FOR

Qt private binary compatibility remains a real risk despite matching 6.11.2. ldd checks do not prove QML plugin loading or rendering. Do not copy the complete Toolbox, disable validation, or change Silverblue system packages. Local staging changes files and needs explicit approval. Stage Director embed/clip/input is a separate room.

## CHECKLIST

- [x] Source library and missing host dependency identified
- [x] Prepare isolated staging and guarded host bridge
- [ ] GitHub CI
- [ ] Operator-approved staging
- [ ] Host runtime readiness check
- [ ] Approved M15 fixed launcher installation
- [ ] Verify open/close/focus and no orphan
- [ ] Stage Director containment coordination
- [ ] Operator final acceptance

## NEXT

Run dedicated M16 CI. Obtain operator local-write approval before staging. Check the host ABI with bridge --probe before attempting a Company launch.

## DECISIONS

Keep M13's trusted fixed launcher, explicit online consent and direct PID lifecycle; preserve existing Coverage map and separate Company data claims. Remain draft and uninstalled.
