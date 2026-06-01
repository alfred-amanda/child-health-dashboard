# Child Health Dashboard

Local-first FastAPI + SQLite + SQLModel backend and Vite/React/TypeScript frontend for Thomas's health dashboard.

## Commands

```bash
make dev
make check
make ci
make backend-test
make frontend-test
```

## Safety boundaries

- No PHI leaves the device by default (`external_services.enabled=false`).
- Every rendered recommendation follows: `Because [evidence], [action]. Urgency. Confidence. Source.`
- Every clinical fact has source/provenance/confidence or renders as not computable.
- Red-flag thresholds are parsed from Thomas's AVS/discharge text, not hardcoded constants.
- Bilirubin thresholds use a local AAP-2022/PediTools-mirrored table by hour-of-life, gestational age, and DAT-positive/hemolytic neurotoxicity risk.
