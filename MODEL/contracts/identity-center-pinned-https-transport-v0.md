# Identity Center // pinned HTTPS metadata and context reader v0

> **STATUS:** GitHub review-branch, experimental host-owned network transport; exact-head CI and independent security review pending. This is not a deployed session host or approved identity provider.
>
> **PATIENT:** `kudokudo1/The-Post-Apollo-Project`.
>
> **SOURCE:** Operator continuation after the explicit CI-only host lifecycle PR #1460 was merged into main. Source inspected at current main. Scope is a bounded read-only HTTPS transport needed before real authenticated Identity Center work.
>
> **OWNER / JURISDICTION:** Identity Center trusted native host. CPU++ and Social are consumers of token-free display snapshots, not holders of bearer tokens or Identity Center grant authority.

## Mechanism and changes

The current `DesktopHostLifecycle` already expects the protected host to inject an authenticated `api_get(access_token)` callback. `TrustedDiscoveryVerifier` expects a trusted `fetch_json(url)` callback for two preapproved issuer paths. These callbacks were previously supplied by synthetic fixtures or host-agnostic functions. This milestone contributes one reusable host-only adapter:

```text
[ separately approved host configuration, NEVER from QML ]
    pinned HTTPS issuer & JWKS URL
    pinned GET https://<separately approved API host>/v0/me/contexts
    timeout / optional explicitly trusted local CA bundle
                         |
              HostPinnedHttpsTransport
    Python stdlib ssl.create_default_context()
    peer certificate + hostname verification REQUIRED
    minimum TLS 1.2; no environment proxy; no redirects
    exact approved metadata/JWKS URLs and one current-user API path
    strict response content type, identity encoding, <=64 KiB body
    generic error status, no URL / server body / token in errors
                         |
              /                          \
  fetch_json(host-pinned URL)       get_contexts(host memory-only bearer)
  metadata/JWKS only               Authorization: Bearer sent over pinned TLS
              |                          |
  existing TrustedDiscoveryVerifier   HostContextReply status+bounded body
  still verifies issuer/S256/JWKS     only exposed to existing
                                     DesktopContextProjection
                                                 |
                                     validated tokenless JSON
                                                 |
                          existing private AF_UNIX display socket
                              existing CPU++/Social read-only viewers
```

`PinnedIdentityHttpsConfig` does not call DNS, open a socket, fetch a file, start an OAuth login, create a directory or change machine settings on construction. A trusted owner process supplies explicit issuer/JWKS/API URLs; API URL must have exactly `/v0/me/contexts` with no query string or client-selected organization, principal, role or credentials. The JWKS URL is on the issuer origin. A caller can only request the exact metadata or JWKS URL on the allowlist. Dynamic URL values from JWT fields, account labels, redirects or provider metadata do not become new trusted endpoints.

The adapter deliberately exposes **no POST, OAuth code exchange, password, login, logout, organization switch, role grant or permission administration**. The previously merged host lifecycle still requires a protected real signed OIDC verifier and token exchange before an actual session can become authenticated. A successful TLS request is **not** proof that its JSON contains legitimate grants; only the separately validated account-context projection can interpret it, and even that projection is display-only. Server-side grants must be rechecked for each business operation.

## Failure and privacy behavior

- Reject non-HTTPS URLs, embedded username/password, fragments, queries, path traversal, percent-escaped endpoints, backslashes, control characters and inconsistent issuer/JWKS origins.
- Use system TLS certificate and host-name verification with `ssl.CERT_REQUIRED` and `check_hostname=True`, minimum TLSv1.2. Trusting an alternative CA bundle is possible only through explicit host-owned absolute-path configuration; no insecure-skip-verify toggle exists.
- Do not follow HTTP redirect responses. Reject unusual status codes, compressed bodies, non-JSON media types, invalid/oversized content-length or bodies above 64 KiB. Bearer strings with whitespace/control characters are rejected before network I/O.
- On 401/403 return only denied status with fixed generic JSON, never provider response content. All other transport failures become generic 503 response. This is suitable for the existing `DesktopContextProjection` to clear old data.
- Strict JSON parser rejects duplicate keys, nonfinite values, invalid UTF-8 and non-object issuer metadata; the existing `TrustedDiscoveryVerifier` is still responsible for issuer, endpoint, S256/JWKS signature and key-trust policy.
- No error messages include user tokens, issuer paths, server messages, local file paths or private identity attributes.

## Verification and limitations

`tests/identity/test_pinned_https_identity_transport_v0.py` starts a disposable **127.0.0.1 HTTPS** server in GitHub CI, with an isolated self-signed `localhost` certificate generated into a test temporary directory. This lets the test verify **real certificate and hostname checks** rather than a mocked network, with no connection to any real identity provider. Tests cover a real host-only API GET feeding the existing tokenless `DesktopContextProjection`, exact issuer metadata/JWKS requests, unauthorized/redirect/invalid-body failures, wrong CA and wrong hostname, invalid URLs and bearer rejection. Adjacent host, projection, discovery and CPU++ contracts must remain green.

The test-only self-signed CA is passed explicitly and is **not** an endorsement of self-signed production IdP certificates. This work does not pin a specific production CA/issuer, provide revocation, evaluate certificate transparency/mTLS/DPoP, choose a real IdP, secure an operating-system credential vault, run a separate privileged process, manage systemd services or perform real SSO login. It makes host-origin HTTPS reads concrete, not production-ready.

## Hospital-compatible checkpoint

### IMPLEMENTATION
Add one host-only exact-URL, TLS-verifying read transport, real disposable TLS tests, dedicated workflow and this indexed contract. No changes to existing CPU++ dimensions, Social IDs, local associations or existing host state machine.

### HOW TO USE
For review/CI. In code, a separately approved native host creates `PinnedIdentityHttpsConfig(...)` and passes `HostPinnedHttpsTransport.get_contexts` as the existing `api_get` callback or `fetch_json` to existing discovery verifier. No supported new live user control or local install.

### VERIFY
Exact-head GitHub CI required, followed by independent security review and eventually a real trusted host pilot. CI cannot prove real-company authentication.

### WATCH OUT FOR
Host owns trust configuration; QML has no credential-bearing API. Never accept pinned URLs from a JWT, discovery document, user-controlled field or local Social label. HTTPS does not replace verified IdP token/tenant membership checks.

### CHECKLIST
- [x] Host-pinned read-only metadata and context GET implementation
- [x] Refuse redirect, wrong host, invalid TLS, invalid bearer and oversized JSON
- [x] Real test-only HTTPS server and negative test cases
- [x] Link to host/projection contracts
- [ ] CI verified at exact head
- [ ] Independent identity/security review
- [ ] Real OIDC signed token exchange, trust config, native host isolation and operator desktop acceptance

### NEXT
Review transport with identity/security owner; separately implement host-owned standards-based OIDC code exchange and cryptographic validation against approved issuer and client, then bind into the existing explicit lifecycle. A real OAuth client, service endpoints and desktop activation require further operator approval.

### DECISIONS
No newly selected IdP, no real account or organization data, no QML bearer, no OAuth token exchange, no production service, no local machine writes, no merge/activation without operator authority.

**Hospital status:** External browser contributor, no verified registered Room/Assignment, Staff Role or desktop session. The PR remains the technical recovery pointer.
