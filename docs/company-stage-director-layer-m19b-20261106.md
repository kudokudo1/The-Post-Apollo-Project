# Company Stage Director M19b // Handoff

PATIENT // The-Post-Apollo-Project
ROOM // Company Network Stage Director integration
STAFF ROLE // External Nurse 2 continuation
ASSIGNMENT // Expose a stable layer-shell name without changing map behavior

## IMPLEMENTATION

Add `WlrLayershell.namespace: "post-apollo-company-network"` to the existing Company PanelWindow. The native SwayPX observer can use this label to find candidate Company panels. The label alone does not establish ownership. The compositor must still verify the live Wayland host, process identity and current geometry before doing anything with it.

## HOW TO USE

There is no new button. Company → Coverage → VECTOR VIEW continues with its existing native map launcher.

## VERIFY

Dedicated Node tests inspect the layer namespace and preserve the M18 viewport and M13 launch contracts. Native Wayland behavior has not been tested on the operator desktop.

## WATCH OUT FOR

This is a discovery label only. Stage Director currently exposes a Weather-only WATCH interface; Company needs a separate implementation. Do not reload local Quickshell without approval.

## CHECKLIST

- [x] Stable Company layer namespace in repository source
- [x] Source and regression tests
- [ ] CI verification
- [ ] Review and merge
- [ ] Native Company observer and independent host verification
- [ ] Operator visual acceptance

## NEXT

SwayPX can implement read-only Company host observations using this stable label and the existing M19 compositor geometry preflight.

## DECISIONS

Draft GitHub source change only. No local file modifications, merge or production activation.
