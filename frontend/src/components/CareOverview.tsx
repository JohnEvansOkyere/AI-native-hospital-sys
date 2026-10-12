import { AlertTriangle, ArrowRight, CheckCircle2, HeartHandshake, Wallet } from 'lucide-react'
import { Escalation, Patient } from '../api/client'

type Props = {
  patients: Patient[]
  alerts: Escalation[]
  onOpenAlert: (alert: Escalation) => void
}

function isToday(value?: string | null): boolean {
  if (!value) return false
  const date = new Date(value)
  const today = new Date()
  return date.getFullYear() === today.getFullYear()
    && date.getMonth() === today.getMonth()
    && date.getDate() === today.getDate()
}

export function CareOverview({ patients, alerts, onOpenAlert }: Props) {
  const urgent = alerts.filter(alert => alert.risk_level === 'red').length
  const medicineAccess = alerts.filter(alert => {
    const text = `${alert.reason} ${String(alert.details.reason || '')}`.toLowerCase()
    return text.includes('cost') || text.includes('afford') || text.includes('ran out') || text.includes('refill')
  }).length
  const belowTarget = patients.filter(patient => patient.care_completion_pct < 75).length
  const handledToday = new Set(
    patients.flatMap(patient => patient.recent_resolutions || [])
      .filter(item => isToday(item.resolved_at))
      .map(item => item.id),
  ).size
  const next = [...alerts].sort((a, b) => {
    if (a.risk_level !== b.risk_level) return a.risk_level === 'red' ? -1 : 1
    return new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
  })[0]

  const cards = [
    { label: 'Urgent cases', value: urgent, detail: 'Open red risk alerts', icon: AlertTriangle, tone: 'text-red-700 bg-red-50', edge: 'border-t-red-500' },
    { label: 'Medicine access', value: medicineAccess, detail: 'Cost or refill barriers', icon: Wallet, tone: 'text-violet-700 bg-violet-50', edge: 'border-t-violet-500' },
    { label: 'Follow-up needed', value: belowTarget, detail: 'Care completion below 75%', icon: HeartHandshake, tone: 'text-amber-700 bg-amber-50', edge: 'border-t-amber-500' },
    { label: 'Resolved today', value: handledToday, detail: 'Outcomes recorded', icon: CheckCircle2, tone: 'text-emerald-700 bg-emerald-50', edge: 'border-t-emerald-600' },
  ]

  return (
    <section aria-label="Care activity summary">
      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
          {cards.map(card => (
            <div key={card.label} className={`min-w-0 rounded-xl border border-slate-200 border-t-2 ${card.edge} bg-white p-3 shadow-sm sm:p-4`}>
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="text-xs font-medium text-slate-500">{card.label}</p>
                  <p className="mt-2 text-2xl font-semibold leading-none tracking-tight text-slate-900">{card.value}</p>
                </div>
                <span className={`flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg ${card.tone}`}>
                  <card.icon size={17} />
                </span>
              </div>
              <p className="mt-3 truncate text-[11px] text-slate-500">{card.detail}</p>
            </div>
          ))}
      </div>
      {next && (
        <button onClick={() => onOpenAlert(next)}
          className="mt-3 inline-flex items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-emerald-500">
          Open highest priority case <ArrowRight size={13} />
        </button>
      )}
    </section>
  )
}
