from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class Product(BaseModel):
    name: str
    version: str

class Artifact(BaseModel):
    digest: str
    uri: Optional[str] = None

class Provenance(BaseModel):
    builder_id: str
    build_region: str
    timestamp: str
    source_repo: str
    commit: str

class SBOMComponent(BaseModel):
    name: str
    version: str
    supplier_jurisdiction: str
    criticality: str = Field(pattern="^(crypto|auth|network|data|ui|other)$")
    foreign_control_risk: float = Field(ge=0.0, le=1.0)

class SBOM(BaseModel):
    format: str
    components: List[SBOMComponent]

class Signing(BaseModel):
    key_jurisdiction: str
    signature: str

class Hosting(BaseModel):
    type: Optional[str] = None
    control_plane_region: Optional[str] = None
    jurisdiction: Optional[str] = None

class SoftwareOriginDossier(BaseModel):
    product: Product
    artifact: Artifact
    provenance: Provenance
    sbom: SBOM
    signing: Signing
    hosting: Optional[Hosting] = None
    attestation: Optional[Dict[str, Any]] = None

class VerifyResponse(BaseModel):
    ok: bool
    errors: List[str] = []

class ScoreWeights(BaseModel):
    w_build: float = 0.35
    w_sbom: float = 0.30
    w_signing: float = 0.20
    w_hosting: float = 0.15

class ScoreRequest(BaseModel):
    dossier: SoftwareOriginDossier
    weights: ScoreWeights = ScoreWeights()
    target_jurisdiction: str = "US"

class ScoreResponse(BaseModel):
    ocs: float
    foi: float
    signals: Dict[str, float]
    explanations: List[str]

class DecideRequest(BaseModel):
    ocs: float
    foi: float
    policy_name: str
    context: Dict[str, Any] = {}

class DecisionResponse(BaseModel):
    verdict: str
    allow: bool
    fee_usd: float
    actions: List[str]
    reasons: List[str]

class AssessRequest(BaseModel):
    dossier: SoftwareOriginDossier
    policy_name: str
    context: Dict[str, Any] = {}
    target_jurisdiction: str = "US"

class AssessResponse(DecisionResponse):
    ocs: float
    foi: float
    explanations: List[str]

class BaselineCreateRequest(BaseModel):
    baseline_id: str
    dossier: SoftwareOriginDossier
    policy_name: str
    target_jurisdiction: str = "US"

class BaselineCreateResponse(BaseModel):
    baseline_id: str
    ocs0: float
    foi0: float

class UpdateEvaluateRequest(BaseModel):
    baseline_id: str
    dossier: SoftwareOriginDossier
    policy_name: str
    context: Dict[str, Any] = {}
    drift_threshold: float = 0.10

class UpdateEvaluateResponse(BaseModel):
    baseline_id: str
    drift: float
    reclassify: bool
    decision: DecisionResponse
