# C4b CI-only signed policy companion for transactional Silverblue layering.
# Do not install on a workstation or treat the disposable signature as release trust.
Name:           postapollo-connections-c4b-policy-ci
Version:        0.1
Release:        1%{?dist}
Summary:        Disposable Post Apollo fake Connections SELinux policy for OSTree tests
License:        MIT
BuildArch:      noarch
Source0:        postapollo_connections.pp
Requires:       selinux-policy-targeted
Requires(post): policycoreutils

%description
Synthetic confined Connections status-service policy for isolated, networkless
Fedora Silverblue CI only. Never a production release or installer.

%prep

%build

%install
install -D -m 0644 %{SOURCE0} \
  %{buildroot}%{_datadir}/selinux/packages/targeted/postapollo_connections.pp

# RPM-OSTree executes scriptlets against the new deployment before composing
# the OSTree commit; libostree labels the signed executable from this policy.
%post
/usr/sbin/semodule -i /usr/share/selinux/packages/targeted/postapollo_connections.pp

%postun
if [ "$1" -eq 0 ]; then
  /usr/sbin/semodule -r postapollo_connections
fi

%files
%{_datadir}/selinux/packages/targeted/postapollo_connections.pp
