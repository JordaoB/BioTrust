# BioTrust

BioTrust is a biometric-first payment platform that combines:
- real payment card flows,
- risk-based transaction decisions,
- continuous face identity checks,
- liveness verification with anti-spoofing,
- and operational observability.

The project was built for TecStorm '26 and is currently implemented as a FastAPI backend plus a browser-based frontend served by the same service.

## Why BioTrust

Conventional payment authentication can be bypassed by credential theft and synthetic identities. BioTrust raises assurance by requiring proof of a live, consistent person only when risk justifies it.

In practice:
- low-risk transactions can be approved with minimal friction,
- medium/high-risk transactions trigger progressive biometric checks,
- and suspicious session behavior (for example, user disappearing from camera) is actively handled.

## Current Status

The repository is production-oriented in architecture and demo-ready in implementation.

Implemented and active now:
- FastAPI backend with MongoDB integration.
- Browser-based payment UX (login, cards, transfers, dashboard).
- Risk engine for contextual transaction scoring.
- ML anomaly detector integration (if model is available).
- Face identity enrollment/verification using OpenCV SFace + YuNet.
- Streaming liveness verification flow (`/api/liveness-stream/*`).
- Continuous identity guard during liveness (reject on person swap).
- No-face timeout cancellation after face was seen (`LIVENESS_NO_FACE_TIMEOUT_SECONDS`, default `5`).
- rPPG precheck fallback so mobile sessions do not block indefinitely.
- Retry logic on liveness start for transient `502/503/504` scenarios.
- Observability endpoints for metrics and alerts.

## Core Capabilities

### 1. Payments and Cards
- Inline card management per user (multiple cards supported).
- Card balance, daily spend, daily limit, and max-per-transaction validation.
- Daily spend auto-reset per UTC day.
- Transfer and merchant payment scenarios.
- Settlement service to move funds after successful approval path.

### 2. Risk Engine
Risk score combines behavioral and contextual factors (location, amount, velocity, trust, timing). The output drives transaction status and whether liveness is required.

Thresholds from configuration:
- `RISK_MEDIUM_THRESHOLD = 26`
- `RISK_HIGH_THRESHOLD = 60`
- `LIVENESS_TRIGGER_THRESHOLD = 26`

### 3. Face Identity (1:1)
- Endpoint-based identity status and verify flow.
- First-time enrollment stores reference encoding only after consent.
- Subsequent transactions verify live capture against stored reference.
- Uses OpenCV face models (YuNet + SFace).
- Model files are auto-downloaded if missing.

### 4. Liveness (Streaming)
Webcam frames are streamed from browser to backend and processed challenge-by-challenge.

Key behavior in current build:
- challenge sequence is randomized based on risk profile,
- anti-spoof checks run continuously,
- if user disappears after being seen, session fails after configured timeout,
- if identity changes mid-session, transaction is force-rejected,
- if rPPG precheck is weak on mobile, flow progresses after bounded wait.

### 5. Security and Hardening
- Security headers middleware.
- Rate-limiting middleware.
- Trusted hosts middleware.
- Session-based auth tokens with access/refresh lifecycle.

### 6. Observability
- Runtime metrics endpoint.
- Alert endpoint for operational anomalies.
- Fraud feed endpoint.
- Structured logging components under `backend/utils/logger.py` and `logs/`.

## Technology Stack

Backend:
- Python 3.10+
- FastAPI
- Uvicorn
- MongoDB (Motor/PyMongo)
- Pydantic / pydantic-settings

Computer Vision and ML:
- OpenCV
- MediaPipe
- NumPy / SciPy
- scikit-learn / joblib

Frontend:
- HTML/CSS/JavaScript
- Tailwind (CDN)

Testing:
- pytest
- end-to-end scenario in `tests/e2e/`

## Repository Layout

```text
backend/
  config.py                  # Settings and environment-driven behavior
  main.py                    # App bootstrap, middleware, routers, static serving
  routes/                    # API route handlers
  services/                  # Domain services (e.g., settlement)
  models/                    # Pydantic models
  middleware/                # Security and rate limiting
  observability/             # Metrics registry
  utils/                     # Logger and helpers

src/core/
  risk_engine.py             # Risk scoring logic
  anomaly_detector.py        # ML anomaly detection wrapper
  liveness_detector_v3.py    # Main liveness engine
  rppg_detector.py           # rPPG extraction and BPM estimation

web/
  index.html                 # Login/entry UI
  dashboard.html             # Main payment dashboard
  css/                       # Styles
  js/                        # Frontend logic (API, auth, webcam, dashboard)

models/opencv_face/
  *.onnx                     # OpenCV face model files

tests/e2e/
  test_transactions_e2e.py   # End-to-end transaction tests
```

## API Surface (Summary)

Health and app:
- `GET /`
- `GET /health`
- `GET /docs`

Frontend serving:
- `GET /web` (serves `web/index.html`)
- `GET /static/*` (serves frontend assets/pages)

Auth:
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/session/{access_token}`
- `POST /api/auth/refresh`
- `GET /api/auth/sessions/active`
- `DELETE /api/auth/sessions/{session_id}`

Users and cards:
- `GET /api/users/{user_id}`
- `GET /api/users/email/{email}`
- `GET /api/users/{user_id}/cards`
- `POST /api/users/{user_id}/cards`
- `DELETE /api/users/{user_id}/cards/{card_index}`

Transactions:
- `POST /api/transactions/`
- `GET /api/transactions/{transaction_id}`
- `GET /api/transactions/user/{user_id}`
- `PATCH /api/transactions/{transaction_id}/liveness`

Face identity:
- `GET /api/face-id/status/{user_id}`
- `POST /api/face-id/verify`
- `POST /api/face-id/reset/{user_id}` (debug mode)

Liveness:
- Legacy: `POST /api/liveness/verify/{transaction_id}` and support endpoints
- Streaming: `POST /api/liveness-stream/start`
- Streaming: `POST /api/liveness-stream/frame/{session_id}`
- Streaming: `POST /api/liveness-stream/complete/{session_id}`
- Streaming: `DELETE /api/liveness-stream/cancel/{session_id}`
- Streaming: `POST /api/liveness-stream/fail/{session_id}`

Observability:
- `GET /api/observability/metrics`
- `GET /api/observability/alerts`
- `GET /api/observability/fraud-feed`

Location and merchants:
- `GET /api/location/reverse`
- `GET /api/merchants/*`

## Configuration

Primary settings are in `backend/config.py` and can be overridden via `.env`.

Important variables:
- `APP_NAME`, `APP_VERSION`, `DEBUG`, `ENVIRONMENT`
- `MONGODB_URL`, `MONGODB_DB_NAME`
- `SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`
- `ENCRYPTION_KEY`
- `API_HOST`, `API_PORT`
- `ALLOWED_HOSTS`
- `CORS_ORIGINS`, `CORS_ALLOW_*`
- `SECURITY_HEADERS_ENABLED`
- `RATE_LIMIT_ENABLED`, `RATE_LIMIT_REQUESTS_PER_MINUTE`
- `LIVENESS_TIMEOUT_SECONDS`
- `LIVENESS_NO_FACE_TIMEOUT_SECONDS`
- `LIVENESS_ENABLE_PASSIVE`
- `RISK_HIGH_THRESHOLD`, `RISK_MEDIUM_THRESHOLD`, `LIVENESS_TRIGGER_THRESHOLD`

## Local Setup

### 1. Prerequisites
- Python 3.10+
- MongoDB running and reachable
- Webcam access for liveness tests

### 2. Install dependencies

```bash
python -m venv venv310
venv310\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment

```bash
copy .env.example .env
```

Adjust `.env` values as needed (database, CORS, hosts, secrets).

### 4. Run the backend

```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Access UI and docs
- Login page: `http://localhost:8000/web`
- Dashboard page: `http://localhost:8000/static/dashboard.html`
- API docs: `http://localhost:8000/docs`

## Mobile and Tunnel Access

When exposing the service through a tunnel or public host:
- include tunnel domain in `ALLOWED_HOSTS`,
- include frontend origin in `CORS_ORIGINS`,
- verify HTTPS is used for camera access on mobile browsers.

## Liveness Flow Notes (Operational)

Current operational protections in liveness stream:
- Start endpoint retries in frontend for transient upstream/server errors.
- Identity checked at startup and continuously during challenge flow.
- If face is not visible for more than configured seconds after first detection, verification fails and transaction is rejected.
- If rPPG cannot stabilize quickly on lower-end or constrained devices, flow proceeds after bounded wait instead of freezing.

## Testing

Run all tests:

```bash
pytest -q
```

Run e2e only:

```bash
pytest tests/e2e -q
```

## Documentation

Additional docs:
- `API_README.md`
- `docs/LOGGING_SYSTEM.md`
- `docs/ML_ANOMALY_DETECTION.md`

## License

This project is licensed under the terms in `LICENSE`.
