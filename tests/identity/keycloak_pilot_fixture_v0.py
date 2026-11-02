"""Generate a short-lived, disposable Keycloak CI realm with random test secrets.

Only run inside an isolated CI runner. This does not use real staff details or
touch any Post-Apollo desktop accounts. All secrets are ephemeral test values.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import secrets
import stat


def _private_json(path: Path, data: object) -> None:
    flags = os.O_CREAT | os.O_WRONLY | os.O_EXCL
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fp:
        json.dump(data, fp)


def prepare(root: Path) -> None:
    root = root.resolve()
    root.mkdir(mode=0o755, parents=True, exist_ok=False)
    (root / "import").mkdir(mode=0o755)
    worker_password = secrets.token_urlsafe(32)
    introspection_secret = secrets.token_urlsafe(40)
    admin_password = secrets.token_urlsafe(40)

    realm = {
        "realm": "post-apollo-disposable",
        "enabled": True,
        "displayName": "Disposable Post-Apollo CI Only",
        "sslRequired": "none",  # ONLY within loopback CI test container.
        "registrationAllowed": False,
        "resetPasswordAllowed": False,
        "loginWithEmailAllowed": False,
        "accessTokenLifespan": 300,
        "users": [{
            "username": "pilot-worker",
            "enabled": True,
            "email": "worker@ci.invalid",
            "emailVerified": True,
            "firstName": "Synthetic",
            "lastName": "Worker",
            "credentials": [{
                "type": "password",
                "value": worker_password,
                "temporary": False,
            }],
            "requiredActions": [],
        }],
        "clients": [
            {
                "clientId": "post-apollo-pilot-public",
                "name": "Disposable PKCE browser client",
                "enabled": True,
                "protocol": "openid-connect",
                "publicClient": True,
                "standardFlowEnabled": True,
                "implicitFlowEnabled": False,
                "directAccessGrantsEnabled": False,
                "serviceAccountsEnabled": False,
                "redirectUris": ["http://127.0.0.1:8765/callback"],
                "webOrigins": [],
                "attributes": {"pkce.code.challenge.method": "S256"},
                "protocolMappers": [{
                    "name": "Pilot API audience",
                    "protocol": "openid-connect",
                    "protocolMapper": "oidc-audience-mapper",
                    "consentRequired": False,
                    "config": {
                        "included.client.audience": "post-apollo-pilot-api",
                        "access.token.claim": "true",
                        "id.token.claim": "false",
                        "introspection.token.claim": "true",
                    },
                }],
            },
            {
                "clientId": "post-apollo-pilot-api",
                "name": "Disposable confidential introspection client",
                "enabled": True,
                "protocol": "openid-connect",
                "publicClient": False,
                "secret": introspection_secret,
                "standardFlowEnabled": False,
                "implicitFlowEnabled": False,
                "directAccessGrantsEnabled": False,
                "serviceAccountsEnabled": False,
            },
        ],
    }
    _private_json(root / "import" / "post-apollo-disposable-realm.json", realm)
    # Keycloak's container UID differs from the CI runner. Only the throwaway
    # import is world-readable so the container can read it; random admin and
    # runner test credentials outside /import stay mode 0600.
    (root / "import" / "post-apollo-disposable-realm.json").chmod(0o644)
    _private_json(root / "runtime.json", {
        "username": "pilot-worker",
        "password": worker_password,
        "introspection_secret": introspection_secret,
    })
    path = root / "admin-password"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fp:
        fp.write(admin_password)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    options = parser.parse_args()
    prepare(options.directory)
    print("Disposable Keycloak realm and test credentials generated.")
