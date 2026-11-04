# Company Network M4 // Hub intake repair, cities and opt-in streets

## IMPLEMENTATION

**+ HUB repair:** Previously the + HUB control silently discarded clicks while the local hub store was not READY, and a successful click merely armed map placement without presenting the form. Now clicking **+ HUB** immediately opens the form. The form requires **PICK LOCATION ON MAP**; the editor temporarily closes, the map accepts a coordinate, and the form reappears **without losing entered fields**. The form reports loading/error state and offers retry. Saving without coordinates or without a ready hub directory refuses with an explicit message. No default coordinate is silently interpreted as an actual hub location.

**More cities:** Existing Natural Earth 1:110m reference layers and capitals are retained; new public-domain, pinned Natural Earth 1:50m populated-place data supply 1,251 global city references, including 111 US cities, 45 Canadian, and 27 Mexican. Labels are density/zoom gated to avoid overcrowding. Search in the right directory finds and focuses cities. They are **reference locations**, not company hubs or verified coverage.

**Streets:** A separate **STREETS** control presents an opt-in prompt. Only choosing **ENABLE STREETS** starts a native, in-widget tile view using Web Mercator instead of stretching the coarse geographic outline. The tile adapter accepts **only** a viewport (lon, lat, zoom, width, height, explicit enable flag), never a hub name, organization label, worker or client field. It requests only currently visible tiles (no prefetch), with a bounded fetch count, named User-Agent, HTTPS, HTTP expiry/ETag support, owner-only disk cache, and visible **© OpenStreetMap contributors** attribution. Turning STREETS off restores offline Natural Earth. The opt-in is per-run and is not automatically persisted.

**Backend:** New \`CompanyStreetTiles.py\` uses OpenStreetMap's best-effort public tile endpoint for user-driven viewing. This is not a commercial SLA or enterprise-scale mapping license. A dedicated provider/service plan must precede production-company rollout. The map component uses cached local raster tile files, preserving desktop-native interaction without opening an external browser.

## HOW TO USE

1. Open Company Network → COVERAGE.
2. **+ HUB** opens the entry form. Enter organization/hub labels, city, region, service family.
3. Click **PICK LOCATION ON MAP**, pick a point on the offline map, and continue in the preserved form. Then **SAVE LOCAL HUB**.
4. Use **CITIES ON** and the reference directory search to find a city.
5. Click **STREETS** and read the prompt. Choose **ENABLE STREETS** to fetch a limited set of current-view street tiles. Streets mode has independent pan/zoom and selectable hub pins; switch off to return to offline map.
6. For streets around a city, select the city from the directory first, then enable streets.

## VERIFY

Run disposable tests from a repository checkout:

\`\`\`bash
node --test tests/company/test_company_map_m4.test.js tests/company/test_company_hub_m3.test.js tests/company/test_company_network_m1.test.js tests/company/test_company_network_m2.test.js
python3 -m unittest discover -s tests/company -p 'test_company_street_tiles_m4.py' -v
python3 -m unittest discover -s tests/company -p 'test_company_hub_directory_m3.py' -v
\`\`\`

Tests use fake HTTP and disposable cache paths. They do not contact the public OSM server, install files on the operator's desktop or verify Wayland/Quickshell rendering.

## WATCH OUT FOR

- Clicking map points is not geocoding: exact addresses must later be verified against a trusted geocoder, and company authorization remains separate.
- Online street requests expose the viewed geographic tile area and network metadata to the tile provider. **Never send confidential personnel/client information to mapping services.**
- Standard OSM tile servers are capacity-limited and may block heavy or commercial use without a dedicated provider. Abide by current tile policy: https://operations.osmfoundation.org/policies/tiles/
- The UI currently offers city references and raster streets; it does not claim a complete searchable street-address database or route engine.
- Native compositor click and focus behavior remains unverified until an authorized desktop test.
- No migrations of organization accounts, real client data or permissions, and no changes to \`shell.qml\` or other widgets.
- Network requests are **opt-in** and never occur during standard offline coverage navigation.

## CHECKLIST

- [x] Expose hub editor on first click and preserve fields while picking
- [x] Surface store errors and retry
- [x] Add more city references and city search
- [x] Add street-mode opt-in, map math and cached tile adapter
- [x] Add isolated M4 tests/CI
- [ ] Native Quickshell / compositor verification
- [ ] Operator visual and functional acceptance
- [ ] Dedicated business-grade map tile agreement/provider
- [ ] Verified address lookup, service coverage and eligibility records

## NEXT

Verify the UI on the operator's desktop. Then integrate an approved geocoding/search provider and properly permissioned service-offering relationships. Actual verified company reach requires contracts, service rules, workforce capacity and evidence, none of which this map invents.

## DECISIONS

The Company Network map remains the owner of its own hub and street data. The street view is deliberately a separate projection/component from Natural Earth, and no location data is disclosed to a third party without an explicit per-run opt-in.
