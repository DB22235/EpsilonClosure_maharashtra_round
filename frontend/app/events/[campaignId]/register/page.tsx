'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useParams, useRouter } from 'next/navigation'
import { ArrowRight, CheckSquare, ShieldCheck, UserCheck, AlertCircle, Loader2, KeyRound } from 'lucide-react'
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
}

export default function RegisterPage() {
  const params = useParams()
  const router = useRouter()
  const campaignId = (params?.campaignId as string) || 'camp_demo_001'
  const event = getDemoEvent(campaignId)

  const { user } = useAuth()
  const [permit, setPermit] = useState<PermitData | null>(null)
  const [idempKey, setIdempKey] = useState<string>('')
  const [rule1, setRule1] = useState(true)
  const [rule2, setRule2] = useState(true)
  const [rule3, setRule3] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  // 1. Check if participant is already registered for this campaign
  useEffect(() => {
    if (!user) return

    api.getCampaignStatus(campaignId)
      .then((st) => {
        const isReg = st?.participant_state === 'REGISTERED' || st?.registration?.is_registered === true
        if (isReg) {
          if (st.registration) {
            sessionStorage.setItem(`fairdrop_reg_${campaignId}`, JSON.stringify(st.registration))
          }
          router.replace(`/events/${campaignId}/status`)
        }
      })
      .catch((err) => {
        console.warn('[Register] Status check notice:', err)
      })
  }, [campaignId, user, router])

  // 2. Retrieve permit and stable idempotency key from sessionStorage
  useEffect(() => {
    if (typeof window !== 'undefined') {
      try {
        const storedPermit = sessionStorage.getItem(`fairdrop_permit_${campaignId}`)
        if (storedPermit) {
          setPermit(JSON.parse(storedPermit))
        }

        let key = sessionStorage.getItem(`fairdrop_idemp_${campaignId}`)
        if (!key) {
          key = `reg_${campaignId.slice(0, 8)}_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`
          sessionStorage.setItem(`fairdrop_idemp_${campaignId}`, key)
        }
        setIdempKey(key)
      } catch (err) {
        console.warn('Failed to load session storage for registration:', err)
      }
    }
  }, [campaignId])

  const isFormValid = rule1 && rule2 && rule3 && !submitting

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!isFormValid) return

    setSubmitting(true)
    setErrorMsg(null)

    const token = permit?.admission_token || 'mock_admission_token'
    const nonce = permit?.nonce || 'mock_nonce_12345678'
    const key = idempKey || `reg_${campaignId}_${Date.now()}`

    try {
      const response = await api.register(campaignId, token, nonce, key, {
        user_agent: typeof navigator !== 'undefined' ? navigator.userAgent : 'fairdrop-client',
        platform: typeof navigator !== 'undefined' ? navigator.platform : 'browser',
      })

      // Cache registration confirmation for the status page
      if (typeof window !== 'undefined') {
        sessionStorage.setItem(`fairdrop_reg_${campaignId}`, JSON.stringify(response))
      }

      router.push(`/events/${campaignId}/status`)
    } catch (err: any) {
      console.error('[Register] Submission status:', err)
      if (err instanceof FairDropApiError) {
        if (err.code === 'DUPLICATE_ENTRY' || err.code === 'ALREADY_REGISTERED') {
          // If already registered, store details and seamlessly redirect to status page
          if (err.details?.registration_id && typeof window !== 'undefined') {
            sessionStorage.setItem(
              `fairdrop_reg_${campaignId}`,
              JSON.stringify({ registration_id: err.details.registration_id })
            )
          }
          router.push(`/events/${campaignId}/status`)
          return
        }
        setErrorMsg(`[${err.code}] ${err.message}`)
      } else {
        setErrorMsg(err.message || 'Registration failed. Please check your connection and try again.')
      }
      setSubmitting(false)
    }
  }

  const participantName = user?.email
    ? user.email.split('@')[0].toUpperCase()
    : 'UNAUTHENTICATED GUEST'
  const participantEmail = user?.email || 'Not signed in — please log in first'

  return (
    <FairShell active="Explore Drops">
      <ProgressSteps current={2} />

      <div className="border-x-[3px] border-b-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] px-5 py-12 sm:px-12 lg:px-20">
        {!permit && (
          <div className="mb-8 border-[3px] border-[var(--fd-ink)] bg-[var(--fd-yellow)] p-4 shadow-[4px_4px_0_var(--fd-ink)] flex flex-wrap items-center justify-between gap-4 font-mono text-xs font-bold">
            <div className="flex items-center gap-2">
              <KeyRound className="size-5 shrink-0 text-[var(--fd-pink)]" />
              <span>No admission permit detected in this browser session. Waiting room admission issues your cryptographic permit.</span>
            </div>
            <Link href={`/events/${campaignId}/waiting-room`} className="button-primary text-xs py-1.5 px-3">
              Enter Waiting Room →
            </Link>
          </div>
        )}

        {errorMsg && (
          <div className="mb-8 border-[3px] border-red-600 bg-red-100 p-4 shadow-[4px_4px_0_var(--fd-ink)] flex items-center gap-3 text-red-950 text-xs font-mono font-bold">
            <AlertCircle className="size-5 shrink-0 text-red-600" />
            <span>{errorMsg}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="grid gap-10 lg:grid-cols-[1fr_1fr]">
          {/* Identity Summary Card */}
          <div className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-6 shadow-[8px_8px_0_var(--fd-ink)]">
            <div className="flex items-center gap-3 border-b-[3px] border-[var(--fd-ink)] pb-4">
              <span className="grid size-10 place-items-center rounded-full border-[3px] border-[var(--fd-ink)] bg-[var(--fd-teal)]">
                <UserCheck className="size-5" />
              </span>
              <div>
                <h2 className="font-display text-2xl font-black">IDENTITY CREDENTIALS</h2>
                <p className="text-xs font-mono font-bold text-[var(--fd-ink)]/70">
                  {user ? 'AUTHENTICATED SUPABASE PARTICIPANT' : 'VERIFIED DEMO USER'}
                </p>
              </div>
            </div>

            <div className="mt-6 flex flex-col gap-4 font-mono text-xs font-bold">
              <div className="border-2 border-[var(--fd-ink)] bg-[var(--fd-cream)] p-4">
                <span className="text-[var(--fd-ink)]/70 uppercase">PARTICIPANT NAME</span>
                <div className="mt-1 text-sm font-black truncate">{participantName}</div>
              </div>

              <div className="border-2 border-[var(--fd-ink)] bg-[var(--fd-cream)] p-4">
                <span className="text-[var(--fd-ink)]/70 uppercase">VERIFIED EMAIL</span>
                <div className="mt-1 text-sm font-black truncate">{participantEmail}</div>
              </div>

              <div className="border-2 border-[var(--fd-ink)] bg-[var(--fd-cream)] p-4">
                <span className="text-[var(--fd-ink)]/70 uppercase">STABLE IDEMPOTENCY KEY</span>
                <div className="mt-1 text-xs font-mono font-black break-all text-[var(--fd-pink)]">
                  {idempKey || 'GENERATING_KEY...'}
                </div>
              </div>

              {permit ? (
                <div className="border-2 border-[var(--fd-ink)] bg-[var(--fd-teal)] p-3 text-center">
                  ✓ PERMIT #{permit.permit_id.slice(0, 12)}... VERIFIED
                </div>
              ) : (
                <div className="border-2 border-[var(--fd-ink)] bg-[var(--fd-yellow)] p-3 text-center">
                  DEMO PASS-THROUGH MODE ACTIVE
                </div>
              )}
            </div>
          </div>

          {/* Policy Rules Sheet & Checkboxes */}
          <div className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-6 shadow-[8px_8px_0_var(--fd-ink)]">
            <div className="flex items-center justify-between border-b-[3px] border-[var(--fd-ink)] pb-4">
              <h2 className="font-display text-2xl font-black">CAMPAIGN AGREEMENT</h2>
              <ShieldCheck className="size-6 text-[var(--fd-pink)]" />
            </div>

            <p className="mt-4 text-sm font-medium leading-relaxed">
              Before submitting your single entry for <strong>{event.name}</strong>, please confirm adherence to campaign terms:
            </p>

            <div className="mt-6 flex flex-col gap-4">
              <label className="flex items-start gap-3 border-2 border-[var(--fd-ink)] bg-[var(--fd-cream)] p-4 text-xs font-bold cursor-pointer">
                <input
                  type="checkbox"
                  checked={rule1}
                  onChange={(e) => setRule1(e.target.checked)}
                  className="mt-0.5 size-4 accent-[var(--fd-pink)] shrink-0"
                />
                <span>I confirm this is my sole account and registration entry for this campaign.</span>
              </label>

              <label className="flex items-start gap-3 border-2 border-[var(--fd-ink)] bg-[var(--fd-cream)] p-4 text-xs font-bold cursor-pointer">
                <input
                  type="checkbox"
                  checked={rule2}
                  onChange={(e) => setRule2(e.target.checked)}
                  className="mt-0.5 size-4 accent-[var(--fd-pink)] shrink-0"
                />
                <span>I understand the lottery selection algorithm uses deterministic uniform sampling after cutoff.</span>
              </label>

              <label className="flex items-start gap-3 border-2 border-[var(--fd-ink)] bg-[var(--fd-cream)] p-4 text-xs font-bold cursor-pointer">
                <input
                  type="checkbox"
                  checked={rule3}
                  onChange={(e) => setRule3(e.target.checked)}
                  className="mt-0.5 size-4 accent-[var(--fd-pink)] shrink-0"
                />
                <span>I agree to redeem my seat within the 15-minute hold window if selected as a winner.</span>
              </label>
            </div>

            <div className="mt-8">
              <button
                type="submit"
                disabled={!isFormValid}
                className={`button-primary w-full justify-center text-center text-lg ${
                  !isFormValid ? 'opacity-50 pointer-events-none' : 'bg-[var(--fd-pink)]'
                }`}
              >
                {submitting ? (
                  <span className="flex items-center gap-2">
                    <Loader2 className="size-5 animate-spin" /> Submitting Registration...
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    Submit Registration <ArrowRight className="size-5" />
                  </span>
                )}
              </button>
            </div>

            <div className="mt-6">
              <DemoNotice>
                Submitting creates your immutable registration record and advances to live status tracking.
              </DemoNotice>
            </div>
          </div>
        </form>
      </div>
    </FairShell>
  )
}
