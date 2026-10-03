# Fair Drop — Product Requirements Document

## 1. Product definition

Fair Drop is a high-demand event registration and limited-seat allocation platform. The demo scenario is **500 seats competing for attention from up to 50,000 participants**.

The product exists to solve two connected problems:

1. The website must remain reliable when demand arrives as a flash crowd.
2. Participants must not gain a meaningful allocation advantage merely by being faster, sending more requests, retrying more aggressively, or automating the process.

Fair Drop does not claim perfect bot detection. It uses controlled registration, identity/eligibility limits, risk-based friction, a frozen roster, an auditable uniform lottery, single-use entitlements, human validation, and atomic inventory controls.

## 2. Target users

### Participants

People trying to register for a scarce event. They may be normal users, slow users, shared-network users, or users who experience refreshes, reconnects, and temporary failures.

### Organizer/operator

The person who creates and controls a campaign, configures the registration window and capacity, starts the draw, observes system health, pauses dangerous operations, and reviews fairness evidence.

### Adversarial clients

Automated or misbehaving clients used by the simulator. They test burst traffic, retries, duplicate submissions, account farms, direct API access, token replay, and race conditions.

### Judges/auditors

People who need to understand why the system is fair and reliable. They require visible rules, reproducible allocation evidence, real metrics, and a clear demonstration of failure resistance.

## 3. Goals

- Support the 500-seat/50,000-participant scenario without collapsing the core application.
- Ensure one eligible entry per participant per campaign.
- Make speed and repeated request volume irrelevant after a valid entry exists.
- Freeze the eligible roster before allocation.
- Produce a reproducible uniform lottery and fixed standby order.
- Prevent duplicate allocations and overselling under concurrent requests.
- Preserve participant state across refresh, reconnect, timeout, and retry.
- Apply stronger friction to suspicious traffic without automatically rejecting shared-network or accessibility users.
- Demonstrate behavior with configurable simulations and real metrics.

## 4. Non-goals

- Perfect identification of every bot.
- Guaranteeing every participant a seat.
- Treating one IP address as one person.
- Using a CAPTCHA as the sole security mechanism.
- Building a production payment system for the hackathon MVP.
- Starting with microservices merely to appear scalable.
- Exposing private participant data on the public audit page.

## 5. Product principles

1. **Remove the race:** registration within the window is not a millisecond competition.
2. **One opportunity, not one request:** repeated requests must not create repeated chances.
3. **Backend authority:** the browser cannot decide eligibility, inventory, result, or expiry.
4. **Durable state:** every important user result can be recovered after refresh or reconnect.
5. **Separate capacity from fairness:** admission protects infrastructure; lottery allocation decides eligibility.
6. **Measure honestly:** compare winners against valid entries, not raw request counts.
7. **Minimize false positives:** shared networks and slow/accessibility users need a recoverable path.

## 6. Core user flow

```text
Event page
  → waiting room/admission
  → identity/session verification
  → optional risk challenge
  → one registration
  → registration receipt
  → registration closes
  → roster freezes
  → lottery runs
  → winner/standby result
  → single-use entitlement
  → human validation
  → temporary seat hold
  → atomic confirmation
  → ticket/confirmation receipt
```

## 7. Functional requirements

### Campaign management

Operators can create a campaign with name, description, capacity, registration start/end, redemption deadline, maximum tickets per participant, policy version, and standby policy.

### Event status

The system exposes campaign state and server-time countdowns. Invalid operations are rejected according to the campaign state machine.

```text
DRAFT → PREPARING → OPEN → CLOSED → FROZEN → DRAWING → CLAIMING → COMPLETED
```

### Waiting room and admission

A participant can join the campaign and receive a short-lived signed admission permit. The permit is bound to the session/campaign/operation and is not equivalent to a visible queue number.

### Registration

A valid participant can register once. Registration accepts an idempotency key. The same key and same request return the original result. The same key with a different request is rejected. A unique campaign/participant constraint prevents duplicate entries.

### Risk and challenges

The system can assign low/medium/high risk based on transparent signals. Medium/high-risk traffic can receive rate limits, cooldown, Turnstile, visual challenge, or MediaPipe challenge. Challenge success is a friction signal, not perfect proof of humanity.

### Lottery

After registration closes, the system freezes a canonical eligible roster, stores a roster hash, runs a reproducible uniform lottery, creates 500 winners and a fixed standby order, and records an audit run.

### Entitlements and seats

Winners receive short-lived single-use entitlements. Final redemption requires human validation. Seat movement is `AVAILABLE → HELD → CONFIRMED`; expired holds return safely to availability according to the published policy.

### Observability

Operators can view participation, fairness, inventory, reliability, security, challenge, cooldown, and false-positive metrics.

## 8. Acceptance criteria

- Confirmed seats never exceed campaign capacity.
- A seat cannot belong to two participants.
- A participant cannot exceed the ticket limit.
- Repeated registration does not create repeated entries.
- Roster cannot change after freeze.
- Lottery result can be independently replayed from stored audit data.
- Replayed permits, challenges, and entitlements are rejected.
- Same idempotency key returns the same result.
- Lost response plus retry does not duplicate state.
- Parallel hold requests cannot oversell.
- Refresh and reconnect recover the participant state.
- Shared-network and slow users are not automatically rejected solely because of IP or latency.
- Dashboard numbers come from actual simulations, not hard-coded values.

## 9. MVP priorities

### Must have

Campaign lifecycle, registration window, identity/verification, one-entry rule, idempotency, roster freeze, uniform lottery, standby order, PostgreSQL inventory authority, atomic holds/confirmation, replay protection, basic rate limits, server-side timers, simulator, dashboard.

### Strong differentiators

Turnstile, five MediaPipe games, visual challenge, risk-based friction, five-minute cooldown, signed permits/entitlements, public audit page, Fairness Receipt, accessibility alternative, operator kill switch.

### Later only if core is stable

Proof-of-work, honeypot, Merkle proof, passkeys, advanced device clustering, payments, multi-region deployment.
