# Known-good Fedora 44 base and Quickshell RPM from diagnostic #2913.
FROM fedora:44@sha256:15da97ed9aa94dd3d92c3925eb89520f6c80e07ea7ee24cba848d1f8b6912b3e
RUN dnf install -y --setopt=install_weak_deps=False dnf5-plugins \
 && dnf copr enable -y errornointernet/quickshell \
 && dnf install -y --setopt=install_weak_deps=False \
    --setopt=skip_if_unavailable=False \
    quickshell-0.3.2-1.fc44 qt6-qtdeclarative qt6-qt5compat qt6-qtbase-gui \
    qt6-qtsvg git nodejs python3 coreutils findutils xdotool xorg-x11-server-Xvfb \
 && test "$(rpm -q --queryformat '%{VERSION}-%{RELEASE}' quickshell)" = "0.3.2-1.fc44" \
 && quickshell --version \
 && dnf clean all
