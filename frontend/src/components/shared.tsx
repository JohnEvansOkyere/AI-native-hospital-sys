/**
 * Shared UI primitives and formatters.
 *
 * Extracted so the clinical dashboard and the WhatsApp demo pane render risk,
 * adherence and timestamps identically — a green badge must mean the same thing
 * wherever a nurse sees it.
 */

export const riskColors = {
  green: { bg: 'bg-emerald-100', text: 'text-emerald-700', dot: 'bg-emerald-500', border: 'border-emerald-200', ring: '#22c55e' },
  amber: { bg: 'bg-amber-100', text: 'text-amber-700', dot: 'bg-amber-500', border: 'border-amber-200', ring: '#f59e0b' },
  red: { bg: 'bg-red-100', text: 'text-red-700', dot: 'bg-red-500', border: 'border-red-200', ring: '#ef4444' },
} as const

export const riskLabel = { green: 'On Track', amber: 'Watch', red: 'Urgent' } as const

export type RiskLevel = keyof typeof riskColors

/** Ordering for triage: the most urgent patient must always surface first. */
export const riskRank: Record<RiskLevel, number> = { red: 0, amber: 1, green: 2 }

export function RiskBadge({ level }: { level: RiskLevel }) {
  const c = riskColors[level]
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold ${c.bg} ${c.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot} ${level === 'red' ? 'pulse-red' : ''}`} />
      {riskLabel[level]}
    </span>
  )
}

export function AdherenceRing({ pct, size = 48 }: { pct: number; size?: number }) {
  const r = (size - 6) / 2
  const circ = 2 * Math.PI * r
  const fill = circ * (1 - pct / 100)
  const color = pct >= 75 ? '#22c55e' : pct >= 50 ? '#f59e0b' : '#ef4444'
  return (
    <svg width={size} height={size} className="rotate-[-90deg]">
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#e2e8f0" strokeWidth={5} />
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth={5}
        strokeDasharray={circ} strokeDashoffset={fill} strokeLinecap="round"
        style={{ transition: 'stroke-dashoffset 0.6s ease' }} />
      <text x="50%" y="50%" textAnchor="middle" dominantBaseline="middle"
        className="rotate-90"
        style={{ transform: `rotate(90deg) translate(0, -${size / 2}px) translate(${size / 2}px, 0)`, fontSize: size * 0.22, fontWeight: 700, fill: color }}>
        {pct}%
      </text>
    </svg>
  )
}

/** Why a patient was escalated, in the clinic's language rather than a code. */
export const reasonLabel: Record<string, string> = {
  cost: 'Cannot afford medicine',
  forgot: 'Forgetting doses',
  side_effect: 'Side effects',
  ran_out: 'Ran out of medicine',
  other: 'Other concern',
}

export const reasonStyle: Record<string, string> = {
  cost: 'bg-red-100 text-red-700',
  forgot: 'bg-blue-100 text-blue-700',
  side_effect: 'bg-purple-100 text-purple-700',
  ran_out: 'bg-orange-100 text-orange-700',
  other: 'bg-slate-100 text-slate-600',
}

export function providerLabel(p: string): string {
  if (p.startsWith('local_whisper')) return 'Local Whisper'
  if (p === 'openai_whisper') return 'Whisper API'
  if (p === 'sahara') return 'Intron Sahara'
  if (p === 'cartesia') return 'Cartesia Ink'
  return p
}

/** TTS providers are different products from the STT ones sharing their vendor
 *  name — Cartesia Ink listens, Cartesia Sonic speaks. Kept separate from
 *  providerLabel so an outbound message never gets labelled with a listener. */
export function voiceLabel(p: string): string {
  if (p === 'intron') return 'Intron TTS'
  if (p === 'cartesia') return 'Cartesia Sonic'
  return p
}

export function channelLabel(c?: string | null): string {
  if (c === 'whatsapp') return 'WhatsApp'
  if (c === 'sms') return 'SMS'
  if (c === 'ussd') return 'USSD'
  return 'Demo'
}

export function formatTime(ts: string) {
  return new Date(ts).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
}

export function formatDate(ts: string) {
  const d = new Date(ts)
  const diff = Math.floor((Date.now() - d.getTime()) / 86400000)
  if (diff === 0) return 'Today'
  if (diff === 1) return 'Yesterday'
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })
}

/** "3h ago" — clinic staff triage on recency, not wall-clock times. */
export function timeAgo(ts: string): string {
  const mins = Math.floor((Date.now() - new Date(ts).getTime()) / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  return days === 1 ? 'yesterday' : `${days}d ago`
}

export function formatDuration(ms: number): string {
  const total = Math.floor(ms / 1000)
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`
}

/** Parse "142/95" into numbers; null when a reading isn't a BP. */
export function parseBP(value: string): { sys: number; dia: number } | null {
  const m = value.match(/(\d{2,3})\s*\/\s*(\d{2,3})/)
  return m ? { sys: +m[1], dia: +m[2] } : null
}

/**
 * BP → risk, mirroring backend/services/ai.py:assess_bp_risk.
 *
 * Duplicated deliberately: this is display only. The backend's rule is the one
 * that actually escalates, and it must stay the single source of clinical truth.
 */
export function bpRisk(sys: number, dia: number): RiskLevel {
  if (sys >= 160 || dia >= 100) return 'red'
  if (sys >= 140 || dia >= 90) return 'amber'
  return 'green'
}
