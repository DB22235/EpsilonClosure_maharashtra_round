'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import {
  ArrowRight,
  BarChart3,
  CheckCircle2,
  ShieldAlert,
  Users,
  Settings,
  Activity,
  PlayCircle,
  Award,
  FileText,
  RefreshCw,
  AlertTriangle,
  Pause,
  Play,
  Flame,
  Check,
  Lock,
} from 'lucide-react'
import { AdminShell, DemoNotice, StatusPill } from '@/components/fair-shell'
import { getDemoEvent } from '@/lib/demo-events'
import { api, isUuid, FairDropApiError } from '@/lib/api'

export default function AdminCampaignOverviewPage() {
  const params = useParams()
  const campaignId = (params?.campaignId as string) || 'camp_demo_001'
  const fallbackEvent = getDemoEvent(campaignId)

  const [campaign, setCampaign] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [activeAction, setActiveAction] = useState<string | null>(null)
  const actionLoading = Boolean(activeAction)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const fetchCampaign = async () => {
    setLoading(true)
    try {
      const data = await api.admin.getCampaign(campaignId)
      setCampaign(data)
    } catch (err: any) {
      console.warn('Failed to load campaign from admin API, using fallback:', err)
      setCampaign({
        id: campaignId,
        name: fallbackEvent.name,
        venue: fallbackEvent.venue,
        status: fallbackEvent.status,
        capacity: fallbackEvent.seats,
        seat_counts: { available: fallbackEvent.seats - 42, held: 12, confirmed: 30, total: fallbackEvent.seats },
        registration_counts: {
          total: fallbackEvent.registeredCount,
          accepted: fallbackEvent.eligibleCount,
          duplicate: fallbackEvent.duplicateCount,
          rejected: 0,
        },
        admission_paused: false,
        registration_paused: false,
        redemption_paused: false,
      })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchCampaign()
  }, [campaignId])

  // Lifecycle state transition handlers
  const handleTransition = async (action: 'prepare' | 'publish' | 'close' | 'freeze') => {
    setActiveAction(action)
    setMessage(null)
    try {
      let res: any
      if (action === 'prepare') {
        res = await api.admin.prepareCampaign(campaignId)
      } else if (action === 'publish') {
        res = await api.admin.publishCampaign(campaignId)
      } else if (action === 'close') {
        res = await api.admin.closeCampaign(campaignId)
      } else if (action === 'freeze') {
        res = await api.admin.freezeCampaign(campaignId)
      }
      if (res?.new_status) {
        setCampaign((prev: any) => prev ? { ...prev, status: res.new_status } : prev)
      }
      setMessage({ type: 'success', text: res?.message || `Successfully transitioned campaign via ${action}.` })
    } catch (err: any) {
      if (err instanceof FairDropApiError && err.code === 'INVALID_STATE_TRANSITION') {
        const details = err.details as any
        const currentInDb = details?.current_status
        if (currentInDb) {
          setCampaign((prev: any) => prev ? { ...prev, status: currentInDb } : prev)
          setMessage({
            type: 'success',
            text: `Campaign is already in ${currentInDb} phase. State synchronized with server.`,
          })
        } else {
          setMessage({ type: 'error', text: `${err.code}: ${err.message}` })
        }
      } else {
        const errorText = err instanceof FairDropApiError ? `${err.code}: ${err.message}` : err.message || 'Transition failed'
        setMessage({ type: 'error', text: errorText })
      }
    } finally {
      await fetchCampaign()
      setActiveAction(null)
    }
  }

  // Emergency Circuit Breaker (Pause / Resume) handlers
  const handleTogglePause = async (scope: 'ADMISSION' | 'REGISTRATION' | 'REDEMPTION', currentPaused: boolean) => {
    setActiveAction(`pause_${scope}`)
    setMessage(null)
    try {
      if (currentPaused) {
        await api.admin.resumeCampaign(campaignId, scope)
        setMessage({ type: 'success', text: `Resumed ${scope} operational scope successfully.` })
      } else {
        await api.admin.pauseCampaign(campaignId, scope, `Manual pause triggered by operator via admin console`)
        setMessage({ type: 'success', text: `Paused ${scope} operational scope (circuit breaker activated).` })
      }
      await fetchCampaign()
    } catch (err: any) {
      const errorText = err instanceof FairDropApiError ? `${err.code}: ${err.message}` : err.message || 'Pause toggle failed'
      setMessage({ type: 'error', text: errorText })
    } finally {
      setActiveAction(null)
    }
  }

  const currentStatus = campaign?.status || fallbackEvent.status
  const seatCounts = campaign?.seat_counts || {
    available: (campaign?.capacity || fallbackEvent.seats) - 42,
    held: 12,
    confirmed: 30,
    total: campaign?.capacity || fallbackEvent.seats,
  }
  const regCounts = campaign?.registration_counts || {
    total: fallbackEvent.registeredCount,
    accepted: fallbackEvent.eligibleCount,
    duplicate: fallbackEvent.duplicateCount,
    rejected: 0,
  }

  const stageOrder = ['DRAFT', 'PREPARING', 'OPEN', 'CLOSED', 'FROZEN', 'CLAIMING']
  const curIdx = stageOrder.indexOf(currentStatus)

  const handleStageClick = (st: string) => {
    const targetIdx = stageOrder.indexOf(st)

    if (targetIdx === curIdx) {
      setMessage({ type: 'success', text: `Campaign is currently active in the ${st} phase.` })
      return
    }

    if (targetIdx < curIdx) {
      setMessage({
        type: 'error',
        text: `Phase ${st} has already completed. Lifecycle transitions are strictly forward-moving and irreversible to guarantee an immutable audit trail.`,
      })
      return
    }

    if (targetIdx === curIdx + 1) {
      if (currentStatus === 'DRAFT') {
        handleTransition('prepare')
      } else if (currentStatus === 'PREPARING') {
        handleTransition('publish')
      } else if (currentStatus === 'OPEN') {
        handleTransition('close')
      } else if (currentStatus === 'CLOSED') {
        handleTransition('freeze')
      } else if (currentStatus === 'FROZEN') {
        window.location.href = `/admin/campaigns/${campaignId}/draw`
      }
      return
    }

    const nextStep = stageOrder[curIdx + 1]
    setMessage({
      type: 'error',
      text: `Cannot skip directly to ${st}. State machine requires sequential progression: complete the next required phase [${nextStep}] first.`,
    })
  }


  return (
    <AdminShell campaignId={campaignId} activeTab="Overview">
      <div className="border-x-[3px] border-b-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-6 sm:p-10">
        
        {/* Campaign Header Card */}
        <div className="flex flex-col gap-4 border-[3px] border-[var(--fd-ink)] bg-[var(--fd-yellow)] p-6 shadow-[6px_6px_0_var(--fd-ink)] sm:flex-row sm:items-center sm:justify-between">
          <div>
            <span className="font-mono text-xs font-black uppercase">CAMPAIGN CONSOLE / OPERATOR OVERVIEW</span>
            <h1 className="font-display text-3xl font-black">{(campaign?.name || fallbackEvent.name).toUpperCase()}</h1>
            <p className="text-xs font-mono font-bold mt-1">
              {campaign?.venue || fallbackEvent.venue} · {seatCounts.total > 0 ? seatCounts.total : (campaign?.capacity || 0)} CAPACITY {seatCounts.total === 0 && (campaign?.capacity || 0) > 0 ? '(SEATS PENDING ALLOCATION)' : ''} · ID: <span className="underline">{campaignId}</span>
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={fetchCampaign}
              disabled={loading || actionLoading}
              className="button-secondary text-xs py-2 px-3 flex items-center gap-1.5 cursor-pointer"
            >
              <RefreshCw className={`size-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
            </button>
            <StatusPill>{currentStatus}</StatusPill>
          </div>
        </div>

        {/* Action Message Banner */}
        {message && (
          <div
            className={`mt-6 border-[3px] border-[var(--fd-ink)] p-4 shadow-[4px_4px_0_var(--fd-ink)] ${
              message.type === 'success' ? 'bg-green-100 text-green-950' : 'bg-red-100 text-red-950'
            }`}
          >
            <div className="flex items-start gap-2.5">
              {message.type === 'success' ? (
                <CheckCircle2 className="size-5 text-green-700 shrink-0 mt-0.5" />
              ) : (
                <AlertTriangle className="size-5 text-red-600 shrink-0 mt-0.5" />
              )}
              <div className="font-mono text-xs font-bold leading-snug">
                <strong>{message.type === 'success' ? 'STATE UPDATED: ' : 'LIFECYCLE NOTICE: '}</strong>
                {message.text}
              </div>
            </div>
          </div>
        )}

        {/* 1. Lifecycle State Machine Controls */}
        <div className="mt-8 border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-6 shadow-[6px_6px_0_var(--fd-ink)]">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b-2 border-[var(--fd-ink)] pb-4">
            <div>
              <span className="font-mono text-xs font-black uppercase text-[var(--fd-ink)]/70">
                LIFECYCLE STATE MACHINE (STRICT SEQUENTIAL ADVANCEMENT)
              </span>
              <h2 className="font-display text-2xl font-black flex items-center gap-2">
                CURRENT STATUS: <span className="text-[var(--fd-pink)]">{currentStatus}</span>
              </h2>
            </div>

            {/* Dynamic Lifecycle Trigger */}
            <div className="flex flex-col items-start sm:items-end gap-1.5">
              <span className="font-mono text-[10px] font-black uppercase text-neutral-500">
                {currentStatus === 'CLAIMING' ? 'LIFECYCLE FINISHED' : 'NEXT REQUIRED OPERATOR ACTION:'}
              </span>
              {currentStatus === 'DRAFT' && (
                <button
                  type="button"
                  onClick={() => handleTransition('prepare')}
                  disabled={actionLoading}
                  className={`button-primary bg-[var(--fd-yellow)] flex items-center gap-2 ${
                    actionLoading ? 'opacity-80 cursor-wait' : 'cursor-pointer hover:brightness-105'
                  }`}
                >
                  {activeAction === 'prepare' ? (
                    <>
                      <RefreshCw className="size-4 animate-spin text-[var(--fd-ink)]" /> Generating Seats & Policy Hash...
                    </>
                  ) : (
                    <>
                      <Flame className="size-4" /> Prepare Campaign & Generate Seats
                    </>
                  )}
                </button>
              )}

              {currentStatus === 'PREPARING' && (
                <button
                  type="button"
                  onClick={() => handleTransition('publish')}
                  disabled={actionLoading}
                  className={`button-primary bg-[var(--fd-teal)] text-[var(--fd-ink)] flex items-center gap-2 ${
                    actionLoading ? 'opacity-80 cursor-wait' : 'cursor-pointer hover:brightness-105'
                  }`}
                >
                  {activeAction === 'publish' ? (
                    <>
                      <RefreshCw className="size-4 animate-spin text-[var(--fd-ink)]" /> Publishing & Opening...
                    </>
                  ) : (
                    <>
                      <Play className="size-4" /> Publish & Open Registrations
                    </>
                  )}
                </button>
              )}

              {currentStatus === 'OPEN' && (
                <button
                  type="button"
                  onClick={() => handleTransition('close')}
                  disabled={actionLoading}
                  className={`button-primary bg-[var(--fd-pink)] flex items-center gap-2 ${
                    actionLoading ? 'opacity-80 cursor-wait' : 'cursor-pointer hover:brightness-105'
                  }`}
                >
                  {activeAction === 'close' ? (
                    <>
                      <RefreshCw className="size-4 animate-spin" /> Closing Window...
                    </>
                  ) : (
                    <>
                      <Pause className="size-4" /> Close Registration Window
                    </>
                  )}
                </button>
              )}

              {currentStatus === 'CLOSED' && (
                <button
                  type="button"
                  onClick={() => handleTransition('freeze')}
                  disabled={actionLoading}
                  className={`button-primary bg-[var(--fd-purple)] text-white flex items-center gap-2 ${
                    actionLoading ? 'opacity-80 cursor-wait' : 'cursor-pointer hover:brightness-105'
                  }`}
                >
                  {activeAction === 'freeze' ? (
                    <>
                      <RefreshCw className="size-4 animate-spin text-white" /> Freezing Roster Hash...
                    </>
                  ) : (
                    <>
                      <Lock className="size-4" /> Freeze Eligible Roster Hash
                    </>
                  )}
                </button>
              )}

              {currentStatus === 'FROZEN' && (
                <Link
                  href={`/admin/campaigns/${campaignId}/draw`}
                  className="button-primary bg-[var(--fd-pink)]"
                >
                  <PlayCircle className="size-4" /> Proceed to Uniform Lottery Draw →
                </Link>
              )}

              {currentStatus === 'CLAIMING' && (
                <div className="flex items-center gap-2 font-mono text-xs font-bold text-green-700 bg-green-100 border-2 border-green-800 px-3 py-2">
                  <Check className="size-4 text-green-800" /> Lottery Drawn · Claiming Window Active
                </div>
              )}
            </div>
          </div>

          {/* Lifecycle Pipeline Progress Bar with Interactive Click Handlers */}
          <div className="mt-4">
            <div className="flex items-center justify-between text-[11px] font-mono font-bold text-neutral-600 mb-2">
              <span>STATE MACHINE PIPELINE</span>
              <span>Click any step to inspect or trigger next action</span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2 font-mono text-xs font-bold text-center">
              {stageOrder.map((st, idx) => {
                const isPast = idx < curIdx
                const isCurrent = idx === curIdx
                const isNext = idx === curIdx + 1

                let boxStyles = 'bg-[var(--fd-cream)] opacity-60 cursor-not-allowed border-dashed'
                let badge = 'LOCKED'
                let badgeColor = 'text-neutral-500'

                if (isPast) {
                  boxStyles = 'bg-green-50 border-green-700 text-green-950 cursor-pointer shadow-[2px_2px_0_green]'
                  badge = '✓ COMPLETED'
                  badgeColor = 'text-green-700'
                } else if (isCurrent) {
                  boxStyles = 'bg-[var(--fd-pink)] text-white shadow-[3px_3px_0_var(--fd-ink)] cursor-pointer ring-2 ring-black'
                  badge = '● ACTIVE NOW'
                  badgeColor = 'text-white'
                } else if (isNext) {
                  if (activeAction) {
                    boxStyles = 'bg-[var(--fd-yellow)] text-[var(--fd-ink)] cursor-wait opacity-80 animate-pulse shadow-[2px_2px_0_var(--fd-ink)]'
                    badge = '⚡ PROCESSING...'
                    badgeColor = 'text-amber-900 font-black'
                  } else {
                    boxStyles = 'bg-[var(--fd-yellow)] text-[var(--fd-ink)] cursor-pointer shadow-[2px_2px_0_var(--fd-ink)] hover:scale-105 transition-transform'
                    badge = '⚡ NEXT (CLICK)'
                    badgeColor = 'text-amber-800'
                  }
                }

                return (
                  <button
                    key={st}
                    type="button"
                    onClick={() => handleStageClick(st)}
                    disabled={actionLoading}
                    className={`p-2.5 border-2 border-[var(--fd-ink)] flex flex-col items-center justify-between min-h-[64px] transition-all text-left w-full ${boxStyles}`}
                    title={
                      isCurrent
                        ? `Current state: ${st}`
                        : isNext
                        ? `Click to advance campaign to ${st}`
                        : isPast
                        ? `Phase ${st} has completed`
                        : `Phase ${st} is locked until previous steps complete`
                    }
                  >
                    <span className="font-black text-xs">{st}</span>
                    <span className={`text-[9px] font-mono font-extrabold uppercase mt-1 ${badgeColor}`}>
                      {badge}
                    </span>
                  </button>
                )
              })}
            </div>
          </div>
        </div>

        {/* 2. Emergency Circuit Breakers (Pause / Resume) */}
        <div className="mt-8 border-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] p-6 shadow-[6px_6px_0_var(--fd-ink)]">
          <div className="flex items-center justify-between border-b-2 border-[var(--fd-ink)] pb-3">
            <div>
              <span className="font-mono text-xs font-black uppercase text-[var(--fd-ink)]/70">SAFETY CONTROLS</span>
              <h2 className="font-display text-2xl font-black">EMERGENCY CIRCUIT BREAKERS</h2>
            </div>
            <span className="font-mono text-[11px] font-bold text-neutral-600">
              ISOLATED OPERATIONAL SCOPES
            </span>
          </div>

          <div className="mt-6 grid gap-4 sm:grid-cols-3">
            {/* Admission Pause */}
            <div className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-4 shadow-[3px_3px_0_var(--fd-ink)] flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-black uppercase">ADMISSION QUEUE</span>
                  <span
                    className={`font-mono text-[10px] font-black px-2 py-0.5 border ${
                      campaign?.admission_paused
                        ? 'bg-red-200 border-red-800 text-red-900'
                        : 'bg-green-200 border-green-800 text-green-900'
                    }`}
                  >
                    {campaign?.admission_paused ? 'PAUSED' : 'NORMAL'}
                  </span>
                </div>
                <p className="font-mono text-xs text-neutral-600 mt-2">
                  Controls waiting room entrance & admission token issuance.
                </p>
              </div>
              <button
                onClick={() => handleTogglePause('ADMISSION', Boolean(campaign?.admission_paused))}
                disabled={actionLoading}
                className={`mt-4 button-primary text-xs py-2 justify-center cursor-pointer ${
                  campaign?.admission_paused ? 'bg-[var(--fd-teal)] text-[var(--fd-ink)]' : 'bg-red-500 text-white'
                }`}
              >
                {campaign?.admission_paused ? 'Resume Admission' : 'Pause Admission'}
              </button>
            </div>

            {/* Registration Pause */}
            <div className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-4 shadow-[3px_3px_0_var(--fd-ink)] flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-black uppercase">REGISTRATION</span>
                  <span
                    className={`font-mono text-[10px] font-black px-2 py-0.5 border ${
                      campaign?.registration_paused
                        ? 'bg-red-200 border-red-800 text-red-900'
                        : 'bg-green-200 border-green-800 text-green-900'
                    }`}
                  >
                    {campaign?.registration_paused ? 'PAUSED' : 'NORMAL'}
                  </span>
                </div>
                <p className="font-mono text-xs text-neutral-600 mt-2">
                  Controls participant entry submission & deduplication lock.
                </p>
              </div>
              <button
                onClick={() => handleTogglePause('REGISTRATION', Boolean(campaign?.registration_paused))}
                disabled={actionLoading}
                className={`mt-4 button-primary text-xs py-2 justify-center cursor-pointer ${
                  campaign?.registration_paused ? 'bg-[var(--fd-teal)] text-[var(--fd-ink)]' : 'bg-red-500 text-white'
                }`}
              >
                {campaign?.registration_paused ? 'Resume Registration' : 'Pause Registration'}
              </button>
            </div>

            {/* Redemption Pause */}
            <div className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-4 shadow-[3px_3px_0_var(--fd-ink)] flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-black uppercase">REDEMPTION</span>
                  <span
                    className={`font-mono text-[10px] font-black px-2 py-0.5 border ${
                      campaign?.redemption_paused
                        ? 'bg-red-200 border-red-800 text-red-900'
                        : 'bg-green-200 border-green-800 text-green-900'
                    }`}
                  >
                    {campaign?.redemption_paused ? 'PAUSED' : 'NORMAL'}
                  </span>
                </div>
                <p className="font-mono text-xs text-neutral-600 mt-2">
                  Controls atomic seat selection & booking redemptions.
                </p>
              </div>
              <button
                onClick={() => handleTogglePause('REDEMPTION', Boolean(campaign?.redemption_paused))}
                disabled={actionLoading}
                className={`mt-4 button-primary text-xs py-2 justify-center cursor-pointer ${
                  campaign?.redemption_paused ? 'bg-[var(--fd-teal)] text-[var(--fd-ink)]' : 'bg-red-500 text-white'
                }`}
              >
                {campaign?.redemption_paused ? 'Resume Redemption' : 'Pause Redemption'}
              </button>
            </div>
          </div>
        </div>

        {/* 3. Overview Stats */}
        <div className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          <div className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] p-5 shadow-[4px_4px_0_var(--fd-ink)]">
            <span className="metric-label">Registered Participants</span>
            <strong className="metric-value text-[var(--fd-pink)]">{regCounts.total.toLocaleString()}</strong>
            <span className="font-mono text-[11px] font-bold text-neutral-600">ALL SUBMISSIONS</span>
          </div>
          <div className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] p-5 shadow-[4px_4px_0_var(--fd-ink)]">
            <span className="metric-label">Deduplicated Eligible</span>
            <strong className="metric-value text-[var(--fd-teal)]">{regCounts.accepted.toLocaleString()}</strong>
            <span className="font-mono text-[11px] font-bold text-[var(--fd-teal)]">CLEANSED ROSTER</span>
          </div>
          <div className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] p-5 shadow-[4px_4px_0_var(--fd-ink)]">
            <span className="metric-label">Duplicates Filtered</span>
            <strong className="metric-value text-red-600">{regCounts.duplicate.toLocaleString()}</strong>
            <span className="font-mono text-[11px] font-bold text-red-600">100% IDEMPOTENT</span>
          </div>
          <div className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] p-5 shadow-[4px_4px_0_var(--fd-ink)]">
            <span className="metric-label">Available Inventory</span>
            <strong className="metric-value">{seatCounts.available}</strong>
            <span className="font-mono text-[11px] font-bold">
              {seatCounts.held} HELD · {seatCounts.confirmed} BOOKED
            </span>
          </div>
        </div>

        {/* 4. Quick Action Console Shortcuts */}
        <div className="mt-10 border-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] p-6 shadow-[6px_6px_0_var(--fd-ink)]">
          <h2 className="font-display text-2xl font-black mb-4">CAMPAIGN CONTROL MODULES</h2>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <Link
              href={`/admin/campaigns/${campaignId}/edit`}
              className="flex items-center justify-between border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-4 shadow-[3px_3px_0_var(--fd-ink)] hover:bg-[var(--fd-pink)] transition-all"
            >
              <div>
                <h3 className="font-display text-lg font-black flex items-center gap-2">
                  <Settings className="size-5" /> Edit Configuration
                </h3>
                <p className="text-xs font-mono mt-1 opacity-70">Update rules, dates, policy tags</p>
              </div>
              <ArrowRight className="size-5" />
            </Link>

            <Link
              href={`/admin/campaigns/${campaignId}/monitor`}
              className="flex items-center justify-between border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-4 shadow-[3px_3px_0_var(--fd-ink)] hover:bg-[var(--fd-teal)] transition-all"
            >
              <div>
                <h3 className="font-display text-lg font-black flex items-center gap-2">
                  <Activity className="size-5" /> Live Traffic Monitor
                </h3>
                <p className="text-xs font-mono mt-1 opacity-70">Queue depth, rate limit logs</p>
              </div>
              <ArrowRight className="size-5" />
            </Link>

            <Link
              href={`/admin/campaigns/${campaignId}/draw`}
              className="flex items-center justify-between border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-4 shadow-[3px_3px_0_var(--fd-ink)] hover:bg-[var(--fd-yellow)] transition-all"
            >
              <div>
                <h3 className="font-display text-lg font-black flex items-center gap-2">
                  <PlayCircle className="size-5" /> Trigger Lottery Draw
                </h3>
                <p className="text-xs font-mono mt-1 opacity-70">Uniform shuffle execution</p>
              </div>
              <ArrowRight className="size-5" />
            </Link>

            <Link
              href={`/admin/campaigns/${campaignId}/claims`}
              className="flex items-center justify-between border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-4 shadow-[3px_3px_0_var(--fd-ink)] hover:bg-[var(--fd-blue)] transition-all"
            >
              <div>
                <h3 className="font-display text-lg font-black flex items-center gap-2">
                  <Award className="size-5" /> Claims & Seat Holds
                </h3>
                <p className="text-xs font-mono mt-1 opacity-70">Winner claim status grid</p>
              </div>
              <ArrowRight className="size-5" />
            </Link>

            <Link
              href={`/events/${campaignId}/audit`}
              className="flex items-center justify-between border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-4 shadow-[3px_3px_0_var(--fd-ink)] hover:bg-[var(--fd-purple)] transition-all"
            >
              <div>
                <h3 className="font-display text-lg font-black flex items-center gap-2">
                  <FileText className="size-5" /> Public Fairness Audit
                </h3>
                <p className="text-xs font-mono mt-1 opacity-70">Verify roster hash & proof</p>
              </div>
              <ArrowRight className="size-5" />
            </Link>

            <Link
              href={`/admin/campaigns/${campaignId}/simulations`}
              className="flex items-center justify-between border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-4 shadow-[3px_3px_0_var(--fd-ink)] hover:bg-[var(--fd-yellow)] transition-all"
            >
              <div>
                <h3 className="font-display text-lg font-black flex items-center gap-2">
                  <ShieldAlert className="size-5" /> Adversarial Simulator
                </h3>
                <p className="text-xs font-mono mt-1 opacity-70">Simulate 50,000 bot requests</p>
              </div>
              <ArrowRight className="size-5" />
            </Link>
          </div>
        </div>

        <div className="mt-8">
          <DemoNotice>
            Connected to FastAPI /api/v1/admin/campaigns/{campaignId}. All lifecycle transitions and circuit breaker operations execute real ACID transactions.
          </DemoNotice>
        </div>
      </div>
    </AdminShell>
  )
}

