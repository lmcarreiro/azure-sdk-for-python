# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------
import binascii

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
from msal.oauth2cli import JwtSigner

from ._constants import Endpoints

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    # pylint:disable=unused-import
    from typing import Any, Mapping


class ClientSecretCredentialBase(object):
    """Sans I/O base for client secret credentials"""

    def __init__(self, tenant_id, client_id, secret, **kwargs):  # pylint:disable=unused-argument
        # type: (str, str, str, **Any) -> None
        if not client_id:
            raise ValueError("client_id should be the id of an Azure Active Directory application")
        if not secret:
            raise ValueError("secret should be an Azure Active Directory application's client secret")
        if not tenant_id:
            raise ValueError(
                "tenant_id should be an Azure Active Directory tenant's id (also called its 'directory id')"
            )
        self._form_data = {"client_id": client_id, "client_secret": secret, "grant_type": "client_credentials"}
        super(ClientSecretCredentialBase, self).__init__()


class CertificateCredentialBase(object):
    """Sans I/O base for certificate credentials"""

    def __init__(self, tenant_id, client_id, certificate_path, **kwargs):  # pylint:disable=unused-argument
        # type: (str, str, str, **Any) -> None
        if not certificate_path:
            raise ValueError(
                "certificate_path must be the path to a PEM file containing an "
                "x509 certificate and its private key, not protected with a password"
            )

        super(CertificateCredentialBase, self).__init__()

        with open(certificate_path, "rb") as f:
            pem_bytes = f.read()

        private_key = serialization.load_pem_private_key(pem_bytes, password=None, backend=default_backend())
        cert = x509.load_pem_x509_certificate(pem_bytes, default_backend())
        fingerprint = cert.fingerprint(hashes.SHA1())

        self._auth_url = Endpoints.AAD_OAUTH2_V2_FORMAT.format(tenant_id)
        self._client_id = client_id
        self._signer = JwtSigner(private_key, "RS256", sha1_thumbprint=binascii.hexlify(fingerprint))

    def _get_request_data(self, *scopes):
        assertion = self._signer.sign_assertion(audience=self._auth_url, issuer=self._client_id)
        return {
            "client_assertion": assertion,
            "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
            "client_id": self._client_id,
            "grant_type": "client_credentials",
            "scope": " ".join(scopes)
        }
