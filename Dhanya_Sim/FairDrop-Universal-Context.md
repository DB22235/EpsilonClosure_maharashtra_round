# Fair Drop — Universal Team Context

> **Shared source of truth for all four team members**
>
> **Project:** Fair Drop — Selling 500 Seats to 50,000 People Without Letting Bots Win
>
> **Team:** Naman, Rohan, Dhanya, Dhruv
>
> **Purpose:** This document defines the product, fairness model, system behavior, technical boundaries, ownership, contracts, integration rules, demo narrative, and non-negotiable correctness requirements. Every team member should read this before changing code.

---

## 1. The problem we are solving

Fair Drop is a high-demand event registration and limited-seat allocation platform. The simulated scenario is **500 available seats and up to 50,000 competing participants**.

The problem is not merely that there are more users than seats. The real problem is that a conventional first-come-first-served system allows speed, request volume, retries, automation, and network proximity to influence who gets a scarce resource. A high-demand event must also remain reliable while users refresh, reconnect, retry, and compete under adversarial traffic.

The system must demonstrate:

- High-concurrency handling.
- Abuse and repeated-attempt handling.
- No duplicate allocations.
- No overselling.
- Consistent inventory state.
- Reliable user state across refreshes, reconnects, and temporary failures.
- Configurable adversarial testing.
- Measurable fairness and system performance.

### Correct product claim

We do **not** claim to detect and eliminate every bot. That is unrealistic and not required.

Our defensible claim is:

> An automated client must not gain a meaningful allocation advantage merely by being faster, sending more requests, repeating attempts, replaying tokens, or creating extra traffic.

A bot that passes the same eligibility rules and obtains one valid entry may still be selected. That is acceptable. What is not acceptable is allowing 10,000 requests to become 10,000 chances.

---

## 2. Core product principle

> **Remove the race instead of trying to make legitimate users better at racing bots.**

The system uses a defined registration window followed by a frozen, auditable uniform lottery. The waiting room and rate limits protect infrastructure; they do not secretly determine winners.

The high-level flow is:

```text
Event published
  → user/session enters waiting room
  → signed admission permit
  → identity and risk checks
  → one idempotent registration per participant
  → registration closes
  → eligible roster freezes
  → deterministic uniform lottery
  → winners and standby order created
  → short-lived single-use entitlement
  → human validation
  → temporary seat hold
  → atomic final confirmation
  → audit and fairness metrics
```

---

## 3. Fairness model

### 3.1 One eligible entry

For the MVP:

- One verified account per campaign.
- Verified email.
- Phone OTP if available; otherwise clearly simulated in the demo.
- One active registration per campaign.
- One entry per verified participant.

These are separate concepts and must not be confused:

1. Whether an account is controlled by software.
2. Whether a request looks automated.
3. Whether the participant is unique and eligible.

### 3.2 Uniform lottery

After registration closes:

1. Freeze the cutoff.
2. Freeze the campaign policy.
3. Remove duplicates using the published rule.
4. Create a canonical roster and roster hash.
5. Run a reproducible shuffle using committed randomness.
6. Select 500 winners.
7. Create a fixed-order standby list.
8. Store the audit record.

The lottery must not use raw arrival speed, number of requests, or queue position as hidden winner criteria.

### 3.3 Human-controlled boundary

The final redemption flow is:

```text
registration or agent assistance
  → lottery
  → winner receives entitlement
  → temporary seat hold
  → human validation
  → human confirms exact event/seat
  → seat becomes CONFIRMED
```

Challenges such as Turnstile, a visual challenge, or a MediaPipe mini-game are friction and risk signals. They are not perfect proof of humanity.

---

## 4. Product state machines

### Campaign

```text
DRAFT → PREPARING → OPEN → CLOSED → FROZEN → DRAWING → CLAIMING → COMPLETED
```

### Registration

```text
RECEIVED → VALIDATING → ACCEPTED
                         ├─ DUPLICATE
                         ├─ REJECTED
                         └─ QUARANTINED
```

### Entitlement/claim

```text
SELECTED → CLAIM_PENDING → HELD → CONFIRMED
                    └──────→ EXPIRED
```

### Seat

```text
AVAILABLE → HELD → CONFIRMED
      ↑       └──→ AVAILABLE after expiry/release
```

Use explicit state values, not inconsistent combinations of booleans.

---

## 5. High-level architecture

```text
Participants / bots
        ↓
Frontend / public event page
        ↓
CDN / WAF / API gateway
        ↓
Authentication + validation + request IDs
        ↓
Admission gate + signed permits + rate limiting
        ↓
FastAPI backend modules
  ┌──────────────┬───────────────┬──────────────┐
  │ Registration │ Risk/friction │ Allocation   │
  │ and sessions │ and challenges│ and claims   │
  └──────┬───────┴──────┬────────┴──────┬───────┘
         │              │               │
         └──────────────┼───────────────┘
                        ↓
                 PostgreSQL authority
                        │
             Redis optional fast state
                        │
              Background workers/jobs
                        ↓
             Metrics + audit dashboard
```

### Architecture decision

For the hackathon, use a **modular monolith** in FastAPI rather than many microservices. The difficult part is correctness under concurrency. Many services would increase integration and debugging cost without improving the core proof.

PostgreSQL is the durable source of truth for campaigns, participants, registrations, seats, holds, entitlements, and audit events. Redis is optional for rate limits, caching, and short-lived admission metadata. Redis must not be the only durable source of ownership.

---

## 6. Default production foundations

Every live website part of Fair Drop must include:

- HTTPS/TLS.
- CDN/static asset delivery.
- WAF or edge protection.
- Load balancing and health checks.
- Versioned API routes.
- Server-side validation.
- Authentication and authorization.
- Secure expiring sessions.
- CSRF/XSS/security-header protections where applicable.
- PostgreSQL migrations and constraints.
- Transaction handling.
- Idempotent state-changing operations.
- Redis/cache failure behavior.
- Background jobs with retries and dead-letter handling.
- Structured logs and request IDs.
- Metrics, tracing, alerts, readiness and liveness checks.
- Secrets outside source code.
- Backups and restore testing.
- CI tests and deployment rollback strategy.
- Privacy minimization and retention rules.

No frontend code is authoritative for identity, inventory, eligibility, pricing, or final booking.

---

## 7. Fair Drop-specific backend requirements

### Required invariants

```text
confirmed_seats <= campaign_capacity
one seat cannot belong to two participants
one participant cannot exceed ticket limit
one campaign + one verified participant = one registration
expired holds do not remain permanently unavailable
replayed tokens are rejected
same idempotency key + same request = same result
same idempotency key + different request = rejection
```

### Signed admission permit

Contains or represents:

- Campaign ID.
- Participant/session ID.
- Expiry.
- Nonce.
- Allowed operation.
- Server signature.

Verify signature, expiry, session binding, and replay status. A browser-visible queue number is not authorization.

### Winner entitlement

A short-lived, single-use server-validated entitlement contains or represents:

- Campaign ID.
- Participant ID.
- Entitlement ID.
- Expiry.
- Nonce.
- Allowed operation.

The browser cannot decide whether it is valid.

### Risk-based friction

Example transparent demo scoring:

```text
+20 repeated burst requests
+20 multiple active sessions
+15 repeated refresh/reconnect attempts
+20 replayed token/challenge
+15 honeypot interaction
+15 duplicate identity relationship
+10 repeated challenge failures
+10 suspicious state transition
```

```text
0–29 LOW      normal flow
30–59 MEDIUM  slow down or step-up verification
60+ HIGH      challenge, cooldown, quarantine, or operation block
```

Never permanently classify someone as a bot from one shared IP, one refresh, slow network, unusual browser, assistive technology, or keyboard-only interaction.

---

## 8. Data model

Core tables/entities:

```text
campaigns
- id, name, description, capacity
- registration_start, registration_end, redemption_deadline
- max_tickets_per_participant
- allocation_method, policy_version, policy_hash
- status, created_at, updated_at

participants
- id, account_id, email_hash, phone_hash
- verification_status, risk_level, created_at

registrations
- id, campaign_id, participant_id
- idempotency_key, request_hash
- status, eligible, created_at

seats
- id, campaign_id, seat_label, status
- held_by, hold_expires_at, confirmed_by, version

entitlements
- id, campaign_id, participant_id
- nonce_hash, status, expires_at, redeemed_at

challenges
- id, session_id, campaign_id, type
- nonce_hash, answer_hash, status, expires_at, attempt_count

lottery_runs
- id, campaign_id, policy_version, roster_hash
- randomness_reference, algorithm_version
- winner_count, standby_count, executed_at

audit_events
- id, campaign_id, participant_id, session_id
- event_type, reason_code, metadata_json, created_at
```

Important unique constraints:

```text
unique(campaign_id, participant_id)
unique(campaign_id, idempotency_key)
```

---

## 9. API contract owned by Dhruv

The stable API surface is:

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
POST /api/admin/campaigns/{id}/draw
POST /api/admin/campaigns/{id}/pause
```

All state-changing endpoints must define request/response schemas, error codes, idempotency behavior, authentication, and permitted state transitions.

Standard response errors use a stable shape:

```json
{
  "error": {
    "code": "REGISTRATION_CLOSED",
    "message": "Registration has ended",
    "request_id": "req_123"
  }
}
```

Frontend and simulator must consume the API contract rather than importing backend internals.

---

## 10. Team ownership and merge-conflict policy

### Ownership map

| Person | Primary ownership | Allowed supporting work |
|---|---|---|
| Naman | MediaPipe human-validation pipeline | Challenge adapters, challenge UX contract, local Python CV tests |
| Rohan | Frontend implementation and integration | API client, screens, state rendering, accessibility, dashboard views |
| Dhanya | AI/adversarial simulation testing | Bot profiles, load scenarios, fairness metrics, attack reports |
| Dhruv | FastAPI backend and system design | Database schema, API contracts, auth/session, allocation, inventory, orchestration |

### Directory ownership

Use this repository shape:

```text
/apps
  /backend        Dhruv
  /frontend       Rohan
  /simulator      Dhanya
  /mediapipe      Naman
/packages
  /api-contract   Dhruv defines; everyone consumes
  /shared-types   Dhruv defines; changes require team agreement
/docs
  /context        shared context files
  /demo           demo scripts and results
/tests
  /integration    Dhruv owns backend correctness
  /simulation     Dhanya owns scenarios and reports
```

### Merge rules

- Do not edit another person’s owned directory without agreement.
- Do not put experimental files in another person’s directory.
- Do not make frontend dependent on backend Python modules.
- Do not make simulator dependent on database internals; use HTTP API.
- Do not import MediaPipe implementation into FastAPI. Dhruv integrates a challenge adapter/API, not Naman’s CV internals.
- Shared API schemas are the only cross-team code contract.
- Changes to `/packages/api-contract` require a small written note and synchronized frontend/simulator updates.
- Keep commits narrow and named by scope: `backend:`, `frontend:`, `mediapipe:`, `simulator:`, `docs:`.
- Rebase or merge main before opening a PR; do not resolve conflicts by deleting another person’s work.
- Every PR must state changed directories, API changes, test evidence, and any migration requirement.

### Integration rule

Each person should be able to work and test independently through stable interfaces:

```text
Naman → challenge result adapter
Rohan → HTTP API / OpenAPI contract
Dhanya → HTTP API + metrics endpoints
Dhruv → database and services behind API contracts
```

---

## 11. Python 3.11.9 environment requirement

Naman and Dhruv must use Python **3.11.9** virtual environments.

Recommended setup:

```bash
python3.11 --version
# Must report Python 3.11.9

python3.11 -m venv .venv
source .venv/bin/activate
python --version
python -m pip install --upgrade pip
```

Use separate environments:

```text
/apps/backend/.venv       Dhruv
/apps/mediapipe/.venv     Naman
```

Commit dependency lock/requirements files, never `.venv`. Pin versions where possible. Do not let the frontend or Dhanya simulator require either Python environment.

If the exact interpreter is not available, stop and report it rather than silently using a different major/minor version for computer-vision or backend reproducibility.

---

## 12. Role summaries

### Naman

Own the MediaPipe pipeline, five short gesture/hand challenges, challenge state, nonce/result format, accessibility fallback, and challenge adapter documentation. The result is a risk/friction signal, not a declaration that a person is human.

### Rohan

Own the frontend screens and UX integration: event page, waiting room, registration status, challenge host, result page, claim flow, timers, dashboard views, audit receipt, error/recovery states, and responsive/accessibility behavior. Use the existing design template but do not change backend rules in the UI.

### Dhanya

Own the simulator and adversarial testing: normal users, fast bots, burst bots, retry bots, account farms, direct API bots, token replay, race-condition attempts, shared-network users, and slow/accessibility users. Produce real metrics and reports, not hard-coded charts.

### Dhruv

Own FastAPI architecture, PostgreSQL models/migrations, auth/session, admission permits, idempotency, risk orchestration, campaign state machine, roster freeze, deterministic lottery, entitlements, atomic seat holds, replay protection, metrics APIs, audit APIs, and integration adapters. Keep the backend modular for future model or challenge integration.

---

## 13. MVP priority

### Must work

1. Campaign creation.
2. Registration window.
3. Verified or clearly simulated identity.
4. One-entry-per-participant.
5. Frozen roster.
6. Uniform lottery.
7. Fixed standby order.
8. PostgreSQL inventory authority.
9. Atomic holds and confirmation.
10. Idempotency.
11. Replay protection.
12. Basic rate limits.
13. Human validation before final redemption.
14. Session and seat timers.
15. Adversarial simulator.
16. Fairness/reliability dashboard.

### Strong differentiators

- Cloudflare Turnstile.
- Five MediaPipe mini-games.
- Visual challenge.
- Risk-based friction.
- Five-minute cooldown.
- Signed permits and entitlements.
- Public audit page.
- Fairness Receipt.
- Human-readable reason codes.
- Accessibility alternative.
- Organizer kill switch.

### Only after the core is stable

- Proof-of-work.
- Honeypot.
- Merkle inclusion proof.
- WebAuthn/passkey final step.
- Advanced device clustering.
- Payment integration.
- Multi-region deployment.

Never remove atomic inventory, lottery integrity, idempotency, replay protection, or the main evidence dashboard to add cosmetic features.

---

## 14. Required demo sequence

1. Organizer creates a 500-seat campaign.
2. UI shows frozen rules and policy version.
3. Normal users and bots register.
4. Burst bots send thousands of duplicate requests.
5. Dashboard shows deduplication and rate limiting.
6. Suspicious clients receive challenges.
7. Repeated abuse triggers cooldown.
8. Registration closes.
9. Roster freezes and hash is shown.
10. Lottery selects winners and standby order.
11. Winner receives a signed single-use entitlement.
12. Two parallel requests try to hold one seat.
13. Only one succeeds.
14. Replayed entitlement is rejected.
15. Lost response is retried with the same idempotency key.
16. Original result returns without duplicate allocation.
17. Legitimate user refreshes/reconnects.
18. Durable state is recovered.
19. Expired hold returns to inventory.
20. Dashboard shows zero overselling and duplicate allocations.
21. Fairness chart shows request volume did not create proportional selection advantage.

### Judge message

> We do not claim perfect bot detection. We remove the speed race, cap each participant at one eligible chance, require human validation before final redemption, protect inventory atomically, and produce measurable evidence that bots cannot dominate allocation.

---

## 15. What the team must not claim

Do not claim:

- Every AI agent is detected.
- MediaPipe proves someone is human.
- Turnstile guarantees no bot can pass.
- One IP equals one person.
- Queue position itself is fairness.
- Frontend timers protect bookings.
- A successful challenge proves uniqueness.
- A CAPTCHA alone makes the system secure.

Use accurate language:

- Reduces automated advantage.
- Combines identity limits, admission control, rate limits, challenges, replay protection, and atomic inventory.
- Measures false positives as well as blocked traffic.
- Keeps fairness allocation separate from traffic admission.
- Proves that more requests do not create more lottery entries.

---

## 16. Definition of done

The project is ready for judging when:

- A clean checkout from registration to confirmation works.
- A refresh/reconnect preserves state.
- Same idempotency key returns the same result.
- Different payload with the same key is rejected.
- Parallel seat requests cannot oversell.
- Replayed permits/entitlements are rejected.
- Registration freezes before the draw.
- Lottery results can be replayed from the stored audit data.
- Standby promotion is deterministic.
- Simulator can generate normal and adversarial traffic.
- Metrics come from actual runs.
- Naman’s challenge pipeline can be integrated without importing its internals into the backend.
- Rohan’s frontend uses documented HTTP contracts.
- Dhanya’s simulator uses documented HTTP endpoints.
- Dhruv’s FastAPI app starts from a clean Python 3.11.9 environment.
- No team member needs to edit another team member’s owned directory for normal development.

---

## 17. Final product identity

Fair Drop is not merely a queue, CAPTCHA, MediaPipe game, bot detector, waitlist, lottery, or ticket database.

It is a combined:

> **Fairness, allocation, inventory-integrity, abuse-resistance, session-reliability, and evidence layer for high-demand events.**

Its defining promise is:

> **Remove the race, make allocation verifiable, protect inventory atomically, add human-controlled friction where risk requires it, preserve legitimate access, and produce measurable evidence that the system remained fair and reliable under adversarial demand.**
