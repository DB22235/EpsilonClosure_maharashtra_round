# Fair Drop — Engineering Rules and Technology Policy

## 1. Non-negotiable correctness rules

1. PostgreSQL is the durable authority for ownership, registration, entitlements, and inventory.
2. The frontend never decides eligibility, allocation, seat state, or expiry.
3. Registration is idempotent.
4. A campaign and verified participant have at most one valid registration.
5. A seat cannot have two owners.
6. Confirmed seats cannot exceed capacity.
7. Roster freezes before the draw.
8. Lottery results are reproducible and auditable.
9. Permits, challenges, and entitlements are bound, expiring, and replay-protected.
10. Server time is authoritative for cutoffs and timers.
11. Metrics must be generated from actual runs.
12. Shared networks and accessibility users must not be rejected solely from one IP or slow behavior.

## 2. What to avoid

### Product claims to avoid

Do not claim that every bot is detected, that MediaPipe proves humanity, that Turnstile guarantees no automation, that one IP equals one person, or that queue position alone is fairness.

### Architectural mistakes to avoid

- Do not begin with many microservices.
- Do not store critical state only in process memory.
- Do not use Redis as the only durable inventory authority.
- Do not use raw request count as lottery entries.
- Do not use first-come-first-served as the fairness claim.
- Do not use frontend timers as security controls.
- Do not put external network calls inside long database transactions.
- Do not add a dependency just to make the architecture look complex.
- Do not hard-code dashboard numbers.
- Do not write directly to another owner’s directory.

### Security mistakes to avoid

- No plaintext passwords.
- No secrets committed to Git.
- No stack traces or database errors returned to users.
- No trust in user-supplied roles or client-side eligibility.
- No logging of passwords, tokens, or full payment data.
- No accepting challenge success without server-side verification.
- No treating IP as identity.

## 3. Required technology choices

### Dhruv backend

- Python **3.11.9**.
- FastAPI.
- Uvicorn.
- Pydantic v2.
- PostgreSQL.
- SQLAlchemy/SQLModel plus Alembic, selected once and used consistently.
- Pytest and HTTP integration tests.
- Redis only where justified.

### Naman MediaPipe

- Python **3.11.9**.
- MediaPipe hand/gesture tooling.
- OpenCV or browser-compatible capture approach as needed.
- Deterministic mock challenge mode for simulator tests.

### Rohan frontend

- Existing team template.
- React or Next.js as already selected by the team.
- Existing chart library for dashboard views.
- No backend internals imported into the frontend.

### Dhanya simulator

- Python or Node based on team preference.
- HTTP load client such as Locust, k6, or a bounded custom runner.
- Deterministic scenario configuration.
- JSON/CSV result output.

### Optional integrations

- Cloudflare Turnstile for managed challenge.
- Object storage only if the project needs file artifacts.
- Email/OTP provider only if configured and necessary.

## 4. Dependency rules

- Pin dependencies where possible.
- Commit dependency manifests/lock files.
- Never commit virtual environments.
- Review license and maintenance status before adding a package.
- Prefer standard library or existing dependency over a new package for small functionality.
- Add a package only when its value is documented.
- Do not allow one team member’s virtual environment to become another member’s dependency.

## 5. Python environment rules

Naman:

```text
/apps/mediapipe/.venv → Python 3.11.9
```

Dhruv:

```text
/apps/backend/.venv → Python 3.11.9
```

Verify:

```bash
python --version
```

If 3.11.9 is unavailable, report the blocker instead of silently using another version for the controlled environment.

## 6. Repository and merge rules

```text
/apps/backend          Dhruv
/apps/frontend         Rohan
/apps/simulator        Dhanya
/apps/mediapipe        Naman
/packages/api-contract shared contract; Dhruv owns definition
/docs                  shared documents
```

Use one branch per contributor. Use commit prefixes `backend:`, `frontend:`, `simulator:`, `mediapipe:`, `contract:`, `test:`, and `docs:`.

Cross-team dependency is through HTTP/OpenAPI and shared JSON schemas. Do not import internal modules across workspaces. A contract change requires an example payload, notification to affected owners, and updated mocks/tests.

## 7. API rules

Every protected endpoint defines authentication, authorization, request schema, response schema, error codes, idempotency, state transitions, and rate-limit class.

State-changing requests must use idempotency keys. Reusing the same key with a different request hash is a conflict.

Stable error shape:

```json
{
  "error": {
    "code": "RATE_LIMITED",
    "message": "Too many requests for this operation",
    "request_id": "req_123"
  }
}
```

## 8. Demo rules

The demo must show actual behavior:

- Normal users and bots register.
- Burst duplicates are blocked/deduplicated.
- Suspicious clients receive friction/cooldown.
- Roster freezes.
- Lottery creates winners and standby order.
- Parallel seat race yields one successful hold.
- Replay fails.
- Lost response retry returns the same result.
- Refresh recovers state.
- Expired hold returns to inventory.
- Dashboard shows zero oversell and duplicate allocation.

## 9. Prioritization rule

If time is short, remove proof-of-work, advanced device clustering, Merkle proofs, payments, and multi-region deployment before removing idempotency, atomic inventory, lottery integrity, replay protection, simulator evidence, or core metrics.
