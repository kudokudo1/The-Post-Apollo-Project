# Identity Center / Local organization genuine Quickshell persistence v0

**PATIENT:** kudokudo1/The-Post-Apollo-Project  
**CONNECTION:** External Hospital-compatible ChatGPT. No verified live Hospital Room, Staff Role, Assignment or workstation attachment.  
**DEPENDENCY:** Merged PR #1041, final 20/20 workflows passed.

## IMPLEMENTATION

A disposable native-Quickshell test follows merged manual organization storage. It adds an **unmounted** LocalOrganizationNativeSmokeV0.qml, test runner, source guards and CI workflow. It uses the real SocialOrganizationDirectoryStore and production IdentityCenterSettingsSections, but **does not modify production QML, launch the user's default shell, or access real companies**.

A first genuine Quickshell 0.3.2 process writes two fictional local companies and one fictional branch. Nine native operations exercise add, rename, archive, and restore, with saved revision and non-verified membership checks after each operation. Python verifies private directory/file permissions and exact persisted data. A **new Quickshell process** opens the same disposable file, validates identical records and verifies no read-side rewrite. The runner uses temporary HOME and XDG runtime/config/data/cache/state paths, with DISPLAY and WAYLAND_DISPLAY disabled and Qt offscreen.

## HOW TO USE

Review the CI on the draft PR. In a separately approved disposable environment with qs installed, the test runner is:

    python3 tests/identity/native_local_organization_smoke_v0.py

It does not need any local deployment for PR review.

## VERIFY

Require both LOCAL_ORG_NATIVE_PASS_CREATE and LOCAL_ORG_NATIVE_PASS_RELOAD and 0700 directory/0600 file assertions. Existing source guards and previous Social Settings storage tests must remain green. This is a real Quickshell process, not a live Sway visual or mouse-interaction acceptance test.

## WATCH OUT FOR

Names are manually entered metadata, not server-verified memberships. They convey no authentication or permissions. The private local file is not encrypted. Nothing in this test proves real compositor rendering, user click behavior, lock/suspend behavior, or safe persistence on the operator workstation.

## CHECKLIST

- [x] Verify PR #1041 merged with all exact-head checks
- [x] Inspect current main, storage owner, and concurrent PR surface
- [x] Implement isolated native persistence test and source guards
- [ ] Exact-head GitHub CI passing
- [ ] Independent review and operator acceptance
- [ ] Separately approved live desktop visual/persistence check

## NEXT

If CI fails, repair the bounded fixture or report any production bug without silently relaxing auth boundaries. After review, live workstation testing needs separate explicit local-write permission.

## DECISIONS

Verification-only follow-up. No local installation, live shell restart, PR merge, production sign-in or organization switching authorized.
