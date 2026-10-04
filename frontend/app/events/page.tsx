'use client'

import { useEffect, useState } from 'react'
import { Filter, Search, RefreshCw, AlertCircle, Sparkles, Database } from 'lucide-react'
import { EventCard, FairShell, PageIntro, StatusPill } from '@/components/fair-shell'
import { demoEvents, DemoEvent } from '@/lib/demo-events'
import { api, FairDropApiError } from '@/lib/api'

function mapCampaignToEvent(c: any, index: number): DemoEvent {
  const colors = ['var(--fd-yellow)', 'var(--fd-pink)', 'var(--fd-teal)', 'var(--fd-cream)']
  const dateStr = c.event_start
    ? new Date(c.event_start).toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' }).toUpperCase()
    : c.registration_start
      ? new Date(c.registration_start).toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' }).toUpperCase()
      : 'APR 2026'

  return {
    id: c.id,
    category: c.allocation_method ? 'LOTTERY DROP' : 'OPEN DROP',
    name: c.name,
    venue: c.venue || 'Global Virtual Arena',
    date: dateStr,
    seats: c.capacity || 500,
    color: colors[index % colors.length],
    status: c.status ? c.status.replace(/_/g, ' ') : 'REGISTRATION OPEN',
    description: c.description || 'Fair uniform lottery allocation with zero speed bias.',
    policyVersion: c.policy_version || 'v1.0',
    rosterHash: c.policy_hash || '',
    randomnessSeed: '',
    registeredCount: 0,
    eligibleCount: 0,
    duplicateCount: 0,
    winnersCount: c.capacity || 500,
    registrationStart: c.registration_start || '',
    registrationEnd: c.registration_end || '',
  }
}

export default function EventsPage() {
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL')
  const [searchQuery, setSearchQuery] = useState<string>('')
  const [events, setEvents] = useState<DemoEvent[]>(demoEvents)
  const [loading, setLoading] = useState(false)
  const [backendCount, setBackendCount] = useState<number>(0)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)

  const fetchCampaigns = async () => {
    setLoading(true)
    setErrorMsg(null)
    try {
      const response = await api.listCampaigns(1, 50)
      const backendData = response?.data || []
      setBackendCount(backendData.length)

      if (backendData.length > 0) {
        const liveEvents = backendData.map((c: any, i: number) => mapCampaignToEvent(c, i))
        // Show live campaigns first, then fallback showcase events
        setEvents([...liveEvents, ...demoEvents])
      } else {
        // Fresh database: keep demo events active for continuous testing
        setEvents(demoEvents)
      }
    } catch (err: any) {
      console.warn('[EventsPage] Failed to fetch live campaigns, using demo events fallback:', err)
      if (err instanceof FairDropApiError) {
        setErrorMsg(`Backend connection notice: ${err.message}`)
      } else {
        setErrorMsg('Backend offline — displaying preloaded showcase drops')
      }
      setEvents(demoEvents)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchCampaigns()
  }, [])

  const categories = ['ALL', 'LOTTERY DROP', 'OPEN DROP', 'DESIGN SYSTEMS', 'MUSIC', 'SPORTS']

  const filteredEvents = events.filter((e) => {
    const matchesCategory = selectedCategory === 'ALL' || e.category.toUpperCase() === selectedCategory.toUpperCase()
    const query = searchQuery.toLowerCase()
    const matchesSearch =
      e.name.toLowerCase().includes(query) ||
      e.venue.toLowerCase().includes(query) ||
      e.description.toLowerCase().includes(query)
    return matchesCategory && matchesSearch
  })

  return (
    <FairShell active="Explore Drops">
      <PageIntro
        eyebrow="Open Drops / 01"
        title={
          <>
            CHOOSE YOUR<br />
            <span className="text-[var(--fd-teal)]">FAIR CHANCE.</span>
          </>
        }
        copy="Registration windows are calm, transparent, and designed so request volume never becomes extra lottery entries."
      />

      <section className="border-x-[3px] border-b-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] px-5 py-10 sm:px-12 lg:px-20">
        
        {/* Banner with Live Indicator */}
        <div className="flex flex-col gap-4 border-[3px] border-[var(--fd-ink)] bg-[var(--fd-yellow)] p-5 shadow-[4px_4px_0_var(--fd-ink)] sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="font-display text-2xl font-black">REGISTRATION IS NOT A RACE.</span>
              {backendCount > 0 ? (
                <span className="flex items-center gap-1 border border-[var(--fd-ink)] bg-green-200 px-2 py-0.5 font-mono text-[10px] font-black uppercase text-green-950">
                  <Database className="size-3" /> {backendCount} LIVE
                </span>
              ) : (
                <span className="flex items-center gap-1 border border-[var(--fd-ink)] bg-[var(--fd-card)] px-2 py-0.5 font-mono text-[10px] font-black uppercase text-[var(--fd-ink)]">
                  <Sparkles className="size-3" /> SHOWCASE MODE
                </span>
              )}
            </div>
            <p className="text-sm font-medium mt-1">Pick a drop, inspect the policy, and register once.</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={fetchCampaigns}
              disabled={loading}
              className="button-secondary text-xs flex items-center gap-1"
              title="Refresh drop list"
            >
              <RefreshCw className={`size-3.5 ${loading ? 'animate-spin' : ''}`} />
              {loading ? 'Refreshing...' : 'Refresh'}
            </button>
            <a className="button-primary text-xs" href="/profile">
              My Profile
            </a>
          </div>
        </div>

        {errorMsg && (
          <div className="mt-4 border-2 border-[var(--fd-ink)] bg-[var(--fd-cream)] p-3 text-xs font-mono font-bold flex items-center justify-between shadow-[2px_2px_0_var(--fd-ink)]">
            <div className="flex items-center gap-2">
              <AlertCircle className="size-4 shrink-0 text-amber-600" />
              <span>{errorMsg}</span>
            </div>
            <button onClick={fetchCampaigns} className="underline hover:text-[var(--fd-pink)] cursor-pointer">
              Retry
            </button>
          </div>
        )}

        {/* Category Filters */}
        <div className="mt-8 flex flex-wrap gap-3">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`border-[3px] border-[var(--fd-ink)] px-4 py-2 font-mono text-xs font-black uppercase shadow-[3px_3px_0_var(--fd-ink)] transition-colors ${
                selectedCategory === cat ? 'bg-[var(--fd-pink)] text-[var(--fd-ink)]' : 'bg-[var(--fd-cream)] hover:bg-[var(--fd-yellow)]'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Search Block */}
        <div className="mt-6 flex flex-col gap-4 sm:flex-row">
          <label className="flex flex-1 items-center gap-3 border-[3px] border-[var(--fd-ink)] bg-[var(--fd-cream)] px-4 py-3 shadow-[3px_3px_0_var(--fd-ink)]">
            <Search className="size-5" />
            <input
              aria-label="Search events"
              placeholder="Search by event title, city, or venue..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-transparent outline-none font-medium placeholder:text-[var(--fd-ink)]/50"
            />
          </label>
          <div className="flex items-center justify-center border-[3px] border-[var(--fd-ink)] bg-[var(--fd-card)] px-5 py-3 font-mono text-xs font-black uppercase shadow-[3px_3px_0_var(--fd-ink)]">
            <Filter className="mr-2 size-4" /> Drops ({filteredEvents.length})
          </div>
        </div>

        {/* Cards Grid */}
        <div className="mt-8 grid gap-6 lg:grid-cols-3">
          {filteredEvents.map((event) => (
            <EventCard key={event.id} event={event} />
          ))}
        </div>
      </section>
    </FairShell>
  )
}
