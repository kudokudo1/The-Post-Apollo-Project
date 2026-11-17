Name:           post-apollo-phone-status-ci
Version:        0.1
Release:        1%{?dist}
Summary:        Disposable PHONE Personal STATUS-only Linux host, no SAVE
License:        LicenseRef-PostApollo-Test-Only
BuildArch:      noarch
AutoReqProv:    no
# Preserve source bytes and refuse rpmbuild shebang rewrites.
%undefine __brp_mangle_shebangs

%description
CI-only PHONE Personal STATUS host, with P47 Linux socket,
P48 peer observation, P49 isolated process entrypoint, P50 signed CI
source-consistency helper and a deliberately non-enabled systemd unit.
No encryption key, vault, contact write, production trust root, C3e or C5.
This package never activates itself or configures SELinux/OSTree.

%prep
# Source is staged byte-for-byte by the separately guarded CI builder.

%build
# No generated code, migrations, provider access, compilation or network.

%install
install -D -m 0555 %{_sourcedir}/PhonePersonalHostSocketP47.py %{buildroot}/usr/libexec/post-apollo/phone/PhonePersonalHostSocketP47.py
install -D -m 0555 %{_sourcedir}/PhonePersonalPeerEvidenceP48.py %{buildroot}/usr/libexec/post-apollo/phone/PhonePersonalPeerEvidenceP48.py
install -D -m 0555 %{_sourcedir}/PhonePersonalStatusHostP49.py %{buildroot}/usr/libexec/post-apollo/phone/PhonePersonalStatusHostP49.py
install -D -m 0555 %{_sourcedir}/PhonePersonalInstalledReleaseP50.py %{buildroot}/usr/libexec/post-apollo/phone/PhonePersonalInstalledReleaseP50.py
install -D -m 0644 %{_sourcedir}/post-apollo-phone-personal-status-ci.service %{buildroot}/usr/libexec/post-apollo/phone/systemd/post-apollo-phone-personal-status-ci.service
install -D -m 0644 %{_sourcedir}/post-apollo-phone-personal-status-ci.service %{buildroot}/usr/lib/systemd/system/post-apollo-phone-personal-status-ci.service

%files
/usr/libexec/post-apollo/phone/PhonePersonalHostSocketP47.py
/usr/libexec/post-apollo/phone/PhonePersonalPeerEvidenceP48.py
/usr/libexec/post-apollo/phone/PhonePersonalStatusHostP49.py
/usr/libexec/post-apollo/phone/PhonePersonalInstalledReleaseP50.py
/usr/libexec/post-apollo/phone/systemd/post-apollo-phone-personal-status-ci.service
/usr/lib/systemd/system/post-apollo-phone-personal-status-ci.service

# Deliberately no %pre, %post, triggers, [Install], host enrollment or SAVE.
