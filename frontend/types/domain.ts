/**
 * Fair Drop — Domain Types
 *
 * Single source of truth for every state enum and core entity shape.
 * Derived from:
 *   - docs/FairDrop-Universal-Context.md  §4, §8
 *   - docs/Fair Drop — Master Backend and Frontend Integration Guide.md §4–§14
 *
 * Rules:
 *   - Never import from lib/api here. This file has zero dependencies.
 *   - Never define a state value as a plain string in a page component.
 */

// ---------------------------------------------------------------------------
// Roles
// ---------------------------------------------------------------------------

export type UserRole = 'USER' | 'ADMIN'

// ---------------------------------------------------------------------------
// Campaign state machine
// DRAFT → PREPARING → OPEN → CLOSED → FROZEN → DRAWING → CLAIMING → COMPLETED
// ---------------------------------------------------------------------------

export type CampaignStatus =
  | 'DRAFT'
  | 'PREPARING'
  | 'OPEN'
  | 'CLOSED'
  | 'FROZEN'
  | 'DRAWING'
  | 'CLAIMING'
  | 'COMPLETED'

// ---------------------------------------------------------------------------
// Registration state machine
// RECEIVED → VALIDATING → ACCEPTED | DUPLICATE | REJECTED | QUARANTINED
// ---------------------------------------------------------------------------

export type RegistrationStatus =
  | 'RECEIVED'
  | 'VALIDATING'
  | 'ACCEPTED'
  | 'DUPLICATE'
  | 'REJECTED'
  | 'QUARANTINED'

// ---------------------------------------------------------------------------
// Entitlement/claim state machine
// SELECTED → CLAIM_PENDING → HELD → CONFIRMED
//                              └──→ EXPIRED
// ---------------------------------------------------------------------------

export type EntitlementStatus =
  | 'SELECTED'
  | 'CLAIM_PENDING'
  | 'HELD'
  | 'CONFIRMED'
  | 'EXPIRED'

// ---------------------------------------------------------------------------
// Seat state machine
// AVAILABLE → HELD → CONFIRMED (expired/released → AVAILABLE)
// ---------------------------------------------------------------------------

export type SeatStatus = 'AVAILABLE' | 'HELD' | 'CONFIRMED'

// ---------------------------------------------------------------------------
// Lottery result (per-participant view)
// ---------------------------------------------------------------------------

export type AllocationResult = 'SELECTED' | 'STANDBY' | 'NOT_SELECTED' | 'PENDING'

// ---------------------------------------------------------------------------
// Admission / waiting-room state
// ---------------------------------------------------------------------------

export type AdmissionState =
  | 'WAITING'
  | 'ADMITTED'
  | 'ALREADY_REGISTERED'
  | 'CHALLENGE_REQUIRED'
  | 'COOLDOWN'
  | 'CAMPAIGN_CLOSED'

// ---------------------------------------------------------------------------
// Risk level
// ---------------------------------------------------------------------------

export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH'

// ---------------------------------------------------------------------------
// Challenge types supported by the backend
// ---------------------------------------------------------------------------

export type ChallengeType = 'TURNSTILE' | 'MEDIAPIPE' | 'VISUAL' | 'MOCK'

// ---------------------------------------------------------------------------
// Allocation method
// ---------------------------------------------------------------------------

export type AllocationMethod = 'UNIFORM_LOTTERY'

// ---------------------------------------------------------------------------
// Participant verification state
// ---------------------------------------------------------------------------

export type VerificationStatus =
  | 'UNVERIFIED'
  | 'EMAIL_VERIFIED'
  | 'PHONE_VERIFIED'
  | 'FULLY_VERIFIED'

// ---------------------------------------------------------------------------
// Pause scope (admin)
// ---------------------------------------------------------------------------

export type PauseScope = 'ADMISSION' | 'REGISTRATION' | 'REDEMPTION'

// ---------------------------------------------------------------------------
// Core entities (matches backend schema fields)
// ---------------------------------------------------------------------------

/** Publicly visible campaign summary returned by GET /api/v1/campaigns */
export interface CampaignSummary {
  id: string
  name: string
  description: string
  capacity: number
  registration_start: string // ISO timestamp
  registration_end: string // ISO timestamp
  redemption_deadline: string // ISO timestamp
  max_tickets_per_participant: number
  allocation_method: AllocationMethod
  status: CampaignStatus
  policy_version: string
  venue?: string | null
  event_start?: string | null
}

/** Full campaign detail (user-facing event page) */
export interface EventDetails extends CampaignSummary {
  admission_paused: boolean
  registration_paused: boolean
  redemption_paused: boolean
  policy_hash?: string | null
}

/** Per-participant registration record */
export interface RegistrationRecord {
  id: string
  campaign_id: string
  status: RegistrationStatus
  eligible: boolean
  duplicate: boolean
  policy_version: string
  created_at: string
  reason_code?: string | null
}

/** Admission permit returned after a successful join */
export interface AdmissionPermit {
  token: string
  expires_at: string
  allowed_operation: string
}

/** Entitlement record (winner's claim token) */
export interface EntitlementRecord {
  id: string
  campaign_id: string
  status: EntitlementStatus
  expires_at: string
  redeemed_at?: string | null
  held_seat_id?: string | null
}

/** Seat record */
export interface SeatRecord {
  id: string
  campaign_id: string
  seat_label: string
  section?: string | null
  row_label?: string | null
  seat_number?: number | null
  status: SeatStatus
}

/** A participant's complete state for a campaign (from GET /status) */
export interface ParticipantCampaignState {
  campaign: {
    id: string
    status: CampaignStatus
    registration_end: string
    redemption_deadline: string
    server_time: string
  }
  participant_state:
    | 'UNREGISTERED'
    | 'REGISTERED'
    | 'SELECTED'
    | 'HELD'
    | 'CONFIRMED'
    | 'COOLDOWN'
    | 'PAUSED'
  registration?: RegistrationRecord | null
  admission?: {
    state: AdmissionState
    permit_expires_at?: string | null
  } | null
  challenge?: {
    id: string
    type: ChallengeType
    status: string
  } | null
  entitlement?: EntitlementRecord | null
  seat_hold?: {
    seat_id: string
    seat_label: string
    hold_expires_at: string
    server_time: string
  } | null
}

/** Lottery result response */
export interface LotteryResultRecord {
  campaign_id: string
  result: AllocationResult
  standby_position?: number | null
  entitlement?: Pick<EntitlementRecord, 'id' | 'status' | 'expires_at'> | null
  audit_reference?: {
    policy_version: string
    roster_hash: string
    randomness_reference: string
    algorithm_version: string
  } | null
}

/** Public audit record */
export interface AuditRecord {
  campaign_id: string
  policy_version: string
  policy_hash: string
  registration_cutoff: string
  registered_count: number
  eligible_count: number
  duplicate_count: number
  roster_hash: string
  randomness_reference: string
  algorithm_version: string
  winner_count: number
  standby_rule: string
  oversell_count: number
  duplicate_allocation_count: number
}

/** Seat hold confirmation */
export interface SeatHoldRecord {
  entitlement_id: string
  seat_id: string
  seat_label: string
  status: 'HELD'
  hold_expires_at: string
  server_time: string
}

/** Final booking confirmation */
export interface BookingRecord {
  booking_id: string
  entitlement_id: string
  seat_id: string
  seat_label: string
  status: 'CONFIRMED'
  confirmed_at: string
  receipt_id: string
}

/** Challenge issued by the server */
export interface ChallengeRecord {
  challenge_id: string
  type: ChallengeType
  nonce: string
  expires_at: string
  max_attempts: number
  implementation_version: string
}

/** Challenge verification result */
export interface ChallengeVerifyResult {
  challenge_id: string
  status: 'PASSED' | 'FAILED'
  risk_level: RiskLevel
  reason_code: string
  verified_until: string
}

/** Authenticated user profile */
export interface UserProfile {
  id: string
  display_name: string
  role: UserRole
  email_verified: boolean
  phone_verified: boolean
  institute_verified: boolean
  verification_status: VerificationStatus
  created_at: string
}
