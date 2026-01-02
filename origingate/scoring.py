from __future__ import annotations
from typing import Dict, List, Tuple
from .models import SoftwareOriginDossier, ScoreWeights

CRIT_WEIGHT = {
    "crypto": 0.35,
    "auth": 0.25,
    "network": 0.20,
    "data": 0.12,
    "ui": 0.05,
    "other": 0.03,
}

US_REGIONS = {"us-east-1","us-east-2","us-west-1","us-west-2","us-gov-east-1","us-gov-west-1"}

def _signal_build(d: SoftwareOriginDossier, target: str) -> Tuple[float, str]:
    region = (d.provenance.build_region or "").lower()
    if target.upper() == "US":
        ok = region in US_REGIONS
        return (1.0 if ok else 0.0, f"Build region={d.provenance.build_region} -> {'US' if ok else 'non-US'}")
    ok = d.provenance.build_region.upper() == target.upper()
    return (1.0 if ok else 0.0, f"Build region={d.provenance.build_region} vs target={target}")

def _signal_signing(d: SoftwareOriginDossier, target: str) -> Tuple[float, str]:
    kj = (d.signing.key_jurisdiction or "").upper()
    ok = kj == target.upper()
    return (1.0 if ok else 0.0, f"Signing key jurisdiction={kj} vs target={target.upper()}")

def _signal_hosting(d: SoftwareOriginDossier, target: str) -> Tuple[float, str]:
    if not d.hosting or not d.hosting.jurisdiction:
        return (0.5, "Hosting jurisdiction missing -> neutral 0.5")
    hj = d.hosting.jurisdiction.upper()
    ok = hj == target.upper()
    return (1.0 if ok else 0.0, f"Hosting jurisdiction={hj} vs target={target.upper()}")

def compute_foi(d: SoftwareOriginDossier, target: str) -> Tuple[float, List[str]]:
    foi = 0.0
    explanations: List[str] = []
    top_contrib = []

    for c in d.sbom.components:
        crit = c.criticality
        v = CRIT_WEIGHT.get(crit, 0.03)
        # foreign-control risk is already 0..1; if supplier is target, dampen
        supplier = (c.supplier_jurisdiction or "").upper()
        r = c.foreign_control_risk
        if supplier == target.upper():
            r = min(r, 0.15)
        contrib = v * r
        foi += contrib
        top_contrib.append((contrib, c.name, crit, supplier, r))

    top_contrib.sort(reverse=True, key=lambda x: x[0])
    for contrib, name, crit, supplier, r in top_contrib[:8]:
        explanations.append(f"FOI contrib {contrib:.3f}: {name} ({crit}) supplier={supplier} risk={r:.2f}")

    # scale to a more human-friendly range
    foi_scaled = foi * 100.0
    return foi_scaled, explanations

def compute_ocssbomsignal(d: SoftwareOriginDossier, target: str) -> Tuple[float, str]:
    # Convert FOI into an SBOM-origin signal in [0,1]: higher FOI -> lower O_c
    foi_scaled, _ = compute_foi(d, target)
    # normalize with a soft cap; 0 -> 1, 50 -> ~0.5, 100 -> ~0.33
    oc = 1.0 / (1.0 + (foi_scaled / 50.0))
    return float(max(0.0, min(1.0, oc))), f"SBOM signal from FOI={foi_scaled:.2f} -> O_c={oc:.2f}"

def score_origin(d: SoftwareOriginDossier, weights: ScoreWeights, target: str="US") -> Tuple[float, float, Dict[str,float], List[str]]:
    explanations: List[str] = []

    O_b, eb = _signal_build(d, target); explanations.append(eb)
    O_s, es = _signal_signing(d, target); explanations.append(es)
    O_h, eh = _signal_hosting(d, target); explanations.append(eh)
    O_c, ec = compute_ocssbomsignal(d, target); explanations.append(ec)

    foi, foi_expl = compute_foi(d, target)
    explanations.extend(foi_expl)

    ocs = (
        weights.w_build * O_b +
        weights.w_sbom * O_c +
        weights.w_signing * O_s +
        weights.w_hosting * O_h
    )

    signals = {"O_b":O_b, "O_c":O_c, "O_s":O_s, "O_h":O_h}
    return float(round(ocs,4)), float(round(foi,4)), signals, explanations
