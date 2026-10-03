# Rohan — Role Context

## Role

You own the **frontend implementation and integration** for Fair Drop. Your design template already exists; this document defines the product behavior, states, API usage, and integration expectations rather than prescribing visual design.

## Project understanding

Fair Drop is a high-demand registration and limited-seat allocation platform. The frontend must make the process understandable under stress: users need to know whether they are waiting, registered, selected, claiming, confirmed, expired, or rejected.

The frontend is not authoritative. It must never decide eligibility, inventory, ticket ownership, lottery outcome, timer expiry, or security validity.

## Primary responsibilities

- Own `/apps/frontend`.
- Integrate the existing design template.
- Build the event page.
- Build waiting-room/admission states.
- Build registration flow.
- Build challenge host states.
- Build result page: winner, standby, not selected, pending.
- Build entitlement and seat-hold flow.
- Build confirmation and expiry states.
- Build refresh/reconnect recovery.
- Build error/retry states using backend error codes.
- Build public audit/fairness receipt views.
- Build organizer dashboard views as agreed with Dhruv and Dhanya.
- Ensure responsive and accessible behavior.
- Add frontend tests for critical state transitions.

## Do not own

Do not modify:

- FastAPI internals.
- PostgreSQL migrations.
- Lottery algorithm.
- Inventory transaction logic.
- Simulator implementation.
- MediaPipe internal implementation.

If the UI needs a backend behavior that does not exist, write an API contract request or issue rather than implementing fake frontend logic.

## Recommended directory ownership

```text
/apps/frontend/
  src/
    api/
    auth/
    pages/
    components/
    state/
    hooks/
    types/
    accessibility/
  tests/
```

## Required user-facing states

### Event page

Display:

- Event name and description.
- Capacity or availability policy where appropriate.
- Registration start/end times.
- Maximum tickets per participant.
- One-entry rule.
- Lottery explanation.
- Human-validation explanation.
- Privacy and policy version.
- Current campaign status.

### Waiting room

Display:

- Current event state.
- Admission status.
- Safe progress information without pretending a browser queue number is authorization.
- Countdown based on server time.
- Connection/retry state.
- Clear explanation that waiting-room position is not the lottery winner decision.

### Registration

Display:

- Verification status.
- Challenge state when requested.
- Submit/processing state.
- Accepted entry receipt.
- Duplicate/retry result.
- Cooldown reason and remaining cooldown.
- Accessible fallback.

### Result

Display:

- Winner, standby, not-selected, or pending result.
- Policy version.
- Entry ID or private receipt reference.
- Entitlement expiry if winner.
- Standby rank if applicable.
- Audit/roster reference where allowed.

### Redemption

Display:

- Server-provided booking timer.
- Human-validation step.
- Seat hold timer.
- Seat status.
- Confirmed ticket result.
- Expired/released state.
- Safe retry guidance.

### Dashboard/audit

Display actual backend metrics:

- Registration attempts.
- Unique participants.
- Eligible entries.
- Duplicate attempts.
- Suspicious traffic.
- Winner/standby counts.
- Selection rates by simulator class.
- Available/held/confirmed seats.
- Oversell count.
- Duplicate allocation count.
- P95/P99 latency.
- Error and retry rates.
- Challenge outcomes.

Do not hard-code numbers.

## API integration rules

Consume documented HTTP APIs only. The stable endpoints are:

```text
POST /api/campaigns/{id}/join
GET  /api/campaigns/{id}/status
POST /api/campaigns/{id}/register
POST /api/challenges
POST /api/challenges/{id}/verify
GET  /api/campaigns/{id}/result
POST /api/entitlements/{id}/hold
POST /api/entitlements/{id}/redeem
POST /api/entitlements/{id}/release
GET  /api/campaigns/{id}/audit
GET  /api/campaigns/{id}/metrics
```

Every state-changing request must:

- Use the correct authenticated session.
- Send an idempotency key when required.
- Preserve the same idempotency key when retrying after an uncertain response.
- Never retry a state-changing request with a new key unless the user intentionally starts a new operation.
- Render backend error codes rather than parsing free-form messages.

## Timer rules

The frontend may display timers, but the backend is authoritative.

Use three visible concepts:

1. Idle session timeout: recommended MVP 2 minutes.
2. Absolute redemption session: recommended MVP 5 minutes.
3. Seat hold: recommended MVP 90–120 seconds.

When the timer reaches zero in the browser, the frontend should re-fetch state. It must not declare success or release inventory locally.

## Refresh and reconnect behavior

On page load or reconnect:

1. Restore authentication/session.
2. Fetch campaign status.
3. Fetch the user’s durable registration/result/claim state.
4. Render the server state.
5. Avoid creating a new entry automatically.

A refresh must not restart a challenge or submit a second registration without explicit user action.

## Error behavior

Use predictable states for:

- `EVENT_NOT_OPEN`
- `REGISTRATION_CLOSED`
- `RATE_LIMITED`
- `CHALLENGE_REQUIRED`
- `COOLDOWN_ACTIVE`
- `DUPLICATE_ENTRY`
- `ENTITLEMENT_EXPIRED`
- `HOLD_EXPIRED`
- `REPLAY_REJECTED`
- `TEMPORARILY_UNAVAILABLE`
- `CONFLICT`

For temporary uncertainty after a timeout, show “Checking your status” and fetch the durable resource. Do not tell the user that the operation failed unless the backend confirms failure.

## MediaPipe integration

Naman owns the challenge engine. You own hosting its contract:

- Start challenge.
- Show instruction and timer.
- Request camera permission only when needed.
- Show fallback path.
- Submit result to the backend.
- Handle pass/fail/timeout/abandonment.

Do not import or modify Naman’s internal CV code as part of normal frontend work.

## Simulator and dashboard integration

Dhanya owns traffic generation and real measurements. The frontend should render metrics from the backend/dashboard API. Do not create fake client-side metrics. Agree on metric names and dimensions through the shared contract.

Important dimensions:

- `normal_human`
- `fast_bot`
- `burst_bot`
- `retry_bot`
- `account_farm`
- `direct_api_bot`
- `token_replay`
- `shared_network_user`
- `slow_accessibility_user`

## Accessibility requirements

Do not make camera use mandatory for every participant. Support:

- Keyboard navigation.
- Screen-reader labels.
- Visible focus.
- Reduced motion where appropriate.
- Non-camera challenge fallback.
- Clear color-independent status messages.
- Sufficient time warnings.

Do not penalize slow or accessibility-focused users in the UI.

## Definition of done

- Complete primary flow renders from event page through confirmed ticket.
- Refresh/reconnect recovers durable state.
- Uncertain responses are safely reconciled.
- Backend error codes render clearly.
- Timers are server-reconciled.
- Challenge component uses Naman’s contract.
- Dashboard uses real Dhanya-generated metrics.
- No frontend code decides security or inventory.
- All work stays within `/apps/frontend` except agreed shared API type updates.
