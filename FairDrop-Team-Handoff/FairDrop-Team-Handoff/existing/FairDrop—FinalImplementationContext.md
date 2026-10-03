# Fair Drop — Final Implementation Context

> **Hackathon project:** Fair Drop: Selling 500 Seats to 50,000 People Without Letting Bots Win
>
> **Document purpose:** This is the final product, architecture, implementation, testing, and demo context for the hackathon build. The separate four-person work-split document is intentionally **not created yet**.

---

## 1. Final Decision in One Paragraph

Fair Drop will **not claim to detect and eliminate every bot**. That is unrealistic and is not what the problem statement requires. The system will allow a user or a legitimate human-assisted agent to join the process, but it will prevent automation from gaining extra chances through speed, request volume, repeated attempts, duplicate accounts, queue manipulation, or token replay. A real person must complete a human-validation step before a temporary seat hold becomes a final booking. Suspicious clients receive additional friction, such as Cloudflare Turnstile, a visual challenge, or a MediaPipe mini-game. Repeated abuse is throttled and moved to a delayed/review path, such as a five-minute cooldown or restricted waiting list. The core fairness comes from **registration plus a frozen uniform lottery**, not from trying to make a perfect CAPTCHA.

---

## 2. The Core Principle

> **Remove the race instead of trying to make users better at racing bots.**

A conventional first-come-first-served booking system rewards:

- Faster internet connections.
- Faster scripts.
- More parallel requests.
- Aggressive retries.
- Direct API access.
- Queue jumping.
- Large numbers of accounts.

Fair Drop changes the process:

1. Users register during a defined registration window.
2. Repeated submissions do not create extra entries.
3. Identity and abuse controls produce one eligible entry per participant.
4. Registration closes.
5. The eligible roster is frozen.
6. The system runs a transparent uniform lottery.
7. Winners receive short-lived, single-use booking entitlements.
8. A human validation step is required before final redemption.
9. PostgreSQL atomically protects the seat inventory.
10. The dashboard proves whether stronger bots actually gained an advantage.

If a bot sends 10,000 requests, it must not receive 10,000 chances.

---

## 3. What “Without Letting Bots Win” Means

The project does **not** require this impossible promise:

> “Every automated browser will be detected and rejected.”

The project requires this measurable promise:

> **An automated client must not gain a meaningful allocation advantage merely by being faster, sending more requests, creating more accounts, or retrying more aggressively.**

A bot that uses one valid account and follows the same rules may still be technically indistinguishable from a human. That is acceptable. It receives only one controlled opportunity.

A bot that floods, duplicates, replays, or manipulates the system should be:

- Rate-limited.
- Asked for stronger verification.
- Delayed.
- Moved to a restricted waiting list.
- Temporarily cooled down.
- Or blocked for the specific operation.

The correct design is **risk-based friction**, not an absolute human-versus-bot binary classifier.

---

## 4. Final User and Agent Policy

### 4.1 What is allowed

A human may use an agent to:

- Find the event.
- Open the website.
- Join the waiting room.
- Track registration status.
- Monitor the lottery result.
- Fill ordinary non-sensitive form fields.

### 4.2 What is not allowed

An automated client must not be allowed to:

- Create unlimited entries.
- Skip the waiting room.
- Reuse a queue token.
- Reserve multiple seats beyond the policy.
- Complete the final human-validation step automatically.
- Replay a successful entitlement.
- Hold seats forever.
- Use repeated requests to increase selection probability.

### 4.3 Human-in-the-loop rule

The final confirmation flow is:

```text
Registration or agent assistance
        -> Fair lottery
        -> Winner receives a temporary entitlement
        -> Seat is temporarily held
        -> Human completes validation
        -> Human confirms the exact event and seat
        -> Seat becomes CONFIRMED
```

This does not prove that a natural human performed every previous action. It creates a meaningful human-controlled boundary before scarce inventory is permanently consumed.

---

## 5. Primary Allocation Model

### 5.1 Registration window

The organizer configures:

- Event name.
- Capacity: 500 seats for the demo.
- Registration start time.
- Registration end time.
- Maximum tickets per participant.
- Eligibility rules.
- Redemption deadline.
- Standby rules.
- Published policy version.

Users register during the window. Arriving earlier within the window does not improve lottery probability.

### 5.2 One entry per participant

For the hackathon MVP, use:

- Verified email.
- Phone OTP if already available in the chosen stack; otherwise simulate it clearly in the demo.
- One account per campaign.
- One active registration per campaign.
- One entry per verified participant.

The system must distinguish:

1. Whether an account is controlled.
2. Whether a request looks automated.
3. Whether the participant is verified as a unique person.

These are different properties and must not be treated as identical.

### 5.3 Uniform lottery

After registration closes:

1. Freeze the registration cutoff.
2. Freeze the campaign policy.
3. Remove duplicate registrations according to the published rule.
4. Create a deterministic roster commitment.
5. Run a reproducible shuffle using a committed seed.
6. Select 500 winners.
7. Create a fixed-order standby list.
8. Store the allocation audit record.

Every eligible entry has the same ex-ante probability under the uniform lottery.

### 5.4 Why the lottery is the fairness core

The lottery makes these factors irrelevant after a valid registration exists:

- Being the first request by a few milliseconds.
- Sending more duplicate requests.
- Refreshing aggressively.
- Using a faster script.
- Having a faster connection.

The waiting room protects capacity. It does **not** secretly decide winners.

---

## 6. High-Level Architecture

```text
                    Participants and Agents
                              |
                              v
                    Frontend / Public Event Page
                              |
                              v
                    Waiting Room / Admission Gate
                              |
                              v
              Signed Permit + Session + Rate Limiting
                              |
                              v
                 Registration and Verification API
                              |
              +---------------+----------------+
              |                                |
              v                                v
       Risk/Friction Service              PostgreSQL
       - request signals                  - campaigns
       - challenge state                  - participants
       - registrations                     - lottery roster
       - cooldowns                         - seats
                                            - holds
                                            - entitlements
                                            - audit log
              |                                |
              v                                v
  Turnstile / MediaPipe / Image Challenge       Inventory Authority
              |
              v
      Lottery and Allocation Service
              |
              v
      Winner Portal + Fairness Receipt
              |
              v
       Organizer Metrics Dashboard
```

### 6.1 Recommended technology for a fast MVP

Use a stack the team already knows. A practical option is:

- **Frontend:** React or Next.js.
- **Backend:** Node.js with TypeScript and Express/Fastify, or the team’s strongest backend framework.
- **Database:** PostgreSQL as the inventory and durable-state authority.
- **Short-lived state/rate limiting:** Redis if already available; otherwise PostgreSQL-backed counters for the MVP.
- **Challenges:** Cloudflare Turnstile plus a custom MediaPipe/visual challenge.
- **Load simulation:** k6, Locust, or a bounded Node/Python simulator.
- **Charts:** Recharts, Chart.js, or another existing chart library.

Do not spend hackathon time adding technologies merely to make the architecture look large. The important properties are correctness, measurable fairness, and a reliable demo.

---

## 7. Registration and Waiting-Room Flow

### 7.1 Before registration

1. User opens the event page.
2. Server creates or recovers a session.
3. User sees event rules, capacity, registration window, maximum tickets, privacy notice, and policy version.
4. User joins the waiting room if traffic exceeds the safe backend level.

### 7.2 During registration

1. User receives a short-lived signed admission permit.
2. Server validates the permit.
3. User completes account and identity verification.
4. Risk signals are evaluated.
5. High-risk users receive step-up friction.
6. The server records one registration using an idempotency key.
7. Repeating the same request returns the original registration result.

### 7.3 After registration closes

1. Registration endpoint closes.
2. Participant roster is frozen.
3. Duplicate entries are removed by the published rule.
4. Lottery runs once.
5. Winners receive private results.
6. Standby participants receive their fixed position.
7. The public audit page shows aggregate evidence.

---

## 8. Anti-Bot and Human-Validation Layers

No single challenge is the main security boundary. The layers are:

### Layer 1: One-entry rule

The strongest fairness control is not a puzzle. It is preventing repeated attempts from creating repeated chances.

```text
One verified participant + one campaign = one lottery entry
```

### Layer 2: Endpoint-specific rate limits

Use different limits for:

- Login or OTP generation.
- Registration.
- Challenge generation.
- Challenge verification.
- Seat hold.
- Final redemption.
- Email or SMS requests.

Do not use only an IP limit because campus, hostel, office, and family networks may contain many legitimate users.

Recommended demo behavior:

```text
Too many requests to one operation
        -> slow that operation
        -> show a reason code
        -> start a 5-minute cooldown after repeated violations
```

### Layer 3: Cloudflare Turnstile

Use Turnstile as the main low-effort managed challenge layer.

Recommended placement:

- Always or conditionally at registration for the demo.
- Definitely before final entitlement redemption.
- Again only for high-risk repeated attempts.

The browser obtains a token. The backend verifies that token. The browser result must never be trusted by itself.

Turnstile supports managed, non-interactive, and invisible modes and can adapt the challenge to the visitor or browser. Cloudflare documents browser checks, proof-of-work-style signals, and server-side validation requirements. See References.

### Layer 4: MediaPipe mini-games

Build five small games using the Roboflow/MediaPipe-style workflow:

1. Show an open palm.
2. Show a thumbs-up.
3. Show a thumbs-down.
4. Show two fingers.
5. Hold a hand inside a target box or circle.

Each challenge should last approximately 5–10 seconds.

The game should:

- Show one instruction.
- Use a short timer.
- Require a fresh challenge nonce.
- Produce a client result.
- Send the result and nonce to the backend.
- Be accepted only once.
- Be bound to the current session.
- Expire quickly.

The MediaPipe result is a risk signal and friction mechanism. It is not a claim of perfect human proof.

Use MediaPipe as:

```text
High-risk or repeated suspicious activity
        -> MediaPipe game
        -> success: continue
        -> failure: retry once or move to cooldown/waiting list
```

Do not force all users to use a camera. Keep an accessible alternative.

### Layer 5: Confusing-image challenge

Add one optional visual challenge for suspicious users, such as:

- Select the object matching a rotated reference.
- Select the image containing a target shape.
- Click three objects in the requested order.
- Identify a simple shape among distractors.

The challenge should be generated from a known server-side answer. Store only the challenge hash and answer hash where practical. Accept it once and expire it quickly.

Do not describe it as AI-proof. Its role is to slow simple automation and add another independent signal.

### Layer 6: Honeypot

Add a hidden field that genuine users never see or fill. If it is populated, add risk rather than immediately permanently banning the participant.

### Layer 7: Proof-of-work, optional

If time permits, require a small hash puzzle for repeated high-volume requests. Keep the difficulty low enough for normal devices. Use it for request-cost control, not human identification.

### Layer 8: Cooldown and restricted waiting list

If the same account/session repeatedly fails or violates controls:

```text
First suspicious event  -> step-up challenge
Second repeated event   -> slow down
Further repetition      -> 5-minute cooldown
Continued abuse         -> restricted waiting list or operation block
```

The toast message should be clear:

> “We detected repeated attempts on this operation. Please come back in 5 minutes. Your valid registration status has not been deleted.”

Do not destroy a valid registration merely because a later request was suspicious.

---

## 9. Session, Booking, and Timer Design

Use three separate timers.

### 9.1 Idle session timeout

Recommended MVP value:

```text
2 minutes of inactivity
```

The frontend shows a warning at 30 seconds remaining. The backend is authoritative and invalidates the session after expiry.

### 9.2 Absolute booking-session timeout

Recommended MVP value:

```text
5 minutes maximum for a winner’s active redemption session
```

The user cannot extend this indefinitely by sending background requests.

### 9.3 Seat-hold timeout

Recommended MVP value:

```text
90–120 seconds for a temporary seat hold
```

The timer begins when the seat moves from AVAILABLE to HELD. If it expires:

- The hold is invalidated server-side.
- The seat returns to AVAILABLE.
- The old entitlement cannot be reused.
- The user must follow the published recovery policy.

OWASP recommends both idle and absolute session timeouts and requires server-side session invalidation rather than relying only on a client-side timer.

---

## 10. Seat and Inventory Rules

Use explicit states:

```text
AVAILABLE -> HELD -> CONFIRMED
                 \
                  -> AVAILABLE after expiry
```

PostgreSQL is the source of truth.

The database must guarantee:

- No seat is assigned to two participants.
- Confirmed seats never exceed capacity.
- A participant does not exceed the ticket limit.
- An expired hold becomes available.
- A repeated request does not create a second reservation.
- A replayed entitlement is rejected.

Use:

- Transactions.
- Conditional updates.
- Row locks where required.
- Unique constraints.
- Short transactions.
- Server-side expiry checks.

Example conceptual conditional update:

```sql
UPDATE seats
SET status = 'HELD',
    held_by = $participant_id,
    hold_expires_at = $expires_at,
    version = version + 1
WHERE id = $seat_id
  AND status = 'AVAILABLE';
```

The backend must check that exactly one row was updated.

---

## 11. Idempotency and Replay Protection

Use an idempotency key for:

- Registration.
- Challenge verification.
- Seat hold.
- Final redemption.
- Payment-like confirmation.

If a response is lost and the client retries the same request, return the original result.

If the same key is used with a different request body, reject it.

Reject:

- Reused challenge nonces.
- Challenges used with a different session.
- Expired admission permits.
- Reused queue permits.
- Reused entitlements.
- Replayed redemption requests.
- Duplicate webhooks in the future payment integration.

---

## 12. Signed Admission Permits and Entitlements

### Admission permit

A permit should contain or represent:

- Campaign ID.
- Participant/session ID.
- Expiration time.
- Nonce.
- Allowed operation.
- Server signature.

The backend must verify the signature, expiry, session binding, and replay status.

A browser-visible queue number is not authorization.

### Winner entitlement

A winner receives a short-lived single-use entitlement containing:

- Campaign ID.
- Participant ID.
- Entitlement ID.
- Expiry time.
- Nonce.
- Allowed operation.

The browser cannot decide whether it is valid. The backend decides.

---

## 13. Suggested Data Model

### campaigns

```text
id
name
description
capacity
registration_start
registration_end
redemption_deadline
max_tickets_per_participant
allocation_method
policy_version
policy_hash
status
created_at
updated_at
```

### participants

```text
id
account_id
email_hash
phone_hash
verification_status
risk_level
created_at
```

### registrations

```text
id
campaign_id
participant_id
idempotency_key
request_hash
status
eligible
created_at
```

Unique constraints:

```text
unique(campaign_id, participant_id)
unique(campaign_id, idempotency_key)
```

### seats

```text
id
campaign_id
seat_label
status
held_by
hold_expires_at
confirmed_by
version
```

### entitlements

```text
id
campaign_id
participant_id
nonce_hash
status
expires_at
redeemed_at
```

### challenges

```text
id
session_id
campaign_id
type
nonce_hash
answer_hash
status
expires_at
attempt_count
```

### audit_events

```text
id
campaign_id
participant_id
session_id
event_type
reason_code
metadata_json
created_at
```

### lottery_runs

```text
id
campaign_id
policy_version
roster_hash
randomness_reference
algorithm_version
winner_count
standby_count
executed_at
```

---

## 14. Suggested API Surface

```text
POST /api/campaigns/:id/join
```

Join the waiting room and obtain a signed admission permit.

```text
GET /api/campaigns/:id/status
```

Read registration state, queue state, countdowns, and published rules.

```text
POST /api/campaigns/:id/register
```

Create one idempotent registration.

```text
POST /api/challenges
```

Create a short-lived challenge for the current session.

```text
POST /api/challenges/:id/verify
```

Verify Turnstile, visual, or MediaPipe challenge output server-side.

```text
GET /api/campaigns/:id/result
```

Return winner, standby, or not-selected status after allocation.

```text
POST /api/entitlements/:id/hold
```

Atomically hold an available seat for a valid winner.

```text
POST /api/entitlements/:id/redeem
```

Perform human validation and atomically confirm the held seat.

```text
POST /api/entitlements/:id/release
```

Release a voluntary hold according to policy.

```text
GET /api/campaigns/:id/audit
```

Return public aggregate audit data.

```text
GET /api/campaigns/:id/metrics
```

Return organizer dashboard metrics.

```text
POST /api/admin/campaigns/:id/draw
```

Freeze the roster and execute the lottery once.

```text
POST /api/admin/campaigns/:id/pause
```

Emergency kill switch for registration, admission, or redemption.

Every protected endpoint must validate the session, campaign, permit, entitlement, idempotency key, and risk state as appropriate.

---

## 15. Risk Scoring for the MVP

Use a transparent demo score rather than a complex machine-learning model.

Example signals:

```text
+20  repeated burst requests
+20  multiple active sessions for one participant
+15  repeated refresh or reconnect attempts
+20  replayed token or challenge
+15  hidden honeypot interaction
+15  duplicate identity relationship
+10  repeated challenge failures
+10  suspicious state transition
```

Risk levels:

```text
0–29    LOW       Allow normal flow
30–59   MEDIUM    Slow down or request step-up verification
60+     HIGH      Strong challenge, cooldown, or restricted queue
```

Every friction or block should have a human-readable reason code, for example:

```text
RATE_BURST
REPLAY_ATTEMPT
DUPLICATE_ENTRY
MULTI_SESSION
CHALLENGE_FAILURE
EXPIRED_HOLD
```

Do not permanently classify a user as a bot based only on:

- One shared IP.
- One refresh.
- A slow network.
- An unusual browser.
- Assistive technology.
- Keyboard-only interaction.

---

## 16. Standby and Expiry Flow

When a winner does not redeem before the deadline:

1. Mark the entitlement expired.
2. Release or preserve the seat according to the published rule.
3. Promote the next standby participant.
4. Issue a new short-lived entitlement.
5. Write the promotion to the audit log.

Replacement must always use the fixed standby order. There must be no hidden manual selection.

---

## 17. Public Audit and Fairness Receipt

### Public audit page

Display aggregate, non-sensitive information:

- Campaign ID.
- Policy version.
- Registration cutoff.
- Registered count.
- Eligible count.
- Duplicate count.
- Roster commitment/hash.
- Randomness reference.
- Algorithm version.
- Winner count.
- Standby rule.
- Aggregate selection rates.
- Oversell count.
- Duplicate allocation count.

### Private Fairness Receipt

Each participant receives:

- Campaign ID.
- Policy version.
- Registration result.
- Eligibility result.
- Eligibility snapshot time.
- Roster commitment.
- Allocation method.
- Randomness reference.
- Winner or standby result.
- Redemption status.

A future enhancement can add Merkle inclusion proofs. For the first demo, a roster hash and private receipt are sufficient if the team cannot implement a full Merkle proof safely.

---

## 18. Dashboard Requirements

The organizer dashboard should display four groups.

### Participation

- Total registration attempts.
- Unique participants.
- Eligible participants.
- Duplicate attempts.
- Suspicious traffic.

### Allocation

- Winners.
- Standby count.
- Human-validation completions.
- Selection rate by simulated client type.
- Bot advantage ratio.
- Group selection rates.

### Inventory

- Available seats.
- Held seats.
- Confirmed seats.
- Expired holds.
- Oversell count.
- Duplicate allocation count.
- Hold expiry rate.

### Reliability and security

- Request rate.
- p95 latency.
- p99 latency.
- Error rate.
- Retry rate.
- Queue wait distribution.
- Challenge success rate.
- Challenge abandonment.
- Cooldown count.
- False-positive count.
- Recovery success rate.

The most important visual comparison is:

```text
Normal users       -> selection rate
Fast bots          -> selection rate
Burst bots         -> selection rate
Retry bots         -> selection rate
Account farms      -> selection rate
```

The expected result is that bot request volume does not create a proportional increase in selection probability.

---

## 19. Adversarial Simulation

Implement configurable simulated clients:

### Normal human

- One account.
- Low request rate.
- Follows the normal flow.
- May refresh once.
- May reconnect.

### Fast bot

- Sends requests immediately.
- Tries to win through speed.

### Burst bot

- Sends many requests in a short interval.

### Retry bot

- Repeats after failures and lost responses.

### Account farm

- Uses many accounts.
- Attempts duplicate registration.

### Direct API bot

- Skips the frontend and calls protected endpoints directly.

### Token replay attacker

- Reuses an admission permit, challenge, or entitlement.

### Race-condition attacker

- Sends parallel requests for the same seat.

### Legitimate shared-network user

- Shares an IP with many other participants.

### Slow or accessibility-focused user

- Has high latency.
- Uses keyboard-only interaction.
- Takes longer to finish a challenge.

Each profile should be configurable by:

- Request rate.
- Number of accounts.
- IP diversity.
- Timing jitter.
- Retry behavior.
- Challenge behavior.

---

## 20. Required Invariants

The test suite and demo must repeatedly verify:

```text
confirmed_seats <= campaign_capacity
```

```text
one seat cannot belong to two participants
```

```text
one participant cannot exceed the ticket limit
```

```text
one campaign + one verified participant = one registration
```

```text
expired holds do not remain permanently unavailable
```

```text
replayed tokens are rejected
```

```text
same idempotency key + same request = same result
```

```text
same idempotency key + different request = rejection
```

These are more important than adding one more visual game.

---

## 21. Hackathon MVP Priority Order

### Priority 0 — Must work

1. Campaign creation.
2. Registration window.
3. Verified account or clearly simulated verified identity.
4. One-entry-per-participant rule.
5. Frozen roster.
6. Uniform lottery.
7. Fixed standby order.
8. PostgreSQL inventory authority.
9. Atomic seat holds and confirmation.
10. Idempotency.
11. Replay protection.
12. Basic rate limits.
13. Human validation before final redemption.
14. Session and seat timers.
15. Adversarial simulator.
16. Fairness and reliability dashboard.

### Priority 1 — Strong differentiators

1. Cloudflare Turnstile.
2. Five MediaPipe mini-games.
3. Confusing-image challenge.
4. Risk-based friction.
5. Five-minute cooldown toast.
6. Signed admission permits.
7. Single-use signed entitlements.
8. Public audit page.
9. Fairness Receipt.
10. Human-readable reason codes.
11. Accessibility alternative.
12. Organizer kill switch.

### Priority 2 — Only if the core is already stable

1. Proof-of-work.
2. Honeypot.
3. Merkle inclusion proof.
4. WebAuthn/passkey final step.
5. Full attack replay lab.
6. Policy simulator.
7. Advanced device clustering.
8. Payment integration.
9. Multi-region deployment.

If time becomes short, remove features in Priority 2 first. Do not remove atomic inventory, lottery integrity, idempotency, or the main demo metrics.

---

## 22. One-Day Implementation Plan

The exact schedule depends on the team’s current codebase, but the work should follow this order.

### Phase 1 — Foundation

- Initialize frontend and backend.
- Create PostgreSQL schema.
- Create one 500-seat campaign.
- Implement campaign status and registration window.
- Implement participant/session creation.

### Phase 2 — Fair registration

- Implement one registration per participant per campaign.
- Add idempotency keys.
- Add basic email or mock OTP verification.
- Close registration and freeze the roster.
- Implement deterministic lottery and standby list.

### Phase 3 — Correct booking

- Create winner entitlements.
- Implement AVAILABLE → HELD → CONFIRMED.
- Add 90–120-second seat holds.
- Add 2-minute idle and 5-minute absolute booking timers.
- Add replay rejection.
- Test parallel seat requests.

### Phase 4 — Anti-abuse layer

- Add endpoint-specific rate limits.
- Add risk scores and reason codes.
- Add 5-minute cooldown behavior.
- Add Cloudflare Turnstile if credentials/configuration are ready.
- Add the first MediaPipe game.
- Add the remaining games only after the booking flow works.

### Phase 5 — Evidence

- Add normal and bot simulators.
- Run attack scenarios.
- Capture zero oversell and zero duplicate allocation.
- Add human versus bot selection-rate charts.
- Add latency charts.
- Add public audit page and Fairness Receipt.

### Phase 6 — Demo polish

- Add clear status messages.
- Add countdowns.
- Add the cooldown toast.
- Add a visible event policy.
- Add a one-click attack simulation control.
- Prepare the judge walkthrough.

---

## 23. Recommended Judge Demonstration

Use a 500-seat campaign and a simulated large population.

### Demo sequence

1. Organizer creates the campaign.
2. The UI shows the frozen rules: 500 seats, registration window, one entry, uniform lottery, standby policy.
3. Normal users and bots register.
4. Burst bots send thousands of duplicate requests.
5. The dashboard shows deduplication and rate limiting.
6. Suspicious clients receive Cloudflare or custom challenges.
7. Repeated abuse triggers the five-minute cooldown toast.
8. Registration closes.
9. The roster is frozen and its commitment is shown.
10. The lottery selects winners and creates standby order.
11. A winner receives a signed single-use entitlement.
12. Two parallel requests try to hold the same seat.
13. Only one request succeeds.
14. A replayed entitlement is rejected.
15. A lost response is retried with the same idempotency key.
16. The original result is returned without duplicate allocation.
17. A legitimate user refreshes or reconnects.
18. Their durable state is recovered.
19. An expired hold returns to inventory.
20. Dashboard shows zero overselling and zero duplicate allocations.
21. Fairness charts show that more bot requests did not create more lottery chances.

### Main judge message

> “We do not claim perfect bot detection. We remove the speed race, cap each participant at one eligible chance, require human validation before final redemption, protect inventory atomically, and produce measurable evidence that bots cannot dominate the allocation.”

---

## 24. What Not to Claim

Do not claim:

- “We identify every AI agent.”
- “Our MediaPipe game proves someone is human.”
- “Cloudflare guarantees no bot can pass.”
- “One IP equals one person.”
- “The queue position itself determines fairness.”
- “The frontend timer protects the booking.”
- “A successful challenge means the participant is unique.”
- “The system is secure because it has a CAPTCHA.”

Use accurate claims:

- “We reduce automated advantage.”
- “We combine identity limits, rate limits, admission control, challenges, replay protection, and atomic inventory.”
- “We measure false positives as well as blocked traffic.”
- “We keep fairness allocation separate from traffic admission.”
- “We prove that more requests do not create more lottery entries.”

---

## 25. Success Criteria

The hackathon MVP is successful if it can demonstrate all of the following:

1. A large simulated population can register without collapsing the core application.
2. Repeated requests do not create repeated entries.
3. The roster is frozen before the draw.
4. The lottery is reproducible and auditable.
5. Standby order is deterministic.
6. Human validation occurs before final redemption.
7. MediaPipe and visual challenges add friction to suspicious traffic.
8. Repeated abuse triggers a five-minute cooldown.
9. Session, absolute booking, and seat-hold timers work server-side.
10. A replayed token or entitlement is rejected.
11. Refresh and reconnect recover valid participant state.
12. Parallel seat requests cannot oversell inventory.
13. Confirmed seats never exceed capacity.
14. Bot request volume does not proportionally increase selection probability.
15. Legitimate shared-network and slow users are not automatically rejected.
16. The dashboard shows fairness, reliability, inventory, and false-positive evidence.

---

## 26. Final Product Identity

Fair Drop is not merely:

- A queue.
- A CAPTCHA.
- A MediaPipe game.
- A bot detector.
- A waitlist.
- A lottery.
- A ticket database.

It is a combined:

> **Fairness, allocation, inventory-integrity, abuse-resistance, session-reliability, and evidence layer for high-demand events.**

Its defining promise is:

> **Remove the race, make allocation verifiable, protect inventory atomically, add human-controlled friction where risk requires it, preserve legitimate access, and produce measurable evidence that the system remained fair and reliable under adversarial demand.**

---

## References

[1]: https://developers.cloudflare.com/turnstile/ "Cloudflare Turnstile Documentation"

[2]: https://developers.google.com/mediapipe/solutions/vision/hand_landmarker "Google MediaPipe Hand Landmarker Documentation"

[3]: https://www.w3.org/TR/webauthn-3/ "Web Authentication: An API for Accessing Public Key Credentials"

[4]: https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html "OWASP Session Management Cheat Sheet"

[5]: https://support.axs.com/hc/en-us/articles/200745935-What-s-a-Waiting-Room "AXS Waiting Room"

[6]: https://help.ticketmaster.com/hc/en-us/articles/9781366115985-What-is-the-queue-and-how-do-I-join "Ticketmaster Queue"

[7]: https://legal.ticketmaster.com/terms-of-use/ "Ticketmaster Terms of Use"

[8]: https://queue-it.com/how-does-queue-it-work/ "How Queue-it Works"

[9]: https://queue-it.com/developers/how-queue-it-works/ "Queue-it Developer Documentation"

[10]: https://queue-it.com/blog/online-fairness/ "Queue-it Online Fairness"

[11]: https://contents.irctc.co.in/en/term_src1.html "IRCTC Terms and Conditions"

[12]: https://indianrailways.gov.in/HindiMagazine/IRJuly2020.pdf "Indian Railways Material on Illegal Ticketing and Automated Booking"

[13]: https://support.bookmyshow.com/support/solutions/articles/4000230248-student-ga-booking-guidelines "BookMyShow Booking Guidelines"

[14]: https://help.ticketek.com.au/hc/en-us/articles/360001862168-On-Sale-Information "Ticketek On-Sale Information"

[15]: https://dicefm.zendesk.com/hc/en-gb/articles/4409669479953-Add-your-tickets-to-the-wait-list "DICE Waitlist"

[16]: https://www.seetickets.com/content/terms-and-conditions "See Tickets Terms and Conditions"
