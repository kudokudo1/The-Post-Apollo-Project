# 🏥 Company Network M14 // Fedora native renderer handoff

**PATIENT:** kudokudo1/The-Post-Apollo-Project  
**ROOM:** Company Network vector renderer integration  
**PROVIDER:** OPEN AI // CHATGPT  
**CONNECTION:** External / Hospital-compatible; no live registration  
**ASSIGNMENT:** Reuse the verified Fedora 44 MapLibre v3.0 install to build and exercise the actual Post-Apollo Company Qt vector probe  
**SCOPE:** Isolated Toolbox build helper, fake-environment contract tests, existing native probe source; not the Quickshell runtime  
**STATUS:** Repository preparation; local Company probe still awaiting runtime test and operator acceptance  

## IMPLEMENTATION

The operator has already compiled MapLibre Native Qt v3.0 against Fedora 44 Qt 6.11.2 / GCC 16 in the dedicated `postapollo-vector44` Toolbox, installed the library at `~/postapollo-vector-lab/maplibre-install`, run the upstream 3/3 CTest suite successfully, and confirmed the upstream Qt Widgets example visibly renders with zoom/pan/movement. These are operator-provided observations, **not** evidence that the separate Post-Apollo Company probe has run locally.

GitHub's Company M7 style, M8–M12 native tests, and M13 explicit sidecar launcher already exist. M14 adds `fedora_lab_m14.sh` to bridge from the known MapLibre install to the **existing** `experiments/company-vector-qt` app without modifying those contracts. It checks CMake/QML/plugin/lib paths, verifies public Qt module version agreement, and supports four explicit actions:

- `check`: read-only inventory, no build.
- `build`: compile `company-vector-probe` in `~/postapollo-vector-lab/company-vector-build`.
- `run-offline`: run the synthetic offline map, not real street tiles or Company records.
- `run-online`: explicitly opt into the existing Post-Apollo styled OpenFreeMap layer; the tile provider can observe viewport requests and IP.

No install, daemon, auto-launch, owner-local data, shell changes or Quickshell configuration mutations. The helper only runs when the operator executes it. Tests exercise fail-closed missing files, offline default, explicit online action, and unsupported action refusal with disposable fake paths.

## HOW TO USE

First ensure the M14 branch is available in the user's local checkout **without resetting or discarding local Quickshell changes**. Do not demand a pull on a dirty worktree. Commands are intended for user execution **after approving that local action**.

In Kitty, where the Toolbox already exists:

```bash
toolbox run -c postapollo-vector44 bash -lc '
  bash "$HOME/.config/quickshell/experiments/company-vector-qt/fedora_lab_m14.sh" check
'
```

When the helper exists and preflight passes, optional isolated compilation:

```bash
toolbox run -c postapollo-vector44 bash -lc '
  bash "$HOME/.config/quickshell/experiments/company-vector-qt/fedora_lab_m14.sh" build
'
```

Run offline synthetic view, or separate opt-in online Post-Apollo style:

```bash
toolbox run -c postapollo-vector44 bash -lc '
  bash "$HOME/.config/quickshell/experiments/company-vector-qt/fedora_lab_m14.sh" run-offline
'
```

```bash
toolbox run -c postapollo-vector44 bash -lc '
  bash "$HOME/.config/quickshell/experiments/company-vector-qt/fedora_lab_m14.sh" run-online
'
```

The online command contacts OpenFreeMap; the offline command must remain synthetic. Commands run under a child Toolbox shell, so script exit cannot terminate the surrounding Kitty interactive shell.

## VERIFY

- Fedora MapLibre v3.0: operator observed build, isolated install, upstream Qt Core/QML/Widgets tests 3/3, standalone Qt Widgets interactive map.
- M14 helper: bash syntax checked and four fake-path unit tests passed in an isolated development environment before PR creation.
- **Not yet proven:** successful compilation of `company-vector-probe` on Fedora 44, QML and GeoServices plugin discovery on the user's Wayland session, or local styled-online rendering. The GitHub action does not reproduce Fedora's GPU/Qt installation.

## WATCH OUT FOR

- M13's launcher accepts **only** the fixed-path, owner-owned `~/.local/libexec/post-apollo/company-vector-probe`. This helper never writes there, so Company → Coverage → VECTOR VIEW still reports NOT INSTALLED until a separate approved, ABI-compatible installation.
- The binary's compiled style fixture paths point into the source checkout. Do not remove/rename the repo while testing.
- C++ sets OpenGL RHI for the native process; do not set a global `QSG_RHI_BACKEND` or alter live Quickshell.
- The old Natural Earth map, Streets raster mode, Company Hub Store, and data permissions remain unchanged.
- Stage Director containment is a separate owner/workstream. The Qt test window is not embedded.

## CHECKLIST

- [x] Recover Fedora MapLibre native build and upstream 3/3 test evidence
- [x] Reuse existing M7–M13 Company sources and launcher contract
- [x] Prepare isolated Fedora build/run helper
- [x] Run disposable helper contract tests
- [ ] Review GitHub CI and M14 draft PR
- [ ] Operator approves/executes local Company probe build
- [ ] Verify offline synthetic style and explicit styled-online map on Fedora
- [ ] Separately authorize user-local installation and M13 launcher test
- [ ] Coordinate Stage Director contained-view integration
- [ ] Operator final acceptance

## NEXT

Run the helper against the already-installed MapLibre prefix inside the dedicated Toolbox, **only with a separate user-approved local build action**. Inspect both offline and opt-in styled-online windows, plugin discovery, motion and window close. Do not copy the upstream Widgets example to the M13 launcher path.

## DECISIONS

Retain the sidecar/native-process boundary, explicit online consent, synthetic offline default, separate Company owner-data access, and the existing Company map. This PR does not authorize a local install, merge, renderer replacement or production activation.
