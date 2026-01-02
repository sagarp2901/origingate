# OriginGate (Software Origin Governance Engine)

OriginGate is a reference implementation for **governance-style, tariff-equivalent controls** on software built outside a target jurisdiction.
It verifies a **Software Origin Dossier (SOD)** (SBOM + provenance + signatures), computes **origin scores** (OCS/FOI), and applies **policy-as-code**
decisions at procurement and update gates.

> This repository is a technical companion to an IEEE-style paper on lifecycle enforcement for digitally delivered software.

## What it does
- Validates a Software Origin Dossier (SOD) JSON payload
- Computes:
  - **OCS** (Origin Confidence Score): composite of build, SBOM, signing, hosting signals
  - **FOI** (Foreign Origin Index): risk-weighted foreign-control dominance over SBOM components
  - **Update drift** vs baseline releases
- Enforces **policy decisions** via a simple YAML rules engine:
  - allow / deny / review
  - compute a **tariff-equivalent compliance fee**

## Quick start

### 1) Run API
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

uvicorn origingate.api.main:app --reload --port 8080
```

### 2) Try a request
```bash
curl -s http://localhost:8080/v1/health | jq
```

### 3) Verify + Score + Decide (single call)
```bash
curl -s -X POST http://localhost:8080/v1/assess \
  -H 'Content-Type: application/json' \
  -d @examples/dossier_foreign.json | jq
```

## Endpoints (high-level)
- `POST /v1/dossiers/verify` — validate dossier structure and integrity bindings
- `POST /v1/origin/score` — compute OCS/FOI (+ explanations)
- `POST /v1/policy/decide` — apply YAML policy and compute fee/actions
- `POST /v1/assess` — verify+score+decide in one call
- `POST /v1/baselines` — register baseline release for drift checks
- `POST /v1/updates/evaluate` — evaluate update vs baseline and reclassify
- `GET /v1/metrics` — basic counters (ESC/UAC/EIR placeholders)
- `GET /v1/openapi.yaml` — OpenAPI spec

## Repository layout
- `origingate/` — API + scoring + policy engine
- `schemas/` — SOD JSON Schema (draft 2020-12)
- `policies/` — sample YAML policies
- `benchmarks/` — synthetic portfolio generator and evaluation harness
- `examples/` — sample dossiers for local testing

## Notes
- Signature verification is **pluggable**. This reference build includes a **demo verifier** (hash + declared signer jurisdiction).
- SBOM parsing supports a simplified CycloneDX-like list of components for the benchmark/evaluation. You can extend to real CycloneDX/SPDX.

## License
MIT (see LICENSE).
