# Fair Drop: Features and Improvements to Existing Systems

## 1. Product direction

Fair Drop should improve the existing high-demand ticketing and registration model by combining four capabilities in one system:

1. **Controlled admission** so the origin does not collapse during a flash crowd.
2. **Fair registration and allocation** so request speed and request volume do not decide who wins.
3. **Correct inventory management** so seats cannot be duplicated or oversold.
4. **Measurable evidence** so organizers can prove how the system behaved under normal and adversarial traffic.

Fair Drop should not attempt to replace every existing ticketing, waiting-room, or bot-protection product. A stronger position is to become the **fair allocation, inventory-integrity, and evidence layer** that works alongside them.

---

## 2. Core features for the MVP

### 2.1 Campaign and event configuration

Organizers should be able to create a drop with:

- Event name and description.
- Total capacity, such as 500 seats.
- Registration start and end times.
- Redemption deadline.
- Maximum tickets per participant.
- Eligibility rules.
- Allocation method.
- Standby and replacement rules.
- Cancellation and rerun rules.
- Published terms and privacy notice.

The configuration should be **versioned and frozen** before the draw. An organizer should not be able to secretly change the rules after seeing the results.

### 2.2 Registration instead of first-come-first-served purchasing

Participants should register during a defined time window instead of racing to purchase the moment the event opens.

The system should store one registration per participant per campaign. Repeated submissions should return the original result rather than creating additional entries.

This removes the advantage of:

- Faster internet connections.
- Faster scripts.
- Automated retries.
- Thousands of repeated requests.
- Direct API calls that bypass the user interface.

### 2.3 One-participant-one-entry enforcement

Fair Drop should support a configurable participant identity model:

- Account ID.
- Verified email or phone.
- Passkey-backed account.
- Organization-issued identity.
- Optional proof-of-personhood provider.
- A combination of several signals.

The system should clearly distinguish between:

- A participant controlling an account.
- A request appearing automated.
- A participant being verified as a unique real-world person.

These are different properties and should not be presented as equivalent.

### 2.4 Transparent lottery allocation

The MVP should use a uniform lottery:

- Freeze the eligible participant roster after registration closes.
- Remove duplicates.
- Publish a commitment to the final roster.
- Use a committed or independently observable randomness source.
- Run a reproducible shuffle.
- Select 500 winners.
- Produce a standby list in a fixed order.

Every eligible entry should have the same ex-ante probability unless the organizer explicitly chooses another policy.

### 2.5 Fairness Receipt

Each participant should receive a private **Fairness Receipt** containing:

- Campaign ID.
- Policy version.
- Registration result.
- Eligibility decision.
- Eligibility snapshot time.
- Roster commitment.
- Allocation method.
- Randomness reference.
- Winner or standby result.
- Redemption status.

The public audit page should reveal aggregate and verifiable information without exposing unnecessary personal data.

### 2.6 Standby and expired-seat handling

When a winner does not redeem before the deadline:

1. Mark the entitlement as expired.
2. Release the seat according to the published policy.
3. Promote the next standby participant.
4. Issue a new short-lived entitlement.
5. Record the promotion in the audit log.

The system must never select a replacement using an improvised manual process that is not recorded or explained.

### 2.7 Single-use digital entitlements

Winners should receive a signed entitlement containing:

- Campaign ID.
- Participant ID.
- Expiry time.
- Entitlement ID.
- Nonce.
- Allowed operation.

The backend must verify the entitlement. The browser must not be trusted to decide whether it is valid.

An entitlement should be:

- Short-lived.
- Bound to the campaign.
- Bound to the participant or account.
- Single-use.
- Rejected after expiry.
- Rejected if already redeemed.

### 2.8 Atomic seat reservation

Seat inventory should use explicit states:

```text
AVAILABLE -> HELD -> CONFIRMED
                 \
                  -> AVAILABLE after expiry
```

A database transaction should guarantee that two simultaneous requests cannot obtain the same seat.

The system should enforce:

- No more than 500 confirmed seats.
- No seat assigned to two participants.
- No participant receiving more than the configured limit.
- No expired hold remaining permanently unavailable.
- No duplicate reservation created by a retry.

### 2.9 Idempotent operations

Registration, redemption, and payment-related operations should accept an idempotency key.

If a participant submits a request and the response is lost, sending the same request again should return the original result rather than creating another registration, reservation, or payment.

If the same idempotency key is reused with different request data, the system should reject it.

### 2.10 Session recovery

Participants should be able to refresh or reconnect without losing their state.

The system should support:

- Durable participant status.
- Short-lived signed session tokens.
- Safe session renewal.
- Reconnection after temporary network failure.
- A clear “your request is still processing” state.
- Recovery from a lost response without duplicate allocation.

### 2.11 Organizer dashboard

The organizer dashboard should display:

- Total registered participants.
- Unique eligible participants.
- Duplicate attempts.
- Suspicious traffic.
- Queue depth.
- Current admission rate.
- Registration success rate.
- Winners and standby count.
- Available, held, expired, and confirmed seats.
- Redemption progress.
- p95 and p99 latency.
- Error and retry rates.
- Fairness metrics.
- Attack simulation results.

### 2.12 Adversarial simulation mode

The platform should include configurable simulated clients that run only against an isolated FairDrop deployment or an approved test environment:

- Normal human.
- Fast human.
- Burst bot.
- Retry bot.
- Account farm.
- Distributed bot.
- Direct API client.
- Headless-browser client in a controlled test environment.
- Token replay attacker.
- Race-condition attacker.
- Denial-of-inventory client.
- Legitimate shared-network user.
- Accessibility-focused user.
- Adaptive AI-policy client.

The simulator must not bypass third-party challenges, solve or defeat production CAPTCHA/Turnstile challenges, use real identities, access real payment or identity services, or send uncontrolled traffic to production. It should model adversarial behavior at the application-workflow level and measure whether automation gains a meaningful allocation advantage.

The dashboard should compare how each client type performs and whether bot request volume, speed, retries, coordination, or inventory hoarding changes its probability of allocation.

### 2.13 Safe AI-policy simulation

An optional AI policy engine may choose among a fixed allowlist of synthetic-client actions:

- `open_page`.
- `wait`.
- `submit_registration`.
- `refresh_status`.
- `retry_after_timeout`.
- `redeem_entitlement`.
- `abandon`.

The AI policy receives sanitized observations from the test deployment and returns schema-validated actions. It must not generate arbitrary URLs or requests, alter browser fingerprints, access credentials or raw tokens, call external verification/payment services, or change the test budget.

Every experiment must record:

- Scenario ID and version.
- Campaign configuration hash.
- Population composition.
- Fixed random seed.
- Request budget and concurrency cap.
- Verification-provider mode.
- Model name and policy version, if an AI policy is used.
- Sanitized observations and selected actions.
- Expected invariants and actual results.

A deterministic replay of the same seed and recorded observations should produce the same policy decisions, or clearly record why a model response differed.

### 2.14 Verification-provider simulation

Turnstile and other external verification services should not be used as high-volume load-test targets. FairDrop should support a local verification stub with explicit outcomes:

- `pass`.
- `expired`.
- `duplicate`.
- `invalid`.
- `wrong_action`.
- `wrong_hostname`.
- `service_error`.

A small number of browser smoke tests may verify the production integration contract using provider-approved test credentials. The simulator must never manufacture production-looking tokens or attempt to defeat a challenge.

### 2.15 Simulator safety contract

Every simulator run must enforce:

- Isolated staging, local, or provider-approved test deployment.
- Synthetic accounts, identities, network identifiers, and payment instruments only.
- An allowlisted endpoint set.
- A fixed maximum request count.
- A fixed concurrency cap.
- An operator-provided campaign and scenario ID.
- Automatic stop on error-rate, latency, or resource thresholds.
- No external email, SMS, payment, identity, or Cloudflare challenge calls.
- Complete audit logging and trace retention limits.
- A kill switch that stops workers without modifying confirmed inventory.

The simulator is a defensive validation system, not a bot-evasion system.

---

## 2.16 AI-simulation behavior model

The AI simulation should represent decisions, not anti-detection techniques. A synthetic client may observe a test response and choose whether to wait, retry, refresh, submit once, redeem, or abandon. It must not be trained or configured to imitate human fingerprints, defeat browser challenges, evade detection, or discover undocumented endpoints.

A client policy can be represented as:

```json
{
  "client_id": "bot-0042",
  "class": "distributed_retry_bot",
  "account_id": "synthetic-account-0042",
  "network_id": "test-network-7",
  "policy": {
    "max_registrations": 20,
    "retry_strategy": "exponential_backoff_with_jitter",
    "parallelism": 4,
    "abandon_probability": 0.15
  },
  "allowed_actions": [
    "open_page",
    "submit_registration",
    "refresh_status",
    "retry_after_timeout",
    "redeem_entitlement",
    "abandon"
  ]
}
```

The AI receives only observations such as:

```json
{
  "registration_open": true,
  "server_response": "accepted",
  "retry_after_seconds": 2,
  "application_status": "registered",
  "verification_stub_result": "pass"
}
```

Its response must pass a strict action schema. Unknown actions, arbitrary request bodies, external URLs, or attempts to access secrets are rejected by the simulator.

### 2.17 Scenario catalogue

The MVP simulator should implement at least these scenarios:

#### Normal human baseline

A participant opens the page, spends realistic time reading instructions, submits once, occasionally refreshes, and may reconnect after a temporary network failure. Include mobile, desktop, slow-network, keyboard-only, screen-reader, and shared-network profiles.

#### Fast but legitimate human

A participant registers quickly but follows the published workflow and submits only once. Speed must not create a false positive or a special lottery advantage.

#### Burst bot

A single account and session submit many registration attempts in a short period. The expected result is one idempotent registration and logged duplicate attempts.

#### Retry bot

The server commits a registration but the response is artificially lost. The client retries with the same idempotency key. The original result must be returned, and reusing the key with changed request data must be rejected.

#### Account farm

Many synthetic accounts attempt to join the same campaign. Test account age, session continuity, identity uniqueness, and network relationships without using real personal data.

#### Distributed bot

Synthetic accounts are spread across controlled test network identifiers. This tests whether account, session, campaign, operation, and entitlement controls still work when IP-only controls are insufficient.

#### Direct API client

The client calls only documented test endpoints but omits UI steps. Authorization, CSRF protection, eligibility, admission, verification, idempotency, and entitlement checks must still be enforced by the backend.

#### Replay client

The client reuses an expired or consumed challenge, admission permit, queue token, idempotency key, or entitlement. Every single-use object must be rejected without changing inventory.

#### Parallel redemption client

Many workers redeem the same entitlement or compete for the final seats. The system must not oversell, duplicate a seat, or allow a participant to exceed the configured limit.

#### Denial-of-inventory client

The client obtains temporary holds and abandons them. Holds must expire, seats must return to `AVAILABLE`, and standby promotion must follow the published policy.

#### Shared-network legitimate users

Many independent synthetic users share one network identifier. They must not all be blocked by one IP-based counter.

#### Accessibility-focused user

The client uses keyboard-only navigation, slower completion, assistive-technology-compatible controls, and an accessible alternative where an additional verification step is required.

### 2.18 Fairness and invariant acceptance criteria

For a uniform lottery with `N` eligible entries and `K` seats:

```text
selection probability = K / N
```

For 50,000 eligible entries and 500 seats, the expected probability is 1% per eligible entry. A client that sends 100 requests must not receive 100 entries.

Every run must verify:

- Confirmed seats never exceed campaign capacity.
- No seat ID is confirmed for two participants.
- No participant exceeds the ticket limit.
- No participant receives more than one eligible entry unless the published policy explicitly allows it.
- No single-use challenge, permit, queue token, idempotency key, or entitlement succeeds twice.
- Expired holds return inventory to `AVAILABLE`.
- Lost responses and retries do not create duplicate state.
- Bot request volume does not increase selection probability after deduplication.
- Legitimate shared-network and accessibility profiles retain a measurable path to completion.

The dashboard should report:

```text
bot_advantage_ratio = bot_selection_rate / baseline_legitimate_selection_rate
false_positive_rate = legitimate_denied_or_stepup / legitimate_population
inventory_integrity = confirmed_seats <= capacity and no duplicate seat IDs
```

Lottery variance is expected. Run many independent seeded draws and report confidence intervals rather than treating one draw as proof of fairness.

---

## 3. Bot and abuse-resistance features

### 3.1 Virtual waiting room or admission gate

When traffic exceeds safe capacity, participants should wait outside the core application. The system should admit users at a controlled rate based on measured backend capacity.

The admission gate should:

- Protect the database.
- Limit active checkout or registration sessions.
- Issue short-lived signed admission permits.
- Reject expired or replayed permits.
- Recover a participant's place after refresh.
- Provide clear wait-state messaging.

The waiting room should protect capacity but should not silently determine the lottery winners.

### 3.2 Endpoint-specific rate limiting

Different operations require different limits:

- Login challenge generation.
- Registration.
- Verification.
- Entitlement redemption.
- Payment authorization.
- Email or SMS requests.

A participant who sends too many registration requests should be slowed or blocked for that operation without automatically blocking every user from the same IP address.

### 3.3 Risk-based friction

Fair Drop should use several signals to produce a risk level:

- Request bursts.
- Repeated failures.
- Challenge reuse.
- Entitlement reuse.
- Suspicious state transitions.
- Many accounts from one session pattern.
- One account across many networks.
- Account age.
- Sudden recovery or credential changes.
- Browser/session continuity.
- Network reputation.

Possible responses:

```text
Low risk       -> allow
Medium risk    -> slow down or request step-up verification
High risk      -> hold for review or require stronger verification
Confirmed abuse -> block the specific operation
```

The system should record a human-readable reason code for each step-up or block.

### 3.4 Replay protection

The system should reject:

- Reused login challenges.
- Challenges used in a different session.
- Expired admission permits.
- Reused queue tokens.
- Reused entitlements.
- Reused idempotency keys with changed request bodies.
- Duplicate payment webhooks.

### 3.5 Adaptive verification

Use stronger verification only when the risk or action justifies it:

- Silent browser challenge for suspicious sessions.
- Email or phone verification for selected flows.
- Passkey/WebAuthn step-up for valuable redemptions or account recovery.
- Human review for ambiguous high-impact cases.

Challenges should be validated server-side and should have an accessible alternative.

### 3.6 Human review and appeal

A small reviewer queue can handle cases that automated controls cannot confidently classify.

Reviewers should see:

- Reason codes.
- Minimal account and event context.
- Duplicate or replay evidence.
- Relevant request history.
- Current entitlement state.

Review outcomes should be:

- Approve.
- Deny with a reason.
- Request an accessible alternative.
- Escalate for a second review.

Human review should be an exception path, not a requirement for every participant.

---

## 4. New features that can differentiate Fair Drop

### 4.1 Public Allocation Audit

After the draw, publish:

- Policy version.
- Registration cutoff.
- Number of registered participants.
- Number of eligible participants.
- Duplicate count.
- Roster commitment.
- Randomness source and reference.
- Allocation algorithm version.
- Number of winners.
- Standby rules.
- Aggregate selection rates.

This lets an independent person verify that the result was generated according to the published process.

### 4.2 Privacy-preserving participant proofs

Instead of exposing the entire participant list, give participants private proofs that their registration was included in the frozen roster.

For example, Fair Drop could later support Merkle inclusion proofs:

- The organizer publishes a Merkle root.
- The participant receives a private proof path.
- The participant can verify that their pseudonymous ID was included.
- The public does not need to see every identity.

### 4.3 Policy Simulator

Before launching, organizers can compare:

- Equal lottery.
- Weighted lottery.
- Reserved-seat lottery.
- Different capacities.
- Different eligibility rules.
- Different standby policies.

The simulator should display expected:

- Selection probabilities.
- Group selection rates.
- Rate gaps.
- Unfilled-seat risk.
- Sensitivity to duplicate participation.

### 4.4 Fairness stress testing

The organizer should be able to run the same policy over many simulated draws and see:

- How much selection rates vary by chance.
- Whether small groups receive unstable results.
- Whether weighted rules produce extreme advantages.
- Whether a bot attack changes the eligible pool.
- Whether standby promotion creates measurable bias.

### 4.5 Attack replay lab

Provide a built-in test environment where the organizer can replay:

- Request flooding.
- Login replay.
- Queue-token replay.
- Duplicate registration.
- Parallel redemption.
- Lost response and retry.
- Distributed account farming.
- Database slowdown.
- Redis outage.

The result should show whether the system preserves its invariants.

### 4.6 Legitimacy and accessibility dashboard

Measure not only how many bots were blocked, but also:

- Challenge abandonment.
- False-positive rate.
- Completion rate for slow users.
- Completion rate for shared networks.
- Keyboard-only completion.
- Screen-reader compatibility.
- Recovery success.
- Manual-review turnaround time.

This prevents the system from appearing successful only because it blocked difficult-to-classify legitimate users.

### 4.7 Graceful degradation mode

If a bot provider, Redis, payment service, or analytics system becomes unavailable, Fair Drop should continue safely where possible.

Examples:

- Pause new redemptions but preserve existing holds.
- Serve a read-only event status page.
- Keep PostgreSQL inventory correctness even if Redis is unavailable.
- Queue notifications for later delivery.
- Return a clear retry state instead of creating an uncertain reservation.

### 4.8 Organizer kill switch

Provide a controlled emergency switch to:

- Pause registration.
- Pause redemption.
- Stop new admissions.
- Preserve existing confirmed seats.
- Display a public incident message.
- Resume only after an operator records the reason.

Every use of the kill switch should appear in the audit log.

---

## 5. Improvements to current ticketing and registration systems

### 5.1 Improvement over first-come-first-served sales

**Current weakness:** The fastest request often wins, which favors bots and high-speed networks.

**Fair Drop improvement:** Use a registration window followed by a lottery or randomized allocation. Speed becomes irrelevant after a valid registration is recorded.

### 5.2 Improvement over ordinary waiting rooms

**Current weakness:** A waiting room controls traffic but may still leave users uncertain about how they were selected. Queue position can also become the hidden allocation mechanism.

**Fair Drop improvement:** Keep admission and allocation separate. The waiting room protects the origin; the allocation service freezes the roster and applies a published rule.

### 5.3 Improvement over opaque lotteries

**Current weakness:** Many users cannot verify who was eligible, what rule was used, or whether the organizer reran the process.

**Fair Drop improvement:** Publish a policy hash, roster commitment, randomness reference, algorithm version, winner count, standby policy, and audit receipt.

### 5.4 Improvement over basic waitlists

**Current weakness:** A waitlist often stores names and emails but does not explain ranking, does not provide measurable fairness, and may rely on manual ticket release.

**Fair Drop improvement:** Use a fixed standby order, explicit expiry rules, automated promotion, and a full event log for each promotion.

### 5.5 Improvement over CAPTCHA-only defenses

**Current weakness:** CAPTCHAs can be automated, outsourced, inaccessible, or frustrating. They do not prevent duplicate accounts or overselling.

**Fair Drop improvement:** Use CAPTCHA or browser challenges only as one risk signal. Combine them with identity limits, rate limits, admission control, replay protection, idempotency, and database inventory constraints.

### 5.6 Improvement over IP-only rate limiting

**Current weakness:** One IP may represent many legitimate users, while a botnet can distribute requests across thousands of IPs.

**Fair Drop improvement:** Apply limits across multiple justified dimensions:

- Account.
- Session.
- Campaign.
- Operation.
- IP or network.
- Verification state.
- Entitlement.

Use proportional friction rather than automatically banning every shared network.

### 5.7 Improvement over client-side queue security

**Current weakness:** A queue position stored only in the browser can be modified, copied, or replayed.

**Fair Drop improvement:** Issue signed, short-lived admission permits and verify them on every protected backend operation. Never treat a browser-visible queue number as authorization.

### 5.8 Improvement over non-atomic inventory systems

**Current weakness:** A system may check whether a seat is free and then update it later. Two simultaneous requests can both pass the check.

**Fair Drop improvement:** Use conditional database updates, row locks, unique constraints, short transactions, and explicit inventory states.

### 5.9 Improvement over fragile retry behavior

**Current weakness:** A timeout causes users or bots to retry, potentially creating duplicate registrations, reservations, or payments.

**Fair Drop improvement:** Use idempotency keys, saved responses, request hashes, durable state, and reconciliation for ambiguous external results.

### 5.10 Improvement over opaque bot blocking

**Current weakness:** Users are often told only that they were blocked, with no recovery or appeal path.

**Fair Drop improvement:** Use reason codes, temporary holds, accessible step-up options, human review, and appeals for consequential cases.

### 5.11 Improvement over limited success metrics

**Current weakness:** Existing systems often report traffic and sales but not whether bots gained a disproportionate advantage or whether legitimate users were falsely blocked.

**Fair Drop improvement:** Report both system and fairness metrics:

- Selection rate by client type.
- Duplicate attempts.
- Bot advantage ratio.
- Legitimate completion rate.
- False-positive rate.
- p95/p99 latency.
- Queue wait distribution.
- Oversell count.
- Duplicate allocation count.
- Hold expiry rate.
- Recovery success rate.

---

## 6. Suggested feature priority

### Priority 0: must have

- Registration window.
- One-entry-per-participant rule.
- Frozen roster.
- Uniform lottery.
- Standby order.
- PostgreSQL inventory authority.
- Atomic seat holds.
- Idempotency.
- Replay protection.
- Basic rate limiting.
- Adversarial simulator.
- Fairness and reliability dashboard.

### Priority 1: strong differentiators

- Fairness Receipt.
- Public allocation audit.
- Signed admission permits.
- Risk-based friction.
- Human review queue.
- Appeal flow.
- Policy simulator.
- Accessibility metrics.
- Attack replay lab.

### Priority 2: stretch features

- Merkle inclusion proofs.
- Public randomness beacon integration.
- WebAuthn/passkey step-up.
- Weighted or reserved allocation policies.
- Privacy-preserving reusable challenge tokens.
- Ticketing-provider integration.
- Payment-provider integration with reconciliation.
- Multi-region failover.
- Advanced anomaly detection.

---

## 7. Features that bots cannot reliably clear without human involvement

No feature can guarantee that a determined attacker will never succeed. However, the following can make automation more difficult when used carefully:

1. **Risk-tiered human review** for ambiguous, high-value cases.
2. **Passkey confirmation** for final redemption or account recovery.
3. **A user-controlled intent confirmation** showing the exact event and entitlement.
4. **Accessible step-up verification** when behavior is suspicious.
5. **Appeal and recovery workflow** that requires context a generic bot may not possess.
6. **Short-lived stateful interactions** that bind the action to a session, account, and entitlement.

Do not rely on visual puzzles, mouse movement, audio CAPTCHAs, trivia questions, or “AI-generated human questions” as your primary security boundary. These can be automated or outsourced and may exclude legitimate users.

The best design is not “bots can never pass.” The best design is:

> A bot cannot gain a meaningful advantage merely by being faster, sending more requests, or retrying more aggressively.

---

## 8. Recommended final feature set for the hackathon demo

If time is limited, demonstrate these features in order:

1. Organizer creates a 500-seat event.
2. Participants register during a fixed window.
3. Repeated bot registrations are deduplicated.
4. The final roster is frozen and committed.
5. The lottery selects 500 winners and a standby list.
6. Winners receive single-use entitlements.
7. Parallel redemption attempts cannot oversell inventory.
8. Replayed challenges and entitlements are rejected.
9. Load testing shows stable latency and controlled admission.
10. The dashboard shows zero duplicate allocations and zero overselling.
11. Fairness metrics show that bot request volume did not improve selection probability.
12. The audit receipt explains how the result was produced.

This combination gives Fair Drop a clear and defensible identity: **not merely a queue, not merely a CAPTCHA, and not merely a ticket database, but a measurable fairness and integrity layer for high-demand allocation.**

## References

[1]: https://queue-it.com/developers/how-queue-it-works/ "Queue-it: How the virtual waiting room works"
[2]: https://developers.cloudflare.com/waiting-room/ "Cloudflare Waiting Room documentation"
[3]: https://help.ticketmaster.com/hc/en-us/articles/9781366115985-What-is-the-queue-and-how-do-I-join "Ticketmaster: What is the queue?"
[4]: https://www.eventbrite.com/help/en-us/articles/811539/how-to-set-up-an-event-waitlist/ "Eventbrite: Set up an event waitlist"
[5]: https://developers.cloudflare.com/turnstile/get-started/server-side-validation/ "Cloudflare Turnstile: Server-side validation"
[6]: https://owasp.org/www-project-automated-threats-to-web-applications/assets/oats/EN/OAT-005_Scalping "OWASP: Scalping"
[7]: https://www.postgresql.org/docs/current/explicit-locking.html "PostgreSQL: Explicit locking"
[8]: https://docs.stripe.com/api/idempotent_requests "Stripe: Idempotent requests"
[9]: https://rfc-editor.org/rfc/rfc9381.html "RFC 9381: Verifiable Random Functions"
[10]: https://drand.love/about/ "drand: Distributed randomness beacon"
[11]: https://fairlearn.org/main/user_guide/assessment/common_fairness_metrics.html "Fairlearn: Common fairness metrics"
[12]: https://grafana.com/docs/k6/latest/ "Grafana k6 documentation"
[13]: https://docs.locust.io/en/stable/ "Locust documentation"
[14]: https://www.w3.org/TR/webauthn-3/ "W3C WebAuthn Level 3"
[15]: https://www.w3.org/WAI/WCAG22/Understanding/accessible-authentication-minimum.html "W3C WAI: Accessible Authentication"
[16]: https://developers.cloudflare.com/waf/rate-limiting-rules/ "Cloudflare WAF: Rate limiting rules"
[17]: https://developers.cloudflare.com/bots/concepts/bot-score/ "Cloudflare Bot Management: Bot scores"
[18]: https://owasp.org/www-project-automated-threats-to-web-applications/assets/oats/EN/OAT-021_Denial_of_Inventory "OWASP: Denial of Inventory"
