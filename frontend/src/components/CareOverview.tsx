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
    { label: 'Urgent now', value: urgent, detail: 'red cases open', icon: AlertTriangle, tone: 'text-red-600 bg-red-50' },
    { label: 'Medicine access', value: medicineAccess, detail: 'cost or refill cases', icon: Wallet, tone: 'text-violet-600 bg-violet-50' },
    { label: 'Below care target', value: belowTarget, detail: 'under 75% completion', icon: HeartHandshake, tone: 'text-amber-600 bg-amber-50' },
    { label: 'Handled today', value: handledToday, detail: 'outcomes recorded', icon: CheckCircle2, tone: 'text-emerald-600 bg-emerald-50' },
  ]

  return (
    <div className="px-3 pt-3 flex-shrink-0">
      <div className="rounded-2xl border border-slate-100 bg-white shadow-sm px-4 py-3 flex items-center gap-4">
        <div className="hidden xl:block min-w-[170px]">
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-emerald-600">Care command centre</p>
          <p className="text-sm font-semibold text-slate-900 mt-0.5">Today’s care work</p>
          <p className="text-[11px] text-slate-400">Signals → action → outcomes</p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 flex-1">
          {cards.map(card => (
            <div key={card.label} className="flex items-center gap-2 min-w-0 rounded-xl bg-slate-50/70 px-2.5 py-2">
              <span className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${card.tone}`}>
                <card.icon size={15} />
              </span>
              <div className="min-w-0">
                <p className="text-base font-bold text-slate-900 leading-none">{card.value}</p>
                <p className="text-[10px] font-semibold text-slate-600 truncate mt-1">{card.label}</p>
                <p className="text-[9px] text-slate-400 truncate">{card.detail}</p>
              </div>
            </div>
          ))}
        </div>

        {next && (
          <button onClick={() => onOpenAlert(next)}
            className="hidden lg:inline-flex items-center gap-2 rounded-xl bg-slate-900 text-white px-3 py-2 text-xs font-semibold hover:bg-slate-800 transition flex-shrink-0">
            Work next case <ArrowRight size={13} />
          </button>
        )}
      </div>
    </div>
  )
}
