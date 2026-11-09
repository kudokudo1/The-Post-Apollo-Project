# 🏥💜 Company M31d // Isolated Fedora MapLibre visual preview

HOSPITAL REPORT

PATIENT // `kudokudo1/The-Post-Apollo-Project`
ROOM // Company native map, first user-visible independent preview
DOCTOR // Nurse 2, external Hospital-compatible successor
PROVIDER // OPEN AI // CHATGPT
CONNECTION // EXTERNAL / HOSPITAL-COMPATIBLE; not registered in live Hospital
ASSIGNMENT // Let operator inspect and pan/zoom the existing native MapLibre application using the known dedicated Fedora 44 Toolbox and library build, without writing live Quickshell
PHASE // Pullable source-only preview launcher and CI contract
STATE // DRAFT; operator's Fedora run not yet performed
REPORT KIND // IMPLEMENTATION / HANDOFF
PERMISSIONS // GitHub branch, isolated test/CI; no operator host writes performed, no production integration, no merge.

## IMPLEMENTATION

The existing `experiments/company-vector-qt/main.cpp` and `main.qml` already implement a standalone Qt6 / MapLibre Native Qt v3 window. The existing `fedora_lab_m14.sh` checks actual Qt versions and installed MapLibre ABI; it compiles and launches one app inside `postapollo-vector-lab` and does not import it into Quickshell. Operator-provided earlier hardware observations indicated their `postapollo-vector44` Toolbox had built MapLibre 3.0.0 and the upstream Widgets example rendered; this is **not** proof the Company probe currently builds on the machine.

**M31d adds `preview_m31d.sh` rather than another map renderer.** It insists on a dedicated clone at `~/postapollo-vector-lab/company-preview-src`, refuses other source directories, overridden local source/lab paths, root execution and global RHI overrides, and delegates only `check|build|run-offline|run-online` to the already verified M14 helper. A fake-Toolbox CI test checks safe refusal, source isolation, explicit online mode, and no build on `check`.

The **default offline window** shows explicitly **synthetic** geographic features, not genuine service roads, real company hubs, or coverage. `run-online` uses the native styled vector OpenFreeMap public style for real road labels and zoom-dependent detail, and visibly warns that selected public viewport tiles and IP are disclosed. No private Company records or local owner-hub data are read by these preview actions.

This is the **first pullable standalone visual preview**, not the final embedded Company map. The SwayPX native compositor distortion and corrected candidate are a **separate** workstream. The full GL correction was verified in M31a CI and generalized matrix in M31b; [M31c SwayPX draft #122](https://github.com/kudokudo1/Post-Apollo-SwayPx/pull/122) is separately testing a generalized native SceneFX build. This M31d launcher **does not patch or replace the running host compositor**, so unusual host GPU/format/width configurations could still reproduce the old upload defect.

## HOW TO USE

These commands are **for the operator to execute only after deciding to make the local clone/build**. Nothing on the user's machine is changed by GitHub creating this PR. They deliberately avoid `~/.config/quickshell` and any `git pull` on the live shell.

In **Kitty on the Fedora host**, clone the isolated preview branch into the existing vector lab (this is the first command that writes local source files):

```bash
mkdir -p "$HOME/postapollo-vector-lab"
git clone --single-branch --branch company/m31d-isolated-fedora-visual-preview-20261108 \
  https://github.com/kudokudo1/The-Post-Apollo-Project.git \
  "$HOME/postapollo-vector-lab/company-preview-src"
```

The clone refuses to overwrite an existing destination. If the destination already exists, **inspect it first**, don't delete/overwrite it.

**Read-only preflight** inside the existing Fedora Toolbox:

```bash
toolbox run -c postapollo-vector44 bash \
  "$HOME/postapollo-vector-lab/company-preview-src/experiments/company-vector-qt/preview_m31d.sh" check
```

If this prints `M14_PREFLIGHT_PASSED`, the existing Qt version/modules, MapLibre install and public QML plugins match the expected lab. It is still not proof of rendering.

**Compile in the dedicated lab only** (writes `~/postapollo-vector-lab/company-vector-build`, not Quickshell):

```bash
toolbox run -c postapollo-vector44 bash \
  "$HOME/postapollo-vector-lab/company-preview-src/experiments/company-vector-qt/preview_m31d.sh" build
```

**View the standalone offline map** (synthetic; no external map tile requests):

```bash
toolbox run -c postapollo-vector44 bash \
  "$HOME/postapollo-vector-lab/company-preview-src/experiments/company-vector-qt/preview_m31d.sh" run-offline
```

**View real public vector streets** (explicit, optional OpenFreeMap network access):

```bash
toolbox run -c postapollo-vector44 bash \
  "$HOME/postapollo-vector-lab/company-preview-src/experiments/company-vector-qt/preview_m31d.sh" run-online
```

Move/zoom the Qt map with mouse/scroll, close the native window normally. The main Company Quickshell page and current map remain unaffected. This preview does not need a host-wide Qt package install, Quickshell restart, Stage Director production compositor switch or `~/.local/libexec` installation.

## VERIFY

The standalone M14 launcher already has separate contract tests; M31d adds a self-contained GitHub Actions source/behavior test with a synthetic `HOME`, dedicated fake clone and fake M14 helper so CI never builds, uploads, launches or uses external map tiles. **Real operator Fedora Qt build, plugin load, Wayland window, and actual pan/zoom require direct visual verification on the host**. If `check` or `build` fails, preserve the exact error; do not change host packages automatically.

To view the **actual native corrected 1493px compositor image in CI**, see the M31a image artifact linked from [SwayPX PR #120](https://github.com/kudokudo1/Post-Apollo-SwayPx/pull/120); M31c's later artifact (if passing) will be a fresh generalized implementation witness, not a Fedora binary.

## WATCH OUT FOR

- This is a source clone plus explicit local build, **not an AppImage/Flatpak or portable precompiled binary**. The earlier Fedora Toolbox already had appropriate dependencies; this branch does not download or install them.
- The standalone native app runs **inside Toolbox** and relies on Toolbox host display forwarding. Wayland display/socket access or plugin/runtime mismatches may prevent the window from opening.
- Qt OpenGL RHI is selected **inside the native process**, not globally. Never set/rewrite `QSG_RHI_BACKEND` in Quickshell to test this.
- Native SwayPX crop/input containment, selected host identity, live Company bridge opt-in and production SceneFX GL alignment correction are not automatically enabled.
- OpenFreeMap online use is explicit and discloses public viewport tiles and IP. Offline data is purely synthetic.
- Do not merge this branch into an active dirty `~/.config/quickshell` checkout; use the dedicated clone.
- This is not an assertion that the map is visually approved until operator actually sees it.

## CHECKLIST

- [x] Recheck latest Company/SwayPX PRs, Syntagma authority and ownership
- [x] Reuse the existing M14 native app, build/launch helper and known Fedora Toolbox
- [x] Add a separate clone-only preview guard, offline default and online disclosure
- [x] Add fake-host tests for strict source/lab identity and read-only preflight
- [ ] GitHub CI source/behavior tests
- [ ] Operator chooses to clone into the isolated lab
- [ ] Operator verifies check/build/offline launch/real online streets
- [ ] M31c native generalized SwayPX renderer test passes
- [ ] Upstream owner review, approved Company embedded integration, physical GPU/focus/input validation and final user acceptance

## NEXT

Run M31d GitHub CI. Then operator can open the standalone map visually using the commands above, without waiting on production Stage Director adoption. Collect exact screenshots/error output of the Fedora run for final viewport styling and interaction fixes. Keep M31c and Company embedding separate and gated by their owner reviews.

## DECISIONS

Dedicated standalone preview first. No unapproved Fedora writes by the assistant, no live Quickshell mutation, no production SwayPX dependency switch, no provider/Company record upload, no merge or final DONE. Rollback of local source/build is optional operator-owned and should never delete an uninspected directory.
