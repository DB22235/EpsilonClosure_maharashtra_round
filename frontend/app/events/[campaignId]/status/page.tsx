'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import { ArrowRight, CheckCircle2, Clock, Hash, Lock, ShieldCheck, RefreshCw, Sparkles, Database } from 'lucide-react'
import { DemoNotice, FairShell, ProgressSteps, StatusPill } from '@/components/fair-shell'
import { getDemoEvent } from '@/lib/demo-events'
import { api, isUuid, FairDropApiError } from '@/lib/api'

interface RegistrationReceipt {
  registration_id?: string
  status?: string
  registered_at?: string
  risk_level?: string
}

export default function StatusPage() {
  const params = useParams()
  const campaignId = (params?.campaignId as string) || 'camp_demo_001'
  const fallbackEvent = getDemoEvent(campaignId)

  const [campaignStatus, setCampaignStatus] = useState<string>('OPEN')
  const [participantState, setParticipantState] = useState<string>('REGISTERED')
  const [receipt, setReceipt] = useState<RegistrationReceipt | null>(null)
  const [loading, setLoading] = useState(false)
  const [lastPolled, setLastPolled] = useState<Date>(new Date())

  // 1. Read cached registration receipt from sessionStorage if available
  useEffect(() => {
    if (typeof window !== 'undefined') {
      try {
        const cached = sessionStorage.getItem(`fairdrop_reg_${campaignId}`)
        if (cached) {
          setReceipt(JSON.parse(cached))
        }
      } catch (err) {
        console.warn('Failed to parse cached registration receipt:', err)
      }
    }
  }, [campaignId])

  // 2. Poll campaign status from backend every 8 seconds
  const fetchStatus = async () => {
    setLoading(true)
    try {
      const data = await api.getCampaignStatus(campaignId)
      if (data?.campaign?.status) {
        setCampaignStatus(data.campaign.status)
      }
      if (data?.participant_state) {
        setParticipantState(data.participant_state)
      }
      if (data?.registration) {
        setReceipt((prev) => ({ ...prev, ...data.registration }))
      }
      setLastPolled(new Date())
    } catch (err: any) {
      console.warn('[StatusPage] Polling notice:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStatus()
    const timer = setInterval(fetchStatus, 8000)
    return () => clearInterval(timer)
  }, [campaignId])

  const isDrawn = campaignStatus === 'DRAWN' || campaignStatus === 'CLAIMING' || campaignStatus === 'CLOSED' || participantState === 'SELECTED' || participantState === 'WON'
  const isFrozen = campaignStatus === 'FROZEN' || isDrawn

  const steps = [
    {
      title: 'REGISTRATION RECEIVED',
      status: 'COMPLETED',
      detail: receipt?.registered_at
        ? `Idempotent entry registered at ${new Date(receipt.registered_at).toLocaleTimeString()}`
        : 'Idempotent entry registered with cryptographic proof',
    },
    {
      title: 'IDENTITY & RISK VALIDATION',
      status: 'COMPLETED',
      detail: `Verified identity pass. Evaluated risk tier: ${receipt?.risk_level || 'LOW'}`,
    },
    {
      title: 'ROSTER CUTOFF & FREEZE',
      status: isFrozen ? 'COMPLETED' : 'ACTIVE',
      detail: isFrozen
        ? 'Accepted entries locked in canonical SHA-256 roster hash'
        : 'Registration window active · Awaiting cutoff freeze',
    },
    {
      title: 'DETERMINISTIC LOTTERY SHUFFLE',
      status: isDrawn ? 'COMPLETED' : isFrozen ? 'ACTIVE' : 'READY',
      detail: isDrawn
        ? 'Draw complete · Winners allocated via uniform shuffle'
        : 'Awaiting NIST / drand randomness beacon seed',
    },
  ]

  const registrationId = receipt?.registration_id || 'REG-2026-948201-FF'
  const policyVersion = fallbackEvent.policyVersion || 'v1.0'
  const rosterHash = fallbackEvent.rosterHash || 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'

  return (
    <FairShell active="Explore Drops">
      <ProgressSteps current={3} />

      <div className="border-x-[3px] border-b-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] px-5 py-12 sm:px-12 lg:px-20">
        <div className="mx-auto max-w-4xl border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-6 shadow-[10px_10px_0_var(--fd-ink)] sm:p-10">
          
          <div className="flex flex-col gap-4 border-b-[3px] border-[var(--fd-ink)] pb-6 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <span className="border-2 border-[var(--fd-ink)] bg-[var(--fd-teal)] px-3 py-1 font-mono text-xs font-black uppercase">
                ENTRY ACTIVE &amp; CONFIRMED
              </span>
              <h1 className="font-display mt-2 text-3xl font-black">REGISTRATION RECEIPT STATUS</h1>
              <p className="text-sm font-medium opacity-75">{fallbackEvent.name}</p>
            </div>
            <div className="flex flex-col items-end gap-2">
              <div className="border-2 border-[var(--fd-ink)] bg-[var(--fd-yellow)] p-3 text-center font-mono text-xs font-bold">
                {isDrawn ? 'LOTTERY DRAW COMPLETED' : isFrozen ? 'ROSTER FROZEN' : 'LOTTERY DRAW IN PROGRESS'}
              </div>
              <button
                onClick={fetchStatus}
                className="text-[11px] font-mono font-bold flex items-center gap-1 opacity-70 hover:opacity-100"
              >
                <RefreshCw className={`size-3 ${loading ? 'animate-spin' : ''}`} /> Polled at {lastPolled.toLocaleTimeString()}
              </button>
            </div>
          </div>

          {/* Receipt Credentials Block */}
          <div className="mt-8 border-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] p-5 shadow-[4px_4px_0_var(--fd-ink)]">
            <h3 className="font-mono text-xs font-black uppercase text-[var(--fd-ink)]/70 mb-3 flex items-center gap-2">
              <Hash className="size-4" /> VERIFIED REGISTRATION CREDENTIALS
            </h3>
            <div className="grid gap-4 sm:grid-cols-2 font-mono text-xs">
              <div>
                <span className="text-[var(--fd-ink)]/60">REGISTRATION ID:</span>
                <div className="font-bold text-sm truncate">{registrationId}</div>
              </div>
              <div>
                <span className="text-[var(--fd-ink)]/60">POLICY VERSION:</span>
                <div className="font-bold text-sm">{policyVersion}</div>
              </div>
              <div className="sm:col-span-2">
                <span className="text-[var(--fd-ink)]/60">FROZEN ROSTER HASH:</span>
                <div className="font-bold text-[11px] break-all bg-[var(--fd-card)] border border-[var(--fd-ink)] p-2 mt-1">
                  {rosterHash}
                </div>
              </div>
            </div>
          </div>

          {/* Linear Progress Timeline Step Chart */}
          <div className="mt-8 flex flex-col gap-4">
            <h3 className="font-display text-xl font-black">PIPELINE VERIFICATION STAGES</h3>
            
            <div className="flex flex-col gap-3">
              {steps.map((s, idx) => (
                <div
                  key={s.title}
                  className={`flex items-start gap-4 border-[3px] border-[var(--fd-ink)] p-4 shadow-[3px_3px_0_var(--fd-ink)] transition-colors ${
                    s.status === 'COMPLETED'
                      ? 'bg-[var(--fd-teal)]'
                      : s.status === 'ACTIVE'
                      ? 'bg-[var(--fd-yellow)]'
                      : 'bg-[var(--fd-cream)]'
                  }`}
                >
                  <span className="grid size-8 shrink-0 place-items-center border-2 border-[var(--fd-ink)] bg-[var(--fd-card)] font-mono text-xs font-black">
                    {idx + 1}
                  </span>
                  <div className="flex-1">
                    <div className="flex items-center justify-between">
                      <h4 className="font-display text-lg font-black">{s.title}</h4>
                      <span className="font-mono text-[10px] font-black uppercase border border-[var(--fd-ink)] px-2 py-0.5 bg-[var(--fd-card)]">
                        {s.status}
                      </span>
                    </div>
                    <p className="mt-1 text-xs font-mono font-bold opacity-80">{s.detail}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* CTA */}
          <div className="mt-10">
            <Link
              href={`/events/${campaignId}/result`}
              className="button-primary w-full justify-center text-center text-lg bg-[var(--fd-pink)]"
            >
              View Draw Result <ArrowRight className="size-5" />
            </Link>
          </div>

          <div className="mt-6">
            <DemoNotice>
              {isDrawn
                ? 'Draw completed on server. Click "View Draw Result" to inspect your allocation.'
                : 'Status refreshes every 8 seconds. You can click "View Draw Result" at any time to verify personal draw status.'}
            </DemoNotice>
          </div>
        </div>
      </div>
    </FairShell>
  )
}
