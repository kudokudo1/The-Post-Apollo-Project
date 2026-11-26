# Native CI image pilot

This is a separate Fedora 44 Xvfb candidate, not a replacement for all test environments. The existing native tests currently install dependencies independently. The pilot pins the Fedora base digest and exact known-good Quickshell RPM, fails closed on unavailable package metadata, and records the resulting image ID and size. Other RPM versions resolve at build time; a future published immutable digest will fix the complete installed environment.

Only changes to this pilot trigger its two jobs, or an explicit workflow dispatch. No existing workflow is changed. The build produces a short-lived image archive, then a separate fresh runner verifies and loads it and runs the existing U1/U2/U3 probes with networking disabled. No secrets, privileged container, host display or production data. Artifact delivery plus load duration is a preliminary measurement, not a registry pull benchmark.

Before adoption: compare actual elapsed setup and test time against healthy existing jobs; qualify a registry-published immutable digest and cold-pull timing; review provenance, package updates and permissions; opt in one workflow at a time. Do not route ordinary JS/Python tests through this image. Debian and isolated Wayland/Sway jobs are separate profiles and remain unchanged. Do not publish or change consumers until review.
