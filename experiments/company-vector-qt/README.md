# Company Network M5 // Isolated MapLibre Native Qt proof

**Patient:** kudokudo1/The-Post-Apollo-Project  
**Room:** Company Network vector renderer compatibility  
**Assignment:** Verify an isolated Qt 6.5+ MapLibre Native Qt v3 renderer *without* changing Quickshell, desktop configuration, or actual company data.  
**Connection:** External / Hospital-compatible; no live Hospital session claimed.

## IMPLEMENTATION

This directory is a **separate Qt 6 application**. Its process-local C++ entry point selects OpenGL RHI before QML starts, as required by MapLibre Native Qt **v3.0**. It loads a QtLocation \`MapView\` backed by the \`maplibre\` geoservices plugin. CMake uses \`QMapLibre::Location\` and \`qmaplibre_location_setup_plugins\`, matching the upstream Qt 6 example.

Two explicit modes:

- **Default (offline):** local \`style-fixture.json\`, with deliberately *synthetic* vector geometry near Flint, MI. It exercises Post-Apollo palette semantics but is **NOT** Flint's actual roads, provider sites, or company service areas. No network requests should occur from the style.
- **\`--online\` (opt-in):** \`https://tiles.openfreemap.org/styles/liberty\`. Tests actual detailed, zoom-varying OSM/OpenMapTiles vector data, but **does not yet apply the custom Post-Apollo vector style**. It discloses the viewed tile area and IP to OpenFreeMap and may request third-party glyph/sprite assets. This mode is never enabled automatically.

The work neither imports this app into \`shell.qml\` nor modifies \`widgets/CompanyCoveragePane.qml\`, \`CompanyStreetMap.qml\`, or the existing hub directory.

## HOW TO USE

**Automated isolated check:** see the dedicated GitHub workflow \`company-network-vector-probe-m5.yml\`; it uses disposable CI runner Qt/MapLibre packages, Xvfb and Mesa software OpenGL. All downloads/installations occur on the CI runner only, never the user's desktop.

**Read-only desktop preflight**, if the operator chooses to run it:

\`\`\`bash
python3 experiments/company-vector-qt/probe_environment.py
\`\`\`

**Run locally only after separate local-write/install approval and verified dependencies.** In an isolated toolbox/test environment where MapLibre v3 is already installed with a matching Qt 6 version:

\`\`\`bash
cmake -S experiments/company-vector-qt -B /tmp/postapollo-vector-probe-build -G Ninja \
  -DCMAKE_PREFIX_PATH="<your Qt install prefix>" \
  -DQMapLibre_DIR="<installed QMapLibre cmake config directory>"
cmake --build /tmp/postapollo-vector-probe-build
/tmp/postapollo-vector-probe-build/company-vector-probe --capture
\`\`\`

Omit \`--capture\` for an interactive window. To view external vector streets, run the exact same binary with **\`--online\`** only when you agree to disclose the selected viewport to OpenFreeMap.

The example CMake paths above are placeholders and should be filled from an inspected test environment, never guessed from the desktop. The capture writes a screenshot to the current working directory in the environment where it is run; it does not prove accurate map rendering by itself.

## VERIFY

- CI contract tests check strict default-offline behavior, isolated process scope, mapping/QML API usage, style fixture classification, and that the existing Company source remains untouched.
- Experimental **native CI gate** attempts real CMake compile, MapLibre plugin load and Qt Quick screenshot in an isolated Xvfb/llvmpipe runner. Failures are evidence of dependency/graphics incompatibility and must NOT be relabeled as success.
- A PNG screenshot is only process/rendering evidence. Human inspection of vector layers, labels, pan/zoom and OpenGL errors remains required.
- Host Quickshell runtime, graphics API compatibility and in-process embedding are **not** proved by a standalone app.

## WATCH OUT FOR

- MapLibre Native Qt **v3** QML requires **OpenGL RHI**. Quickshell may already use a different graphics API or environment: never inject or change \`QSG_RHI_BACKEND\` globally without an authorized and reversible desktop test.
- Native Qt plugin binaries must match the installed Qt major/minor and ABI. Do not copy CI binaries into a live Fedora Silverblue host.
- MapLibre Native Qt **v4** is unreleased and API-incompatible with v3. Do not silently upgrade the fixture to v4.
- OpenFreeMap's public instance permits custom applications and includes geographic detail, but has no SLA; large fleet deployment needs a provider / self-hosting plan and ODbL attribution/redistribution review.
- No real roads are bundled in offline proof. Provider coverage and client eligibility are distinct datasets and remain unimplemented.
- No client/worker identifiers, credentials, contracts or organization names belong in this probe.

## CHECKLIST

- [x] Inspect current Company code, repo state, native Qt integration docs
- [x] Create isolated executable, synthetic offline style, explicit online option
- [x] Create read-only environment inventory and deterministic contract tests
- [ ] Native CI compile/plugin/window gate passes
- [ ] Independent screenshot review and performance measurements
- [ ] Fedora Silverblue + Quickshell compatibility investigation under operator authorization
- [ ] Continuous vector map pilot using actual Flint/Ontario OSM data
- [ ] Post-Apollo custom vector style, company layer overlaid, smooth pan/zoom
- [ ] Operator accepts renderer replacement before touching shared widget

## NEXT

On success, build a dedicated Post-Apollo vector style based on OpenMapTiles layer names, using an explicitly approved map source, then test detailed Flint/southern Ontario geography on a separate standalone application. On failure, record exact missing Qt, plugin, OpenGL or style resolution condition and try a separate-process fallback. **Do not replace the original Company map until operator acceptance.**

## DECISIONS

This proof intentionally favors isolation over quick integration: a native graphics mismatch must not destabilize Quickshell. The standalone Qt scene is reversible; no live desktop activation, background monitoring or repo merge is authorized. MapLibre Native Qt v3.0 is pinned as the currently released API for this proof.

Sources:
- https://github.com/maplibre/maplibre-native-qt/tree/v3.0.0/examples/quick
- https://maplibre.org/maplibre-native-qt/docs/md_docs_2Usage.html
- https://openfreemap.org/quick_start/
- https://openfreemap.org/
