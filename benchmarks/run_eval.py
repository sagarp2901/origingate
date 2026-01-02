from __future__ import annotations
import json
from pathlib import Path
from collections import Counter
from origingate.models import SoftwareOriginDossier, ScoreWeights
from origingate.verify import verify_dossier
from origingate.scoring import score_origin
from origingate.policy import decide

def load(portfolio_dir: str):
    p = Path(portfolio_dir)
    labels = json.loads((p / "labels.json").read_text())
    items = []
    for row in labels:
        d = json.loads((p / row["file"]).read_text())
        items.append((row["file"], row["class"], SoftwareOriginDossier.model_validate(d)))
    return items

def confusion(pred, truth):
    tp = sum(1 for p,t in zip(pred,truth) if p and t)
    fp = sum(1 for p,t in zip(pred,truth) if p and not t)
    fn = sum(1 for p,t in zip(pred,truth) if (not p) and t)
    tn = sum(1 for p,t in zip(pred,truth) if (not p) and (not t))
    prec = tp / (tp+fp) if (tp+fp) else 0.0
    rec = tp / (tp+fn) if (tp+fn) else 0.0
    return {"tp":tp,"fp":fp,"fn":fn,"tn":tn,"precision":round(prec,3),"recall":round(rec,3)}

def main(portfolio_dir="portfolio_out", policy="enterprise_moderate"):
    items = load(portfolio_dir)
    w = ScoreWeights()
    counts = Counter()
    pred_foreign = []
    truth_foreign = []

    for fn, cls, dossier in items:
        vr = verify_dossier(dossier)
        if not vr.ok:
            counts["invalid"] += 1
            continue
        ocs, foi, _, _ = score_origin(dossier, w, "US")
        # define truth foreign: foreign or laundered are foreign-dominant
        truth = cls in ("foreign","laundered")
        # prediction foreign: based on thresholds used by decision engine
        dec = decide(ocs, foi, policy, {"annual_usage_usd": 1_000_000})
        pred = dec.verdict in ("ALLOW_WITH_FEE","DENY") and ocs < 0.60 and foi > 25.0
        pred_foreign.append(pred)
        truth_foreign.append(truth)
        counts[dec.verdict] += 1

    print("Verdicts:", dict(counts))
    print("Foreign detection:", confusion(pred_foreign, truth_foreign))

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--portfolio", default="portfolio_out")
    ap.add_argument("--policy", default="enterprise_moderate")
    args = ap.parse_args()
    main(args.portfolio, args.policy)
