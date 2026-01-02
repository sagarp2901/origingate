from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional
from .models import SoftwareOriginDossier

@dataclass
class Baseline:
    baseline_id: str
    ocs0: float
    foi0: float
    artifact_digest: str

_BASELINES: Dict[str, Baseline] = {}

def put_baseline(b: Baseline) -> None:
    _BASELINES[b.baseline_id] = b

def get_baseline(baseline_id: str) -> Optional[Baseline]:
    return _BASELINES.get(baseline_id)
