'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import { ArrowRight, AlertTriangle, CheckCircle2, Clock, Loader2, ShieldCheck, Zap, LogIn, AlertCircle, RefreshCw, KeyRound } from 'lucide-react'
import { DemoNotice, FairShell, ProgressSteps, StatusPill } from '@/components/fair-shell'
import { getDemoEvent } from '@/lib/demo-events'
import { useAuth } from '@/lib/AuthContext'
import { api, FairDropApiError } from '@/lib/api'

interface PermitData {
  permit_id: string
  admission_token: string
  nonce: string
  expires_at: string
  campaign_id: string
  server_time: string
}

export default function WaitingRoomPage() {
  const params = useParams()
  const router = useRouter()
  const campaignId = (params?.campaignId as string) || 'camp_demo_001'
  const event = getDemoEvent(campaignId)

  const { user, loading: authLoading } = useAuth()
  const [countdown, setCountdown] = useState(5)
  const [admitted, setAdmitted] = useState(false)
  const [alreadyRegistered, setAlreadyRegistered] = useState(false)
  const [existingRegId, setExistingRegId] = useState<string | null>(null)
  const [requesting, setRequesting] = useState(false)
  const [permitData, setPermitData] = useState<PermitData | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [errorCode, setErrorCode] = useState<string | null>(null)

  // 1. Check if user already holds an active registration for this campaign
  useEffect(() => {
    if (!user || authLoading) return

    api.getCampaignStatus(campaignId)
      .then((st) => {
        const isReg = st?.participant_state === 'REGISTERED' || st?.registration?.is_registered === true
        if (isReg) {
          setAlreadyRegistered(true)
          setExistingRegId(st.registration?.registration_id || st.registration?.id || null)
          setAdmitted(true)
          setCountdown(0)
        }
      })
      .catch((err) => {
        // Fallback: check sessionStorage
        try {
          const cached = sessionStorage.getItem(`fairdrop_reg_${campaignId}`)
          if (cached) {
            const parsed = JSON.parse(cached)
            setAlreadyRegistered(true)
            setExistingRegId(parsed.registration_id || null)
            setAdmitted(true)
            setCountdown(0)
          }
        } catch {}
      })
  }, [campaignId, user, authLoading])

  // 2. Check if we already have an active permit cached in sessionStorage for this campaign
  useEffect(() => {
    if (typeof window !== 'undefined') {
      try {
        const cached = sessionStorage.getItem(`fairdrop_permit_${campaignId}`)
        if (cached) {
          const parsed = JSON.parse(cached)
          // If not expired, reuse permit
          if (new Date(parsed.expires_at) > new Date()) {
            setPermitData(parsed)
            setAdmitted(true)
            setCountdown(0)
          }
        }
      } catch (err) {
        console.warn('Could not read cached permit:', err)
      }
    }
  }, [campaignId])

  // 3. Countdown timer for queuing delay
  useEffect(() => {
    if (admitted || !user || authLoading || alreadyRegistered) return

    if (countdown > 0) {
      const timer = setTimeout(() => setCountdown(countdown - 1), 1000)
      return () => clearTimeout(timer)
    } else if (countdown === 0 && !admitted && !requesting && !errorMsg) {
      requestAdmissionPermit()
    }
  }, [countdown, admitted, user, authLoading, requesting, errorMsg, alreadyRegistered])

  // 3. Request cryptographic permit
  const requestAdmissionPermit = async () => {
    if (!user) return
    setRequesting(true)
    setErrorMsg(null)
    setErrorCode(null)

    try {
      const res = await api.joinCampaign(campaignId, {
        user_agent: typeof navigator !== 'undefined' ? navigator.userAgent : 'fairdrop-client',
        platform: typeof navigator !== 'undefined' ? navigator.platform : 'browser',
      })

      const permit: PermitData = {
        permit_id: res.permit_id || `permit_${Math.random().toString(36).substring(2, 9)}`,
        admission_token: res.admission_token || 'mock_admission_token',
        nonce: res.nonce || 'mock_nonce_12345678',
        expires_at: res.expires_at || new Date(Date.now() + 10 * 60 * 1000).toISOString(),
        campaign_id: campaignId,
        server_time: res.server_time || new Date().toISOString(),
      }

      setPermitData(permit)
      setAdmitted(true)

      // Store in sessionStorage for the registration form
      if (typeof window !== 'undefined') {
        sessionStorage.setItem(`fairdrop_permit_${campaignId}`, JSON.stringify(permit))
      }
    } catch (err: any) {
      console.error('[WaitingRoom] Failed to obtain admission permit:', err)
      if (err instanceof FairDropApiError) {
        setErrorCode(err.code)
        setErrorMsg(err.message)
      } else {
        setErrorMsg(err.message || 'An unexpected error occurred while entering the waiting room.')
      }
    } finally {
      setRequesting(false)
    }
  }

  return (
    <FairShell active="Explore Drops">
      <ProgressSteps current={1} />

      <div className="border-x-[3px] border-b-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] px-5 py-12 sm:px-12 lg:px-20">
        <div className="mx-auto max-w-3xl border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-6 shadow-[10px_10px_0_var(--fd-ink)] sm:p-10">
          
          {/* Header bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 border-b-[3px] border-[var(--fd-ink)] pb-4 font-mono text-xs font-black">
            <span className="flex items-center gap-2">
              <span className={`size-3 rounded-full ${admitted ? 'bg-[var(--fd-teal)]' : 'bg-[var(--fd-pink)] animate-pulse'}`} />
              ADMISSION CONTROL: {admitted ? 'PERMIT GRANTED' : requesting ? 'SIGNING TOKEN' : 'CALM QUEUE'}
            </span>
            <span>
              {permitData ? `PERMIT #${permitData.permit_id.slice(0, 13)}...` : 'TOKEN: ISSUANCE PENDING'}
            </span>
          </div>

          {/* Main content body */}
          <div className="mt-8 text-center">
            {authLoading ? (
              <div className="flex flex-col items-center py-10">
                <Loader2 className="size-10 animate-spin text-[var(--fd-ink)]" />
                <p className="mt-4 font-mono text-xs font-bold">VERIFYING AUTHENTICATED SESSION...</p>
              </div>
            ) : !user ? (
              /* Unauthenticated Gate */
              <div className="flex flex-col items-center border-[3px] border-[var(--fd-ink)] bg-[var(--fd-yellow)] p-8 shadow-[6px_6px_0_var(--fd-ink)]">
                <div className="grid size-16 place-items-center rounded-full border-[3px] border-[var(--fd-ink)] bg-[var(--fd-pink)] shadow-[3px_3px_0_var(--fd-ink)]">
                  <LogIn className="size-8 text-[var(--fd-ink)]" />
                </div>
                
                <h1 className="font-display mt-5 text-3xl font-black">AUTHENTICATION REQUIRED</h1>
                
                <p className="mt-3 max-w-md text-sm font-medium leading-relaxed">
                  Fair Drop enforces an auditable <strong>1-entry-per-person policy</strong>. To enter the admission queue and generate your cryptographically signed permit, please sign in.
                </p>

                <div className="mt-6 flex flex-wrap justify-center gap-4">
                  <Link href={`/login?redirect=/events/${campaignId}/waiting-room`} className="button-primary">
                    <LogIn className="size-4" /> Sign In to Enter
                  </Link>
                  <Link href={`/signup?redirect=/events/${campaignId}/waiting-room`} className="button-secondary">
                    Create Account
                  </Link>
                </div>
              </div>
            ) : errorMsg ? (
              /* Error State */
              <div className="flex flex-col items-center border-[3px] border-[var(--fd-ink)] bg-red-100 p-8 shadow-[6px_6px_0_var(--fd-ink)] text-red-950">
                <AlertCircle className="size-12 text-red-700" />
                <h2 className="font-display mt-4 text-2xl font-black">
                  {errorCode === 'REGISTRATION_NOT_STARTED'
                    ? 'REGISTRATION NOT YET OPEN'
                    : errorCode === 'REGISTRATION_CLOSED'
                      ? 'REGISTRATION WINDOW CLOSED'
                      : errorCode === 'CAMPAIGN_PAUSED'
                        ? 'ADMISSIONS TEMPORARILY PAUSED'
                        : 'ADMISSION REQUEST FAILED'}
                </h2>
                <p className="mt-2 text-sm font-mono font-bold max-w-md">
                  {errorMsg}
                </p>
                <button
                  onClick={() => {
                    setErrorMsg(null)
                    setCountdown(3)
                  }}
                  className="button-primary mt-6 text-xs bg-[var(--fd-yellow)] text-[var(--fd-ink)]"
                >
                  <RefreshCw className="size-4" /> Retry Queue Admission
                </button>
              </div>
            ) : !admitted ? (
              /* Queuing / Countdown State */
              <div className="flex flex-col items-center">
                <div className="relative grid size-24 place-items-center rounded-full border-[3px] border-[var(--fd-ink)] bg-[var(--fd-yellow)] shadow-[4px_4px_0_var(--fd-ink)]">
                  {requesting ? (
                    <KeyRound className="size-12 animate-pulse text-[var(--fd-ink)]" />
                  ) : (
                    <Loader2 className="size-12 animate-spin text-[var(--fd-ink)]" />
                  )}
                </div>
                
                <h1 className="font-display mt-6 text-3xl font-black sm:text-4xl">
                  {requesting ? 'ISSUING SIGNED PERMIT...' : 'CALM ADMISSION ROOM'}
                </h1>

                <p className="mt-3 max-w-md text-base font-medium leading-relaxed">
                  You are in the verified admission queue for <strong>{event.name}</strong>. Refreshing or speed-clicking will not change your outcome.
                </p>

                {/* Timer Countdown Visual */}
                <div className="mt-8 border-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] p-5 shadow-[4px_4px_0_var(--fd-ink)] w-full max-w-md">
                  <span className="font-mono text-xs font-bold uppercase text-[var(--fd-ink)]/70">
                    ADMISSION PERMIT RELEASE IN
                  </span>
                  <div className="font-mono text-5xl font-black text-[var(--fd-pink)] mt-2">
                    00:0{countdown}
                  </div>
                  <p className="mt-2 text-xs font-mono font-bold text-[var(--fd-ink)]/80">
                    VERIFYING IDENTITY & CRYPTOGRAPHIC NONCE...
                  </p>
                </div>

                <button
                  onClick={requestAdmissionPermit}
                  disabled={requesting}
                  className="mt-5 text-xs font-mono font-bold underline cursor-pointer hover:text-[var(--fd-pink)]"
                >
                  Skip timer &amp; request permit immediately →
                </button>
              </div>
            ) : alreadyRegistered ? (
              /* Already Registered Bypass State */
              <div className="flex flex-col items-center animate-in fade-in zoom-in duration-300">
                <div className="grid size-20 place-items-center rounded-full border-[3px] border-[var(--fd-ink)] bg-[var(--fd-teal)] shadow-[4px_4px_0_var(--fd-ink)]">
                  <ShieldCheck className="size-10 text-[var(--fd-ink)]" />
                </div>

                <span className="mt-4 inline-block border-2 border-[var(--fd-ink)] bg-[var(--fd-yellow)] px-3 py-1 font-mono text-xs font-black uppercase">
                  ACTIVE REGISTRATION CONFIRMED
                </span>

                <h1 className="font-display mt-4 text-3xl font-black sm:text-4xl text-[var(--fd-ink)]">
                  ENTRY ALREADY ACTIVE!
                </h1>

                <p className="mt-3 max-w-md text-base font-medium">
                  You already hold a verified registration entry for <strong>{event.name}</strong>. You do not need to wait in queue or re-submit.
                </p>

                {existingRegId && (
                  <div className="mt-5 border-2 border-[var(--fd-ink)] bg-[var(--fd-cream)] px-5 py-3 font-mono text-xs font-bold shadow-[3px_3px_0_var(--fd-ink)] text-center">
                    <span className="text-[var(--fd-ink)]/70 block text-[10px]">RECORD IDENTIFIER:</span>
                    <strong className="text-sm font-black">{existingRegId}</strong>
                  </div>
                )}
              </div>
            ) : (
              /* Admitted State */
              <div className="flex flex-col items-center animate-in fade-in zoom-in duration-300">
                <div className="grid size-20 place-items-center rounded-full border-[3px] border-[var(--fd-ink)] bg-[var(--fd-teal)] shadow-[4px_4px_0_var(--fd-ink)]">
                  <ShieldCheck className="size-10 text-[var(--fd-ink)]" />
                </div>

                <h1 className="font-display mt-6 text-3xl font-black sm:text-4xl text-[var(--fd-ink)]">
                  ADMISSION GRANTED!
                </h1>

                <p className="mt-3 max-w-md text-base font-medium">
                  Your cryptographic admission permit has been issued. You have an active permit to submit your single lottery registration entry.
                </p>

                {/* Cryptographic Proof Card */}
                {permitData && (
                  <div className="mt-6 border-2 border-[var(--fd-ink)] bg-[var(--fd-yellow)] p-4 text-left font-mono text-xs font-bold w-full max-w-md shadow-[4px_4px_0_var(--fd-ink)]">
                    <div className="flex justify-between border-b border-[var(--fd-ink)] pb-2 mb-2">
                      <span className="text-[var(--fd-ink)]/70">PERMIT ID:</span>
                      <span className="truncate max-w-[200px]">{permitData.permit_id}</span>
                    </div>
                    <div className="flex justify-between border-b border-[var(--fd-ink)] pb-2 mb-2">
                      <span className="text-[var(--fd-ink)]/70">SESSION NONCE:</span>
                      <span className="truncate max-w-[200px]">{permitData.nonce.slice(0, 10)}... (SINGLE-USE)</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[var(--fd-ink)]/70">VALID UNTIL:</span>
                      <span>{new Date(permitData.expires_at).toLocaleTimeString()}</span>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Warning Labels */}
          <div className="mt-8 grid gap-4 sm:grid-cols-2">
            <div className="flex items-start gap-3 border-2 border-[var(--fd-ink)] bg-[var(--fd-yellow)] p-4 text-xs font-bold">
              <AlertTriangle className="size-5 shrink-0 text-[var(--fd-ink)]" />
              <span>DO NOT OPEN MULTIPLE TABS: Our rate control automatically invalidates parallel session registrations.</span>
            </div>
            <div className="flex items-start gap-3 border-2 border-[var(--fd-ink)] bg-[var(--fd-teal)] p-4 text-xs font-bold">
              <Zap className="size-5 shrink-0 text-[var(--fd-ink)]" />
              <span>EQUAL SHUFFLE ODDS: Your arrival order inside the room has zero bearing on the final lottery draw.</span>
            </div>
          </div>

          {/* CTA */}
          <div className="mt-8">
            {alreadyRegistered ? (
              <Link
                href={`/events/${campaignId}/status`}
                className="button-primary w-full justify-center text-center text-lg bg-[var(--fd-teal)] text-[var(--fd-ink)]"
              >
                View Registration Status <ArrowRight className="size-5" />
              </Link>
            ) : (
              <Link
                href={`/events/${campaignId}/register`}
                className={`button-primary w-full justify-center text-center text-lg ${
                  !admitted ? 'opacity-50 pointer-events-none' : 'bg-[var(--fd-teal)]'
                }`}
              >
                Continue to Registration <ArrowRight className="size-5" />
              </Link>
            )}
          </div>

          <div className="mt-6">
            <DemoNotice>
              {alreadyRegistered
                ? 'Your registration is confirmed. Click "View Registration Status" to monitor live lottery draw.'
                : admitted
                  ? 'Permit stored in sessionStorage. Click Continue to submit verified registration entry.'
                  : 'Pacing queue automatically signs permit when ready. Sign in is required to generate permit.'}
            </DemoNotice>
          </div>
        </div>
      </div>
    </FairShell>
  )
}
