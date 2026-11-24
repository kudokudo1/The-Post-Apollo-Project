Name:           post-apollo-forest-host-ci
Version:        0.1
Release:        1%{?dist}
Summary:        Disposable Forest deny-only installed host candidate
License:        LicenseRef-PostApollo-Test-Only
BuildArch:      noarch
AutoReqProv:    no
Requires:       python3
Source0:        native_host_candidate_b5b.py

# Preserve exact B5b bytes and the explicit RPM file modes.
%undefine __brp_mangle_shebangs

%description
CI-only Forest candidate. No private data, service unit, automatic startup,
signing key, credential enrollment, or production permission.

%prep

%build

%install
install -D -m 0555 %{SOURCE0} %{buildroot}/usr/libexec/post-apollo/forest-ci/forest-host
chmod 0755 %{buildroot}/usr/libexec/post-apollo/forest-ci

%files
%attr(0755,root,root) %dir /usr/libexec/post-apollo/forest-ci
%attr(0555,root,root) /usr/libexec/post-apollo/forest-ci/forest-host

# No scriptlets, triggers, service files or activation.
