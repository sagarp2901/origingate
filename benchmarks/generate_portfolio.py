from __future__ import annotations
import json, random, hashlib, datetime
from pathlib import Path

CRITS = ["crypto","auth","network","data","ui","other"]
CRIT_W = [8,7,7,6,3,2]
JURIS = ["US","EU","IN","CN","CA","BR","SG"]

def mk_dossier(name: str, version: str, build_region: str, key_juris: str, hosting_juris: str, foreign_bias: float):
    comps=[]
    for i in range(random.randint(80,250)):
        crit = random.choices(CRITS, weights=CRIT_W)[0]
        supplier = random.choice(JURIS)
        if random.random() < foreign_bias:
            supplier = random.choice([j for j in JURIS if j != "US"])
        risk = 0.08
        if supplier != "US":
            base = {"crypto":0.95,"auth":0.8,"network":0.7,"data":0.6,"ui":0.3,"other":0.2}[crit]
            risk = max(0.05, min(1.0, random.gauss(base, 0.12)))
        else:
            risk = max(0.0, min(0.3, random.gauss(0.08, 0.05)))
        comps.append({
            "name": f"lib{i}",
            "version": f"{random.randint(0,5)}.{random.randint(0,20)}.{random.randint(0,50)}",
            "supplier_jurisdiction": supplier,
            "criticality": crit,
            "foreign_control_risk": round(risk, 3)
        })
    digest = "sha256:" + hashlib.sha256(f"{name}:{version}:{build_region}:{key_juris}".encode()).hexdigest()
    return {
      "product":{"name":name,"version":version},
      "artifact":{"digest":digest,"uri":f"oci://registry.example/{name}:{version}"},
      "provenance":{
        "builder_id":"github-actions://bench",
        "build_region":build_region,
        "timestamp":datetime.datetime.utcnow().isoformat()+"Z",
        "source_repo":"https://git.example/org/repo",
        "commit":hashlib.sha1(version.encode()).hexdigest()[:8]
      },
      "sbom":{"format":"cyclonedx-lite","components":comps},
      "signing":{"key_jurisdiction":key_juris,"signature":"demo"},
      "hosting":{"type":"saas","control_plane_region":"us-east-1","jurisdiction":hosting_juris},
    }

def main(out_dir="portfolio_out", n=200, seed=7):
    random.seed(seed)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    labels = []
    for k in range(n):
        name = f"Prod{k}"
        version = f"{random.randint(0,9)}.{random.randint(0,9)}.{random.randint(0,20)}"
        # 3 classes: domestic, foreign, laundered
        cls = random.choices(["domestic","foreign","laundered"], weights=[0.45,0.35,0.20])[0]
        if cls == "domestic":
            d = mk_dossier(name, version, "us-east-1", "US", "US", foreign_bias=0.10)
        elif cls == "foreign":
            d = mk_dossier(name, version, "eu-central-1", "EU", "US", foreign_bias=0.75)
        else:
            # laundered build: US build + US key but foreign-heavy deps
            d = mk_dossier(name, version, "us-west-2", "US", "US", foreign_bias=0.80)
        fn = out / f"{name}_{version}.json"
        fn.write_text(json.dumps(d, indent=2))
        labels.append({"file": fn.name, "class": cls})
    (out / "labels.json").write_text(json.dumps(labels, indent=2))
    print(f"Wrote {n} dossiers to {out} and labels.json")

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="portfolio_out")
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    main(args.out, args.n, args.seed)
