'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import { PlayCircle, CheckCircle2, RefreshCw, Lock, Sparkles, AlertCircle, ArrowRight, ShieldCheck } from 'lucide-react'
import { AdminShell, DemoNotice } from '@/components/fair-shell'
import { getDemoEvent } from '@/lib/demo-events'
import { api, isUuid, FairDropApiError } from '@/lib/api'

export default function AdminCampaignDrawPage() {
  const params = useParams()
  const campaignId = (params?.campaignId as string) || 'camp_demo_001'
  const fallbackEvent = getDemoEvent(campaignId)

  const [campaign, setCampaign] = useState<any>(null)
  const [fairness, setFairness] = useState<any>(null)
  const [customSeed, setCustomSeed] = useState('')
  const [loading, setLoading] = useState(true)
  const [executing, setExecuting] = useState(false)
  const [drawResult, setDrawResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function loadData() {
      setLoading(true)
      try {
        const [cData, fData] = await Promise.allSettled([
          api.admin.getCampaign(campaignId),
          api.getFairness(campaignId),
        ])

        if (cData.status === 'fulfilled' && cData.value) {
          setCampaign(cData.value)
          if (cData.value.status === 'CLAIMING') {
            setDrawResult({
              status: 'CLAIMING',
              winners_count: cData.value.capacity || fallbackEvent.seats,
              standby_count: 500,
            })
          }
        }
        if (fData.status === 'fulfilled' && fData.value) {
          setFairness(fData.value)
        }
      } catch (err) {
        console.warn('Failed to load draw page data:', err)
      } finally {
        setLoading(false)
      }
    }

    loadData()
  }, [campaignId])

  const handleTrigger = async () => {
    setExecuting(true)
    setError(null)

    try {
      // If campaign is CLOSED, freeze roster first
      if (campaign?.status === 'CLOSED') {
        await api.admin.freezeCampaign(campaignId)
      }

      const seedToSend = customSeed.trim() || undefined
      const res = await api.admin.drawLottery(campaignId, seedToSend)
      setDrawResult(res)
      setCampaign((prev: any) => ({ ...prev, status: 'CLAIMING' }))
    } catch (err: any) {
      if (err instanceof FairDropApiError) {
        setError(`${err.code}: ${err.message}`)
      } else {
        setError(err.message || 'Draw execution failed.')
      }
    } finally {
      setExecuting(false)
    }
  }

  const currentStatus = campaign?.status || fallbackEvent.status
  const isClaiming = currentStatus === 'CLAIMING' || drawResult != null
  const rosterHash =
    fairness?.roster_hash ||
    campaign?.policy_hash ||
    fallbackEvent.rosterHash ||
    'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
  const seedDisplay =
    drawResult?.randomness_seed ||
    fairness?.randomness_seed ||
    fairness?.randomness_commitment ||
    fallbackEvent.randomnessSeed ||
    'drand_beacon_3849120'
  const winnersCount = drawResult?.winners_count ?? fallbackEvent.winnersCount
  const eligibleCount = fairness?.total_eligible ?? fallbackEvent.eligibleCount
  const seats = campaign?.capacity ?? fallbackEvent.seats

  return (
    <AdminShell campaignId={campaignId} activeTab="Draw">
      <div className="border-x-[3px] border-b-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-6 sm:p-10">
        
        <div className="flex flex-col gap-4 border-[3px] border-[var(--fd-ink)] bg-[var(--fd-yellow)] p-6 shadow-[6px_6px_0_var(--fd-ink)] sm:flex-row sm:items-center sm:justify-between">
          <div>
            <span className="font-mono text-xs font-black uppercase">CAMPAIGN CONSOLE / LOTTERY EXECUTION</span>
            <h1 className="font-display text-3xl font-black">UNIFORM LOTTERY SHUFFLE TRIGGER</h1>
            <p className="text-xs font-mono font-bold mt-1">DETERMINISTIC FISHER-YATES LOTTERY ENGINE</p>
          </div>
          <span
            className={`border-2 border-[var(--fd-ink)] px-3 py-1 font-mono text-xs font-black uppercase ${
              isClaiming ? 'bg-[var(--fd-teal)]' : 'bg-[var(--fd-pink)] text-white'
            }`}
          >
            {isClaiming ? 'DRAW EXECUTED · CLAIMING' : `STATUS: ${currentStatus}`}
          </span>
        </div>

        {error && (
          <div className="mt-6 border-[3px] border-[var(--fd-ink)] bg-red-100 p-4 shadow-[4px_4px_0_var(--fd-ink)]">
            <div className="flex items-start gap-2.5">
              <AlertCircle className="size-5 text-red-600 shrink-0 mt-0.5" />
              <div>
                <strong className="font-display text-sm font-black text-red-700 block">EXECUTION HALTED</strong>
                <p className="font-mono text-xs font-bold text-red-900 mt-1 leading-snug">{error}</p>
                <p className="font-mono text-[11px] text-neutral-600 mt-2">
                  Tip: A campaign must be transitioned from CLOSED → FROZEN before running the lottery draw.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Shuffling Execution Box */}
        <div className="mt-8 border-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] p-8 text-center shadow-[8px_8px_0_var(--fd-ink)]">
          <div className="mx-auto grid size-20 place-items-center rounded-full border-[3px] border-[var(--fd-ink)] bg-[var(--fd-pink)] shadow-[4px_4px_0_var(--fd-ink)]">
            <Sparkles className="size-10 text-[var(--fd-ink)]" />
          </div>

          <h2 className="font-display mt-4 text-3xl font-black">
            {isClaiming ? 'LOTTERY DRAW EXECUTED & VERIFIED' : 'READY FOR SHUFFLE EXECUTION'}
          </h2>

          <p className="mt-2 max-w-lg mx-auto text-sm font-medium">
            Shuffling <strong>{eligibleCount.toLocaleString()}</strong> eligible participants to allocate{' '}
            <strong>{seats}</strong> seats with 0 oversell guarantee.
          </p>

          <div className="mt-6 max-w-xl mx-auto border-2 border-[var(--fd-ink)] bg-[var(--fd-card)] p-4 font-mono text-xs font-bold text-left">
            <div>
              FROZEN ROSTER HASH: <span className="text-[var(--fd-pink)] font-black break-all">{rosterHash}</span>
            </div>
            <div className="mt-2">
              RANDOMNESS SEED: <span className="break-all">{seedDisplay}</span>
            </div>
            <div className="mt-2">
              SELECTED WINNERS:{' '}
              <span className="text-[var(--fd-teal)] font-black">{winnersCount} PARTICIPANTS</span>
            </div>
          </div>

          {/* Optional Custom Seed */}
          {!isClaiming && (
            <div className="mt-6 max-w-xl mx-auto text-left font-mono text-xs">
              <label className="flex flex-col gap-1.5 font-bold">
                <span className="uppercase text-[var(--fd-ink)]/70">Custom Randomness Beacon Seed (Optional)</span>
                <input
                  type="text"
                  value={customSeed}
                  onChange={(e) => setCustomSeed(e.target.value)}
                  placeholder="e.g. drand_round_42109 or leave blank for auto-generated seed"
                  className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-3 text-xs outline-none focus:shadow-[3px_3px_0_var(--fd-pink)] font-mono"
                />
              </label>
            </div>
          )}

          <div className="mt-8 flex flex-wrap justify-center gap-4">
            <button
              onClick={handleTrigger}
              disabled={executing}
              className="button-primary text-lg bg-[var(--fd-pink)] px-8 py-4 cursor-pointer disabled:opacity-50"
            >
              {executing ? (
                <>
                  <RefreshCw className="size-5 animate-spin" /> Executing Fisher-Yates Shuffle...
                </>
              ) : isClaiming ? (
                <>
                  <RefreshCw className="size-5" /> Re-Execute Uniform Lottery Draw
                </>
              ) : (
                <>
                  <PlayCircle className="size-6" /> Execute Uniform Lottery Draw
                </>
              )}
            </button>

            {isClaiming && (
              <Link
                href={`/events/${campaignId}/audit`}
                className="button-secondary text-base py-4 px-6 flex items-center gap-2"
              >
                <ShieldCheck className="size-5 text-[var(--fd-teal)]" /> View Public Audit Receipt
              </Link>
            )}
          </div>
        </div>

        <div className="mt-8">
          <DemoNotice>
            Lottery execution invokes POST /api/v1/admin/campaigns/{campaignId}/draw which generates winning Entitlements and moves lifecycle status to CLAIMING.
          </DemoNotice>
        </div>
      </div>
    </AdminShell>
  )
}

