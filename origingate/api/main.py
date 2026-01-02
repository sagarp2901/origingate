from __future__ import annotations
from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
import os

from ..models import (
    VerifyResponse, ScoreRequest, ScoreResponse,
    DecideRequest, DecisionResponse,
    AssessRequest, AssessResponse,
    BaselineCreateRequest, BaselineCreateResponse,
    UpdateEvaluateRequest, UpdateEvaluateResponse,
)
from ..verify import verify_dossier
from ..scoring import score_origin
from ..policy import decide
from ..store import Baseline, put_baseline, get_baseline

app = FastAPI(title="OriginGate", version="0.1.0")

@app.get("/v1/health")
def health():
    return {"ok": True, "service": "origingate", "version": "0.1.0"}

@app.get("/v1/openapi.yaml", response_class=PlainTextResponse)
def openapi_yaml():
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    path = os.path.join(repo_root, "openapi.yaml")
    return open(path, "r", encoding="utf-8").read()

@app.post("/v1/dossiers/verify", response_model=VerifyResponse)
def dossiers_verify(req: dict):
    # We accept dict so users can post raw JSON; validate into model
    try:
        from ..models import SoftwareOriginDossier
        d = SoftwareOriginDossier.model_validate(req)
    except Exception as e:
        return VerifyResponse(ok=False, errors=[f"schema validation error: {e}"])
    return verify_dossier(d)

@app.post("/v1/origin/score", response_model=ScoreResponse)
def origin_score(req: ScoreRequest):
    vr = verify_dossier(req.dossier)
    if not vr.ok:
        raise HTTPException(status_code=400, detail={"errors": vr.errors})
    ocs, foi, signals, explanations = score_origin(req.dossier, req.weights, req.target_jurisdiction)
    return ScoreResponse(ocs=ocs, foi=foi, signals=signals, explanations=explanations)

@app.post("/v1/policy/decide", response_model=DecisionResponse)
def policy_decide(req: DecideRequest):
    return decide(req.ocs, req.foi, req.policy_name, req.context)

@app.post("/v1/assess", response_model=AssessResponse)
def assess(req: AssessRequest):
    vr = verify_dossier(req.dossier)
    if not vr.ok:
        raise HTTPException(status_code=400, detail={"errors": vr.errors})
    ocs, foi, signals, explanations = score_origin(req.dossier, target=req.target_jurisdiction, weights=__import__("origingate.models", fromlist=["ScoreWeights"]).ScoreWeights())
    decision = decide(ocs, foi, req.policy_name, req.context)
    return AssessResponse(**decision.model_dump(), ocs=ocs, foi=foi, explanations=explanations)

@app.post("/v1/baselines", response_model=BaselineCreateResponse)
def create_baseline(req: BaselineCreateRequest):
    vr = verify_dossier(req.dossier)
    if not vr.ok:
        raise HTTPException(status_code=400, detail={"errors": vr.errors})
    from ..models import ScoreWeights
    ocs, foi, _, _ = score_origin(req.dossier, ScoreWeights(), req.target_jurisdiction)
    put_baseline(Baseline(baseline_id=req.baseline_id, ocs0=ocs, foi0=foi, artifact_digest=req.dossier.artifact.digest))
    return BaselineCreateResponse(baseline_id=req.baseline_id, ocs0=ocs, foi0=foi)

@app.post("/v1/updates/evaluate", response_model=UpdateEvaluateResponse)
def evaluate_update(req: UpdateEvaluateRequest):
    b = get_baseline(req.baseline_id)
    if not b:
        raise HTTPException(status_code=404, detail="baseline not found")
    from ..models import ScoreWeights
    # Score update
    vr = verify_dossier(req.dossier)
    if not vr.ok:
        raise HTTPException(status_code=400, detail={"errors": vr.errors})
    ocs, foi, _, _ = score_origin(req.dossier, ScoreWeights(), "US")
    drift = float(round(b.ocs0 - ocs, 4))
    reclassify = drift > float(req.drift_threshold)
    decision = decide(ocs, foi, req.policy_name, req.context)
    return UpdateEvaluateResponse(baseline_id=req.baseline_id, drift=drift, reclassify=reclassify, decision=decision)
