import { useEffect, useState } from 'react'
import { AlertTriangle, CalendarClock, CircleAlert, RefreshCw, Send } from 'lucide-react'
import { api, Escalation, TodayWorklist } from '../api/client'

type Props = {
  refreshKey: number
  onOpenAlert: (alert: Escalation) => void
  onSelectPatient: (patientId: number) => void
}

export function TodayQueue({ refreshKey, onOpenAlert, onSelectPatient }: Props) {
  const [worklist, setWorklist] = useState<TodayWorklist | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    api.getTodayWorklist()
      .then(data => active && setWorklist(data))
      .catch(reason => active && setError(reason instanceof Error ? reason.message : 'Queue unavailable'))
    return () => { active = false }
  }, [refreshKey])

  if (error) return <div className="mx-3 mt-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">{error}</div>
  if (!worklist) return <div className="mx-3 mt-3 flex items-center gap-2 text-xs text-slate-400"><RefreshCw size={13} className="animate-spin" /> Loading today’s queue…</div>

  const cards = [
    { label: 'Unacknowledged', value: worklist.counts.unacknowledged, icon: CircleAlert, tone: 'text-red-700 bg-red-50' },
    { label: 'Appointments', value: worklist.counts.appointments, icon: CalendarClock, tone: 'text-blue-700 bg-blue-50' },
    { label: 'Delivery failures', value: worklist.counts.failed_deliveries, icon: Send, tone: 'text-amber-700 bg-amber-50' },
  ]

  return (
    <section className="mx-3 mt-3 rounded-2xl border border-slate-100 bg-white p-3 shadow-sm" aria-label="Today's care queue">
      <div className="mb-3 flex items-center justify-between">
        <div>
          <h2 className="text-sm font-bold text-slate-900">Today</h2>
          <p className="text-[11px] text-slate-500">Work that needs a person—not another dashboard metric.</p>
        </div>
        <span className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">{worklist.date}</span>
      </div>
      <div className="grid grid-cols-3 gap-2">
        {cards.map(card => (
          <div key={card.label} className={`rounded-xl px-3 py-2 ${card.tone}`}>
            <card.icon size={14} aria-hidden="true" />
            <p className="mt-1 text-xl font-bold">{card.value}</p>
            <p className="text-[10px] font-semibold">{card.label}</p>
          </div>
        ))}
      </div>
      {(worklist.alerts.length > 0 || worklist.failed_deliveries.length > 0) && (
        <div className="mt-3 flex gap-2 overflow-x-auto pb-1">
          {worklist.alerts.slice(0, 4).map(alert => (
            <button key={`alert-${alert.id}`} onClick={() => onOpenAlert(alert)}
              className="min-w-56 rounded-xl border border-red-100 bg-red-50 p-3 text-left hover:border-red-300 focus:outline-none focus:ring-2 focus:ring-red-200">
              <div className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-wide text-red-600">
                <AlertTriangle size={12} /> {alert.risk_level} {alert.overdue ? '· overdue' : ''}
              </div>
              <p className="mt-1 truncate text-xs font-bold text-slate-800">{alert.patient_name}</p>
              <p className="mt-0.5 line-clamp-2 text-[11px] text-slate-600">{alert.reason}</p>
            </button>
          ))}
          {worklist.failed_deliveries.slice(0, 3).map(item => (
            <button key={`delivery-${item.id}`} onClick={() => onSelectPatient(item.patient_id)}
              className="min-w-56 rounded-xl border border-amber-100 bg-amber-50 p-3 text-left hover:border-amber-300 focus:outline-none focus:ring-2 focus:ring-amber-200">
              <p className="text-[10px] font-bold uppercase tracking-wide text-amber-700">Delivery failed</p>
              <p className="mt-1 truncate text-xs font-bold text-slate-800">{item.patient_name}</p>
              <p className="mt-0.5 line-clamp-2 text-[11px] text-slate-600">{item.delivery_error}</p>
            </button>
          ))}
        </div>
      )}
    </section>
  )
}
