# 🏥💜 Company M30v // Real Qt CPU readback evidence, NOT native wl_buffer attestation

HOSPITAL REPORT

PATIENT // `kudokudo1/The-Post-Apollo-Project`  
ROOM // Company native MapLibre / buffer evidence  
DOCTOR // Nurse 2, external Hospital-compatible successor  
PROVIDER // OPEN AI // CHATGPT  
CONNECTION // EXTERNAL / HOSPITAL-COMPATIBLE; not live registered  
ASSIGNMENT // Introduce bounded read-only metadata from Company native Qt image readback  
PHASE // Company-owned first half of M30v, no host admission  
BASE // Company `main` at `9359b637d22ef66c7d2ebcfa4c9c75a24d51e1a9`  
SOURCE // M30u merged [PR #1544](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1544);
SwayPX M30t [PR #116](https://github.com/kudokudo1/Post-Apollo-SwayPx/pull/116)
still draft at time of inspection.  
OWNER // Company renderer (this change). SwayPX compositor native actor,
Wayland buffer, scene/input/clip remain a separate owner. Social pairing unchanged.

## IMPLEMENTATION

The Stage Director worker's recorded
[coordination handoff](https://github.com/kudokudo1/The-Post-Apollo-Project/pull/1544#issuecomment-6724674448)
requires distinguishing **calculated** row stride from **observed**
row stride, and collecting actual native surface/allocator/format
evidence before production rendering authority.

M30u has a pure Company QML JS buffer *candidate*; its experimental
1493×788 visible Canvas, 1494×788 physical Qt source and 0-pixel
reference drift derive from the real M30t native CI. That result does
not establish a universal 4-byte pixel/8-byte alignment rule.

M30v adds the first **narrow, genuinely observed** metadata:

- `experiments/company-vector-qt/CompanyVectorReadbackEvidence.h`
  is a pure C++ inspector of a real `QImage` returned by
  `QQuickWindow::grabWindow()`. It reads `image.format()`,
  `image.depth()`, **`image.bytesPerLine()`**, dimensions,
  row minimum and CPU readback padding, `image.devicePixelRatio()`,
  and the original logical `QQuickWindow` dimensions and DPR.
  It refuses missing images, overflow/invalid dimensions, impossible
  stride and unreasonable scale.
- Every result, including a successful Qt readback, **unconditionally**
  declares `productionAuthority=false`,
  `selectedNativeActorVerified=false`,
  `waylandBufferAttested=false`.
  Actual native buffer allocation kind, DRM format, modifier,
  wl_buffer stride and surface scale are explicitly `null`.
  The output calls itself `QT_CPU_READBACK_ONLY` and says native import
  is not approved.
- Original `main.cpp` gains an explicit
  **`--readback-evidence`**, one-shot **offline-only** command-line
  flag. It rejects all online modes, owner-local hubs, fixture hubs,
  alternate samples, benchmark, screenshot capture and any additional
  flag. It waits a bounded 5.5 seconds, reads the existing Qt
  window's pixels **in memory**, emits one JSON object with only
  metadata and exits. It never saves pixel data.
- The normal Quickshell
  `services/company/CompanyVectorSidecarController.qml` /
  `CompanyVectorSidecarLaunch.py` never passes that flag, and
  M30v never modifies those files. The existing standalone offline /
  explicitly-consented online UI, PID ownership and lazy bridge stay
  unchanged.
- A native C++ unit-test executable exercises actual Qt6
  `QImage` objects at widths 1493/1494 and a different RGB888
  format, plus DPR, missing-image and invalid-geometry refusals.
  The test checks the helper never claims actual native buffer
  format/stride/scene permission.
- GitHub Actions compiles/runs the Qt6Gui C++ harness and existing
  M5/M26/M30q/M30u regressions. It does **not** run the full
  MapLibre Qt application yet.

## HOW TO USE

The future installed native Qt map can run **only by explicitly passing**
`--readback-evidence` directly to its standalone executable. This is
an optional diagnostic, **not** a new Company menu or a routine
launcher path. The only output is a single log record prefixed
`COMPANY_M30V_QT_READBACK_EVIDENCE`, containing a compact JSON object.

The source tests can be run with
`python3 -m unittest discover -s tests/company -p 'test_company_vector_readback_m30v.py' -v`.
The new CI job additionally compiles Qt6Gui against real library headers.

No local Fedora command, installation, shell restart, or production
renderer activation was performed.

## VERIFY

At the implementation checkpoint, exact-head CI is pending. To pass:
1. Native Qt6 C++ test must **measure** actual 1493px and 1494px
   `QImage::bytesPerLine` and an RGB888 counterexample, rather
   than assign 5972/5976 from a formula.
2. Any successful record must keep actual Wayland/DRM buffer metadata
   `null` and all authority bits false.
3. Invalid/empty image, dimensions and DPR must refuse.
4. The explicit CLI must not be available to the automatic Company
   QProcess sidecar or any online/private/hub input.
5. Existing Company M5/M26/M30q/M30u contracts must still pass.

## WATCH OUT FOR

**M30v does not yet attest a native wl_buffer.** Qt's
`QQuickWindow::grabWindow()` may internally copy and reformat the
actual compositor source texture, and its `QImage::bytesPerLine`
is the pitch of the **CPU readback allocation**, not necessarily the
pitch of a dmabuf, wl_shm or OpenGL texture.

Do **not** treat the new observed CPU pitch as trust in a selected
surface, authenticated executable, compositor buffer modifier, actual
GPU format/stride or authorized scene/input clipping. That separate
SwayPX work must use an authenticated selected native actor and inspect
the real, live compositor buffer/import/scale path.

Also note: the 5.5-second offline probe checks the Qt window's
readback capability, not whether the MapLibre geographic layers
finished loading or if service coverage is accurate.

## CHECKLIST

- [x] Reconcile M30u merge, M30t draft and GitHub handoff ownership
- [x] Check Syntagma staff/permissions and current Company main
- [x] Add Company-owned pure bounded Qt readback evidence header
- [x] Add explicit offline-only main.cpp diagnostic flag
- [x] Add native Qt C++ metadata and negative tests
- [x] Add CI workflow and existing Company scope/launcher regressions
- [ ] Exact-head GitHub CI green, including compiled Qt6 proof
- [ ] Native MapLibre/Qt readback verified in isolated real Wayland test
- [ ] SwayPX Company owner independently attests actual wl_buffer
- [ ] Trusted host/ELF and production scene/input admission authorized
- [ ] Operator visual and Fedora multi-output acceptance

## NEXT

Verify M30v GitHub CI. If green, the next **separate**
M30w/wl_buffer-owner task is read-only compositor observation of
the authenticated selected actor's actual buffer format, row pitch,
allocation, modifier, scale, transform and target logical viewport.
Only compare M30u's calculated backing candidate against this
independently collected evidence when both sources are bound to the
**same native actor/surface/generation**, and refuse uncertainty.
Native production scene/input permission must remain OFF until
the separate owner/operator review.

## DECISIONS

The handoff explicitly preserves the Company/SwayPX/Social ownership
boundary. M30v records only **Qt readback evidence** from an explicit
standalone offline diagnostic, not universal GPU pitch, production
buffer attestation or live host authorization. No local machine write,
merge or production actuation performed.
