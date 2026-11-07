Name:           postapollo-connections-c3d-ci-status
Version:        0.1
Release:        1%{?dist}
Summary:        Disposable signed fake Post-Apollo Connections status host
License:        LicenseRef-PostApollo-Test-Only
BuildArch:      noarch
AutoReqProv:    no

%description
CI-only, signed fake read-only service files used with an explicitly started
Fedora SELinux enforcing VM. No real provider, secrets, installer, activation,
account creation, or policy-modifying scriptlets.

%prep
# All input files are version controlled and staged by the test builder.

%build
# No generated executable or downstream fetch.

%install
install -D -m 0555 %{_sourcedir}/C2rStatusHost.py \
  %{buildroot}/usr/libexec/post-apollo/connections-status-host
install -D -m 0644 %{_sourcedir}/postapollo-connections-status.service.template \
  %{buildroot}/usr/lib/systemd/system/postapollo-connections-status.service
install -D -m 0644 %{_sourcedir}/org.postapollo.ConnectionsStatus1.conf.template \
  %{buildroot}/usr/share/dbus-1/system.d/org.postapollo.ConnectionsStatus1.conf

%files
/usr/libexec/post-apollo/connections-status-host
/usr/lib/systemd/system/postapollo-connections-status.service
/usr/share/dbus-1/system.d/org.postapollo.ConnectionsStatus1.conf

# No %pre/%post, %trigger, systemd enablement or SELinux policy installation.
# Dedicated service user and C2r policy exist ONLY inside the disposable guest.
