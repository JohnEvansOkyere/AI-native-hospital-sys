import { useEffect, useState } from 'react'
import { AlertTriangle, Bell, CalendarClock, CircleAlert, RefreshCw, Send } from 'lucide-react'
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
      .then(data => {
        if (!active) return
        setWorklist(data)
        setError('')
      })
      .catch(reason => active && setError(reason instanceof Error ? reason.message : 'Queue unavailable'))
    return () => { active = false }
  }, [refreshKey])

  if (error) return <div className="mx-3 mt-3 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">{error}</div>
  if (!worklist) return <div className="mx-3 mt-3 flex items-center gap-2 text-xs text-slate-400"><RefreshCw size={13} className="animate-spin" /> Loading today’s queue…</div>

  const cards = [
    { label: 'Awaiting owner', value: worklist.counts.unacknowledged, icon: CircleAlert, tone: 'text-red-700 bg-red-50' },
    { label: 'Appointments', value: worklist.counts.appointments, icon: CalendarClock, tone: 'text-blue-700 bg-blue-50' },
    { label: 'Reminders due', value: worklist.counts.reminders_due, icon: Bell, tone: 'text-violet-700 bg-violet-50' },
    { label: 'Failed messages', value: worklist.counts.failed_deliveries, icon: Send, tone: 'text-amber-700 bg-amber-50' },
  ]

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm" aria-label="Today's care queue">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-900">Today’s operations</h2>
          <p className="mt-0.5 text-xs text-slate-500">Scheduled care and work that needs staff attention.</p>
        </div>
        <span className="flex-shrink-0 text-[11px] font-medium text-slate-500">{worklist.date}</span>
      </div>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {cards.map(card => (
          <div key={card.label} className="flex min-w-0 items-center gap-2 rounded-lg border border-slate-100 bg-slate-50 px-2.5 py-2">
            <span className={`flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-md ${card.tone}`}>
              <card.icon size={15} aria-hidden="true" />
            </span>
            <div className="min-w-0">
              <p className="text-lg font-semibold leading-none text-slate-900">{card.value}</p>
              <p className="mt-1 truncate text-[10px] font-medium text-slate-500">{card.label}</p>
            </div>
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
