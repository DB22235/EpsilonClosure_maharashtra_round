'use client'

import Link from 'next/link'
import { useParams } from 'next/navigation'
import { ShieldAlert, Play, CheckCircle2, Zap, AlertTriangle, RefreshCw } from 'lucide-react'
import { AdminShell, DemoNotice } from '@/components/fair-shell'
import { getDemoEvent } from '@/lib/demo-events'
import { useState } from 'react'

export default function AdminCampaignSimulationsPage() {
  const params = useParams()
  const campaignId = (params?.campaignId as string) || 'camp_demo_001'
  const event = getDemoEvent(campaignId)

  const [runningSim, setRunningSim] = useState(false)
  const [simResults, setSimResults] = useState(true)

  const runSimulation = () => {
    setRunningSim(true)
    setTimeout(() => {
      setRunningSim(false)
      setSimResults(true)
    }, 2500)
  }

  return (
    <AdminShell campaignId={campaignId} activeTab="Simulations">
      <div className="border-x-[3px] border-b-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-6 sm:p-10">
        
        <div className="flex flex-col gap-4 border-[3px] border-[var(--fd-ink)] bg-[var(--fd-yellow)] p-6 shadow-[6px_6px_0_var(--fd-ink)] sm:flex-row sm:items-center sm:justify-between">
          <div>
            <span className="font-mono text-xs font-black uppercase">CAMPAIGN CONSOLE / STRESS & BOT SIMULATOR</span>
            <h1 className="font-display text-3xl font-black">ADVERSARIAL TRAFFIC & SYBIL SIMULATION</h1>
            <p className="text-xs font-mono font-bold mt-1">TEST SYSTEM UNDER 50,000 SYNTHETIC BOT CONCURRENCY</p>
          </div>
          <button
            onClick={runSimulation}
            disabled={runningSim}
            className="button-primary bg-[var(--fd-pink)] text-base"
          >
            {runningSim ? (
              <>
                <RefreshCw className="size-5 animate-spin" /> Simulating 50,000 Traffic...
              </>
            ) : (
              <>
                <Play className="size-5" /> Run Adversarial Simulation
              </>
            )}
          </button>
        </div>

        {/* Simulation Output Dashboard */}
        <div className="mt-8 grid gap-6 sm:grid-cols-3">
          <div className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] p-5 shadow-[4px_4px_0_var(--fd-ink)]">
            <span className="metric-label">Simulated Bot Requests</span>
            <strong className="metric-value text-red-600">50,000</strong>
            <span className="font-mono text-[11px] font-bold">100% REJECTED AT DEDUPLICATION</span>
          </div>

          <div className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] p-5 shadow-[4px_4px_0_var(--fd-ink)]">
            <span className="metric-label">Bot Win Rate Advantage</span>
            <strong className="metric-value text-[var(--fd-teal)]">0.00%</strong>
            <span className="font-mono text-[11px] font-bold">EXACT SAME ODDS AS HUMAN</span>
          </div>

          <div className="border-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] p-5 shadow-[4px_4px_0_var(--fd-ink)]">
            <span className="metric-label">Oversell Anomaly Count</span>
            <strong className="metric-value text-[var(--fd-teal)]">0</strong>
            <span className="font-mono text-[11px] font-bold">STRICT 500 INVENTORY HOLD</span>
          </div>
        </div>

        {/* Simulation Verdict Sheet */}
        <div className="mt-8 border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] p-6 shadow-[6px_6px_0_var(--fd-ink)]">
          <h2 className="font-display text-2xl font-black mb-4 flex items-center gap-2">
            <ShieldAlert className="size-6 text-[var(--fd-pink)]" /> SIMULATION VERDICT REPORT
          </h2>

          <div className="bg-[var(--fd-ink)] text-[var(--fd-cream)] p-5 font-mono text-xs font-bold flex flex-col gap-2.5 border-2 border-[var(--fd-ink)]">
            <p className="text-[var(--fd-yellow)]">[SIM] Initializing 50,000 synthetic bot clients across 500 IP subnet proxies...</p>
            <p className="text-[var(--fd-teal)]">[SIM] Injecting 250,000 automated registration payload requests over 10 seconds...</p>
            <p className="text-purple-300">[SIM] Rate limiters triggered: 210,000 requests throttled with 429 Too Many Requests.</p>
            <p className="text-[var(--fd-pink)]">[SIM] Idempotency rule executed: 49,500 duplicate bot entries stripped from roster.</p>
            <p className="text-[var(--fd-teal)]">[SIM VERDICT] 500 legitimate seats allocated via uniform lottery. Bot speed advantage: 0.00%.</p>
          </div>
        </div>

        <div className="mt-8">
          <DemoNotice>
            Static Adversarial Simulator demonstrating Fair Drop's resistance to bot speed and request flooding.
          </DemoNotice>
        </div>
      </div>
    </AdminShell>
  )
}
