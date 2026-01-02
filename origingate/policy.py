from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple
import os, yaml
from .models import DecisionResponse

POLICY_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "policies")

@dataclass
class Policy:
    name: str
    thresholds: Dict[str, float]
    actions: Dict[str, List[str]]
    fee: Dict[str, Any]
    review_band: Dict[str, float] | None = None

def load_policy(name: str) -> Policy:
    path = os.path.join(POLICY_DIR, f"{name}.yaml")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Policy not found: {path}")
    data = yaml.safe_load(open(path, "r", encoding="utf-8"))
    return Policy(
        name=data["name"],
        thresholds=data.get("thresholds", {}),
        actions=data.get("actions", {}),
        fee=data.get("fee", {"enabled": False}),
        review_band=data.get("review_band"),
    )

def decide(ocs: float, foi: float, policy_name: str, context: Dict[str, Any] | None = None) -> DecisionResponse:
    context = context or {}
    p = load_policy(policy_name)

    tau = float(p.thresholds.get("tau_min_ocs", 0.6))
    gamma = float(p.thresholds.get("gamma_max_foi", 25.0))

    reasons: List[str] = []
    actions: List[str] = []
    fee_usd = 0.0

    # review band (optional)
    if p.review_band:
        low = float(p.review_band.get("ocs_low", 0.45))
        high = float(p.review_band.get("ocs_high", tau))
        if low <= ocs < high:
            verdict = "REVIEW"
            allow = False
            reasons.append(f"OCS in review band: {ocs:.3f} in [{low},{high})")
            actions = p.actions.get("on_review", ["log_audit","manual_review"])
            return DecisionResponse(verdict=verdict, allow=allow, fee_usd=fee_usd, actions=actions, reasons=reasons)

    # allow path
    if ocs >= tau and foi <= gamma:
        verdict = "ALLOW"
        allow = True
        reasons.append(f"Meets thresholds: OCS={ocs:.3f}>=tau={tau}, FOI={foi:.2f}<=gamma={gamma}")
        actions = p.actions.get("on_allow", ["log_audit","approve"])
    else:
        # foreign-dominant path
        if ocs < tau and foi > gamma:
            verdict = "ALLOW_WITH_FEE" if p.fee.get("enabled", False) else "DENY"
            allow = p.fee.get("enabled", False)
            reasons.append(f"Foreign-dominant: OCS={ocs:.3f}<tau={tau} and FOI={foi:.2f}>gamma={gamma}")
            if allow:
                actions = p.actions.get("on_allow", ["log_audit","approve"])
            else:
                actions = p.actions.get("on_deny", ["log_audit","deny"])
        else:
            verdict = "DENY"
            allow = False
            reasons.append(f"Does not meet thresholds: OCS={ocs:.3f}, FOI={foi:.2f}")
            actions = p.actions.get("on_deny", ["log_audit","deny"])

    # fee calculation if enabled + allowed
    if allow and p.fee.get("enabled", False):
        rate = float(p.fee.get("rate", 0.10))
        usage_field = p.fee.get("usage_field", "annual_usage_usd")
        U = float(context.get(usage_field, 0.0))
        fee_usd = max(0.0, U * rate * (1.0 - float(ocs)))
        reasons.append(f"Fee computed: U={U} rate={rate} (1-OCS)={1-ocs:.3f} => fee={fee_usd:.2f}")

    return DecisionResponse(verdict=verdict, allow=allow, fee_usd=float(round(fee_usd,2)), actions=actions, reasons=reasons)
