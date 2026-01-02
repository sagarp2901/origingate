from __future__ import annotations
from typing import List
from .models import SoftwareOriginDossier, VerifyResponse

def verify_dossier(d: SoftwareOriginDossier) -> VerifyResponse:
    errors: List[str] = []

    # Demo verification: ensure digest is sha256:...
    if not d.artifact.digest.startswith("sha256:"):
        errors.append("artifact.digest must start with 'sha256:'")

    # Demo signing check
    if not d.signing.signature:
        errors.append("missing signing.signature")

    # SBOM sanity
    if len(d.sbom.components) == 0:
        errors.append("sbom.components empty")

    ok = len(errors) == 0
    return VerifyResponse(ok=ok, errors=errors)
