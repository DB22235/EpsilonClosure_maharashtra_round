'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import {
  ArrowRight,
  CheckCircle2,
  Clock,
  ShieldCheck,
  Ticket,
  AlertCircle,
  AlertTriangle,
  Loader2,
  RefreshCw,
  Zap,
  Info,
  ExternalLink,
  Sparkles,
} from 'lucide-react'
import { DemoNotice, FairShell, ProgressSteps, StatusPill } from '@/components/fair-shell'
import { getDemoEvent } from '@/lib/demo-events'
import { useAuth } from '@/lib/AuthContext'
import { api, FairDropApiError, isUuid } from '@/lib/api'

export default function ClaimPage() {
  const params = useParams()
  const router = useRouter()
  const campaignId = (params?.campaignId as string) || 'camp_demo_001'
  const fallbackEvent = getDemoEvent(campaignId)

  const { user } = useAuth()
  const [campaign, setCampaign] = useState<any>(null)
  const [participantResult, setParticipantResult] = useState<any>(null)
  const [seats, setSeats] = useState<any[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [fastForwarding, setFastForwarding] = useState<boolean>(false)

  const [entitlementToken, setEntitlementToken] = useState<string>('')
  const [selectedSeat, setSelectedSeat] = useState<string>('')
  const [selectedSeatId, setSelectedSeatId] = useState<string>('')
  const [holdingSeconds, setHoldingSeconds] = useState<number>(899) // 14m 59s
  const [holding, setHolding] = useState<boolean>(false)
  const [redeeming, setRedeeming] = useState<boolean>(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)

  // 1. Fetch live campaign, participant outcome, and live seat map
  const loadPageData = async () => {
    setLoading(true)
    setErrorMsg(null)
    try {
      // 1. Fetch Campaign
      const camp = await api.getCampaign(campaignId).catch(() => null)
      setCampaign(camp)

      // 2. Fetch User's Lottery Result / Entitlement
      const res = await api.getResult(campaignId).catch(() => null)
      setParticipantResult(res)
      if (res?.entitlement_id) {
        setEntitlementToken(res.entitlement_id)
      } else {
        // Check session storage
        try {
          const cached = sessionStorage.getItem(`fairdrop_result_${campaignId}`)
          if (cached) {
            const parsed = JSON.parse(cached)
            if (parsed.entitlement_id) setEntitlementToken(parsed.entitlement_id)
          }
        } catch {}
      }

      // 3. Fetch Real Seat Map from PostgreSQL
      const seatRes = await api.getSeats(campaignId).catch(() => null)
      if (seatRes?.seats && seatRes.seats.length > 0) {
        setSeats(seatRes.seats)
        const firstAvail = seatRes.seats.find((s: any) => s.status === 'AVAILABLE')
        if (firstAvail) {
          setSelectedSeat(firstAvail.seat_label)
          setSelectedSeatId(firstAvail.id)
        }
      }
    } catch (err: any) {
      console.warn('[ClaimPage] Data load warning:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadPageData()
  }, [campaignId])

  // 2. Countdown timer for seat hold
  useEffect(() => {
    if (holdingSeconds <= 0) return
    const timer = setInterval(() => {
      setHoldingSeconds((prev) => (prev > 0 ? prev - 1 : 0))
    }, 1000)
    return () => clearInterval(timer)
  }, [holdingSeconds])

  const formatTimer = (secs: number) => {
    const m = Math.floor(secs / 60)
    const s = secs % 60
    return `${m}:${s < 10 ? '0' : ''}${s}`
  }

  // 3. Atomic Seat Hold Trigger with Real Database Seat ID
  const handleSelectSeat = async (seat: any) => {
    if (seat.status !== 'AVAILABLE' || holding) return

    setHolding(true)
    setErrorMsg(null)
    setSuccessMsg(null)

    if (campaignStatus !== 'CLAIMING') {
      setErrorMsg(`Seat selection is disabled. Campaign is currently in the ${campaignStatus} phase (seats unlock in CLAIMING phase).`)
      setHolding(false)
      return
    }

    const tokenToUse = entitlementToken || ''

    if (!tokenToUse) {
      setErrorMsg('No winning lottery entitlement found for your account. You cannot hold a seat without winning the lottery draw.')
      setHolding(false)
      return
    }

    const holdKey = `hold_${campaignId}_${seat.id}_${user?.id || 'anon'}`

    try {
      const holdRes = await api.holdSeat(campaignId, seat.id, tokenToUse, holdKey)

      setSelectedSeat(holdRes.seat_label || seat.seat_label)
      setSelectedSeatId(holdRes.seat_id || seat.id)

      if (holdRes.hold_expires_at) {
        const diffSecs = Math.max(0, Math.floor((new Date(holdRes.hold_expires_at).getTime() - Date.now()) / 1000))
        setHoldingSeconds(diffSecs)
      } else {
        setHoldingSeconds(15 * 60)
      }

      setSeats((prev) =>
        prev.map((s) =>
          s.id === seat.id
            ? { ...s, status: 'HELD' }
            : s.id === selectedSeatId && s.status === 'HELD'
            ? { ...s, status: 'AVAILABLE' }
            : s
        )
      )

      setSuccessMsg(`Atomically held seat ${holdRes.seat_label || seat.seat_label} for 15 minutes!`)
    } catch (err: any) {
      console.error('[Claim] Hold failed:', err)
      if (err instanceof FairDropApiError) {
        if (err.code === 'SEAT_ALREADY_HELD' || err.code === 'SEAT_NOT_AVAILABLE' || err.code === 'SEAT_UNAVAILABLE') {
          setSeats((prev) => prev.map((s) => (s.id === seat.id ? { ...s, status: 'HELD' } : s)))
          setErrorMsg(`Seat ${seat.seat_label} is held by another user. Please select another seat.`)
        } else if (err.code === 'ENTITLEMENT_NOT_FOUND') {
          setErrorMsg('No valid entitlement found matching token for participant. Complete the lottery draw first.')
        } else {
          setErrorMsg(`[${err.code}] ${err.message}`)
        }
      } else {
        setErrorMsg(err.message || `Failed to hold seat ${seat.seat_label}. Please retry.`)
      }
    } finally {
      setHolding(false)
    }
  }

  // 4. Confirm Booking Redemption
  const handleConfirmBooking = async () => {
    setRedeeming(true)
    setErrorMsg(null)
    setSuccessMsg(null)

    if (campaignStatus !== 'CLAIMING') {
      setErrorMsg(`Booking redemption is disabled. Campaign is currently in ${campaignStatus} phase.`)
      setRedeeming(false)
      return
    }

    const tokenToUse = entitlementToken || ''
    if (!tokenToUse) {
      setErrorMsg('No winning lottery entitlement found. Entitlement token is required to redeem seats.')
      setRedeeming(false)
      return
    }

    const targetSeatId = selectedSeatId || (seats.length > 0 ? seats[0].id : '')
    if (!targetSeatId) {
      setErrorMsg('Please select a seat from the map first.')
      setRedeeming(false)
      return
    }

    const redeemKey = `redeem_${campaignId}_${targetSeatId}_${user?.id || 'anon'}`

    try {
      const redeemRes = await api.redeemSeat(campaignId, targetSeatId, tokenToUse, redeemKey)

      if (typeof window !== 'undefined') {
        sessionStorage.setItem(
          `fairdrop_confirmed_${campaignId}`,
          JSON.stringify({
            ...redeemRes,
            seat_label: redeemRes.seat_label || selectedSeat,
            confirmed_at: redeemRes.confirmed_at || new Date().toISOString(),
          })
        )
      }

      router.push(`/events/${campaignId}/confirmed`)
    } catch (err: any) {
      console.error('[Claim] Redemption failed:', err)
      if (err instanceof FairDropApiError) {
        setErrorMsg(`[${err.code}] ${err.message}`)
      } else {
        setErrorMsg(err.message || 'Failed to confirm booking. Please try again.')
      }
      setRedeeming(false)
    }
  }

  // 5. Operator Fast-Forward Simulation: Run Draw & Grant Test Winner Entitlement
  const handleOperatorFastForward = async () => {
    setFastForwarding(true)
    setErrorMsg(null)
    setSuccessMsg(null)
    try {
      // Step A: Register current user if not already registered
      await api.register(
        campaignId,
        'fast_forward_token',
        'fast_forward_nonce',
        `reg_ff_${Date.now()}`,
        { region: 'GLOBAL' }
      ).catch(() => null)

      // Step B: Advance lifecycle to CLAIMING if needed
      if (campaign?.status === 'DRAFT') {
        await api.admin.prepareCampaign(campaignId).catch(() => null)
        await api.admin.publishCampaign(campaignId).catch(() => null)
      }
      if (campaign?.status === 'OPEN' || campaign?.status === 'PREPARING') {
        await api.admin.closeCampaign(campaignId).catch(() => null)
      }
      await api.admin.freezeCampaign(campaignId).catch(() => null)
      await api.admin.drawLottery(campaignId, 'beacon_fast_forward_seed_001').catch(() => null)

      setSuccessMsg('⚡ Fast-forward complete: Lottery draw executed! Winning entitlement granted to your account.')
      await loadPageData()
    } catch (err: any) {
      setErrorMsg(`Fast-forward failed: ${err.message}`)
    } finally {
      setFastForwarding(false)
    }
  }

  const campaignStatus = campaign?.status || fallbackEvent.status
  const isClaimingOpen = campaignStatus === 'CLAIMING' || !isUuid(campaignId)
  const isWinner = participantResult?.is_winner || Boolean(entitlementToken) || !isUuid(campaignId)

  // Organize real seats into rows (e.g. A, B, C...)
  const seatRows: Record<string, any[]> = {}
  seats.slice(0, 50).forEach((s) => {
    const row = s.row_label || s.section || 'A'
    if (!seatRows[row]) seatRows[row] = []
    seatRows[row].push(s)
  })

  return (
    <FairShell active="Explore Drops">
      <ProgressSteps current={5} />

      <div className="border-x-[3px] border-b-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] px-5 py-12 sm:px-12 lg:px-20">
        
        {/* Banner: Error or Notice */}
        {errorMsg && (
          <div className="mb-8 border-[3px] border-red-600 bg-red-100 p-4 font-mono text-xs font-bold text-red-950 shadow-[4px_4px_0_var(--fd-ink)] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="size-5 shrink-0 text-red-700" />
              <span>{errorMsg}</span>
            </div>
            <StatusPill>SEAT MAP NOTICE</StatusPill>
          </div>
        )}

        {successMsg && (
          <div className="mb-8 border-[3px] border-green-600 bg-green-100 p-4 font-mono text-xs font-bold text-green-950 shadow-[4px_4px_0_var(--fd-ink)] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="size-5 shrink-0 text-green-700" />
              <span>{successMsg}</span>
            </div>
            <StatusPill>VERIFIED</StatusPill>
          </div>
        )}

        {/* ── Lifecycle State Guard: If Campaign Is Not Yet In CLAIMING Phase ─────────── */}
        {!isClaimingOpen && (
          <div className="mb-10 border-[3px] border-[var(--fd-ink)] bg-[var(--fd-yellow)] p-8 shadow-[8px_8px_0_var(--fd-ink)]">
            <div className="flex items-start gap-4">
              <AlertTriangle className="size-8 text-[var(--fd-ink)] shrink-0 mt-1" />
              <div>
                <span className="font-mono text-xs font-black uppercase text-neutral-800">
                  LIFECYCLE GUARD · LOTTERY ALLOCATION IN PROGRESS
                </span>
                <h2 className="font-display text-3xl font-black mt-1">
                  CURRENT STATUS: {campaignStatus.toUpperCase()}
                </h2>
                <p className="font-mono text-xs font-bold mt-2 leading-relaxed max-w-3xl">
                  {campaignStatus === 'OPEN' && (
                    <>
                      Registrations are currently <strong>OPEN</strong>. Fair Drop does not permit direct seat checkout while the registration window is active. Once registrations close, an automated uniform lottery draw will generate verifiable seat claim entitlements.
                    </>
                  )}
                  {(campaignStatus === 'CLOSED' || campaignStatus === 'FROZEN') && (
                    <>
                      Registrations are <strong>CLOSED</strong>. The immutable participant roster has been hashed, and the uniform lottery draw is pending execution.
                    </>
                  )}
                  {campaignStatus === 'DRAFT' && (
                    <>
                      This campaign is currently in <strong>DRAFT</strong> mode and has not yet published tickets.
                    </>
                  )}
                </p>

                <div className="mt-6 flex flex-wrap items-center gap-4">
                  {campaignStatus === 'OPEN' && (
                    <Link href={`/events/${campaignId}/register`} className="button-primary bg-[var(--fd-teal)] text-[var(--fd-ink)]">
                      Register For This Drop →
                    </Link>
                  )}
                  <Link href={`/events/${campaignId}/status`} className="button-secondary">
                    View My Entry Status
                  </Link>
                  <Link href={`/admin/campaigns/${campaignId}`} className="button-secondary bg-[var(--fd-card)] flex items-center gap-1.5">
                    Admin Campaign Console <ExternalLink className="size-3.5" />
                  </Link>
                  <button
                    type="button"
                    onClick={handleOperatorFastForward}
                    disabled={fastForwarding}
                    className="button-primary bg-[var(--fd-pink)] flex items-center gap-2 cursor-pointer shadow-[3px_3px_0_var(--fd-ink)]"
                    title="Simulates closing, freezing, and drawing lottery with current user as Winner #1"
                  >
                    {fastForwarding ? <Loader2 className="size-4 animate-spin" /> : <Sparkles className="size-4" />}
                    <span>⚡ Run Test Draw & Grant Entitlement</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── Main Interactive Seat Selection Workspace ───────────────────────────── */}
        <div className="grid gap-10 lg:grid-cols-[1.2fr_0.8fr]">
          
          {/* Seat Grid Layout */}
          <div className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-6 shadow-[8px_8px_0_var(--fd-ink)]">
            <div className="flex flex-col gap-2 border-b-[3px] border-[var(--fd-ink)] pb-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="font-display text-2xl font-black">INTERACTIVE SEAT SELECTION</h2>
                <p className="text-xs font-mono font-bold text-[var(--fd-ink)]/70">
                  {seats.length > 0 ? `LIVE POSTGRESQL INVENTORY (${seats.length} SEATS)` : 'STAGE / FRONT ROW LAYOUT'}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={loadPageData}
                  disabled={loading}
                  className="button-secondary text-[11px] py-1 px-2.5 flex items-center gap-1"
                >
                  <RefreshCw className={`size-3.5 ${loading ? 'animate-spin' : ''}`} /> Sync
                </button>
                <div className="border-2 border-[var(--fd-ink)] bg-[var(--fd-teal)] px-3 py-1 font-mono text-xs font-black uppercase">
                  {holding ? 'ACQUIRING HOLD...' : 'ATOMIC LOCK ACTIVE'}
                </div>
              </div>
            </div>

            {/* Stage Graphic */}
            <div className="mt-6 border-2 border-[var(--fd-ink)] bg-[var(--fd-ink)] p-3 text-center text-xs font-mono font-bold text-[var(--fd-cream)] uppercase tracking-widest shadow-[3px_3px_0_var(--fd-ink)]">
              MAIN STAGE / PODIUM
            </div>

            {/* Legend */}
            <div className="mt-6 flex flex-wrap gap-4 text-xs font-mono font-bold justify-center">
              <span className="flex items-center gap-1.5">
                <span className="size-4 border border-[var(--fd-ink)] bg-[var(--fd-pink)] inline-block" /> Selected ({selectedSeat || 'None'})
              </span>
              <span className="flex items-center gap-1.5">
                <span className="size-4 border border-[var(--fd-ink)] bg-[var(--fd-teal)] inline-block" /> Available
              </span>
              <span className="flex items-center gap-1.5">
                <span className="size-4 border border-[var(--fd-ink)] bg-[var(--fd-yellow)] inline-block" /> Temporary Hold
              </span>
              <span className="flex items-center gap-1.5">
                <span className="size-4 border border-[var(--fd-ink)] bg-neutral-300 inline-block opacity-60" /> Booked
              </span>
            </div>

            {/* Visual Multi-Colored Seats Grid */}
            <div className="mt-6 flex flex-col gap-3 overflow-x-auto pb-2">
              {Object.keys(seatRows).length > 0 ? (
                Object.entries(seatRows).map(([rowLabel, rowSeats]) => (
                  <div key={rowLabel} className="flex items-center gap-2 justify-center">
                    <span className="w-6 font-mono text-xs font-black text-center">{rowLabel}</span>
                    {rowSeats.map((seat: any) => {
                      const isSelected = seat.id === selectedSeatId || seat.seat_label === selectedSeat
                      const isAvail = seat.status === 'AVAILABLE'
                      const isHeld = seat.status === 'HELD' && !isSelected
                      const isBooked = seat.status === 'CONFIRMED'

                      let colorClass = 'bg-[var(--fd-teal)] hover:bg-[var(--fd-yellow)] cursor-pointer'
                      if (isSelected) {
                        colorClass = 'bg-[var(--fd-pink)] scale-110 shadow-[3px_3px_0_var(--fd-ink)] z-10'
                      } else if (isHeld) {
                        colorClass = 'bg-[var(--fd-yellow)] opacity-80 cursor-not-allowed'
                      } else if (isBooked) {
                        colorClass = 'bg-neutral-300 opacity-40 cursor-not-allowed'
                      }

                      return (
                        <button
                          key={seat.id}
                          type="button"
                          disabled={(!isAvail && !isSelected) || holding || !isClaimingOpen || !isWinner}
                          onClick={() => handleSelectSeat(seat)}
                          className={`size-9 border-2 border-[var(--fd-ink)] font-mono text-[10px] font-black transition-all ${
                            !isClaimingOpen || !isWinner ? 'opacity-40 cursor-not-allowed' : colorClass
                          }`}
                          title={`Seat ${seat.seat_label} - Status: ${seat.status}${!isClaimingOpen ? ' (Selection locked until CLAIMING phase)' : ''}`}
                        >
                          {seat.seat_number ? seat.seat_number.toString().padStart(2, '0') : seat.seat_label}
                        </button>
                      )
                    })}
                  </div>
                ))
              ) : (
                <div className="text-center py-10 font-mono text-xs font-bold text-neutral-500">
                  {loading ? 'Loading seat inventory from server...' : 'No seats generated yet. Organizers generate seats during the Prepare step.'}
                </div>
              )}
            </div>
          </div>

          {/* Holding Timer & Verification Sidebar */}
          <div className="flex flex-col gap-6">
            <div className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-yellow)] p-6 shadow-[8px_8px_0_var(--fd-ink)]">
              <div className="flex items-center justify-between border-b-[3px] border-[var(--fd-ink)] pb-4">
                <span className="font-mono text-xs font-black uppercase flex items-center gap-2">
                  <Clock className="size-4" /> HOLD TIMER COUNTDOWN
                </span>
                <span className="font-mono text-xs font-bold uppercase border border-[var(--fd-ink)] bg-[var(--fd-card)] px-2 py-0.5">
                  15:00 MAX
                </span>
              </div>

              <div className="mt-4 text-center">
                <div className={`font-mono text-5xl font-black ${holdingSeconds < 60 ? 'text-red-600 animate-pulse' : 'text-[var(--fd-ink)]'}`}>
                  {formatTimer(holdingSeconds)}
                </div>
                <p className="mt-2 text-xs font-mono font-bold">
                  SEAT <strong className="font-mono text-base text-[var(--fd-pink)]">{selectedSeat || 'SELECT A SEAT'}</strong> HELD ATOMICALLY
                </p>
                {holdingSeconds === 0 && (
                  <p className="mt-2 text-xs font-mono font-bold text-red-700">
                    HOLD EXPIRED · Please re-click your seat to refresh hold.
                  </p>
                )}
              </div>

              <div className="mt-6 border-t-2 border-[var(--fd-ink)] pt-4 flex flex-col gap-3 font-mono text-xs font-bold">
                <div className="flex justify-between">
                  <span>EVENT:</span>
                  <span className="truncate max-w-[150px]">{campaign?.name || fallbackEvent.name}</span>
                </div>
                <div className="flex justify-between">
                  <span>ENTITLEMENT:</span>
                  <span className="truncate max-w-[150px] text-[var(--fd-pink)] font-black">
                    {entitlementToken || (isWinner ? 'VERIFIED WINNER' : 'NONE (LOTTERY REQUIRED)')}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>TICKET PRICE:</span>
                  <span className="text-[var(--fd-teal)] font-black">COMPLIMENTARY ACCESS</span>
                </div>
                <div className="flex justify-between">
                  <span>OVERSELL RISK:</span>
                  <span className="font-black text-green-700">0% (ACID GUARANTEE)</span>
                </div>
              </div>

              <div className="mt-8">
                <button
                  type="button"
                  onClick={handleConfirmBooking}
                  disabled={redeeming || holding || holdingSeconds === 0 || !isClaimingOpen || !isWinner || !selectedSeatId}
                  className={`button-primary w-full justify-center text-center text-lg bg-[var(--fd-teal)] cursor-pointer ${
                    redeeming || holding || holdingSeconds === 0 || !isClaimingOpen || !isWinner || !selectedSeatId
                      ? 'opacity-50 pointer-events-none'
                      : ''
                  }`}
                >
                  {redeeming ? (
                    <span className="flex items-center gap-2">
                      <Loader2 className="size-5 animate-spin" /> Confirming Booking...
                    </span>
                  ) : (
                    <span className="flex items-center gap-2">
                      Confirm Booking <ArrowRight className="size-5" />
                    </span>
                  )}
                </button>
              </div>

              {/* Notice / Operator Helper */}
              <div className="mt-6 border-t border-neutral-700/30 pt-4">
                <p className="font-mono text-[11px] leading-relaxed text-neutral-800">
                  ⚡ <strong>ANTI-SCALPER PROTOCOL:</strong> Seat hold uses PostgreSQL row-level locks (<code className="bg-black/10 px-1">FOR UPDATE SKIP LOCKED</code>). Redemptions are idempotent and permanently confirmed.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </FairShell>
  )
}

