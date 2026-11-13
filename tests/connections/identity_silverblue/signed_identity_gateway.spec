Name:           post-apollo-identity-silverblue-ci
Version:        0.1
Release:        1%{?dist}
Summary:        Disposable deny-only Identity command gateway for Silverblue CI
License:        LicenseRef-PostApollo-Test-Only
BuildArch:      noarch
AutoReqProv:    no
# These are the byte-exact Identity DOC files measured by the separate
# release manifest. Fedora BRP normally rewrites the entrypoint shebang
# and strips executable mode from Python modules without a shebang.
# Refuse that mutation; builder separately checks all nine exact bytes/modes.
%undefine __brp_mangle_shebangs

%description
CI-only exact Identity command gateway with deny-only human/seat/peer callbacks.
No provider secrets, release root, receipt signing key, startup scriptlet, or
production authentication. Installation and SELinux verification are separate.

%prep
# Eight immutable source files staged from the reviewed Identity implementation.

%build
# Do not generate or download Python code.

%install
install -D -m 0555 %{_sourcedir}/identity-gateway-ci %{buildroot}/usr/libexec/post-apollo/identity/identity-gateway-ci
install -D -m 0555 %{_sourcedir}/desktop_command_gateway_v0.py %{buildroot}/usr/libexec/post-apollo/identity/desktop_command_gateway_v0.py
install -D -m 0555 %{_sourcedir}/desktop_host_lifecycle_v0.py %{buildroot}/usr/libexec/post-apollo/identity/desktop_host_lifecycle_v0.py
install -D -m 0555 %{_sourcedir}/desktop_context_projection_v0.py %{buildroot}/usr/libexec/post-apollo/identity/desktop_context_projection_v0.py
install -D -m 0555 %{_sourcedir}/desktop_session_host_v0.py %{buildroot}/usr/libexec/post-apollo/identity/desktop_session_host_v0.py
install -D -m 0555 %{_sourcedir}/native_loopback_callback_v0.py %{buildroot}/usr/libexec/post-apollo/identity/native_loopback_callback_v0.py
install -D -m 0555 %{_sourcedir}/private_context_ipc_v0.py %{buildroot}/usr/libexec/post-apollo/identity/private_context_ipc_v0.py
install -D -m 0555 %{_sourcedir}/signed_command_receipt_v0.py %{buildroot}/usr/libexec/post-apollo/identity/signed_command_receipt_v0.py
install -D -m 0644 %{_sourcedir}/post-apollo-identity-silverblue-ci.service %{buildroot}/usr/lib/systemd/system/post-apollo-identity-silverblue-ci.service

%files
/usr/libexec/post-apollo/identity/identity-gateway-ci
/usr/libexec/post-apollo/identity/desktop_command_gateway_v0.py
/usr/libexec/post-apollo/identity/desktop_host_lifecycle_v0.py
/usr/libexec/post-apollo/identity/desktop_context_projection_v0.py
/usr/libexec/post-apollo/identity/desktop_session_host_v0.py
/usr/libexec/post-apollo/identity/native_loopback_callback_v0.py
/usr/libexec/post-apollo/identity/private_context_ipc_v0.py
/usr/libexec/post-apollo/identity/signed_command_receipt_v0.py
/usr/lib/systemd/system/post-apollo-identity-silverblue-ci.service

# No RPM scriptlets, triggers, automatic systemd enablement or SELinux mutation.
