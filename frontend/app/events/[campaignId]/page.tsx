'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import { ArrowRight, Calendar, CheckCircle2, MapPin, Shield, Ticket, Users, RefreshCw, AlertCircle } from 'lucide-react'
import { DemoNotice, FairShell, PageIntro, ProgressSteps, StatusPill } from '@/components/fair-shell'
import { getDemoEvent, DemoEvent } from '@/lib/demo-events'
import { api, isUuid, FairDropApiError } from '@/lib/api'
import { useAuth } from '@/lib/AuthContext'

export default function EventDetailPage() {
  const params = useParams()
  const campaignId = (params?.campaignId as string) || 'camp_demo_001'
  const fallbackEvent = getDemoEvent(campaignId)

  const { user } = useAuth()
  const [eventData, setEventData] = useState<DemoEvent>(fallbackEvent)
  const [userRegistration, setUserRegistration] = useState<{
    isRegistered: boolean
    registrationId?: string
    status?: string
  } | null>(null)
  const [loading, setLoading] = useState(false)
  const [isLive, setIsLive] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  useEffect(() => {
    if (!campaignId) return

    if (isUuid(campaignId)) {
      setLoading(true)
      setErrorMsg(null)
      api.getCampaign(campaignId)
        .then((c) => {
          const dateStr = c.event_start
            ? new Date(c.event_start).toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' }).toUpperCase()
            : c.registration_start
              ? new Date(c.registration_start).toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' }).toUpperCase()
              : 'UPCOMING'

          const regStart = c.registration_start
            ? new Date(c.registration_start).toLocaleString('en-US', { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit' })
            : 'TBD'
          const regEnd = c.registration_end
            ? new Date(c.registration_end).toLocaleString('en-US', { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit' })
            : 'TBD'

          setEventData({
            id: c.id,
            category: c.allocation_method ? 'LOTTERY DROP' : 'OPEN DROP',
            name: c.name,
            venue: c.venue || 'Global Virtual Arena',
            date: dateStr,
            seats: c.capacity || 500,
            color: 'var(--fd-yellow)',
            status: c.status ? c.status.replace(/_/g, ' ') : 'OPEN',
            description: c.description || 'Fair uniform lottery allocation with zero speed bias.',
            policyVersion: c.policy_version || 'v1.0',
            rosterHash: c.policy_hash || 'SHA-256 Verified at window close',
            randomnessSeed: 'NIST Beacon / drand entropy',
            registeredCount: c.registration_counts?.total ?? 0,
            eligibleCount: c.registration_counts?.accepted ?? 0,
            duplicateCount: c.registration_counts?.duplicate ?? 0,
            winnersCount: c.capacity || 500,
            registrationStart: regStart,
            registrationEnd: regEnd,
          })
          setIsLive(true)
        })
        .catch((err: any) => {
          console.warn('[EventDetail] Failed to load live campaign, using demo fallback:', err)
          if (err instanceof FairDropApiError) {
            setErrorMsg(`[${err.code}] ${err.message}`)
          }
          setEventData(fallbackEvent)
        })
        .finally(() => {
          setLoading(false)
        })
    } else {
      setEventData(fallbackEvent)
    }

    // Check if authenticated user is already registered for this campaign
    if (user && isUuid(campaignId)) {
      api.getCampaignStatus(campaignId)
        .then((st) => {
          const isReg = st?.participant_state === 'REGISTERED' || st?.registration?.is_registered === true
          if (isReg) {
            setUserRegistration({
              isRegistered: true,
              registrationId: st.registration?.registration_id || st.registration?.id,
              status: st.registration?.status || 'REGISTERED',
            })
          } else {
            setUserRegistration({ isRegistered: false })
          }
        })
        .catch(() => {
          try {
            const cached = sessionStorage.getItem(`fairdrop_reg_${campaignId}`)
            if (cached) {
              const parsed = JSON.parse(cached)
              setUserRegistration({ isRegistered: true, registrationId: parsed.registration_id })
            } else {
              setUserRegistration({ isRegistered: false })
            }
          } catch {
            setUserRegistration({ isRegistered: false })
          }
        })
    } else {
      setUserRegistration(null)
    }
  }, [campaignId, user])

  return (
    <FairShell active="Explore Drops">
      <ProgressSteps current={0} />

      <PageIntro
        eyebrow={isLive ? `Live Backend Drop · ID: ${eventData.id.slice(0, 8)}...` : `Campaign #${eventData.id}`}
        title={
          <>
            {eventData.name.toUpperCase()}<br />
            <span className="text-[var(--fd-pink)]">{eventData.seats} SEATS ALLOCATION</span>
          </>
        }
        copy={eventData.description}
      />

      <section className="border-x-[3px] border-b-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] px-5 py-12 sm:px-12 lg:px-20">
        {errorMsg && (
          <div className="mb-6 border-2 border-[var(--fd-ink)] bg-amber-100 p-4 font-mono text-xs font-bold text-amber-900 shadow-[3px_3px_0_var(--fd-ink)] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertCircle className="size-4 shrink-0" />
              <span>{errorMsg} (Using preloaded parameters)</span>
            </div>
            <StatusPill>OFFLINE PREVIEW</StatusPill>
          </div>
        )}

        <div className="grid gap-10 lg:grid-cols-[1.2fr_0.8fr]">
          {/* Main Info */}
          <div className="flex flex-col gap-8">
            <div className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] p-6 shadow-[6px_6px_0_var(--fd-ink)]">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-display text-2xl font-black">LOTTERY PARAMETERS & RULES</h2>
                <StatusPill>{eventData.status}</StatusPill>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="border-2 border-[var(--fd-ink)] bg-[var(--fd-card)] p-4">
                  <span className="metric-label">Allocation Algorithm</span>
                  <strong className="font-mono text-lg font-black text-[var(--fd-pink)]">UNIFORM SHUFFLE</strong>
                </div>
                <div className="border-2 border-[var(--fd-ink)] bg-[var(--fd-card)] p-4">
                  <span className="metric-label">Policy Version</span>
                  <strong className="font-mono text-lg font-black">{eventData.policyVersion}</strong>
                </div>
                <div className="border-2 border-[var(--fd-ink)] bg-[var(--fd-card)] p-4">
                  <span className="metric-label">Capacity Limit</span>
                  <strong className="font-mono text-lg font-black">{eventData.seats} SEATS (0 OVERSELL)</strong>
                </div>
                <div className="border-2 border-[var(--fd-ink)] bg-[var(--fd-card)] p-4">
                  <span className="metric-label">Registration Window</span>
                  <strong className="font-mono text-xs font-black">{eventData.registrationStart} → {eventData.registrationEnd}</strong>
                </div>
              </div>
            </div>

            {/* Policy Rules */}
            <div className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-6 shadow-[6px_6px_0_var(--fd-ink)]">
              <h3 className="font-display text-xl font-black mb-3">PUBLIC FAIRNESS COMMITMENTS</h3>
              <ul className="flex flex-col gap-3 font-medium text-sm">
                <li className="flex items-start gap-3 border-b pb-3 border-[var(--fd-ink)]">
                  <CheckCircle2 className="size-5 shrink-0 text-[var(--fd-teal)] mt-0.5" />
                  <span><strong>One Entry Per Person:</strong> Duplicate entries created by automated software or multiple browser tabs are stripped prior to shuffling.</span>
                </li>
                <li className="flex items-start gap-3 border-b pb-3 border-[var(--fd-ink)]">
                  <CheckCircle2 className="size-5 shrink-0 text-[var(--fd-teal)] mt-0.5" />
                  <span><strong>Speed Does Not Matter:</strong> Submitting on the first second grants the exact same probability as submitting minutes before cutoff.</span>
                </li>
                <li className="flex items-start gap-3">
                  <CheckCircle2 className="size-5 shrink-0 text-[var(--fd-teal)] mt-0.5" />
                  <span><strong>Public Audit Trail:</strong> A verifiable hash of the eligible roster and random seed is published after drawing.</span>
                </li>
              </ul>
            </div>
          </div>

          {/* Sticky Details Box */}
          <div className="flex flex-col gap-6">
            <div className="sticky top-6 border-[3px] border-[var(--fd-ink)] bg-[var(--fd-yellow)] p-6 shadow-[8px_8px_0_var(--fd-ink)]">
              <div className="flex items-center justify-between border-b-[3px] border-[var(--fd-ink)] pb-4">
                <span className="font-mono text-xs font-bold uppercase">EVENT DETAILS</span>
                <Ticket className="size-6" />
              </div>

              <div className="mt-6 flex flex-col gap-4 text-sm font-bold">
                <div className="flex items-center gap-3">
                  <MapPin className="size-5 shrink-0" />
                  <span>{eventData.venue}</span>
                </div>
                <div className="flex items-center gap-3">
                  <Calendar className="size-5 shrink-0" />
                  <span>{eventData.date}</span>
                </div>
                <div className="flex items-center gap-3">
                  <Users className="size-5 shrink-0" />
                  <span>{eventData.registeredCount.toLocaleString()} Participants Registered</span>
                </div>
                <div className="flex items-center gap-3">
                  <Shield className="size-5 shrink-0" />
                  <span>Audited Roster Hash Active</span>
                </div>
              </div>

              <div className="mt-8">
                {userRegistration?.isRegistered ? (
                  <div className="flex flex-col gap-3">
                    <div className="border-2 border-[var(--fd-ink)] bg-[var(--fd-teal)] p-3 text-xs font-mono font-black flex items-center justify-between shadow-[3px_3px_0_var(--fd-ink)]">
                      <span className="flex items-center gap-1.5">
                        <CheckCircle2 className="size-4" /> ENTRY CONFIRMED
                      </span>
                      {userRegistration.registrationId && (
                        <span className="text-[10px] opacity-80 truncate max-w-[130px]">
                          #{userRegistration.registrationId.slice(0, 8)}...
                        </span>
                      )}
                    </div>

                    {eventData.status === 'DRAWN' || eventData.status === 'CLAIMING' || eventData.status === 'CLOSED' ? (
                      <Link
                        href={`/events/${campaignId}/result`}
                        className="button-primary w-full justify-center text-center text-base bg-[var(--fd-pink)] shadow-[4px_4px_0_var(--fd-ink)]"
                      >
                        View Draw Result <ArrowRight className="size-5" />
                      </Link>
                    ) : (
                      <Link
                        href={`/events/${campaignId}/status`}
                        className="button-primary w-full justify-center text-center text-base bg-[var(--fd-teal)] text-[var(--fd-ink)] shadow-[4px_4px_0_var(--fd-ink)]"
                      >
                        View Registration Status <ArrowRight className="size-5" />
                      </Link>
                    )}
                  </div>
                ) : (
                  <Link
                    href={`/events/${campaignId}/waiting-room`}
                    className="button-primary w-full justify-center text-center text-lg bg-[var(--fd-pink)]"
                  >
                    Join Fair Drop <ArrowRight className="size-5" />
                  </Link>
                )}
              </div>

              <div className="mt-6">
                <DemoNotice>
                  {userRegistration?.isRegistered
                    ? 'You hold an active verified registration for this drop. Click above to view your registration status and live draw updates.'
                    : 'Clicking "Join Fair Drop" enters the calm waiting room to issue your verified cryptographic admission permit.'}
                </DemoNotice>
              </div>
            </div>
          </div>
        </div>
      </section>
    </FairShell>
  )
}
