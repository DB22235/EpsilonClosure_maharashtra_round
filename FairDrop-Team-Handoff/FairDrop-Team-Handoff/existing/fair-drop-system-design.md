# Fair Drop Backend System Design

## Scope and design position

This document separates the system into two parts:

1. **Default production website foundations** — capabilities that any serious live website should have, regardless of the Fair Drop problem.
2. **Fair Drop-specific capabilities** — features required because the website must handle extreme demand, abusive automation, limited inventory, and measurable fairness.

The most important architectural principle is:

> Do not mix ordinary website concerns with seat-allocation concerns. The normal web platform should be reliable and secure on its own. Fair Drop should then add a controlled allocation subsystem with stronger concurrency and audit guarantees.

For a hackathon, the architecture can be implemented as a modular monolith. For a large production platform, the same modules can later be separated into services. Starting with many independent microservices would add operational complexity before the core correctness is proven.

---

# Part 1 — Default foundations required by any live website

These are not optional “nice-to-have” components. They are the baseline capabilities expected in a real production website.

## 1. Client and delivery layer

### Web or mobile client

The frontend is responsible for:

- Rendering pages and user interfaces.
- Collecting user input.
- Displaying loading, success, and error states.
- Maintaining a local view of server state.
- Retrying safe read operations when appropriate.
- Avoiding duplicate submissions from accidental double-clicks.

The frontend must not be trusted for security, permissions, inventory, pricing, or final business decisions. It is a user interface, not the source of truth.

### CDN and static asset delivery

Static assets such as JavaScript, CSS, images, fonts, and public event information should be delivered through a CDN.

The CDN provides:

- Lower latency for users in different regions.
- Reduced load on the application servers.
- Caching of immutable assets.
- Better resilience during traffic spikes.

Use content-hashed asset names so a new deployment does not accidentally serve stale JavaScript or CSS.

### Load balancer or edge gateway

The load balancer receives incoming traffic and distributes it across healthy application instances.

It should support:

- TLS termination or secure TLS pass-through.
- Health checks.
- Connection limits.
- Request-size limits.
- Routing to the correct application version.
- Graceful removal of unhealthy instances.

The load balancer is not a fairness mechanism. It only distributes traffic and protects the application tier.

### Web application firewall

A WAF can block common malicious traffic such as:

- Known exploit patterns.
- Malformed requests.
- Excessively large payloads.
- Suspicious protocol behavior.
- Common injection attempts.

A WAF is useful, but it does not replace application-level authorization, validation, identity controls, or abuse detection.

---

## 2. Application/API layer

### API gateway or backend entry point

All client requests should enter through a controlled API boundary.

The API boundary should handle:

- Authentication extraction.
- Request correlation IDs.
- Schema validation.
- API versioning.
- Rate limiting.
- Request timeouts.
- Standard error formatting.
- Access logging.
- Routing to the correct application module.

A consistent error shape is important. For example:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The submitted event ID is invalid",
    "requestId": "req_123"
  }
}
```

Do not expose stack traces, SQL errors, internal hostnames, secrets, or sensitive debugging information to users.

### Stateless application servers

Application instances should preferably be stateless. Any instance should be able to process a request.

Avoid storing important session state only in process memory because:

- The request may reach another instance.
- The instance may restart.
- Horizontal scaling becomes difficult.
- Deployments can lose the state.

Durable state belongs in the database or a deliberate external state store.

### Modular backend structure

Even if the system is one deployable application, separate the code into modules such as:

- Identity and authentication.
- User profile.
- Event/catalog management.
- Orders or registrations.
- Payments, if applicable.
- Notifications.
- Administration.
- Audit logging.
- Fair Drop allocation.

This gives most of the benefits of service separation without immediately accepting the operational cost of microservices.

### Input validation

Validate every request on the server:

- Required fields.
- Data types.
- String lengths.
- Allowed enum values.
- Date and time formats.
- Numeric ranges.
- Ownership of referenced resources.
- Business rules.

Client-side validation improves user experience but cannot be used as the security boundary.

### Authorization

Authentication answers:

> Who is this user?

Authorization answers:

> Is this user allowed to perform this action on this resource?

Every protected endpoint should perform authorization checks. Do not assume that because a user can see a button, they are allowed to call the endpoint.

Use explicit roles and permissions, for example:

- `user`.
- `event_operator`.
- `support_agent`.
- `administrator`.

Never rely on a user-supplied role field.

---

## 3. Identity, authentication, and sessions

### Account lifecycle

The system should support:

- Registration.
- Email verification.
- Password reset.
- Account recovery.
- Account deactivation.
- Session revocation.
- Login notifications for suspicious activity.

For a hackathon prototype, email/password plus a simulated verification step may be sufficient. For a serious ticketing platform, passkeys, verified contact details, and stronger account controls are preferable.

### Password and credential security

If passwords are supported:

- Never store plaintext passwords.
- Use a modern password-hashing algorithm such as Argon2id or bcrypt with appropriate parameters.
- Apply login throttling.
- Avoid revealing whether an email address exists.
- Support secure reset tokens with expiration and one-time use.

### Session management

Use secure, expiring sessions or short-lived access tokens with controlled refresh tokens.

For browser sessions, secure cookies should normally include:

- `HttpOnly`.
- `Secure`.
- Appropriate `SameSite` policy.
- Short or controlled lifetime.

The backend should support logout and session revocation. A logout button that only clears frontend state is not sufficient.

### CSRF and XSS protection

For cookie-authenticated browser applications:

- Use CSRF protection on state-changing requests.
- Escape or sanitize user-generated content.
- Apply a strong Content Security Policy where possible.
- Avoid inserting untrusted HTML.
- Set security headers.

These controls belong in the default platform even though they are not specific to Fair Drop.

---

## 4. Primary database and data integrity

### Durable transactional database

Use a relational database such as PostgreSQL as the durable source of truth for core business data.

It should store:

- Users and identities.
- Events.
- Registrations or orders.
- Inventory ownership.
- Claims or reservations.
- Administrative actions.
- Audit records.

A relational database is particularly valuable where correctness depends on constraints, transactions, relationships, and consistent updates.

### Schema migrations

Database changes must be versioned through migrations.

Every deployment should know:

- Which schema version is active.
- Which migrations have run.
- Whether migrations are backward-compatible during rolling deployment.

Never make undocumented manual database changes in production.

### Constraints

Use database constraints for rules that must never be violated:

- Primary keys.
- Foreign keys.
- Unique constraints.
- Non-null constraints.
- Check constraints.
- Appropriate indexes.

Application code should validate early, but the database must still protect the final state.

### Transactions

Use transactions when multiple changes must succeed or fail together.

Examples:

- Creating an order and its line items.
- Recording a payment result and updating order status.
- Writing an idempotency record and its business result.
- Allocating inventory and creating ownership.

Do not use long transactions around slow external network calls. Persist an intermediate state, call the external system, then transition state safely.

### Backups and recovery

A live website needs:

- Automated backups.
- Point-in-time recovery where appropriate.
- Backup encryption.
- Restore testing.
- Defined recovery point objective, or RPO.
- Defined recovery time objective, or RTO.

A backup that has never been restored is not proven reliable.

---

## 5. Caching and fast ephemeral state

### Redis or equivalent cache

A cache can reduce database load for data that is safe to recompute or expire.

Good cache candidates include:

- Public event details.
- Session metadata.
- Short-lived rate-limit counters.
- Temporary idempotency lookup data.
- Distributed locks, only with careful design.
- Queue or admission metadata.

The cache should not silently become the only durable source of truth for critical ownership or payment records.

### Cache invalidation

Define how cached data is invalidated when the underlying data changes.

For inventory or seat availability, stale cache data may mislead the user. The final write decision must use authoritative state.

### Failure behavior

The system must define what happens if the cache is unavailable:

- Can read traffic fall back to the database?
- Should non-critical features degrade?
- Should critical writes fail safely?
- How is stale state prevented?

A cache outage should not corrupt ownership or financial state.

---

## 6. Background jobs and asynchronous work

Long-running or retryable work should not block the request thread.

Typical background jobs include:

- Sending email or SMS.
- Generating reports.
- Processing webhooks.
- Cleaning expired sessions.
- Rebuilding search indexes.
- Reconciliation.
- Fraud review.
- Exporting audit data.

Use a durable job queue where losing a job would be harmful. Jobs should be:

- Retryable.
- Idempotent.
- Observable.
- Dead-lettered after repeated failure.
- Safe to run more than once if a retry occurs.

Do not assume a job executes exactly once. Production systems generally need at-least-once processing with idempotent handlers.

---

## 7. External integrations

A live website may integrate with:

- Email providers.
- SMS or OTP providers.
- Payment gateways.
- Analytics providers.
- Search services.
- Object storage.
- Identity providers.

External calls must have:

- Timeouts.
- Retries only for safe or explicitly idempotent operations.
- Circuit breakers or failure thresholds.
- Response validation.
- Webhook signature verification.
- Reconciliation for delayed or missing callbacks.

Never assume a successful HTTP response alone means the external business action completed correctly.

---

## 8. File and media storage

User-uploaded files should usually go to object storage rather than the application server’s local disk.

The system should define:

- File-size limits.
- Allowed content types.
- Malware scanning where appropriate.
- Private versus public access.
- Signed download URLs.
- Retention and deletion rules.
- Metadata validation.

Local disk on an application instance is usually ephemeral and should not be the only copy of important files.

---

## 9. Observability and operations

### Structured logging

Logs should be machine-readable and include:

- Timestamp.
- Severity.
- Service or module.
- Request ID.
- User ID or anonymized subject where appropriate.
- Event ID or order ID.
- Error code.
- Duration.

Do not log passwords, full payment-card data, tokens, or unnecessary personal information.

### Metrics

At minimum, measure:

- Request rate.
- Error rate.
- Latency percentiles such as P50, P95, and P99.
- Database latency.
- Cache latency.
- Queue depth.
- Job failure count.
- Active sessions.
- Resource utilization.

Average latency is not enough. A platform can have an acceptable average while a large group experiences severe delays.

### Tracing

Distributed tracing or at least request correlation is useful for finding where time is spent across:

```text
Client → gateway → API → cache/database → worker → external provider
```

### Alerting

Alerts should be tied to user impact and operational risk, not every harmless log warning.

Examples:

- Sustained high error rate.
- Database connection exhaustion.
- Queue backlog growing beyond safe limits.
- Payment webhook failure.
- Inventory reconciliation mismatch.
- Unusual authentication failure spike.
- Application instances failing health checks.

### Health checks

Use separate checks for:

- Liveness: is the process alive?
- Readiness: can it safely receive traffic?
- Dependency health: are required dependencies available?

A process may be alive but not ready to serve requests.

---

## 10. Security and privacy baseline

Every live website should include:

- TLS everywhere.
- Secret management outside source code.
- Least-privilege service accounts.
- Dependency and container scanning.
- Secure headers.
- Rate limiting.
- Input validation.
- Authorization checks.
- Audit logging for sensitive actions.
- Data minimization.
- Encryption at rest where appropriate.
- Retention and deletion policies.
- Incident response procedures.

Do not collect identity data merely because it may be useful later. Collect only what the product needs and explain why it is collected.

---

## 11. Deployment and release management

A production website needs:

- Separate development, staging, and production environments.
- Reproducible builds.
- Automated tests in CI.
- Infrastructure configuration under version control.
- Secret injection at deployment time.
- Database migration controls.
- Rollback or roll-forward procedures.
- Feature flags for risky changes.
- Blue-green or rolling deployment where appropriate.

A deployment is not complete merely because the code compiled. It must be observable and reversible.

---

## 12. Testing baseline

### Unit tests

Test business rules in isolation.

### Integration tests

Test the application against real or realistic databases, caches, queues, and external-provider mocks.

### Contract tests

Ensure clients and services agree on API shapes.

### End-to-end tests

Test critical user journeys from browser to backend.

### Load tests

Measure behavior under expected load, not only maximum theoretical load.

### Failure tests

Test:

- Database timeout.
- Cache outage.
- Queue delay.
- External provider failure.
- Process restart.
- Duplicate request.
- Network timeout after a successful server write.

### Security tests

Include authorization bypass attempts, injection attempts, session issues, abuse cases, and dependency vulnerabilities.

---

# Part 2 — Fair Drop-specific extensions

The following capabilities are added because the platform must allocate scarce seats under extreme and adversarial demand.

## 1. Event lifecycle and state machine

The event must have explicit states rather than loosely related boolean fields.

```text
DRAFT
  ↓
PREPARING
  ↓
OPEN
  ↓
CLOSED
  ↓
FROZEN
  ↓
DRAWING
  ↓
CLAIMING
  ↓
COMPLETED
```

The backend must reject operations that do not belong to the current event state.

For example:

- Registration is allowed only during `OPEN`.
- The participant list cannot change during `FROZEN`.
- The draw cannot start before `CLOSED`.
- A claim cannot be created before `CLAIMING`.

This state machine is one of the most important differences from a normal website.

---

## 2. Separate traffic protection from allocation fairness

These are different responsibilities.

### Traffic protection asks:

> Can this request safely enter the system without overwhelming it?

It may use:

- Global concurrency limits.
- Per-IP and per-account limits.
- Signed admission tokens.
- Backpressure.
- Bot challenges.
- WAF rules.
- Queueing.

### Allocation fairness asks:

> Among valid participants, who receives one of the limited seats?

It must not blindly use raw request speed or raw request count as the allocation rule.

This separation should appear explicitly in the system design diagram and in the explanation to judges.

---

## 3. Identity and eligibility record

The system needs an event-specific participant identity model.

A generic user account is not automatically enough because one person may create many accounts or multiple clients may share one IP address.

The eligibility record should track:

- Event ID.
- User or account ID.
- Verification level.
- Session or device signals.
- Risk assessment result.
- Eligibility state.
- Entry creation time.
- Audit reference.

Be careful not to claim perfect human detection. The stronger property is that repeated traffic does not automatically create repeated allocation opportunities.

---

## 4. Registration or entry subsystem

The entry subsystem should receive a user’s participation request and create at most one valid entry for that event and eligibility identity.

Important properties:

- Entry creation is server-side.
- Duplicate entry requests are idempotent.
- The database enforces uniqueness.
- A timeout after a successful write does not create another entry.
- The response includes a durable entry ID.
- The user can retrieve the current entry state after refresh or reconnect.

Conceptual uniqueness rule:

```text
UNIQUE(event_id, eligible_identity_id)
```

Do not use the number of HTTP requests as the number of lottery opportunities.

---

## 5. Idempotency subsystem

Every state-changing entry or claim request should accept an idempotency key.

The system should store:

- Idempotency key.
- User or identity scope.
- Event scope.
- Request fingerprint.
- Result status.
- Response body or response reference.
- Expiration time.

If the same key is submitted again, return the original result.

If the same key is reused with a materially different payload, reject it rather than silently treating it as a new request.

Idempotency is required for:

- Entry submission.
- Claim submission.
- Ticket issuance.
- Payment initiation, if payment is later added.

---

## 6. Participant-list freeze

At the end of registration, the system must stop the list from changing before drawing winners.

The freeze process should:

1. Transition the event from `OPEN` to `CLOSED`.
2. Complete or reject in-flight entries according to a defined policy.
3. Select the final valid entry set.
4. Store a canonical ordering.
5. Calculate an entry-list hash.
6. Transition to `FROZEN`.

The canonical list must be reproducible. If the list can change silently during or after the draw, the fairness claim is weak.

---

## 7. Auditable draw subsystem

The draw subsystem should record:

- Event ID.
- Number of available seats.
- Number of valid entries.
- Canonical entry-list hash.
- Randomness commitment, if used.
- Draw execution time.
- Algorithm version.
- Winner and reserve ordering.
- Operator or job identity.
- Result hash.

A useful audit design uses a committed random seed before the final participant list is known, then reveals it after the list is frozen. The final result can then be replayed from the seed, event ID, and entry-list hash.

The key point is not merely “we used random.” The key point is that the draw can be independently reproduced and checked.

---

## 8. Winner, reserve, and claim subsystem

Do not treat selection as the same thing as final ticket issuance.

A selected user may:

- Fail to claim.
- Lose eligibility during verification.
- Abandon the claim.
- Encounter a payment failure.
- Let the claim expire.

Use explicit states:

```text
SELECTED
  ↓
CLAIM_PENDING
  ├── RESERVED
  │     ↓
  │   ISSUED
  └── EXPIRED
```

Reserve participants should have an explicit rank and promotion policy.

The promotion rule must be deterministic and auditable. For example, the next reserve can be promoted only after a winner’s claim expires or is definitively rejected.

---

## 9. Inventory and allocation integrity

Inventory must be updated atomically with ticket ownership or reservation creation.

The system must guarantee:

- Inventory never becomes negative.
- A ticket cannot have two owners.
- A user cannot receive two valid allocations unless the product explicitly allows it.
- A retry does not consume another seat.
- Expired holds return to the correct state.
- The result remains correct after concurrent requests.

The authoritative inventory update must be transactional. Redis counters can help absorb load, but they should not be the only durable record of ownership unless the design includes rigorous durability and reconciliation.

---

## 10. Abuse and adversarial-traffic subsystem

The system should classify traffic behavior without assuming that one signal proves a user is a bot.

Possible signals include:

- Request rate.
- Concurrent requests.
- Repeated payloads.
- Failed challenge count.
- Account creation burst.
- Device or session reuse.
- IP and network reputation.
- Suspicious automation indicators.
- Abnormal navigation patterns.

Responses should be graduated:

```text
Low risk       → normal processing
Moderate risk  → challenge or throttling
High risk      → stronger verification or quarantine
Extreme risk   → rejection or review
```

Do not use IP address as the sole identity model. Shared networks create false positives, and distributed bots evade IP-only rules.

---

## 11. Adversarial simulator

The simulator is part of the product demonstration, not an afterthought.

It should support configurable client profiles such as:

- Normal participant.
- Fast retry client.
- High-volume bot.
- Distributed bot.
- Slow bot.
- Refresh-heavy user.
- Network-failure client.
- Duplicate-submission client.

Parameters should include:

- Number of clients.
- Request rate.
- Concurrency.
- Retry policy.
- Traffic start time.
- Failure injection rate.
- Identity reuse behavior.

The simulator must label traffic classes so fairness results can be compared accurately.

---

## 12. Fairness and integrity dashboard

The dashboard should show real measurements generated by the simulation.

Important metrics include:

- Total requests.
- Unique valid entries.
- Duplicate attempts.
- Requests rejected or throttled.
- Entries by traffic class.
- Winners by traffic class.
- Winner rate by traffic class.
- Difference from expected allocation probability.
- P50, P95, and P99 API latency.
- Error rate.
- Queue or admission depth.
- Seats issued.
- Overselling count.
- Duplicate allocation count.
- Draw verification status.
- Claim expiry and reserve promotions.

Do not display only a vague “fairness score.” Show the raw numerator and denominator behind the score.

For example:

```text
High-volume bot entries: 1,200
High-volume bot winners: 12
Bot winner rate: 1.00%

Normal-user entries: 48,800
Normal-user winners: 488
Normal-user winner rate: 1.00%
```

These figures are illustrative only; the dashboard must use actual simulation results.

---

## 13. Fair Drop data model

A reasonable starting relational model is:

```text
users
- id
- email_hash or verified_contact_reference
- verification_level
- status
- created_at

sessions
- id
- user_id
- device_reference
- created_at
- expires_at
- revoked_at

events
- id
- name
- capacity
- registration_opens_at
- registration_closes_at
- state
- algorithm_version
- seed_commitment
- entry_list_hash
- result_hash
- created_at

eligibility_records
- id
- event_id
- user_id
- verification_level
- risk_state
- status
- created_at

entries
- id
- event_id
- eligibility_record_id
- idempotency_key
- status
- created_at
- accepted_at

lottery_results
- id
- event_id
- entry_id
- rank
- result_type
- created_at

claims
- id
- event_id
- entry_id
- user_id
- status
- expires_at
- claimed_at

allocations
- id
- event_id
- claim_id
- user_id
- seat_reference
- status
- issued_at

idempotency_records
- scope
- key
- request_hash
- response_reference
- expires_at

risk_events
- id
- event_id
- user_id or session_id
- signal_type
- severity
- created_at

audit_events
- id
- event_id
- actor
- action
- payload_hash
- created_at
```

The exact schema can change, but the concepts should remain explicit.

---

## 14. Fair Drop request flow

A high-level request flow is:

```text
User client
   ↓
CDN / WAF
   ↓
Load balancer / API gateway
   ↓
Authentication and request validation
   ↓
Admission and abuse controls
   ↓
Fair Drop application module
   ↓
Idempotency check
   ↓
Eligibility and uniqueness check
   ↓
Transactional database write
   ↓
Entry receipt returned to user
```

After registration closes:

```text
Event closure
   ↓
Freeze valid entries
   ↓
Calculate canonical-list hash
   ↓
Run auditable draw
   ↓
Store winner and reserve order
   ↓
Open claim window
   ↓
Issue allocations atomically
   ↓
Promote reserves after expiry
   ↓
Publish audit and fairness metrics
```

---

## 15. Recommended implementation boundary

For the hackathon, use a **modular monolith** with:

- React or another frontend framework.
- Node.js with TypeScript or FastAPI with Python.
- PostgreSQL as the source of truth.
- Redis for short-lived rate limits, queue metadata, and cache.
- A background worker for draw, claim expiry, and metrics aggregation.
- A traffic simulator as a separate process.
- A dashboard for operators and judges.

The code should have clear module boundaries even if it deploys as one backend application.

A sensible deployment shape is:

```text
Frontend/CDN
      ↓
API application × N
      ├── PostgreSQL
      ├── Redis
      ├── Job queue/worker
      └── Metrics/logging

Traffic simulator ──→ API
Fairness dashboard ──→ API/metrics store
```

Do not start with ten microservices. The hard part is proving correctness under concurrency. A modular monolith makes transactions, debugging, and demonstration easier.

---

## 16. Critical design decisions to document explicitly

Your system design should state these decisions rather than leave them ambiguous:

1. What is the source of truth for users, entries, claims, and ownership?
2. What exactly counts as one eligible participant?
3. What happens when the same request is retried?
4. When does registration close?
5. What happens to requests arriving exactly at the closing boundary?
6. Can the participant list change after freezing?
7. How is the draw reproducible?
8. What happens if a selected user does not claim?
9. What happens if the database or cache is temporarily unavailable?
10. How is inventory protected from concurrent writes?
11. Which metrics prove fairness?
12. Which signals trigger a challenge, throttle, quarantine, or rejection?
13. How can an auditor reproduce the allocation result?
14. How are privacy-sensitive identity and risk signals stored and deleted?

If these questions are not answered, the system design is incomplete even if the architecture diagram looks impressive.

---

## 17. Critical mistakes to avoid

### Mistake: treating the frontend as authoritative

The browser can be modified. All security, eligibility, and inventory decisions belong on the backend.

### Mistake: making the queue equal to fairness

A queue protects capacity but may still reward speed, early arrival, or automation.

### Mistake: using raw requests as entries

This converts request flooding into extra allocation probability.

### Mistake: relying only on IP rate limits

This harms shared networks and does not stop distributed automation.

### Mistake: putting all state in Redis

Fast state is not automatically durable ownership state.

### Mistake: ignoring retries

Timeouts and refreshes are normal user behavior. Without idempotency, they become duplicate opportunities or duplicate tickets.

### Mistake: claiming bots are eliminated

No practical system can guarantee perfect bot detection. The stronger and more defensible goal is to reduce or eliminate the advantage of speed, volume, and repetition.

### Mistake: building microservices before proving correctness

Service boundaries do not solve race conditions. They can make them harder to debug.

### Mistake: showing invented metrics

All fairness and performance numbers shown to judges must come from an actual reproducible test run.

---

## Final design principle

The default live-website foundation should make the platform secure, observable, scalable, recoverable, and maintainable.

The Fair Drop layer should then add controlled admission, unique participation, idempotent state transitions, auditable allocation, atomic claims, adversarial simulation, and measurable fairness.

The clean conceptual separation is:

```text
Default platform:
Can the website reliably serve users and protect their data?

Fair Drop layer:
Can scarce seats be allocated correctly and defensibly when demand and abuse are extreme?
```

Both questions must be answered. A system that survives traffic but allocates unfairly is not a solution. A system with a fair allocation rule that crashes under demand is also not a solution.
