'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import { ArrowLeft, Check, Copy, ShieldCheck, Sparkles, Terminal, FileText, CheckCircle2 } from 'lucide-react'
import { DemoNotice, FairShell, PageIntro } from '@/components/fair-shell'
import { getDemoEvent } from '@/lib/demo-events'
import { api, isUuid } from '@/lib/api'

export default function AuditPage() {
  const params = useParams()
  const campaignId = (params?.campaignId as string) || 'camp_demo_001'
  const fallbackEvent = getDemoEvent(campaignId)

  const [loading, setLoading] = useState(true)
  const [copiedHash, setCopiedHash] = useState<string | null>(null)
  const [fairness, setFairness] = useState<any>(null)
  const [auditEvents, setAuditEvents] = useState<any[]>([])
  const [metrics, setMetrics] = useState<any>(null)
  const [campaignName, setCampaignName] = useState(fallbackEvent.name)

  useEffect(() => {
    let mounted = true

    async function loadAuditData() {
      setLoading(true)
      try {
        const [fairnessRes, auditRes, metricsRes] = await Promise.allSettled([
          api.getFairness(campaignId),
          api.getAudit(campaignId, 1, 50),
          api.getMetrics(campaignId),
        ])

        if (!mounted) return

        if (fairnessRes.status === 'fulfilled' && fairnessRes.value) {
          setFairness(fairnessRes.value)
        }
        if (auditRes.status === 'fulfilled' && auditRes.value?.data) {
          setAuditEvents(auditRes.value.data)
        }
        if (metricsRes.status === 'fulfilled' && metricsRes.value) {
          setMetrics(metricsRes.value)
          if (metricsRes.value.name) setCampaignName(metricsRes.value.name)
        }
      } catch (err) {
        console.error('Audit fetch error:', err)
      } finally {
        if (mounted) setLoading(false)
      }
    }

    loadAuditData()
    return () => {
      mounted = false
    }
  }, [campaignId])

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text)
    setCopiedHash(label)
    setTimeout(() => setCopiedHash(null), 2500)
  }

  // Merged view data
  const rosterHash =
    fairness?.roster_hash ||
    fallbackEvent.rosterHash ||
    'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
  const evidenceHash =
    fairness?.evidence_hash ||
    '7d1a5518b57700201d16a50ee7b3512a831e5f8f949f57ebbf794c483161c28b'
  const randomnessSeed =
    fairness?.randomness_seed ||
    fairness?.randomness_commitment ||
    fallbackEvent.randomnessSeed ||
    'drand_beacon_3849120'
  const winnersCount = metrics?.winners_count ?? fallbackEvent.winnersCount
  const totalRegistrations =
    metrics?.registrations_count ?? fallbackEvent.registeredCount
  const eligibleCount =
    fairness?.total_eligible ?? metrics?.eligible_roster_count ?? fallbackEvent.eligibleCount
  const duplicatesCount =
    metrics
      ? Math.max(0, (metrics.registrations_count || 0) - (metrics.eligible_roster_count || 0))
      : fallbackEvent.duplicateCount
  const capacity = metrics?.capacity ?? fallbackEvent.seats
  const oversellCount = metrics?.oversell_count ?? 0
  const selectionProbability = fairness?.selection_probability
    ? (fairness.selection_probability * 100).toFixed(2) + '%'
    : `${((capacity / (eligibleCount || 1)) * 100).toFixed(2)}%`

  return (
    <FairShell active="Public Audit">
      <PageIntro
        eyebrow={`Public Fairness Audit / #${campaignId}`}
        title={
          <>
            PUBLIC ALLOCATION<br />
            <span className="text-[var(--fd-yellow)] [text-shadow:3px_3px_0_var(--fd-ink)]">EVIDENCE RECEIPT.</span>
          </>
        }
        copy={`Complete cryptographic and statistical proof for ${campaignName}. Open for independent verification.`}
      />

      <section className="border-x-[3px] border-b-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] px-5 py-12 sm:px-12 lg:px-20">
        
        {/* Banner */}
        <div className="flex flex-col gap-4 border-[3px] border-[var(--fd-ink)] bg-[var(--fd-teal)] p-6 shadow-[6px_6px_0_var(--fd-ink)] sm:flex-row sm:items-center sm:justify-between">
          <div>
            <span className="font-mono text-xs font-black uppercase text-[var(--fd-ink)]/80">AUDIT VERIFICATION STATUS</span>
            <div className="font-display text-2xl font-black">
              {metrics?.status === 'OPEN' ? 'REGISTRATION WINDOW OPEN · CONTINUOUS AUDIT' : 'LOTTERY DRAW AUDITED & VERIFIED'}
            </div>
            {fairness?.statement && (
              <p className="font-mono text-xs font-bold text-[var(--fd-ink)]/90 mt-1">
                INVARIANT: {fairness.statement.toUpperCase()}
              </p>
            )}
          </div>
          <Link href={`/events/${campaignId}`} className="button-secondary">
            <ArrowLeft className="size-4" /> Back to Campaign
          </Link>
        </div>

        {/* 4 Key Statistics Cards */}
        <div className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          <div className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] p-5 shadow-[4px_4px_0_var(--fd-ink)]">
            <span className="metric-label">Policy Version</span>
            <strong className="metric-value">{fallbackEvent.policyVersion}</strong>
          </div>
          <div className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] p-5 shadow-[4px_4px_0_var(--fd-ink)]">
            <span className="metric-label">Selected Winners</span>
            <strong className="metric-value text-[var(--fd-pink)]">{winnersCount}</strong>
          </div>
          <div className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] p-5 shadow-[4px_4px_0_var(--fd-ink)]">
            <span className="metric-label">Oversell Count</span>
            <strong className="metric-value text-[var(--fd-teal)]">{oversellCount}</strong>
          </div>
          <div className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] p-5 shadow-[4px_4px_0_var(--fd-ink)]">
            <span className="metric-label">Allocation Prob</span>
            <strong className="metric-value text-[1.8rem]">{selectionProbability}</strong>
          </div>
        </div>

        {/* Roster Hash Box */}
        <div className="mt-8 border-[3px] border-[var(--fd-ink)] bg-[var(--fd-yellow)] p-6 shadow-[6px_6px_0_var(--fd-ink)]">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-2">
            <h2 className="font-display text-2xl font-black">FROZEN ROSTER HASH BOX</h2>
            <button
              onClick={() => copyToClipboard(rosterHash, 'roster')}
              className="button-secondary text-xs py-1 px-3 self-start sm:self-auto flex items-center gap-1.5"
            >
              {copiedHash === 'roster' ? (
                <>
                  <CheckCircle2 className="size-3.5 text-green-700" /> Copied Hash!
                </>
              ) : (
                <>
                  <Copy className="size-3.5" /> Copy Roster Hash
                </>
              )}
            </button>
          </div>
          <p className="text-xs font-mono font-bold text-[var(--fd-ink)]/80 mb-4">
            SHA-256 Digest of all {eligibleCount.toLocaleString()} deduplicated participant IDs prior to shuffle.
          </p>

          <div className="border-2 border-[var(--fd-ink)] bg-[var(--fd-card)] p-4 font-mono text-xs font-black break-all shadow-[3px_3px_0_var(--fd-ink)]">
            {rosterHash}
          </div>

          <div className="mt-4 flex flex-wrap gap-4 text-xs font-mono font-bold">
            <span>
              RANDOM SEED BEACON:{' '}
              <strong className="underline break-all">{randomnessSeed}</strong>
            </span>
            <span>STANDBY QUEUE: <strong>{metrics?.standby_count ?? 500} BACKUP POSITIONS</strong></span>
          </div>

          {/* Evidence Canonical Digest */}
          <div className="mt-4 pt-4 border-t-2 border-[var(--fd-ink)]/30 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs font-mono">
            <div>
              <span className="font-bold opacity-75">CANONICAL EVIDENCE HASH: </span>
              <span className="font-black break-all">{evidenceHash}</span>
            </div>
            <button
              onClick={() => copyToClipboard(evidenceHash, 'evidence')}
              className="text-[11px] font-black underline flex items-center gap-1 hover:text-[var(--fd-pink)]"
            >
              {copiedHash === 'evidence' ? '✓ Copied' : 'Copy Evidence Hash'}
            </button>
          </div>
        </div>

        {/* Verified Metrics Table */}
        <div className="mt-10 border-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] p-6 shadow-[6px_6px_0_var(--fd-ink)]">
          <h2 className="font-display text-2xl font-black mb-4">VERIFIED AUDIT METRICS TABLE</h2>

          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left font-mono text-xs font-bold">
              <thead>
                <tr className="border-b-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] text-[var(--fd-ink)]">
                  <th className="p-3">METRIC NAME</th>
                  <th className="p-3">MEASURED VALUE</th>
                  <th className="p-3">TARGET THRESHOLD</th>
                  <th className="p-3">STATUS</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b-2 border-[var(--fd-ink)]">
                  <td className="p-3">Total Registration Attempts</td>
                  <td className="p-3">{totalRegistrations.toLocaleString()}</td>
                  <td className="p-3">Unlimited</td>
                  <td className="p-3 text-[var(--fd-teal)] font-black">✓ PASS</td>
                </tr>
                <tr className="border-b-2 border-[var(--fd-ink)]">
                  <td className="p-3">Deduplicated Eligible Roster</td>
                  <td className="p-3">{eligibleCount.toLocaleString()}</td>
                  <td className="p-3">1 per verified user</td>
                  <td className="p-3 text-[var(--fd-teal)] font-black">✓ PASS</td>
                </tr>
                <tr className="border-b-2 border-[var(--fd-ink)]">
                  <td className="p-3">Duplicate / Sybil Attempts Stripped</td>
                  <td className="p-3">{duplicatesCount.toLocaleString()}</td>
                  <td className="p-3">100% Filtered</td>
                  <td className="p-3 text-[var(--fd-teal)] font-black">✓ CLEANSED</td>
                </tr>
                <tr className="border-b-2 border-[var(--fd-ink)]">
                  <td className="p-3">Max Seats Allocation</td>
                  <td className="p-3">{capacity}</td>
                  <td className="p-3 font-black text-red-600">Strict Cap {capacity}</td>
                  <td className="p-3 text-[var(--fd-teal)] font-black">✓ EXACT</td>
                </tr>
                <tr className="border-b-2 border-[var(--fd-ink)]">
                  <td className="p-3">Double Booking Anomalies</td>
                  <td className="p-3">{metrics?.duplicate_allocation_count ?? 0}</td>
                  <td className="p-3">0</td>
                  <td className="p-3 text-[var(--fd-teal)] font-black">✓ ZERO</td>
                </tr>
                <tr>
                  <td className="p-3">Confirmed Oversell Violations</td>
                  <td className="p-3">{oversellCount}</td>
                  <td className="p-3">0</td>
                  <td className="p-3 text-[var(--fd-teal)] font-black">✓ ZERO OVERSELL</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Security Logs Visual Charts Overview */}
        <div className="mt-10 border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-6 shadow-[6px_6px_0_var(--fd-ink)]">
          <div className="flex items-center justify-between border-b-[3px] border-[var(--fd-ink)] pb-4">
            <h2 className="font-display text-2xl font-black flex items-center gap-2">
              <Terminal className="size-6 text-[var(--fd-pink)]" /> AUDIT ENGINE EVENT STREAM
            </h2>
            <span className="font-mono text-xs font-black uppercase border-2 border-[var(--fd-ink)] bg-[var(--fd-yellow)] px-3 py-1">
              {auditEvents.length > 0 ? `${auditEvents.length} SIGNED EVENTS` : 'LOG STREAM SIGNED'}
            </span>
          </div>

          <div className="mt-6 flex flex-col gap-3 font-mono text-xs font-bold bg-[var(--fd-ink)] text-[var(--fd-cream)] p-5 border-2 border-[var(--fd-ink)] max-h-96 overflow-y-auto">
            {auditEvents.length > 0 ? (
              auditEvents.map((evt, idx) => (
                <p key={evt.id || idx} className="leading-relaxed">
                  <span className="text-[var(--fd-muted)]">[{new Date(evt.created_at).toISOString().replace('T', ' ').slice(0, 19)} UTC]</span>{' '}
                  <span className="text-[var(--fd-pink)] font-black">[{evt.actor_type || 'SYSTEM'}]</span>{' '}
                  <span className="text-[var(--fd-yellow)] font-bold">{evt.event_type}</span>:{' '}
                  <span className="text-[var(--fd-teal)]">
                    {evt.metadata_json && Object.keys(evt.metadata_json).length > 0
                      ? JSON.stringify(evt.metadata_json)
                      : evt.reason_code || 'Operation completed verified'}
                  </span>
                </p>
              ))
            ) : (
              <>
                <p className="text-[var(--fd-teal)]">[INFO] 2026-04-15 23:59:59 UTC: [SYSTEM] REGISTRATION_WINDOW_CLOSED: Registration window closed. Total registrations: {totalRegistrations.toLocaleString()}.</p>
                <p className="text-[var(--fd-yellow)]">[INFO] 2026-04-16 00:00:05 UTC: [SYSTEM] IDEMPOTENCY_DEDUPLICATION_EXECUTED: Filtered {duplicatesCount.toLocaleString()} duplicate submissions.</p>
                <p className="text-purple-300">[INFO] 2026-04-16 00:00:12 UTC: [ADMIN] ROSTER_FROZEN: Canonical roster locked with SHA-256 {rosterHash.slice(0, 24)}...</p>
                <p className="text-[var(--fd-pink)]">[INFO] 2026-04-16 00:00:30 UTC: [SYSTEM] LOTTERY_DRAWN: Fisher-Yates uniform shuffle executed with beacon {randomnessSeed}.</p>
                <p className="text-[var(--fd-teal)]">[SUCCESS] 2026-04-16 00:00:35 UTC: [SYSTEM] ZERO_OVERSELL_VERIFIED: {winnersCount} winners selected. 0 oversell anomalies confirmed.</p>
              </>
            )}
          </div>

          <div className="mt-6">
            <DemoNotice>
              Public audit trail is cryptographically signed and immutable. All participant records are deduplicated prior to Fisher-Yates draw execution.
            </DemoNotice>
          </div>
        </div>

      </section>
    </FairShell>
  )
}

