'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import { ArrowRight, Check, ExternalLink, Sparkles, Trophy, ShieldCheck, Clock, AlertCircle, RefreshCw, Hourglass } from 'lucide-react'
import { DemoNotice, FairShell, ProgressSteps, StatusPill } from '@/components/fair-shell'
import { getDemoEvent } from '@/lib/demo-events'
import { api, FairDropApiError } from '@/lib/api'
import { useAuth } from '@/lib/AuthContext'

interface ResultData {
  status: string
  is_winner: boolean
  rank?: number | null
  entitlement_id?: string | null
  hold_expires_at?: string | null
  redemption_deadline?: string | null
}

export default function ResultPage() {
  const params = useParams()
  const campaignId = (params?.campaignId as string) || 'camp_demo_001'
  const event = getDemoEvent(campaignId)
  const { user } = useAuth()

  const [result, setResult] = useState<ResultData | null>(null)
  const [loading, setLoading] = useState(true)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const fetchResult = async () => {
    setLoading(true)
    setErrorMsg(null)
    try {
      const data = await api.getResult(campaignId)
      if (data) {
        setResult(data)
      }
    } catch (err: any) {
      console.warn('[ResultPage] Failed to fetch draw result:', err)
      if (err instanceof FairDropApiError) {
        setErrorMsg(err.message)
      } else {
        setErrorMsg(err.message || 'Could not load draw result.')
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchResult()
  }, [campaignId])

  const statusStr = result?.status?.toUpperCase() || ''
  const isWinner = Boolean(result && (result.is_winner || statusStr === 'WON' || statusStr === 'SELECTED'))
  const isWaitlist = Boolean(result && (statusStr === 'WAITLISTED' || statusStr === 'STANDBY'))
  const isPending = Boolean(result && (statusStr === 'PENDING_DRAW' || statusStr === 'REGISTERED'))
  const isNotRegistered = Boolean(result && statusStr === 'NOT_REGISTERED')
  const isNotDrawn = !isWinner && !isWaitlist && !isPending && !isNotRegistered

  return (
    <FairShell active="Explore Drops">
      <ProgressSteps current={4} />

      <div className="border-x-[3px] border-b-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] px-5 py-12 sm:px-12 lg:px-20">
        <div className="mx-auto max-w-4xl border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-6 shadow-[10px_10px_0_var(--fd-ink)] sm:p-10">
          
          {errorMsg && (
            <div className="mb-6 border-2 border-[var(--fd-ink)] bg-amber-100 p-3 text-xs font-mono font-bold text-amber-950 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <AlertCircle className="size-4 shrink-0 text-amber-700" />
                <span>{errorMsg}</span>
              </div>
              <button onClick={fetchResult} className="underline text-xs">
                Retry
              </button>
            </div>
          )}

          {isWinner ? (
            /* Winner Banner */
            <div className="relative overflow-hidden border-[3px] border-[var(--fd-ink)] bg-[var(--fd-yellow)] p-8 text-center shadow-[6px_6px_0_var(--fd-ink)]">
              <div className="absolute top-2 left-2 flex gap-2">
                <Sparkles className="size-6 text-[var(--fd-pink)] animate-bounce" />
                <Sparkles className="size-5 text-[var(--fd-teal)]" />
              </div>
              <div className="absolute top-2 right-2 flex gap-2">
                <Sparkles className="size-6 text-[var(--fd-teal)]" />
                <Sparkles className="size-5 text-[var(--fd-pink)] animate-bounce" />
              </div>

              <div className="mx-auto grid size-20 place-items-center rounded-full border-[3px] border-[var(--fd-ink)] bg-[var(--fd-pink)] shadow-[4px_4px_0_var(--fd-ink)]">
                <Trophy className="size-10 text-[var(--fd-ink)]" />
              </div>

              <span className="mt-4 inline-block border-2 border-[var(--fd-ink)] bg-[var(--fd-card)] px-3 py-1 font-mono text-xs font-black uppercase">
                LOTTERY DRAW RESULT: SELECTED
              </span>

              <h1 className="font-display mt-3 text-4xl font-black sm:text-6xl text-[var(--fd-ink)]">
                YOU ARE A WINNER!
              </h1>

              <p className="mt-3 max-w-lg mx-auto text-base font-bold">
                Congratulations! Your entry was selected in the uniform lottery draw for <strong>{event.name}</strong>.
              </p>
            </div>
          ) : isWaitlist ? (
            /* Waitlisted Banner */
            <div className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-yellow)] p-8 text-center shadow-[6px_6px_0_var(--fd-ink)]">
              <div className="mx-auto grid size-20 place-items-center rounded-full border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] shadow-[4px_4px_0_var(--fd-ink)]">
                <Hourglass className="size-10 text-[var(--fd-ink)] animate-pulse" />
              </div>

              <span className="mt-4 inline-block border-2 border-[var(--fd-ink)] bg-[var(--fd-card)] px-3 py-1 font-mono text-xs font-black uppercase">
                LOTTERY DRAW RESULT: STANDBY QUEUE
              </span>

              <h1 className="font-display mt-3 text-3xl font-black sm:text-5xl text-[var(--fd-ink)]">
                STANDBY WAITLIST
              </h1>

              <p className="mt-3 max-w-lg mx-auto text-base font-medium">
                You are in position <strong>#{result?.rank || 1}</strong> on the standby queue. If selected winners forfeit their 15-minute hold window, seats are automatically offered to standby participants in strict order.
              </p>
            </div>
          ) : isPending ? (
            /* Pending Draw Banner */
            <div className="border-[3px] border-[var(--fd-ink)] bg-blue-50 p-8 text-center shadow-[6px_6px_0_var(--fd-ink)]">
              <div className="mx-auto grid size-20 place-items-center rounded-full border-[3px] border-[var(--fd-ink)] bg-[var(--fd-teal)] shadow-[4px_4px_0_var(--fd-ink)]">
                <Clock className="size-10 text-[var(--fd-ink)] animate-pulse" />
              </div>

              <span className="mt-4 inline-block border-2 border-[var(--fd-ink)] bg-[var(--fd-card)] px-3 py-1 font-mono text-xs font-black uppercase text-blue-900">
                REGISTRATION CONFIRMED
              </span>

              <h1 className="font-display mt-3 text-3xl font-black sm:text-4xl text-[var(--fd-ink)]">
                AWAITING LOTTERY DRAW
              </h1>

              <p className="mt-3 max-w-lg mx-auto text-sm font-medium text-neutral-700">
                Your entry for <strong>{event.name}</strong> is confirmed. The organizer has not yet executed the uniform lottery draw. Check back once registration concludes!
              </p>
            </div>
          ) : isNotRegistered ? (
            /* Not Registered Banner */
            <div className="border-[3px] border-[var(--fd-ink)] bg-amber-50 p-8 text-center shadow-[6px_6px_0_var(--fd-ink)]">
              <div className="mx-auto grid size-20 place-items-center rounded-full border-[3px] border-[var(--fd-ink)] bg-[var(--fd-yellow)] shadow-[4px_4px_0_var(--fd-ink)]">
                <AlertCircle className="size-10 text-[var(--fd-ink)]" />
              </div>

              <span className="mt-4 inline-block border-2 border-[var(--fd-ink)] bg-[var(--fd-card)] px-3 py-1 font-mono text-xs font-black uppercase text-amber-900">
                NO ENTRY FOR THIS ACCOUNT
              </span>

              <h1 className="font-display mt-3 text-3xl font-black sm:text-4xl text-[var(--fd-ink)]">
                NOT REGISTERED
              </h1>

              <p className="mt-3 max-w-lg mx-auto text-sm font-medium text-neutral-700">
                The currently signed-in account{' '}
                <strong className="font-mono text-xs bg-amber-200 px-1 py-0.5 border border-amber-400">
                  {user?.email || 'this session'}
                </strong>{' '}
                is not registered as a participant for <strong>{event.name}</strong>.
              </p>

              <div className="mt-6 flex flex-col sm:flex-row items-center justify-center gap-3">
                <Link
                  href="/login"
                  className="button-primary bg-[var(--fd-yellow)] text-xs font-mono font-bold"
                >
                  Switch Account / Sign In
                </Link>
                <Link
                  href={`/events/${campaignId}/register`}
                  className="button-secondary text-xs font-mono font-bold"
                >
                  View Event Registration
                </Link>
              </div>
            </div>
          ) : (
            /* Not Selected Banner (actually participated and ranked outside capacity) */
            <div className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] p-8 text-center shadow-[6px_6px_0_var(--fd-ink)]">
              <span className="inline-block border-2 border-[var(--fd-ink)] bg-[var(--fd-card)] px-3 py-1 font-mono text-xs font-black uppercase">
                LOTTERY DRAW RESULT: NOT DRAWN
              </span>

              <h1 className="font-display mt-3 text-3xl font-black sm:text-4xl text-[var(--fd-ink)]">
                DRAW COMPLETED
              </h1>

              <p className="mt-3 max-w-lg mx-auto text-sm font-medium">
                Your entry was not selected in this uniform lottery round for <strong>{event.name}</strong>. You can inspect the public verifiable cryptographic audit trail to verify that all participants had identical odds.
              </p>
            </div>
          )}

          {/* Winner Claim Instructions */}
          {isWinner && (
            <div className="mt-8 border-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] p-6 shadow-[6px_6px_0_var(--fd-ink)]">
              <h2 className="font-display text-2xl font-black mb-4">CLAIM INSTRUCTIONS &amp; DEADLINE</h2>

              <div className="grid gap-4 sm:grid-cols-3 font-mono text-xs font-bold mb-6">
                <div className="border-2 border-[var(--fd-ink)] bg-[var(--fd-card)] p-4">
                  <span className="text-[var(--fd-ink)]/70 uppercase">ENTITLEMENT TOKEN</span>
                  <div className="mt-1 text-sm font-black text-[var(--fd-pink)] truncate">
                    {result?.entitlement_id || 'ENTITLEMENT_ISSUED'}
                  </div>
                </div>
                <div className="border-2 border-[var(--fd-ink)] bg-[var(--fd-card)] p-4">
                  <span className="text-[var(--fd-ink)]/70 uppercase">DRAW RANK</span>
                  <div className="mt-1 text-sm font-black text-[var(--fd-teal)]">
                    POSITION #{result?.rank ?? '1'}
                  </div>
                </div>
                <div className="border-2 border-[var(--fd-ink)] bg-[var(--fd-card)] p-4">
                  <span className="text-[var(--fd-ink)]/70 uppercase">ALLOCATION TYPE</span>
                  <div className="mt-1 text-sm font-black">SINGLE TICKET HOLD</div>
                </div>
              </div>

              <div className="flex flex-col gap-3 text-sm font-medium">
                <div className="flex items-center gap-3">
                  <span className="grid size-6 place-items-center border-2 border-[var(--fd-ink)] bg-[var(--fd-teal)] font-black text-xs">1</span>
                  <span>Select your seat from the interactive floor map on the claim page.</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="grid size-6 place-items-center border-2 border-[var(--fd-ink)] bg-[var(--fd-teal)] font-black text-xs">2</span>
                  <span>Confirm your single-use entitlement token before timer expires.</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="grid size-6 place-items-center border-2 border-[var(--fd-ink)] bg-[var(--fd-teal)] font-black text-xs">3</span>
                  <span>Download your signed ticket receipt with security audit stamp.</span>
                </div>
              </div>
            </div>
          )}

          {/* Action CTAs */}
          <div className="mt-8 flex flex-col gap-4 sm:flex-row">
            {isWinner && (
              <Link
                href={`/events/${campaignId}/claim`}
                className="button-primary flex-1 justify-center text-center text-lg bg-[var(--fd-pink)]"
              >
                Claim Your Seat <ArrowRight className="size-5" />
              </Link>
            )}

            <Link
              href={`/events/${campaignId}/audit`}
              className="button-secondary justify-center text-center text-sm flex items-center gap-2"
            >
              <ShieldCheck className="size-4" /> View Public Audit <ExternalLink className="size-4" />
            </Link>
          </div>

          <div className="mt-6">
            <DemoNotice>
              {isWinner
                ? 'Selected winner state. Click "Claim Your Seat" to choose your seat on the interactive floor map.'
                : 'Draw outcomes are cryptographically verifiable on the Public Audit page.'}
            </DemoNotice>
          </div>
        </div>
      </div>
    </FairShell>
  )
}
