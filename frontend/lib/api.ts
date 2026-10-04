/**
 * Fair Drop — Centralized Typed API Client
 *
 * Automatically:
 * 1. Attaches current Supabase JWT via Authorization: Bearer <token>
 * 2. Injects unique X-Request-ID for distributed tracing
 * 3. Injects Idempotency-Key for mutating state changes
 * 4. Parses standardized Fair Drop error envelopes:
 *    { error: { code, message, request_id, details } }
 */

import { env } from './config/env'
import { supabase } from './supabase'

export interface ApiErrorEnvelope {
  error: {
    code: string
    message: string
    request_id?: string
    details?: Record<string, any>
  }
}

export class FairDropApiError extends Error {
  code: string
  requestId?: string
  details?: Record<string, any>
  status: number

  constructor(status: number, envelope: ApiErrorEnvelope) {
    super(envelope.error.message || `API error: ${status}`)
    this.name = 'FairDropApiError'
    this.status = status
    this.code = envelope.error.code || 'UNKNOWN_ERROR'
    this.requestId = envelope.error.request_id
    this.details = envelope.error.details
  }
}

export const isUuid = (val: string): boolean =>
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(val)

function generateRequestId(): string {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return `req_${crypto.randomUUID().replace(/-/g, '')}`
  }
  return `req_${Math.random().toString(36).substring(2, 15)}`
}

interface RequestOptions extends RequestInit {
  idempotencyKey?: string
}

async function request<T = any>(path: string, options: RequestOptions = {}): Promise<T> {
  const baseUrl = env.NEXT_PUBLIC_API_BASE_URL.replace(/\/$/, '')
  const url = `${baseUrl}${path.startsWith('/') ? path : `/${path}`}`

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'X-Request-ID': generateRequestId(),
    ...((options.headers as Record<string, string>) || {}),
  }

  // 1. Attach Supabase JWT if authenticated
  try {
    const { data: { session } } = await supabase.auth.getSession()
    if (session?.access_token) {
      headers['Authorization'] = `Bearer ${session.access_token}`
    }
  } catch (err) {
    console.warn('[api] Failed to read Supabase session token:', err)
  }

  // 2. Attach Idempotency-Key if provided
  if (options.idempotencyKey) {
    headers['Idempotency-Key'] = options.idempotencyKey
  }

  let response: Response
  try {
    response = await fetch(url, {
      ...options,
      headers,
    })
  } catch (fetchErr: any) {
    throw new FairDropApiError(0, {
      error: {
        code: 'NETWORK_ERROR',
        message: fetchErr.message || `Unable to connect to backend at ${baseUrl}`,
        request_id: headers['X-Request-ID'],
      },
    })
  }

  // 3. Handle 204 No Content
  if (response.status === 204) {
    return {} as T
  }

  // 4. Parse JSON
  let body: any
  try {
    body = await response.json()
  } catch {
    body = { error: { code: 'INVALID_JSON', message: await response.text() } }
  }

  if (!response.ok) {
    const errorEnvelope: ApiErrorEnvelope = body.error
      ? body
      : {
          error: {
            code: `HTTP_${response.status}`,
            message: body.message || response.statusText || 'An unexpected error occurred',
            request_id: headers['X-Request-ID'],
          },
        }
    throw new FairDropApiError(response.status, errorEnvelope)
  }

  return body as T
}

export const api = {
  // ── Auth & Identity ──────────────────────────────────────────────────────────
  me: () => request('/auth/me', { method: 'GET' }),
  adminMe: () => request('/auth/me/admin', { method: 'GET' }),
  confirmEmail: (email: string) =>
    request('/auth/confirm', {
      method: 'POST',
      body: JSON.stringify({ email }),
    }),

  // ── Public Campaigns ─────────────────────────────────────────────────────────
  listCampaigns: (page = 1, pageSize = 20) =>
    request(`/campaigns?page=${page}&page_size=${pageSize}`, { method: 'GET' }),

  getCampaign: (id: string) =>
    request(`/campaigns/${id}`, { method: 'GET' }),

  getCampaignStatus: (id: string) => {
    if (!isUuid(id)) {
      return Promise.resolve({
        campaign: { id, status: 'OPEN', name: 'Showcase Demo Drop' },
        participant_state: 'REGISTERED',
        registration: {
          id: `reg_demo_${id}`,
          status: 'REGISTERED',
          registered_at: new Date().toISOString(),
        },
      } as any)
    }
    return request(`/campaigns/${id}/status`, { method: 'GET' })
  },

  getSeats: (id: string, limit = 500, offset = 0) => {
    if (!isUuid(id)) {
      const rows = ['A', 'B', 'C', 'D', 'E']
      const demoSeats = []
      for (const r of rows) {
        for (let i = 1; i <= 10; i++) {
          const num = i.toString().padStart(3, '0')
          const seatLabel = `${r}-${num}`
          demoSeats.push({
            id: `00000000-0000-0000-0000-${r.charCodeAt(0)}${num.padStart(8, '0')}`,
            seat_label: seatLabel,
            section: r,
            row_label: r,
            seat_number: i,
            status: ['A-001', 'A-002', 'B-005', 'C-003', 'D-008', 'E-010'].includes(seatLabel)
              ? 'CONFIRMED'
              : ['A-010', 'B-001', 'C-005', 'D-002'].includes(seatLabel)
              ? 'HELD'
              : 'AVAILABLE',
            hold_expires_at: null,
          })
        }
      }
      return Promise.resolve({
        campaign_id: id,
        total_seats: demoSeats.length,
        available_seats: demoSeats.filter((s) => s.status === 'AVAILABLE').length,
        held_seats: demoSeats.filter((s) => s.status === 'HELD').length,
        confirmed_seats: demoSeats.filter((s) => s.status === 'CONFIRMED').length,
        seats: demoSeats,
      } as any)
    }
    return request(`/campaigns/${id}/seats?limit=${limit}&offset=${offset}`, { method: 'GET' })
  },


  joinCampaign: (id: string, clientMeta?: Record<string, any>) => {
    // Demo slug safety fallback so exploring demo events never crashes on 422 UUID error
    if (!isUuid(id)) {
      const now = new Date()
      const expiresAt = new Date(now.getTime() + 10 * 60 * 1000)
      return Promise.resolve({
        permit_id: `permit_demo_${Math.random().toString(36).substring(2, 10)}`,
        admission_token: `token_demo_${Math.random().toString(36).substring(2, 15)}_${Math.random().toString(36).substring(2, 15)}`,
        nonce: `nonce_${Math.random().toString(36).substring(2, 18)}`,
        expires_at: expiresAt.toISOString(),
        campaign_id: id,
        server_time: now.toISOString(),
      })
    }
    return request(`/campaigns/${id}/join`, {
      method: 'POST',
      body: JSON.stringify({ client_meta: clientMeta || {} }),
    })
  },

  register: (
    campaignId: string,
    admissionToken: string,
    nonce: string,
    idempotencyKey: string,
    clientMeta?: Record<string, any>,
  ) => {
    if (!isUuid(campaignId)) {
      return Promise.resolve({
        registration_id: `reg_demo_${Math.random().toString(36).substring(2, 10)}`,
        campaign_id: campaignId,
        participant_id: 'participant_demo_user',
        status: 'REGISTERED',
        registered_at: new Date().toISOString(),
        risk_level: 'LOW',
        challenge_required: false,
        message: 'Showcase registration accepted successfully',
      } as any)
    }
    return request(`/campaigns/${campaignId}/register`, {
      method: 'POST',
      idempotencyKey,
      body: JSON.stringify({
        admission_token: admissionToken,
        nonce,
        client_meta: clientMeta || {},
      }),
    })
  },

  getResult: (campaignId: string) => {
    if (!isUuid(campaignId)) {
      return Promise.resolve({
        campaign_id: campaignId,
        participant_id: 'participant_demo_user',
        status: 'WON',
        is_winner: true,
        rank: 42,
        entitlement_id: 'ent_demo_win_042',
        hold_expires_at: new Date(Date.now() + 15 * 60 * 1000).toISOString(),
        redemption_deadline: new Date(Date.now() + 60 * 60 * 1000).toISOString(),
      } as any)
    }
    return request(`/campaigns/${campaignId}/result`, { method: 'GET' })
  },

  // ── Entitlements & Booking (Step 8) ───────────────────────────────────────────
  holdSeat: (
    campaignId: string,
    seatId: string | null,
    entitlementToken: string,
    idempotencyKey: string,
  ) => {
    if (!isUuid(campaignId)) {
      const now = new Date()
      const holdExpires = new Date(now.getTime() + 15 * 60 * 1000)
      return Promise.resolve({
        seat_id: seatId || '00000000-0000-0000-0000-000000000042',
        seat_label: seatId || 'Seat A-042',
        hold_expires_at: holdExpires.toISOString(),
        entitlement_id: entitlementToken || 'ent_demo_win_042',
        message: 'Seat successfully held.',
      } as any)
    }
    return request(`/entitlements/${campaignId}/hold`, {
      method: 'POST',
      idempotencyKey,
      body: JSON.stringify({
        entitlement_token: entitlementToken,
        seat_id: seatId && isUuid(seatId) ? seatId : null,
      }),
    })
  },

  redeemSeat: (
    campaignId: string,
    seatId: string,
    entitlementToken: string,
    idempotencyKey: string,
  ) => {
    if (!isUuid(campaignId)) {
      return Promise.resolve({
        booking_id: `book_demo_${Math.random().toString(36).substring(2, 10)}`,
        receipt_id: `RCP-2026-${Math.random().toString(36).substring(2, 8).toUpperCase()}`,
        campaign_id: campaignId,
        participant_id: 'participant_demo_user',
        seat_id: isUuid(seatId) ? seatId : '00000000-0000-0000-0000-000000000042',
        seat_label: isUuid(seatId) ? 'Seat A-042' : seatId,
        confirmed_at: new Date().toISOString(),
        message: 'Booking confirmed successfully.',
      } as any)
    }
    return request(`/entitlements/${campaignId}/redeem`, {
      method: 'POST',
      idempotencyKey,
      body: JSON.stringify({
        entitlement_token: entitlementToken,
        seat_id: seatId,
      }),
    })
  },

  releaseSeat: (campaignId: string, seatId: string, entitlementToken: string) => {
    if (!isUuid(campaignId)) {
      return Promise.resolve({
        status: 'RELEASED',
        seat_id: seatId,
        message: 'Seat hold successfully released.',
      } as any)
    }
    return request(`/entitlements/${campaignId}/release`, {
      method: 'POST',
      body: JSON.stringify({
        entitlement_token: entitlementToken,
        seat_id: seatId,
      }),
    })
  },

  // ── Verifiable Audit & Fairness ──────────────────────────────────────────────
  getAudit: (campaignId: string, page = 1, pageSize = 50) => {
    if (!isUuid(campaignId)) {
      return Promise.resolve({
        data: [
          {
            id: 'evt_audit_001',
            campaign_id: campaignId,
            actor_type: 'SYSTEM',
            event_type: 'REGISTRATION_WINDOW_CLOSED',
            reason_code: 'TIME_EXPIRED',
            metadata_json: { total_registrations: 42861, cleansed: 1656 },
            request_id: 'req_audit_001',
            created_at: new Date(Date.now() - 3600000).toISOString(),
          },
          {
            id: 'evt_audit_002',
            campaign_id: campaignId,
            actor_type: 'ADMIN',
            event_type: 'ROSTER_FROZEN',
            reason_code: 'PRE_DRAW_LOCK',
            metadata_json: { eligible_count: 41205, roster_hash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855' },
            request_id: 'req_audit_002',
            created_at: new Date(Date.now() - 3000000).toISOString(),
          },
          {
            id: 'evt_audit_003',
            campaign_id: campaignId,
            actor_type: 'SYSTEM',
            event_type: 'LOTTERY_DRAWN',
            reason_code: 'FISHER_YATES_UNIFORM',
            metadata_json: { seed: 'drand_beacon_round_3849120', winners: 500, standby: 500 },
            request_id: 'req_audit_003',
            created_at: new Date(Date.now() - 2400000).toISOString(),
          },
          {
            id: 'evt_audit_004',
            campaign_id: campaignId,
            actor_type: 'SYSTEM',
            event_type: 'ZERO_OVERSELL_VERIFIED',
            reason_code: 'INVARIANT_PASS',
            metadata_json: { max_capacity: 500, allocated: 500, oversell: 0 },
            request_id: 'req_audit_004',
            created_at: new Date(Date.now() - 1800000).toISOString(),
          },
        ],
        total: 4,
        limit: pageSize,
        offset: (page - 1) * pageSize,
      } as any)
    }
    const offset = (page - 1) * pageSize
    return request(`/campaigns/${campaignId}/audit?limit=${pageSize}&offset=${offset}`, {
      method: 'GET',
    })
  },

  getFairness: (campaignId: string) => {
    if (!isUuid(campaignId)) {
      return Promise.resolve({
        campaign_id: campaignId,
        roster_hash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        randomness_seed: null,
        randomness_commitment: 'a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3',
        lottery_run_id: 'run_demo_001',
        total_eligible: 41205,
        capacity: 500,
        selection_probability: 500 / 41205,
        statement: 'selection probability is independent of request rate',
        reproducibility_notes: 'Execute Fisher-Yates shuffle with committed seed over canonical roster hash.',
        evidence_hash: '7d1a5518b57700201d16a50ee7b3512a831e5f8f949f57ebbf794c483161c28b',
        draw_executed_at: new Date(Date.now() - 2400000).toISOString(),
      } as any)
    }
    return request(`/campaigns/${campaignId}/fairness`, { method: 'GET' })
  },

  getMetrics: (campaignId: string) => {
    if (!isUuid(campaignId)) {
      return Promise.resolve({
        campaign_id: campaignId,
        name: 'Showcase Demo Drop',
        status: 'CLAIMING',
        capacity: 500,
        registrations_count: 42861,
        eligible_roster_count: 41205,
        winners_count: 500,
        standby_count: 500,
        seats_total: 500,
        seats_available: 458,
        seats_held: 12,
        seats_confirmed: 30,
        bookings_count: 30,
        challenges_passed: 41205,
        challenges_failed: 1656,
        holds_expired_count: 2,
        entitlements_expired_count: 0,
        duplicate_allocation_count: 0,
        oversell_count: 0,
        generated_at: new Date().toISOString(),
      } as any)
    }
    return request(`/campaigns/${campaignId}/metrics`, { method: 'GET' })
  },

  // ── Admin Operations ─────────────────────────────────────────────────────────
  admin: {
    createCampaign: (data: Record<string, any>) =>
      request('/admin/campaigns', {
        method: 'POST',
        body: JSON.stringify(data),
      }),

    listCampaigns: (page = 1, pageSize = 50) =>
      request(`/admin/campaigns?page=${page}&page_size=${pageSize}`, {
        method: 'GET',
      }),

    getCampaign: (id: string) => {
      if (!isUuid(id)) {
        return Promise.resolve({
          id,
          name: 'Showcase Demo Drop',
          description: '500 high-demand pass allocation with verified uniform lottery distribution.',
          venue: 'San Francisco, CA',
          capacity: 500,
          registration_start: new Date(Date.now() - 86400000).toISOString(),
          registration_end: new Date(Date.now() + 86400000).toISOString(),
          redemption_deadline: new Date(Date.now() + 172800000).toISOString(),
          max_tickets_per_participant: 1,
          allocation_method: 'UNIFORM_LOTTERY',
          standby_policy: 'FIXED_ORDER',
          status: 'OPEN',
          policy_version: 'v1.0.5',
          admission_paused: false,
          registration_paused: false,
          redemption_paused: false,
          policy_hash: 'demo_policy_hash_001',
          created_by: '00000000-0000-0000-0000-000000000001',
          created_at: new Date(Date.now() - 172800000).toISOString(),
          updated_at: new Date().toISOString(),
          seat_counts: { available: 458, held: 12, confirmed: 30, total: 500 },
          registration_counts: { total: 42861, accepted: 41205, duplicate: 1656, rejected: 0 },
        } as any)
      }
      return request(`/admin/campaigns/${id}`, { method: 'GET' })
    },

    updateCampaign: (id: string, data: Record<string, any>) => {
      if (!isUuid(id)) {
        return Promise.resolve({ id, ...data, message: 'Demo campaign updated' } as any)
      }
      return request(`/admin/campaigns/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      })
    },

    prepareCampaign: (id: string) => {
      if (!isUuid(id)) {
        return Promise.resolve({
          campaign_id: id,
          previous_status: 'DRAFT',
          new_status: 'PREPARING',
          message: 'Campaign prepared and seat inventory generated',
          server_time: new Date().toISOString(),
        } as any)
      }
      return request(`/admin/campaigns/${id}/prepare`, { method: 'POST' })
    },

    publishCampaign: (id: string) => {
      if (!isUuid(id)) {
        return Promise.resolve({
          campaign_id: id,
          previous_status: 'PREPARING',
          new_status: 'OPEN',
          message: 'Campaign published and open for registrations',
          server_time: new Date().toISOString(),
        } as any)
      }
      return request(`/admin/campaigns/${id}/publish`, { method: 'POST' })
    },

    closeCampaign: (id: string) => {
      if (!isUuid(id)) {
        return Promise.resolve({
          campaign_id: id,
          previous_status: 'OPEN',
          new_status: 'CLOSED',
          message: 'Campaign registrations closed',
          server_time: new Date().toISOString(),
        } as any)
      }
      return request(`/admin/campaigns/${id}/close`, { method: 'POST' })
    },

    freezeCampaign: (id: string) => {
      if (!isUuid(id)) {
        return Promise.resolve({
          campaign_id: id,
          status: 'FROZEN',
          roster_hash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
          eligible_count: 500,
          frozen_at: new Date().toISOString(),
          message: 'Eligible roster frozen and verified',
        } as any)
      }
      return request(`/admin/campaigns/${id}/freeze`, { method: 'POST' })
    },

    drawLottery: (id: string, seed?: string) => {
      if (!isUuid(id)) {
        return Promise.resolve({
          campaign_id: id,
          status: 'CLAIMING',
          winners_count: 500,
          standby_count: 500,
          randomness_seed: seed || 'drand_beacon_seed_demo_77',
          randomness_commitment: 'a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3',
          executed_at: new Date().toISOString(),
          message: 'Uniform Fisher-Yates lottery draw executed successfully',
        } as any)
      }
      return request(`/admin/campaigns/${id}/draw`, {
        method: 'POST',
        body: JSON.stringify({ randomness_seed: seed || null }),
      })
    },

    pauseCampaign: (id: string, scope: string, reason?: string) => {
      if (!isUuid(id)) {
        return Promise.resolve({
          id,
          [`${scope.toLowerCase()}_paused`]: true,
          message: `Campaign scope ${scope} paused`,
        } as any)
      }
      return request(`/admin/campaigns/${id}/pause`, {
        method: 'POST',
        body: JSON.stringify({ scope, reason: reason || 'Operational pause triggered' }),
      })
    },

    resumeCampaign: (id: string, scope: string) => {
      if (!isUuid(id)) {
        return Promise.resolve({
          id,
          [`${scope.toLowerCase()}_paused`]: false,
          message: `Campaign scope ${scope} resumed`,
        } as any)
      }
      return request(`/admin/campaigns/${id}/resume`, {
        method: 'POST',
        body: JSON.stringify({ scope }),
      })
    },

    getFairnessEvidence: (id: string) => {
      if (!isUuid(id)) {
        return Promise.resolve({
          campaign_id: id,
          roster_hash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
          randomness_seed: 'drand_beacon_round_3849120',
          randomness_commitment: 'a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3',
          total_eligible: 41205,
          capacity: 500,
          selection_probability: 500 / 41205,
          statement: 'selection probability is independent of request rate',
          reproducibility_notes: 'Deterministic Fisher-Yates with unredacted operator seed.',
          evidence_hash: '7d1a5518b57700201d16a50ee7b3512a831e5f8f949f57ebbf794c483161c28b',
          draw_executed_at: new Date(Date.now() - 2400000).toISOString(),
        } as any)
      }
      return request(`/admin/campaigns/${id}/fairness-evidence`, { method: 'GET' })
    },
  },
}
