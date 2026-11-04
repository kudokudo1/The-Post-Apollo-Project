# Company Network M9 // Neighborhood Zoom + Demo Hub Marker

## IMPLEMENTATION

M8 is merged. Its GitHub runner successfully built Qt6 + source-built MapLibre v3 with OpenGL and captured real vector geography. Visual review confirms:
- Nationwide screenshot shows the US, Mexico, administrative borders and coastlines.
- Rural screenshot shows regional winding roads, smaller roads, and place names.
- Canadian screenshot shows Toronto roads and neighborhoods in a consistent Post-Apollo palette.
- The old M8 non-purple color diagnostic is **unreliable** (rural returned 0 despite visible roads). Do not use it as an acceptance threshold.

M9 extends this same **standalone** native renderer. It does not modify the running Company map, Qt backend, shell or any private business records.

1. **Fine zoom regression samples:** Add SUBURB (Troy, MI, z16), VILLAGE (Craigsville, WV, z15), NEIGHBORHOOD (Toronto, z16), and BORDER (Detroit/Windsor, z14), in addition to country/regional views. The world-wide provider and source remain unchanged.
2. **Synthetic hub anchor:** An explicit \`--mock-hub\` flag instantiates a geographically positioned \`MapQuickItem\` only when online mode is also explicitly enabled. It displays a hollow orange ring and a \`DEMO HUB\` label near Toronto. This is deliberately fabricated test geometry, never a claim about a real company.
3. **Navigation:** Replaces the overflowing camera preset column with a clipped, scrollable side rail. Retains the same \`MapView\`, coordinate system, map, and Post-Apollo visual identity at all zooms.
4. **Color diagnostics:** Log cyan/magenta/orange sample counts within the *map viewport*, excluding header, footer and controls. This is only an observational smoke signal, **not a claim of exact map content**.
5. **Native CI:** Save screenshots for offline, USA, RURAL, CANADA, NEIGHBORHOOD, VILLAGE and BORDER. Require the synthetic marker registration log for NEIGHBORHOOD.

## HOW TO USE

No local install, merge or desktop restart is required to inspect the GitHub CI captures. Optional standalone command, only if the operator later approves a compatible test environment:

\`\`\`bash
./company-vector-probe --styled-online --sample=NEIGHBORHOOD --mock-hub --capture
\`\`\`

This makes remote tile and glyph requests for the **public Toronto test location** and creates a **synthetic, unverified demo hub**. It does not read actual hub names or protected records.

## VERIFY

Run offline tests from a temporary repository checkout:

\`\`\`bash
python3 -m unittest discover -s tests/company -p 'test_company_vector_locality_m9.py' -v
python3 -m unittest discover -s tests/company -p 'test_company_native_online_m8.py' -v
\`\`\`

Native GitHub CI proves build/start and captures still images. Independent review of the high-zoom screenshots is needed to check labeled neighborhoods, local residential streets, buildings and exact marker anchoring. Full drag/zoom smoothness and user desktop compatibility are still unverified.

## WATCH OUT FOR

- A synthetic marker anchored to a coordinate is **not** an authenticated Company hub, provider, operating region, or service eligibility.
- OSM/OpenMapTiles-based street and building detail depends on data and source zoom. Missing address labels must not be invented.
- OpenFreeMap is the opt-in test source, not a contracted business-scale service.
- MapLibre Qt v3 uses process-local OpenGL; no permission to switch Quickshell's global renderer is inferred.
- MapQuickItem is tested only in the standalone Qt window. Bridging its selection and state into Quickshell requires separate, permissioned inter-process design and native desktop tests.

## CHECKLIST

- [x] M8 real road rendering visually verified
- [x] Add close-zoom samples
- [x] Add geographically anchored demo marker
- [x] Prevent rail overflow
- [x] Add focused static/native regression tests
- [ ] Pass M9 native map-item registration gate
- [ ] Review high-zoom geographic screenshots
- [ ] Measure pan/zoom jitter and frame pacing
- [ ] Prove safe inter-process window/control integration
- [ ] Bind authorized Company hub store read-only, later

## DECISIONS

Keep one vector map engine across zooms, with high-detail samples across multiple regions. Test markers never cross into real organizational data. Preserve local-desktop read-only default and operator acceptance.
