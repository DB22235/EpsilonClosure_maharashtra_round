# Fair Drop — Master Backend and Frontend Integration Guide

> **Status:** Definitive implementation contract for the hackathon
>
> **Purpose:** One source of truth for the complete backend-heavy system, API contracts, database behavior, authentication, security, allocation, inventory integrity, challenge integration, frontend integration, simulator integration, testing, and deployment.
>
> **Primary principle:** Remove the race. Do not try to prove that every request came from a biological human. Ensure that automation cannot gain a meaningful allocation advantage through speed, request volume, retries, duplicate identities, replay, or queue manipulation.

---

## 0. Non-negotiable decisions

These decisions are final for the MVP.

1. **Allocation is registration plus a uniform lottery**, not raw first-come-first-served.
2. **The waiting room protects capacity.** It does not secretly choose winners.
3. **One verified participant gets one eligible entry per campaign.**
4. **Supabase Auth manages authentication.** FastAPI validates Supabase JWTs and owns authorization.
5. **FastAPI is the only business-logic API.** The browser does not directly decide eligibility, winners, inventory, holds, or final booking.
6. **PostgreSQL is the durable source of truth.** Redis is optional acceleration only.
7. **Human validation happens before final redemption.** It is a risk/friction signal, not perfect proof of humanity.
8. **Recommended claim order:** selected entitlement → human validation → seat hold → exact event/seat confirmation.
9. **Seat inventory uses explicit states:** `AVAILABLE → HELD → CONFIRMED`; expired/released holds return to `AVAILABLE`.
10. **All state-changing operations are idempotent where applicable.**
11. **All security-sensitive tokens are short-lived, signed or server-recorded, bound, and replay-protected.**
12. **Timers are server-authoritative.** Frontend timers only display server timestamps.
13. **The system must measure legitimate-user harm as well as bot resistance.**
14. **No production claim will say that every bot is detected or blocked.**
15. **The hackathon MVP does not process real payments.** Final confirmation represents successful redemption.

---

# 1. System identity and scope

Fair Drop simulates a high-demand event such as **500 seats and up to 50,000 competing participants**.

It must demonstrate:

- High-concurrency handling.
- Controlled admission.
- One-entry-per-participant enforcement.
- Abuse and repeated-attempt handling.
- A frozen eligible roster.
- A deterministic, auditable uniform lottery.
- Fixed-order standby promotion.
- Human-controlled friction before final redemption.
- Atomic inventory and no overselling.
- Idempotent retries.
- Replay protection.
- Refresh/reconnect recovery.
- Configurable adversarial simulation.
- Fairness, reliability, inventory, and false-positive evidence.

The correct product claim is:

> **An automated client must not gain a meaningful allocation advantage merely by being faster, sending more requests, repeating attempts, replaying tokens, creating extra traffic, or manipulating the queue.**

A client that passes the same eligibility process and receives one valid entry may still be selected. That is acceptable. Ten thousand requests must not become ten thousand lottery entries.

---

# 2. Final end-to-end lifecycle

```text
Admin creates draft campaign
  → Admin prepares and validates policy/inventory
  → Admin publishes campaign
  → Campaign becomes visible to users
  → User opens event page
  → User authenticates with Supabase Auth
  → FastAPI validates Supabase JWT and role
  → User joins admission gate/waiting room
  → FastAPI issues signed admission permit
  → User passes identity/risk checks
  → User receives step-up challenge if required
  → User submits one idempotent registration
  → Registration remains durable across refresh/reconnect
  → Registration window closes
  → In-flight entries resolve by documented server-time rule
  → Eligible roster freezes
  → Canonical roster hash is stored
  → Admin runs deterministic uniform lottery once
  → Winners and fixed standby order are created
  → Winner receives short-lived single-use entitlement
  → Winner completes human validation
  → Winner selects an available seat
  → PostgreSQL atomically changes AVAILABLE → HELD
  → Winner confirms exact event and seat
  → PostgreSQL atomically changes HELD → CONFIRMED
  → Booking/receipt is shown
  → Expired claims release seats and promote standby in fixed order
  → Audit, metrics, and public evidence remain available
```

---

# 3. Roles and authentication

## 3.1 Roles

```text
USER
ADMIN
```

A user can:

- View published campaigns.
- Join a campaign.
- Register once.
- Complete challenges.
- View registration status.
- View lottery results.
- Claim and confirm a seat if selected.
- View a private fairness receipt.

An admin can:

- Create and edit draft campaigns.
- Prepare and publish campaigns.
- Open, pause, resume, and close registration.
- Freeze the roster.
- Run the lottery.
- Monitor claims, metrics, risk, and inventory.
- Pause redemption.
- View audit information.
- Process standby promotion according to fixed order.

## 3.2 Supabase Auth boundary

Supabase Auth is responsible for:

- Sign-up.
- Sign-in.
- Email verification.
- Magic link or password login.
- Optional phone OTP.
- Issuing and refreshing the authenticated JWT.
- Sign-out.

FastAPI is responsible for:

- Verifying the Supabase JWT signature and claims.
- Loading the application profile.
- Checking `USER` or `ADMIN` role.
- Checking participant verification state.
- Applying campaign-specific eligibility.
- Authorizing every protected operation.

The frontend must never send a trusted role in the request body. The backend obtains the authenticated Supabase subject and loads the role server-side.

## 3.3 Database profile

Supabase-managed identity:

```text
auth.users
- id
- email
- phone
- created_at
```

Application profile:

```text
profiles
- id UUID primary key references auth.users(id)
- display_name text
- role text check in ('USER', 'ADMIN')
- email_verified boolean
- phone_verified boolean
- institute_verified boolean
- created_at timestamptz
- updated_at timestamptz
```

For the hackathon, seed one admin account manually. Do not create an admin from an untrusted public form.

## 3.4 Request authentication headers

Every protected request from Next.js to FastAPI sends:

```http
Authorization: Bearer <supabase_access_token>
Content-Type: application/json
X-Request-ID: <client-generated-or-server-generated-request-id>
```

State-changing requests also send:

```http
Idempotency-Key: <unique-key-for-this-logical-operation>
```

For a browser cookie-based deployment, add CSRF protection as appropriate. For a bearer-token SPA flow, keep tokens out of URLs and never log them.

---

# 4. Campaign state machine

```text
DRAFT
  → PREPARING
  → OPEN
  → CLOSED
  → FROZEN
  → DRAWING
  → CLAIMING
  → COMPLETED
```

## Valid transitions

| Current state | Allowed transition | Meaning |
|---|---|---|
| `DRAFT` | `PREPARING` | Validate policy and inventory |
| `PREPARING` | `DRAFT` | Return to draft after validation failure |
| `PREPARING` | `OPEN` | Publish/open registration |
| `OPEN` | `CLOSED` | Stop new registrations |
| `OPEN` | pause/resume operational flag | Temporarily stop admission or registration without corrupting state |
| `CLOSED` | `FROZEN` | Resolve entries and freeze eligible roster |
| `FROZEN` | `DRAWING` | Begin one lottery run |
| `DRAWING` | `CLAIMING` | Winners and standby order created |
| `CLAIMING` | `COMPLETED` | Claim/redemption window finished |

A paused campaign must retain its underlying lifecycle state and a separate pause flag/reason.

## Campaign fields

```text
id UUID
name text
description text
venue text nullable
event_start timestamptz nullable
capacity integer > 0
registration_start timestamptz
registration_end timestamptz
redemption_deadline timestamptz
max_tickets_per_participant integer > 0
allocation_method text = 'UNIFORM_LOTTERY'
standby_policy text = 'FIXED_ORDER'
policy_version text
policy_hash text
status campaign_status
admission_paused boolean
registration_paused boolean
redemption_paused boolean
published_at timestamptz nullable
created_by UUID
created_at timestamptz
updated_at timestamptz
```

Important policy fields are frozen before the draw and must not be silently changed after registrations begin.

---

# 5. Registration state machine

```text
RECEIVED
  → VALIDATING
  → ACCEPTED

VALIDATING → DUPLICATE
VALIDATING → REJECTED
VALIDATING → QUARANTINED
```

## Registration rules

- One verified participant per campaign.
- One active registration per campaign.
- Duplicate submissions return the original result or the documented duplicate result.
- A new idempotency key for an already-registered participant cannot create another eligible entry.
- Registration is transactional.
- Registration cutoff uses server time.
- In-flight requests at cutoff are resolved using one documented rule. Recommended rule: the database transaction must commit before the server-side cutoff to be accepted; otherwise it is closed/rejected.

## Registration fields

```text
id UUID
campaign_id UUID
participant_id UUID
idempotency_key text
request_hash text
status registration_status
eligible boolean
risk_score integer
risk_level text
reason_code text nullable
received_at timestamptz
validated_at timestamptz nullable
created_at timestamptz
updated_at timestamptz
```

Constraints:

```text
unique(campaign_id, participant_id)
unique(campaign_id, idempotency_key)
```

---

# 6. Waiting room and admission permits

The waiting room protects capacity. It does not select lottery winners.

## Join flow

1. Authenticated user calls `POST /api/v1/campaigns/{id}/join`.
2. FastAPI validates campaign status and session.
3. The admission service returns one of:
   - `ADMITTED`
   - `WAITING`
   - `ALREADY_REGISTERED`
   - `CHALLENGE_REQUIRED`
   - `COOLDOWN`
   - `CAMPAIGN_CLOSED`
4. If admitted, FastAPI issues a short-lived signed permit.
5. The permit is required for protected registration operations.

## Admission permit contents

```text
campaign_id
participant_id
session_id
issued_at
expires_at
nonce
allowed_operation
key_id
signature
```

The backend verifies:

- Signature.
- Campaign binding.
- Participant/session binding.
- Expiration.
- Allowed operation.
- Nonce not previously consumed.

A queue position displayed in the browser is never authorization.

## Permit behavior

- Short-lived.
- Single-use or operation-scoped.
- Rejected after expiration.
- Rejected if replayed.
- Rejected if used by another session.
- Rejected if used for another campaign or operation.

---

# 7. Participant, session, and identity model

## Participants

```text
participants
- id UUID
- account_id UUID references profiles.id
- email_hash text
- phone_hash text nullable
- verification_status text
- risk_level text
- created_at timestamptz
- updated_at timestamptz
```

Never use raw email or phone as a public identity key. Hash or minimize sensitive fields according to the chosen privacy design.

## Server sessions

```text
sessions
- id UUID
- participant_id UUID
- campaign_id UUID nullable
- supabase_subject UUID
- created_at timestamptz
- last_activity_at timestamptz
- absolute_expires_at timestamptz
- idle_expires_at timestamptz
- status text
- last_ip_hash text nullable
- user_agent_hash text nullable
```

Recommended timers:

```text
Idle session timeout: 2 minutes
Absolute redemption session timeout: 5 minutes
Seat hold timeout: 90–120 seconds
```

The backend enforces expiry. The frontend only displays the server-provided expiry timestamp.

Do not keep a session alive with meaningless background polling.

## One active session behavior

The system may allow normal refresh/reconnect. It should not automatically reject a shared-network user or every second session. If multiple active sessions create suspicious behavior, add a risk signal and step-up friction rather than treating one IP as one person.

---

# 8. Risk scoring and friction

Use a transparent MVP score and reason codes.

## Signals

```text
RATE_BURST             +20  repeated burst requests
MULTI_SESSION          +20  suspicious active-session pattern
REFRESH_RECONNECT      +15  repeated refresh/reconnect abuse
REPLAY_ATTEMPT         +20  replayed token/challenge/entitlement
HONEYPOT_INTERACTION   +15  hidden field or endpoint interaction
DUPLICATE_IDENTITY     +15  identity relationship signal
CHALLENGE_FAILURE      +10  repeated challenge failure
SUSPICIOUS_TRANSITION  +10  invalid state sequence
```

## Risk levels

```text
0–29    LOW       Normal flow
30–59   MEDIUM    Slow down or request step-up verification
60+     HIGH      Strong challenge, cooldown, quarantine, or operation block
```

Do not permanently classify a participant from only:

- One shared IP.
- One page refresh.
- Slow network.
- Unusual browser.
- Assistive technology.
- Keyboard-only use.

## Actions

```text
LOW       → allow
MEDIUM    → Turnstile, visual, or other step-up challenge
HIGH      → MediaPipe challenge, cooldown, quarantine, or operation block
REPEATED  → five-minute operation-specific cooldown
```

Cooldown response:

```json
{
  "error": {
    "code": "COOLDOWN_ACTIVE",
    "message": "This operation is temporarily paused for this session.",
    "request_id": "req_123",
    "details": {
      "retry_after_seconds": 300,
      "operation": "REGISTER"
    }
  }
}
```

A valid previous registration must not be deleted merely because a later request receives a cooldown.

---

# 9. Challenge adapter architecture

Naman owns MediaPipe internals. FastAPI owns the challenge contract and adapter, not the computer-vision implementation.

## Supported challenge types

```text
TURNSTILE
MEDIAPIPE
VISUAL
MOCK
```

## Challenge table

```text
challenges
- id UUID
- campaign_id UUID
- session_id UUID
- participant_id UUID nullable
- type challenge_type
- nonce_hash text
- answer_hash text nullable
- status text
- expires_at timestamptz
- attempt_count integer
- max_attempts integer
- implementation_version text
- created_at timestamptz
- consumed_at timestamptz nullable
```

## Challenge result contract

Frontend or Naman’s adapter sends:

```json
{
  "challenge_id": "ch_123",
  "campaign_id": "camp_123",
  "session_id": "sess_123",
  "type": "MEDIAPIPE",
  "nonce": "server-issued-nonce",
  "result": "SUCCESS",
  "confidence": 0.94,
  "attempt": 1,
  "duration_ms": 6420,
  "implementation_version": "mediapipe-v1"
}
```

## Backend validation

FastAPI verifies:

1. Challenge exists.
2. Challenge belongs to campaign.
3. Challenge belongs to session.
4. Participant/session binding is valid.
5. Nonce matches.
6. Challenge is not expired.
7. Attempt count is within limit.
8. Challenge is not already consumed.
9. Result shape is valid.
10. External Turnstile token is verified server-side when applicable.

Challenge success is one risk signal, not proof of a unique natural person.

## Accessible alternative

Do not require a camera for every participant. Offer Turnstile, visual, or another accessible step-up path where appropriate. Record challenge abandonment and completion metrics separately.

---

# 10. Lottery and roster freeze

## Freeze process

At registration cutoff:

1. Transition `OPEN → CLOSED`.
2. Stop new registration commits.
3. Resolve in-flight entries by the documented server-time rule.
4. Select valid registrations.
5. Apply the duplicate policy.
6. Sort the canonical roster deterministically.
7. Calculate and store the roster hash.
8. Store policy version and policy hash.
9. Transition `CLOSED → FROZEN`.

## Canonical roster

The canonical roster should use stable pseudonymous participant identifiers and a deterministic sort order. Do not publish personal data.

Example canonical record:

```json
{
  "campaign_id": "camp_123",
  "participant_pseudonym": "p_8f1c...",
  "registration_id": "reg_456",
  "eligible": true
}
```

## Lottery process

1. Confirm campaign is `FROZEN`.
2. Confirm no previous successful lottery run exists.
3. Transition `FROZEN → DRAWING`.
4. Use committed randomness.
5. Include campaign ID, roster hash, policy hash, and algorithm version in the randomness input.
6. Deterministically shuffle the canonical roster.
7. Select `capacity` winners, or all eligible participants if fewer than capacity.
8. Store the remainder as fixed-order standby.
9. Create winner entitlements.
10. Store `lottery_run` audit record.
11. Transition `DRAWING → CLAIMING`.

## Lottery data

```text
lottery_runs
- id UUID
- campaign_id UUID
- policy_version text
- policy_hash text
- roster_hash text
- randomness_reference text
- randomness_commitment text
- algorithm_version text
- winner_count integer
- standby_count integer
- executed_at timestamptz
- executed_by UUID
```

The lottery must be replayable from stored metadata. Do not use an unreproducible uncontrolled random call.

---

# 11. Entitlements and claims

## Entitlement state machine

```text
SELECTED
  → CLAIM_PENDING
  → HELD
  → CONFIRMED

CLAIM_PENDING → EXPIRED
HELD → EXPIRED
```

## Entitlement fields

```text
entitlements
- id UUID
- campaign_id UUID
- participant_id UUID
- lottery_run_id UUID
- nonce_hash text
- status entitlement_status
- expires_at timestamptz
- redeemed_at timestamptz nullable
- held_seat_id UUID nullable
- created_at timestamptz
- updated_at timestamptz
```

A winner entitlement is:

- Short-lived.
- Bound to campaign.
- Bound to participant.
- Bound to allowed operation.
- Single-use.
- Rejected after expiry.
- Rejected after redemption.

## Recommended claim order

```text
SELECTED
  → human validation
  → seat selection
  → atomically create HELD state
  → exact event/seat confirmation
  → atomically create CONFIRMED state
```

This prevents a failed high-risk client from consuming a scarce seat before validation.

---

# 12. Inventory and atomic booking

## Seat fields

```text
seats
- id UUID
- campaign_id UUID
- seat_label text
- section text nullable
- row_label text nullable
- seat_number integer nullable
- status seat_status
- held_by_entitlement_id UUID nullable
- hold_expires_at timestamptz nullable
- confirmed_by_participant_id UUID nullable
- confirmed_at timestamptz nullable
- version integer
- created_at timestamptz
- updated_at timestamptz
```

## Seat state machine

```text
AVAILABLE → HELD → CONFIRMED
     ↑        |
     └────────┘ after expiry/release
```

## Hold transaction

The hold operation must run in one short database transaction:

```text
BEGIN
  lock or atomically claim the entitlement
  verify entitlement is valid and not expired
  verify participant owns entitlement
  verify participant ticket limit
  lock or atomically claim an AVAILABLE seat
  create HELD seat state
  store hold expiry
  update entitlement to HELD
COMMIT
```

Do not keep a database transaction open while calling Turnstile, MediaPipe, email, or another slow external service.

## Confirm transaction

```text
BEGIN
  lock the entitlement and seat hold
  verify participant/session binding
  verify hold has not expired
  verify human validation is recorded
  verify seat belongs to this entitlement
  transition HELD → CONFIRMED
  consume entitlement
  write audit event
COMMIT
```

## Required invariants

```text
confirmed_seats <= campaign_capacity
one seat cannot belong to two participants
one participant cannot exceed ticket limit
expired holds do not remain unavailable
no duplicate reservation from retries
no overselling
no duplicate allocation
```

Use conditional updates, row locks, unique constraints, short transactions, and explicit states.

---

# 13. Idempotency and replay protection

## Idempotency table

```text
idempotency_records
- id UUID
- scope text
- key text
- actor_id UUID
- campaign_id UUID nullable
- request_hash text
- response_status integer
- response_body_json jsonb
- resource_type text nullable
- resource_id UUID nullable
- expires_at timestamptz
- created_at timestamptz
```

## Required behavior

```text
same key + same request
    → return original response

same key + different request body
    → reject with IDEMPOTENCY_CONFLICT

new key + already-registered participant
    → return existing/duplicate policy result

lost response after successful commit
    → retry recovers original result
```

Use idempotency for:

- Registration.
- Challenge verification where a duplicate response could create state.
- Entitlement hold.
- Entitlement redeem.
- Release where applicable.
- Future payment-like operations.

## Replay protection

Reject:

- Reused admission permits.
- Expired admission permits.
- Reused challenge nonces.
- Challenges used in another session.
- Reused entitlements.
- Expired entitlements.
- Replayed redemption requests.
- Changed payload under an old idempotency key.

---

# 14. Complete API route contract

All routes use the `/api/v1` prefix. The OpenAPI document at `/docs` is the integration authority.

## 14.1 Public campaign routes

### `GET /api/v1/campaigns`

Returns published campaigns visible to users.

Query parameters:

```text
status=OPEN|CLAIMING|COMPLETED optional
page integer default 1
page_size integer default 20
```

Response:

```json
{
  "data": [
    {
      "id": "camp_123",
      "name": "Hackathon Arena Finals",
      "description": "...",
      "capacity": 500,
      "registration_start": "2026-10-04T09:00:00Z",
      "registration_end": "2026-10-04T10:00:00Z",
      "redemption_deadline": "2026-10-04T12:00:00Z",
      "max_tickets_per_participant": 1,
      "allocation_method": "UNIFORM_LOTTERY",
      "status": "OPEN",
      "policy_version": "v1.0"
    }
  ],
  "meta": {"page": 1, "page_size": 20, "total": 1}
}
```

### `GET /api/v1/campaigns/{id}`

Returns public campaign details, published rules, status, server time, and policy information. It must not expose private participant data.

### `GET /api/v1/campaigns/{id}/status`

Authenticated user status endpoint.

Response:

```json
{
  "campaign": {
    "id": "camp_123",
    "status": "OPEN",
    "registration_end": "2026-10-04T10:00:00Z",
    "redemption_deadline": "2026-10-04T12:00:00Z",
    "server_time": "2026-10-04T09:12:00Z"
  },
  "participant_state": "REGISTERED",
  "registration": {
    "id": "reg_123",
    "status": "ACCEPTED",
    "eligible": true,
    "created_at": "2026-10-04T09:10:00Z"
  },
  "admission": {
    "state": "ADMITTED",
    "permit_expires_at": "2026-10-04T09:17:00Z"
  },
  "challenge": null,
  "entitlement": null,
  "seat_hold": null
}
```

This endpoint is the frontend’s primary recovery endpoint after refresh/reconnect.

## 14.2 Admission and registration routes

### `POST /api/v1/campaigns/{id}/join`

Auth: authenticated user.

Purpose: join or recover waiting-room/admission state.

Request:

```json
{}
```

Response:

```json
{
  "state": "ADMITTED",
  "campaign_id": "camp_123",
  "session_id": "sess_123",
  "permit": {
    "token": "signed-permit",
    "expires_at": "2026-10-04T09:17:00Z",
    "allowed_operation": "REGISTER"
  },
  "server_time": "2026-10-04T09:12:00Z"
}
```

Waiting response:

```json
{
  "state": "WAITING",
  "campaign_id": "camp_123",
  "session_id": "sess_123",
  "estimated_wait_seconds": 120,
  "refresh_required": false,
  "server_time": "2026-10-04T09:12:00Z"
}
```

### `POST /api/v1/campaigns/{id}/register`

Auth: authenticated user; valid admission permit where required.

Headers:

```http
Idempotency-Key: reg-key-123
```

Request:

```json
{
  "admission_permit": "signed-permit",
  "turnstile_token": "optional-token",
  "challenge_id": "optional-challenge-id",
  "challenge_result": "optional-result",
  "consent": true
}
```

Response:

```json
{
  "registration_id": "reg_123",
  "status": "ACCEPTED",
  "eligible": true,
  "duplicate": false,
  "policy_version": "v1.0",
  "created_at": "2026-10-04T09:12:30Z"
}
```

Possible error codes:

```text
AUTH_REQUIRED
CAMPAIGN_NOT_FOUND
CAMPAIGN_NOT_OPEN
REGISTRATION_NOT_STARTED
REGISTRATION_CLOSED
ADMISSION_REQUIRED
ADMISSION_PERMIT_EXPIRED
ADMISSION_PERMIT_REPLAYED
IDENTITY_NOT_VERIFIED
DUPLICATE_ENTRY
CHALLENGE_REQUIRED
CHALLENGE_FAILED
COOLDOWN_ACTIVE
IDEMPOTENCY_CONFLICT
```

## 14.3 Challenge routes

### `POST /api/v1/challenges`

Auth: authenticated user.

Request:

```json
{
  "campaign_id": "camp_123",
  "type": "TURNSTILE",
  "operation": "REGISTER",
  "requested_reason": "MEDIUM_RISK"
}
```

Response:

```json
{
  "challenge_id": "ch_123",
  "type": "TURNSTILE",
  "nonce": "nonce_123",
  "expires_at": "2026-10-04T09:14:00Z",
  "max_attempts": 2,
  "implementation_version": "turnstile-v1"
}
```

### `POST /api/v1/challenges/{id}/verify`

Auth: authenticated user.

Headers:

```http
Idempotency-Key: challenge-key-123
```

Request differs by challenge type:

```json
{
  "nonce": "nonce_123",
  "type": "MEDIAPIPE",
  "result": "SUCCESS",
  "confidence": 0.94,
  "duration_ms": 6420,
  "implementation_version": "mediapipe-v1",
  "turnstile_token": null
}
```

Response:

```json
{
  "challenge_id": "ch_123",
  "status": "PASSED",
  "risk_level": "LOW",
  "reason_code": "CHALLENGE_PASSED",
  "verified_until": "2026-10-04T09:20:00Z"
}
```

Possible errors:

```text
CHALLENGE_NOT_FOUND
CHALLENGE_EXPIRED
CHALLENGE_REPLAYED
CHALLENGE_SESSION_MISMATCH
CHALLENGE_ATTEMPT_LIMIT
CHALLENGE_FAILED
TURNSTILE_VERIFICATION_FAILED
```

## 14.4 Result and audit routes

### `GET /api/v1/campaigns/{id}/result`

Auth: authenticated user.

Response:

```json
{
  "campaign_id": "camp_123",
  "result": "SELECTED",
  "standby_position": null,
  "entitlement": {
    "id": "ent_123",
    "status": "CLAIM_PENDING",
    "expires_at": "2026-10-04T12:00:00Z"
  },
  "audit_reference": {
    "policy_version": "v1.0",
    "roster_hash": "hash_123",
    "randomness_reference": "rand_123",
    "algorithm_version": "lottery-v1"
  }
}
```

Standby response:

```json
{
  "campaign_id": "camp_123",
  "result": "STANDBY",
  "standby_position": 127,
  "entitlement": null,
  "audit_reference": {}
}
```

### `GET /api/v1/campaigns/{id}/audit`

Public aggregate audit endpoint.

Response:

```json
{
  "campaign_id": "camp_123",
  "policy_version": "v1.0",
  "policy_hash": "policy_hash",
  "registration_cutoff": "2026-10-04T10:00:00Z",
  "registered_count": 48213,
  "eligible_count": 46890,
  "duplicate_count": 1323,
  "roster_hash": "roster_hash",
  "randomness_reference": "rand_123",
  "algorithm_version": "lottery-v1",
  "winner_count": 500,
  "standby_rule": "FIXED_ORDER",
  "aggregate_selection_rates": {},
  "oversell_count": 0,
  "duplicate_allocation_count": 0
}
```

## 14.5 Entitlement and booking routes

### `POST /api/v1/entitlements/{id}/hold`

Auth: authenticated winner.

Headers:

```http
Idempotency-Key: hold-key-123
```

Request:

```json
{
  "campaign_id": "camp_123",
  "seat_id": "seat_18",
  "challenge_id": "ch_123",
  "challenge_status": "PASSED"
}
```

Response:

```json
{
  "entitlement_id": "ent_123",
  "seat_id": "seat_18",
  "seat_label": "A-18",
  "status": "HELD",
  "hold_expires_at": "2026-10-04T11:31:30Z",
  "server_time": "2026-10-04T11:30:00Z"
}
```

Possible errors:

```text
ENTITLEMENT_NOT_FOUND
ENTITLEMENT_NOT_OWNED
ENTITLEMENT_EXPIRED
ENTITLEMENT_REPLAYED
CAMPAIGN_PAUSED
SEAT_NOT_AVAILABLE
TICKET_LIMIT_REACHED
CHALLENGE_REQUIRED
CHALLENGE_NOT_PASSED
IDEMPOTENCY_CONFLICT
```

### `POST /api/v1/entitlements/{id}/redeem`

Auth: authenticated winner who owns the hold.

Headers:

```http
Idempotency-Key: redeem-key-123
```

Request:

```json
{
  "campaign_id": "camp_123",
  "seat_id": "seat_18",
  "confirm_event_name": "Hackathon Arena Finals",
  "confirm_seat_label": "A-18",
  "human_validation_id": "ch_123"
}
```

Response:

```json
{
  "booking_id": "booking_123",
  "entitlement_id": "ent_123",
  "seat_id": "seat_18",
  "seat_label": "A-18",
  "status": "CONFIRMED",
  "confirmed_at": "2026-10-04T11:30:20Z",
  "receipt_id": "receipt_123"
}
```

Possible errors:

```text
ENTITLEMENT_NOT_FOUND
ENTITLEMENT_NOT_OWNED
ENTITLEMENT_EXPIRED
HOLD_NOT_FOUND
HOLD_EXPIRED
SEAT_MISMATCH
HUMAN_VALIDATION_REQUIRED
HUMAN_VALIDATION_EXPIRED
REDEMPTION_PAUSED
CONFIRMATION_MISMATCH
REPLAYED_REDEMPTION
IDEMPOTENCY_CONFLICT
```

### `POST /api/v1/entitlements/{id}/release`

Auth: authenticated winner.

Releases a valid hold where the published policy permits it. Must be idempotent.

## 14.6 Admin routes

All require authenticated `ADMIN` role.

### `POST /api/v1/admin/campaigns`

Create a draft campaign.

### `GET /api/v1/admin/campaigns`

List campaigns and operational status.

### `GET /api/v1/admin/campaigns/{id}`

Return full admin-visible campaign configuration and counts.

### `PATCH /api/v1/admin/campaigns/{id}`

Edit only allowed draft/preparing fields. Reject frozen policy changes.

### `POST /api/v1/admin/campaigns/{id}/prepare`

Validate policy, timestamps, capacity, inventory, and required terms.

### `POST /api/v1/admin/campaigns/{id}/publish`

Publish campaign and make it visible to users.

### `POST /api/v1/admin/campaigns/{id}/open`

Move a prepared campaign to `OPEN` if the schedule permits.

### `POST /api/v1/admin/campaigns/{id}/close`

Stop registration.

### `POST /api/v1/admin/campaigns/{id}/freeze`

Resolve in-flight registrations, create canonical roster, calculate roster hash, and move `CLOSED → FROZEN`.

### `POST /api/v1/admin/campaigns/{id}/draw`

Run the deterministic lottery exactly once.

### `POST /api/v1/admin/campaigns/{id}/pause`

Pause admission, registration, or redemption.

Request:

```json
{
  "scope": "REGISTRATION",
  "reason": "Investigating burst traffic"
}
```

### `POST /api/v1/admin/campaigns/{id}/resume`

Resume the selected paused scope.

### `GET /api/v1/admin/campaigns/{id}/audit`

Detailed audit events for the admin.

### `GET /api/v1/admin/campaigns/{id}/metrics`

Detailed metrics.

### `GET /api/v1/admin/campaigns/{id}/claims`

Claim, hold, confirmation, expiry, and standby status.

### `POST /api/v1/admin/campaigns/{id}/standby/process-next`

Promote the next standby participant according to fixed order. Backend chooses the participant; admin cannot choose an arbitrary participant.

## 14.7 Metrics routes

### `GET /api/v1/campaigns/{id}/metrics`

Authenticated admin or permitted public aggregate view.

Metrics:

```text
total_attempts
unique_participants
eligible_entries
duplicate_attempts
suspicious_traffic
winner_count
standby_count
selection_rate_by_client_class
bot_advantage_ratio
available_seats
held_seats
confirmed_seats
expired_holds
oversell_count
duplicate_allocation_count
p95_latency_ms
p99_latency_ms
error_rate
retry_rate
challenge_success_count
challenge_failure_count
challenge_abandonment_count
cooldown_count
false_positive_count
recovery_success_count
```

---

# 15. Standard response and error contract

## Success envelope

Either a direct typed object or the following consistent envelope may be used. Choose one convention and apply it everywhere. Recommended:

```json
{
  "data": {},
  "meta": {
    "request_id": "req_123",
    "server_time": "2026-10-04T09:12:00Z"
  }
}
```

## Error envelope

```json
{
  "error": {
    "code": "REGISTRATION_CLOSED",
    "message": "Registration has ended",
    "request_id": "req_123",
    "details": {}
  }
}
```

Stable error codes are part of the frontend contract. Messages may improve, but codes must not change casually.

HTTP status guidance:

```text
400 invalid request or state transition
401 missing/invalid authentication
403 authenticated but not authorized
404 resource not found or not visible
409 state conflict/idempotency conflict/seat unavailable
410 expired permit/challenge/entitlement/hold
429 rate limited/cooldown
500 unexpected server error
503 safe temporary unavailability
```

When uncertain after a timeout, return or recover a durable state. Never create an uncertain second reservation.

---

# 16. Frontend–backend integration guide

## 16.1 Next.js responsibilities

Next.js owns:

- Pages and components.
- Supabase Auth UI.
- Route guards for user experience.
- API client.
- Loading, error, retry, and recovery states.
- Display timers from server timestamps.
- Waiting-room UI.
- Registration UI.
- Challenge host UI.
- Seat map.
- Confirmation screens.
- Admin dashboard views.
- Charts and audit pages.

Next.js does not own:

- Eligibility decisions.
- Winner selection.
- Seat availability truth.
- Entitlement validity.
- Timer authority.
- Admin authorization.
- Risk score authority.

## 16.2 Suggested Next.js route map

```text
/
/login
/signup
/verify-email
/events
/events/[campaignId]
/events/[campaignId]/waiting-room
/events/[campaignId]/register
/events/[campaignId]/status
/events/[campaignId]/result
/events/[campaignId]/claim
/events/[campaignId]/confirmed
/events/[campaignId]/audit
/profile

/admin/login
/admin
/admin/campaigns
/admin/campaigns/new
/admin/campaigns/[campaignId]
/admin/campaigns/[campaignId]/edit
/admin/campaigns/[campaignId]/monitor
/admin/campaigns/[campaignId]/draw
/admin/campaigns/[campaignId]/claims
/admin/campaigns/[campaignId]/audit
/admin/campaigns/[campaignId]/simulations
```

## 16.3 API client rules

Create one typed API client under the frontend application, for example:

```text
/apps/frontend/src/lib/api/client.ts
/apps/frontend/src/lib/api/types.ts
/apps/frontend/src/lib/api/errors.ts
/apps/frontend/src/lib/api/campaigns.ts
/apps/frontend/src/lib/api/registration.ts
/apps/frontend/src/lib/api/challenges.ts
/apps/frontend/src/lib/api/entitlements.ts
/apps/frontend/src/lib/api/admin.ts
```

The client must:

1. Read the current Supabase access token.
2. Add `Authorization` header.
3. Add `X-Request-ID`.
4. Add `Idempotency-Key` for state-changing calls.
5. Parse the standard error envelope.
6. Preserve `request_id` for support/debugging.
7. Never retry non-idempotent calls with a new key automatically.
8. Retry safe GET requests with bounded exponential backoff.
9. For a timed-out state-changing request, retry with the **same** idempotency key.

## 16.4 Timer implementation

Backend returns absolute ISO timestamps:

```json
{
  "server_time": "2026-10-04T11:30:00Z",
  "hold_expires_at": "2026-10-04T11:31:30Z"
}
```

Frontend computes:

```text
remaining = hold_expires_at - estimated_server_now
```

Do not trust the user’s local wall clock without correcting against `server_time`.

When the visual timer reaches zero, call the status endpoint. The backend decides whether the hold is expired.

## 16.5 Recovery after refresh/reconnect

On every protected campaign page:

1. Restore Supabase Auth session.
2. Obtain current access token.
3. Call `GET /api/v1/campaigns/{id}/status`.
4. Render the state returned by the backend.
5. Do not infer state from localStorage alone.

Recovery state examples:

```text
REGISTERED       → registration status page
SELECTED         → result/claim page
HELD             → seat-hold confirmation page
CONFIRMED        → booking confirmation page
COOLDOWN         → cooldown page/toast
PAUSED           → incident message and retry state
```

## 16.6 Polling/realtime

For the MVP, use polling every 5–10 seconds for status changes. Do not poll every second.

Use Supabase Realtime only if already stable. Realtime is a user-experience improvement, not the authority.

## 16.7 Frontend error mapping

| Error code | Frontend behavior |
|---|---|
| `AUTH_REQUIRED` | Send to login and preserve redirect URL |
| `FORBIDDEN` | Show access denied |
| `CAMPAIGN_NOT_OPEN` | Show campaign status |
| `REGISTRATION_CLOSED` | Disable registration and show cutoff |
| `CHALLENGE_REQUIRED` | Open challenge host |
| `CHALLENGE_FAILED` | Show retry state and attempt count |
| `COOLDOWN_ACTIVE` | Show 5-minute countdown toast/page |
| `ADMISSION_PERMIT_EXPIRED` | Call join/recover again |
| `ENTITLEMENT_EXPIRED` | Show expired claim state |
| `SEAT_NOT_AVAILABLE` | Refresh seat map and choose again |
| `HOLD_EXPIRED` | Clear local hold UI and refresh status |
| `IDEMPOTENCY_CONFLICT` | Stop retry and show support/request ID |
| `REPLAY_ATTEMPT` | Show security message, do not loop |
| `CAMPAIGN_PAUSED` | Show safe incident state |
| `503` | Show retry-after state without duplicating writes |

---

# 17. Database schema summary

Required durable tables:

```text
profiles
participants
sessions
campaigns
campaign_policy_snapshots
registrations
idempotency_records
admission_permits or replay_records
challenges
lottery_runs
lottery_entries/results
entitlements
seats
bookings
standby_promotions
audit_events
metric_events or metric aggregates
```

## Bookings table

```text
bookings
- id UUID
- campaign_id UUID
- participant_id UUID
- entitlement_id UUID unique
- seat_id UUID unique
- status text
- confirmed_at timestamptz
- receipt_id text
- created_at timestamptz
```

Unique constraints:

```text
unique(entitlement_id)
unique(seat_id) where status = 'CONFIRMED'
```

The exact partial-index syntax depends on the chosen ORM/migration style, but the database must enforce uniqueness rather than relying only on Python checks.

## Audit events

```text
audit_events
- id UUID
- campaign_id UUID nullable
- participant_id UUID nullable
- session_id UUID nullable
- actor_type text
- actor_id UUID nullable
- event_type text
- reason_code text nullable
- metadata_json jsonb
- request_id text
- created_at timestamptz
```

Never place secrets, access tokens, or raw challenge answers in audit metadata.

---

# 18. FastAPI backend structure

```text
/apps/backend/
  app/
    main.py
    config.py
    dependencies.py
    api/
      router.py
      routes_public_campaigns.py
      routes_campaigns.py
      routes_registration.py
      routes_challenges.py
      routes_entitlements.py
      routes_admin.py
      routes_metrics.py
      routes_health.py
    domain/
      campaign.py
      participant.py
      session.py
      admission.py
      registration.py
      risk.py
      challenge.py
      lottery.py
      entitlement.py
      inventory.py
      audit.py
    models/
      campaign.py
      participant.py
      registration.py
      seat.py
      entitlement.py
      challenge.py
      audit.py
    schemas/
      common.py
      auth.py
      campaign.py
      admission.py
      registration.py
      challenge.py
      lottery.py
      entitlement.py
      metrics.py
      admin.py
    repositories/
      campaigns.py
      participants.py
      registrations.py
      seats.py
      entitlements.py
      challenges.py
      audit.py
    services/
      auth_service.py
      session_service.py
      admission_service.py
      registration_service.py
      risk_service.py
      challenge_service.py
      lottery_service.py
      entitlement_service.py
      inventory_service.py
      metrics_service.py
      audit_service.py
    security/
      jwt.py
      signatures.py
      replay.py
      rate_limits.py
      request_ids.py
    integrations/
      supabase_auth.py
      turnstile.py
      challenge_adapter.py
      redis.py
    workers/
      expiry_worker.py
      metrics_worker.py
      standby_worker.py
  migrations/
  tests/
    unit/
    integration/
    concurrency/
  requirements.txt or pyproject.toml
  README.md
```

Use domain/service/repository separation inside one FastAPI deployable application. Do not create microservices during the hackathon.

---

# 19. Configuration and secrets

Environment variables should include:

```text
APP_ENV=development|demo|production
APP_NAME=fair-drop
API_V1_PREFIX=/api/v1
DATABASE_URL=...
REDIS_URL=optional
SUPABASE_URL=...
SUPABASE_JWT_AUDIENCE=authenticated
SUPABASE_JWT_ISSUER=...
SUPABASE_JWT_SECRET_OR_JWKS_URL=...
TURNSTILE_SECRET_KEY=...
SIGNING_KEY_ID=...
SIGNING_PRIVATE_KEY=...
IDLE_SESSION_SECONDS=120
ABSOLUTE_REDEMPTION_SECONDS=300
SEAT_HOLD_SECONDS=120
COOLDOWN_SECONDS=300
MAX_CHALLENGE_ATTEMPTS=2
```

Never commit secrets. Never expose service-role keys or signing private keys to Next.js. Frontend only receives public configuration such as Supabase URL and anon key where appropriate.

Python requirement:

```text
Python 3.11.9
/apps/backend/.venv
```

Pin dependencies and commit requirements/lock files, never `.venv`.

---

# 20. Redis behavior

Redis may be used for:

- Rate-limit counters.
- Caching public campaign state.
- Short-lived admission metadata.
- Challenge acceleration.
- Queue metadata.

Redis must not be the only authority for:

- Seat ownership.
- Confirmed booking.
- Winner entitlement.
- Registration uniqueness.
- Lottery result.

If Redis fails:

- PostgreSQL inventory remains correct.
- New admissions may pause or degrade safely.
- Registration may use a database-backed fallback or pause.
- Existing confirmed bookings remain intact.
- The API returns a clear retry/read-only state.

---

# 21. Background workers and scheduled jobs

Required worker jobs:

## Expired session/hold worker

- Find expired holds.
- Lock each candidate row.
- Confirm it is still expired.
- Return `HELD → AVAILABLE`.
- Mark entitlement `HELD → EXPIRED` where applicable.
- Write audit events.
- Trigger standby promotion according to policy.

## Standby promotion worker

- Select the lowest unprocessed standby position.
- Lock the row.
- Issue one entitlement.
- Record promotion.
- Never choose arbitrary replacements.

## Idempotency cleanup worker

- Remove or archive expired idempotency records according to retention policy.

## Metrics aggregation worker

- Aggregate raw metric events.
- Never replace source audit events with hard-coded dashboard values.

Workers must be safe to restart. Each state transition must be idempotent or protected by a lock/unique constraint.

---

# 22. Security and privacy requirements

- HTTPS in deployed environments.
- Server-side Supabase JWT validation.
- Admin authorization in FastAPI.
- Short-lived signed permits and entitlements.
- Replay protection.
- Rate limits by operation, account, session, campaign, verification state, and network signal.
- Do not hard-block every shared IP.
- Do not trust frontend state.
- Do not log tokens, passwords, raw OTPs, or challenge answers.
- Hash or minimize email, phone, device, and IP-derived data.
- Use request IDs in logs and user-facing errors.
- Apply security headers and appropriate CORS.
- Validate all request bodies with Pydantic schemas.
- Use database migrations and constraints.
- Keep admin audit events.
- Provide accessible alternatives to camera challenges.
- Retain only the data required for the demo/policy.

---

# 23. Test and verification plan

## Unit tests

- Campaign transitions.
- Registration eligibility.
- Risk thresholds.
- Permit signing and verification.
- Challenge expiry and nonce checks.
- Deterministic lottery.
- Standby ordering.
- Timer calculations.
- Error mapping.

## Database/integration tests

- Unique registration constraint.
- Same idempotency key/same body returns same result.
- Same idempotency key/different body rejects.
- Expired hold release.
- Replay rejection.
- Admin role enforcement.
- Roster freeze boundary.
- Draw cannot run twice.

## Concurrency tests

- Parallel registration for the same participant.
- Parallel holds for the same seat.
- Parallel holds for different seats.
- Parallel redeem requests.
- Parallel standby promotion.
- Lost response followed by retry.
- Worker restart during expiry.
- Database conflict during confirmation.

## Adversarial tests

- Fast bot.
- Burst bot.
- Retry bot.
- Account farm.
- Direct API caller.
- Token replay.
- Challenge replay.
- Race-condition attacker.
- Shared-network legitimate users.
- Slow/accessibility-focused users.

## Required assertions

```text
confirmed_seats <= capacity
no seat belongs to two participants
no participant exceeds ticket limit
one participant has one registration
expired holds return to inventory
replayed permits/challenges/entitlements fail
same idempotency key + same request returns same result
different request under same key fails
lottery replay returns identical order
standby promotion follows fixed order
```

---

# 24. Metrics and fairness evidence

Metrics must come from real events or real simulation runs.

Required metrics:

```text
total_attempts
unique_participants
eligible_entries
duplicate_attempts
suspicious_traffic
winners
standby_count
selection_rate_by_client_class
human_win_rate
bot_win_rate
bot_advantage_ratio
available_seats
held_seats
confirmed_seats
expired_holds
oversell_count
duplicate_allocation_count
p95_latency
p99_latency
error_rate
retry_rate
challenge_success
challenge_failure
challenge_abandonment
cooldown_count
false_positive_rate
recovery_success_rate
```

Useful definitions:

```text
human_win_rate = human_winners / eligible_human_entries
bot_win_rate = bot_winners / eligible_bot_entries
bot_advantage = bot_win_rate - human_win_rate
```

The key evidence is that increasing bot request volume does not proportionally increase bot selection probability.

Also report legitimate-user impact:

- Shared-network completion.
- Slow-network completion.
- Keyboard-only completion.
- Challenge abandonment.
- False-positive rate.
- Recovery success.

---

# 25. Frontend page behavior by backend state

| Backend state | Frontend page/behavior |
|---|---|
| `UNAUTHENTICATED` | Login/signup with redirect preserved |
| `DRAFT/PREPARING` public | Not visible or show unavailable |
| `OPEN` | Event page and join button |
| `WAITING` | Waiting room; no refresh required |
| `ADMITTED` | Registration page |
| `CHALLENGE_REQUIRED` | Challenge host |
| `REGISTERED` | Registration status |
| `CLOSED` | Registration closed message |
| `FROZEN/DRAWING` | Result pending |
| `SELECTED` | Result and claim button |
| `STANDBY` | Standby position |
| `NOT_SELECTED` | Final result |
| `CLAIM_PENDING` | Human validation and seat selection |
| `HELD` | Seat confirmation with server timer |
| `CONFIRMED` | Booking confirmation and receipt |
| `EXPIRED` | Expired state and published recovery option |
| `COOLDOWN` | Five-minute cooldown countdown |
| `PAUSED` | Safe incident message |
| `503` | Retry/read-only state |

---

# 26. Admin frontend flow

```text
Admin login
  → Admin dashboard
  → Create draft campaign
  → Configure event, rules, capacity, and times
  → Save draft
  → Prepare and validate
  → Publish/open campaign
  → Monitor registrations, risk, inventory, and latency
  → Close registration
  → Freeze roster
  → Review roster hash and policy version
  → Run lottery
  → Monitor winners, standby, claims, holds, and confirmations
  → Process fixed-order standby promotions
  → Pause/resume if necessary
  → View audit and final metrics
```

Admin buttons must be state-aware. Do not show `Run Lottery` before `FROZEN`. Do not show `Publish` after the policy is frozen. Do not allow arbitrary standby selection.

Destructive or irreversible admin actions require a confirmation dialog and produce an audit event.

---

# 27. API integration workflow for the team

## Backend owner

Dhruv owns:

- FastAPI.
- PostgreSQL models/migrations.
- Supabase JWT validation.
- Roles and sessions.
- Admission permits.
- Registration/idempotency.
- Risk orchestration.
- Challenge adapter.
- Roster freeze.
- Lottery.
- Entitlements.
- Inventory transactions.
- Metrics/audit APIs.

## Frontend owner

Rohan consumes only:

- OpenAPI schemas.
- Stable JSON responses.
- Stable error codes.
- Documented server timestamps.
- Documented state transitions.

Rohan does not import backend Python code or access the database directly.

## MediaPipe owner

Naman provides:

- Challenge type names.
- Input expectations.
- Result contract.
- Implementation version.
- Confidence/duration semantics.
- Accessible fallback behavior.

FastAPI consumes the adapter result and does not import MediaPipe internals.

## Simulator owner

Dhanya uses:

- Public HTTP API.
- Documented auth/test fixtures.
- Metrics endpoints.
- Stable client-class labels.

The simulator must not query backend database internals or create undocumented production bypasses.

## Shared contract rules

- OpenAPI is generated from FastAPI.
- Any schema change requires a written note.
- Changes to shared API types require synchronized frontend and simulator updates.
- Every PR states changed directories, API changes, tests, and migration needs.
- Keep commits narrow:
  - `backend:`
  - `frontend:`
  - `mediapipe:`
  - `simulator:`
  - `docs:`

---

# 28. Demo sequence for judges

1. Admin creates a 500-seat event.
2. UI shows fixed policy, capacity, registration window, and uniform lottery.
3. Normal users and bots register.
4. Burst bots send duplicate requests.
5. Backend deduplicates and rate-limits them.
6. Suspicious clients receive challenges.
7. Repeated abuse triggers five-minute cooldown.
8. Registration closes.
9. Roster freezes and hash is displayed.
10. Admin runs the deterministic lottery.
11. Winner receives a single-use entitlement.
12. Winner completes human validation.
13. Two parallel requests attempt the same seat.
14. Only one succeeds.
15. Replayed entitlement is rejected.
16. Lost response is retried with the same idempotency key.
17. Original result returns without duplicate booking.
18. User refreshes/reconnects and state is recovered.
19. Expired hold returns to inventory.
20. Dashboard shows zero overselling and zero duplicate allocations.
21. Fairness chart shows more requests did not create more selection probability.

Judge statement:

> **We do not claim perfect bot detection. We remove the speed race, cap each participant at one eligible chance, require human validation before final redemption, protect inventory atomically, and produce measurable evidence that bots cannot dominate allocation.**

---

# 29. Definition of done

The backend and integration are ready when:

- FastAPI starts cleanly from Python 3.11.9.
- Migrations create the required schema.
- Supabase JWT authentication works.
- `USER` and `ADMIN` authorization works.
- Admin campaign lifecycle works.
- Published campaigns appear to users.
- Registration is idempotent and unique.
- Waiting/admission permits are signed, bound, expiring, and replay-protected.
- Roster freezes before the draw.
- Lottery is deterministic and reproducible.
- Standby order is fixed.
- Entitlements are bound, expiring, and single-use.
- Challenge adapter supports Turnstile, MediaPipe, visual, and mock modes.
- Human validation is required before final redemption.
- Holds and confirmations are atomic.
- Parallel requests cannot oversell.
- Refresh/reconnect retrieves durable state.
- Session, redemption, and seat timers are server-authoritative.
- Same idempotency key/same request returns the same result.
- Same key/different request is rejected.
- Replayed permits, challenges, and entitlements are rejected.
- Metrics and audit APIs return real data.
- Frontend consumes documented HTTP contracts.
- Simulator consumes documented HTTP contracts.
- Expiry and standby workers are restart-safe.
- Errors expose stable codes and request IDs.
- No secrets are exposed to the frontend or committed.
- No team member needs to edit another owner’s internals for normal integration.

---

# 30. Final implementation rule

When there is a conflict between visual convenience and backend correctness, backend correctness wins.

When there is a conflict between bot friction and legitimate accessibility, use adaptive friction and an alternative path rather than an absolute block.

When there is a conflict between Redis speed and PostgreSQL ownership, PostgreSQL wins.

When there is a conflict between a browser timer and a server timestamp, the server wins.

When there is a conflict between a queue display and a signed backend permit, the signed backend permit wins.

When there is a conflict between a frontend assumption and the OpenAPI contract, the OpenAPI contract wins.

> **Fair Drop is complete only when fairness, allocation, inventory integrity, authentication, recovery, and evidence all work together—not when the booking screen merely looks finished.**
