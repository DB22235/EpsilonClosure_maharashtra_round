export interface DemoEvent {
  id: string
  category: string
  name: string
  venue: string
  date: string
  seats: number
  color: string
  status: string
  description: string
  policyVersion: string
  rosterHash: string
  randomnessSeed: string
  registeredCount: number
  eligibleCount: number
  duplicateCount: number
  winnersCount: number
  registrationStart: string
  registrationEnd: string
}

export const demoEvents: DemoEvent[] = [
  {
    id: 'camp_demo_001',
    category: 'DESIGN SYSTEMS',
    name: 'Future / Forward 2026',
    venue: 'Austin Convention Center, TX',
    date: 'APR 18, 2026',
    seats: 500,
    color: 'var(--fd-yellow)',
    status: 'Registration open',
    description: 'A design systems conference exploring the intersection of accessibility, performance, and modern tooling. 500 curated seats, uniform lottery allocation.',
    policyVersion: 'v1.0.4',
    rosterHash: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    randomnessSeed: 'beacon_drand_round_3849120',
    registeredCount: 42861,
    eligibleCount: 41205,
    duplicateCount: 1656,
    winnersCount: 500,
    registrationStart: '2026-04-01 09:00 UTC',
    registrationEnd: '2026-04-15 23:59 UTC'
  },
  {
    id: 'camp_demo_002',
    category: 'MUSIC',
    name: 'Sunset Sessions Brooklyn',
    venue: 'Navy Yard Pier 17, NY',
    date: 'MAY 02, 2026',
    seats: 500,
    color: 'var(--fd-pink)',
    status: 'Registration opens soon',
    description: 'An intimate outdoor music festival in Brooklyn. Limited to 500 attendees. Uniform lottery allocation.',
    policyVersion: 'v1.0.2',
    rosterHash: 'f4d8a11278bc2d149afbf4c8996fb92427ae41e4649b934ca495991b7852b899',
    randomnessSeed: 'beacon_drand_round_3849200',
    registeredCount: 18400,
    eligibleCount: 17900,
    duplicateCount: 500,
    winnersCount: 500,
    registrationStart: '2026-04-10 12:00 UTC',
    registrationEnd: '2026-04-28 23:59 UTC'
  },
  {
    id: 'camp_demo_003',
    category: 'SPORTS',
    name: 'City Run Club Marathon',
    venue: 'Waterfront Park, Portland, OR',
    date: 'JUN 11, 2026',
    seats: 500,
    color: 'var(--fd-teal)',
    status: 'Registration opens soon',
    description: 'Portland\'s premier urban run event. 500 places, uniform lottery, results in 48 hours.',
    policyVersion: 'v1.0.3',
    rosterHash: '9a8b7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b',
    randomnessSeed: 'beacon_drand_round_3849300',
    registeredCount: 29500,
    eligibleCount: 28800,
    duplicateCount: 700,
    winnersCount: 500,
    registrationStart: '2026-05-01 08:00 UTC',
    registrationEnd: '2026-05-25 23:59 UTC'
  }
]

export function getDemoEvent(campaignId: string): DemoEvent {
  return demoEvents.find(e => e.id === campaignId) || {
    ...demoEvents[0],
    id: campaignId,
    name: campaignId.replace(/_/g, ' ').toUpperCase()
  }
}
