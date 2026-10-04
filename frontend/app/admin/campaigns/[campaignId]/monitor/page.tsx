'use client'

import Link from 'next/link'
import { useParams } from 'next/navigation'
import { Activity, AlertOctagon, CheckCircle2, Shield, Zap } from 'lucide-react'
import { AdminShell, DemoNotice, Metric, StatusPill } from '@/components/fair-shell'
import { getDemoEvent } from '@/lib/demo-events'

export default function AdminCampaignMonitorPage() {
  const params = useParams()
  const campaignId = (params?.campaignId as string) || 'camp_demo_001'
  const event = getDemoEvent(campaignId)

  return (
    <AdminShell campaignId={campaignId} activeTab="Monitor">
      <div className="border-x-[3px] border-b-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-6 sm:p-10">
        
        <div className="flex flex-col gap-4 border-[3px] border-[var(--fd-ink)] bg-[var(--fd-yellow)] p-6 shadow-[6px_6px_0_var(--fd-ink)] sm:flex-row sm:items-center sm:justify-between">
          <div>
            <span className="font-mono text-xs font-black uppercase">CAMPAIGN CONSOLE / MONITOR</span>
            <h1 className="font-display text-3xl font-black">REAL-TIME TRAFFIC & RISK METRICS</h1>
            <p className="text-xs font-mono font-bold mt-1">RATE LIMITERS & TURNSTILE VERIFICATION HEALTH</p>
          </div>
          <span className="flex items-center gap-2 font-mono text-xs font-black border-2 border-[var(--fd-ink)] bg-[var(--fd-teal)] px-3 py-1">
            <span className="size-3 rounded-full bg-green-600 animate-pulse" /> LIVE STREAM ACTIVE
          </span>
        </div>

        <div className="mt-8 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
          <div className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] p-5 shadow-[4px_4px_0_var(--fd-ink)]">
            <span className="metric-label">Current RPS</span>
            <strong className="metric-value text-[var(--fd-pink)]">1,480</strong>
            <span className="font-mono text-[11px] font-bold">PEAK: 12,500 RPS</span>
          </div>
          <div className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] p-5 shadow-[4px_4px_0_var(--fd-ink)]">
            <span className="metric-label">Queue Depth</span>
            <strong className="metric-value">420</strong>
            <span className="font-mono text-[11px] font-bold text-[var(--fd-teal)]">AVG WAIT: 3.2s</span>
          </div>
          <div className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] p-5 shadow-[4px_4px_0_var(--fd-ink)]">
            <span className="metric-label">Rate-Limited Requests</span>
            <strong className="metric-value text-red-600">8,420</strong>
            <span className="font-mono text-[11px] font-bold">429 HTTP BLOCKS</span>
          </div>
          <div className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] p-5 shadow-[4px_4px_0_var(--fd-ink)]">
            <span className="metric-label">High-Risk Suspicious</span>
            <strong className="metric-value text-amber-600">3.2%</strong>
            <span className="font-mono text-[11px] font-bold">CHALLENGE ISSUED</span>
          </div>
        </div>

        {/* Live Traffic Feed Logs */}
        <div className="mt-10 border-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] p-6 shadow-[6px_6px_0_var(--fd-ink)]">
          <h2 className="font-display text-2xl font-black mb-4">TRAFFIC & ADMISSION INGESTION LOG</h2>

          <div className="bg-[var(--fd-ink)] text-[var(--fd-cream)] p-5 font-mono text-xs font-bold flex flex-col gap-2.5 border-2 border-[var(--fd-ink)]">
            <p className="text-[var(--fd-teal)]">[PERMIT_OK] 14:02:18.102 IP=198.51.100.42 Token=PERMIT-84920 Risk=LOW (0.02)</p>
            <p className="text-[var(--fd-yellow)]">[CHALLENGE] 14:02:18.145 IP=203.0.113.88 Turnstile required Risk=MEDIUM (0.45)</p>
            <p className="text-red-400">[RATE_LIMIT] 14:02:18.200 IP=198.51.100.99 Burst threshold exceeded (50 req/sec) → HTTP 429</p>
            <p className="text-[var(--fd-teal)]">[PERMIT_OK] 14:02:18.290 IP=198.51.100.104 Token=PERMIT-84921 Risk=LOW (0.01)</p>
            <p className="text-[var(--fd-pink)]">[IDEMPOTENCY] 14:02:18.330 User=alex.morgan@example.com duplicate registration attempt detected → Stripped</p>
          </div>
        </div>

        <div className="mt-8">
          <DemoNotice>
            Static Monitor View simulating live traffic ingestion and rate limit statistics.
          </DemoNotice>
        </div>
      </div>
    </AdminShell>
  )
}
