# CPU++ // TRUE COLD-START GLOW ISOLATION

**Hospital // Nurse 3p // temporary diagnostic, not a permanent repair**

The UI selector starts at BASE on every Quickshell process launch unless a
startup environment variable is set. Switching the UI selector from BASE to
C or D *after* launch is not a true cold-start experiment, since both samplers
may already have attached.

The live Quickshell configuration must include this diagnostic version of
`widgets/CpuPlusW.qml`. From the updated project checkout run:

```bash
# C = ONLY Main Mode icon sample glow attached during initial QML creation
POST_APOLLO_CPU_GLOW_TEST=C bash scripts/restart_quickshell_safe.sh

# D = ONLY Main Mode caption sample glow attached during initial QML creation
POST_APOLLO_CPU_GLOW_TEST=D bash scripts/restart_quickshell_safe.sh

# E = both sampled glows ON, whole-button scale held exactly at 1.0
POST_APOLLO_CPU_GLOW_TEST=E bash scripts/restart_quickshell_safe.sh

# Baseline, neither override; both samples attach normally
bash scripts/restart_quickshell_safe.sh
```

The safe restart script kills the old Quickshell **process** to avoid
Qt's in-process ShaderEffectSource teardown crashes, then starts the
replacement with file watching disabled. The environment variable is
inherited by the new Quickshell process. Do not merely reload QML,
and do not launch a second parallel Quickshell instance.

If the live config lives somewhere other than
`${XDG_CONFIG_HOME:-$HOME/.config}/quickshell`, pass its directory
as the restart script's first positional argument.

Expected initial highlighted selector: C / ICON for `C`, D / LABEL for
`D`, E / FIXED for `E`, BASE otherwise. Do not click BASE before recording the first-open
result. Open CPU++ once, record scattering, close/reopen the menu without
restarting Quickshell, then record the second-open result.

All other CPU++ behavior, including scaling, THERMAL's independent
artwork, and perimeter halos is unchanged. This does not alter
`SafeDropShadow`, `TextHashGlow`, or `ModeButton`.

**Operator result needed for each C / D:** Does scattering appear on first
opening? Does it appear on the second opening? The source owner should
correlate those observations with the static QML conditions.

## E // FIXED-SCALE CONTROL

The operator confirmed C and D were selected on first launch, and the
rendering defect seems to affect the opposite displayed text cluster.
E is a **new** diagnostic: both glows remain enabled, while the entire
CPU++ Main Mode button uses `scale: 1.0` in idle, selected, hover and
pressed states. Text face changes, source capture, and all perimeter halos
remain active. Test E on first open and after closing/reopening, using a
fresh Quickshell process. Compare against BASE. This differentiates a
whole-button transform-specific defect from broader source sampling/painting.
It does not establish whether a texture or placement is at fault.
