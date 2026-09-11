# Vision 5D — Phase 1 Core Platform

AI-native architectural platform. Phase 1 establishes the secure, durable, observable foundation.

## Quick Start
```bash
cd vision-5d
pip install -e ".[dev]"
python -m uvicorn apps.api.main:app --reload --port 8000
# In another terminal:
python apps/worker/main.py
# Open apps/web/index.html in browser
```

## Architecture
- **apps/api** — FastAPI backend (17 endpoints)
- **apps/worker** — Durable job worker (17-state machine)
- **apps/web** — Minimal Phase 1 console
- **packages/contracts** — Shared Pydantic models
- **packages/domain** — SQLAlchemy models + DB config
- **packages/security** — Encryption, secret scanning

## Phase 1 Skills (33 at Level 4)
D-OBSERVE(2) D-ARTIFACT(4) D-SEC(2) D-PROJ(8) D-LLMCONF(7) D-INTAKE(5) D-HERMES(3) D-QA(2)
