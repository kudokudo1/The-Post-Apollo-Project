# Company Network // M3 Operator-Reported Hub Directory

**PATIENT:** kudokudo1/The-Post-Apollo-Project  
**ASSIGNMENT:** Company Network geographic operations M3, isolated source integration  
**AUTHORITY:** Operator-specified feature development only. No live Hospital registration, PR merge, local desktop activation or authenticated company permission is assumed.

## IMPLEMENTATION

Add a bounded, owner-local manual hub directory for **non-personal operational metadata**. Each entry stores a hub display label, operator-entered organization label, city/locality, 2–3 letter region code, country (US/CAN/MEX), longitude and latitude, one service family, internal ID, archival flag, and permanent \`reported: true\` classification. No client names, worker names, recruitment details, service eligibility or contract claims are stored.

A new \`CompanyHubStore.qml\` routes fixed read/create/archive/restore calls through one \`CompanyHubDirectory.py\` process boundary. The Python document is versioned (\`post-apollo.company-hubs.local.v1\`), revision checked, locked, size/capacity bounded and atomically saved to \`$XDG_DATA_HOME/post-apollo/company/hubs-v1.json\`, defaulting to \`~/.local/share/post-apollo/company/hubs-v1.json\`. Its directory and file are owner-only. Missing records read as empty without creating files; corrupt/unsafe files are refused.

The Coverage screen adds **+ HUB**. An operator clicks a map coordinate, then enters location, organization label and service-family metadata in an in-widget editor. On explicit SAVE, the private writer creates a claimed hub; the resulting orange hollow pin and directory row are clickable. White markers still mean geographic state capitals, and a filled coverage region is **never** drawn from these claims.

## HOW TO USE

1. Open Company Network → COVERAGE.
2. Select a regional view and click **+ HUB**.
3. Click the geographic location where the hub is reported. This selects coordinates, not a verified street address.
4. Enter Hub Name, Organization Label, City/Locality, State/Region code, Country, and Service Family.
5. Select **SAVE LOCAL HUB**. The orange outlined pin appears on the map; click it or its directory row to inspect the claim.

The + HUB action only enables placement if the private store reports READY. Missing writable privileges or an unsafe store do not grant any access. This does not create a verified organization account or an operational coverage area.

## VERIFY

Run on a disposable checkout:

\`\`\`bash
python3 -m unittest discover -s tests/company -p 'test_company_hub_directory_m3.py' -v
node --test tests/company/test_company_hub_m3.test.js tests/company/test_company_network_m1.test.js tests/company/test_company_network_m2.test.js
\`\`\`

CI does not prove live compositor rendering, pointer/focus behavior, Emoji fonts or user acceptance.

## WATCH OUT FOR

- **No encryption**: owner-only local files protect against other OS users under ordinary permissions, not malicious same-user processes, backups or unauthorized administrators. Do not store personnel/client information in this metadata store.
- Records are operator-reported and may be inaccurate. There is no evidence verification, organization authorization, provider API, government contract check, or county/city eligibility calculation yet.
- A single service-family tag is allowed per entry in M3; this is not a complete multi-program relationship model.
- The organization label is not a Social identity grant. Identity Center remains authoritative for validated memberships and permissions.
- M3 storage methods include archive/restore foundation, but in-widget archive/restore controls are reserved for a reviewed follow-up. Do not manually edit the private JSON.
- Manual selected coordinates are not geocoded or street-level validated. This is a working planning registry, not a client referral routing authority.
- The existing Company icon and window are intentionally unchanged, allowing the independent icon/header PR to proceed.

## CHECKLIST

- [x] Implement private non-personal store and validation
- [x] Connect map hub-pick/save and reported-only pins
- [x] Add disposable regression tests/CI
- [ ] CI and independent QML review
- [ ] Native desktop verification, operator acceptance
- [ ] Evidence-backed provider/contract verification and role-based access
- [ ] Multiple service offers and county/city coverage modeling
- [ ] Separate confidential workforce/client enrollment systems

## NEXT

After isolated visual acceptance, add audited provider service-offering links, geographic eligibility areas (including county/city shapes), and distinction among **reported, independently verified, contract-supported, remotely delivered, and proposed** coverage. Employee/client networks require a separate permissioned system.

## DECISIONS

This implementation does not modify \`shell.qml\`, \`CompanyNetworkW.qml\`, \`modules/CompanyNetwork.qml\`, Identity Center, Weather Station or any actual company records. No merge or desktop activation is authorized by this source implementation.
