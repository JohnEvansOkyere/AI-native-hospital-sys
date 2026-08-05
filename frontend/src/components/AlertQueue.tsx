/**
 * The triage queue — what a nurse opens the dashboard to see.
 *
 * Escalations are ordered by clinical urgency, not arrival time: a red BP
 * reading outranks an older cost barrier. Each row states plainly what happened
 * and what the clinic is expected to do about it.
 */

import { AlertTriangle, Check, ChevronRight, HeartPulse, Wallet } from 'lucide-react'
import { Escalation } from '../api/client'
import { reasonLabel, riskColors, timeAgo } from './shared'

type Props = {
  alerts: Escalation[]
  onResolve: (id: number) => void
  onSelectPatient: (patientId: number) => void
}

/** Cost barriers carry the NHIS workflow; BP readings are the clinical red flag. */
function alertIcon(reason: string) {
  if (reason.toLowerCase().includes('bp') || reason.toLowerCase().includes('pressure')) {
    return <HeartPulse size={14} />
  }
  if (reason.toLowerCase().includes('cost') || reason.toLowerCase().includes('afford')) {
    return <Wallet size={14} />
  }
  return <AlertTriangle size={14} />
}

/** What the clinic should actually do — an alert without an action is just noise. */
function nextAction(alert: Escalation): string {
  const r = alert.reason.toLowerCase()
  if (r.includes('bp') || r.includes('pressure')) return 'Call patient · review medication'
  if (r.includes('cost') || r.includes('afford')) return 'Check NHIS-covered alternative'
  if (r.includes('side')) return 'Clinical review of side effects'
  if (r.includes('ran out') || r.includes('refill')) return 'Arrange refill'
  return 'Review and contact patient'
}

export function AlertQueue({ alerts, onResolve, onSelectPatient }: Props) {
  const ordered = [...alerts].sort((a, b) => {
    if (a.risk_level !== b.risk_level) return a.risk_level === 'red' ? -1 : 1
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  })

  return (
    <div className="bg-white rounded-2xl border border-slate-100 shadow-sm flex flex-col overflow-hidden h-full">
      <div className="px-4 py-3 border-b border-slate-100 flex items-center gap-2 flex-shrink-0">
        <AlertTriangle size={16} className={alerts.length ? 'text-red-500' : 'text-slate-300'} />
        <h2 className="font-semibold text-slate-800 text-sm">Needs attention</h2>
        {alerts.length > 0 && (
          <span className="ml-auto text-xs font-bold bg-red-100 text-red-700 px-2 py-0.5 rounded-full">
            {alerts.length}
          </span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto">
        {ordered.length === 0 ? (
          <div className="p-8 text-center">
            <Check size={28} className="text-emerald-400 mx-auto mb-2" />
            <p className="text-sm text-slate-500 font-medium">No open alerts</p>
            <p className="text-xs text-slate-400 mt-1">Every patient is on track.</p>
          </div>
        ) : (
          <ul className="divide-y divide-slate-50">
            {ordered.map(a => {
              const c = riskColors[a.risk_level]
              const reading = (a.details as Record<string, unknown>)?.reading
              return (
                <li key={a.id} className={`px-4 py-3 border-l-4 ${
                  a.risk_level === 'red' ? 'border-l-red-500' : 'border-l-amber-400'}`}>
                  <div className="flex items-start gap-2">
                    <span className={`mt-0.5 ${c.text}`}>{alertIcon(a.reason)}</span>
                    <div className="flex-1 min-w-0">
                      <button
                        onClick={() => a.patient_id && onSelectPatient(a.patient_id)}
                        className="font-semibold text-sm text-slate-800 hover:text-emerald-700 flex items-center gap-1 group">
                        {a.patient_name || `Patient ${a.patient_id}`}
                        <ChevronRight size={12} className="opacity-0 group-hover:opacity-100 transition" />
                      </button>

                      <p className="text-xs text-slate-600 mt-0.5">
                        {reasonLabel[a.reason] || a.reason}
                        {typeof reading === 'string' && (
                          <span className="ml-1 font-mono font-semibold text-slate-800">{reading}</span>
                        )}
                      </p>

                      <p className="text-[11px] text-slate-500 mt-1 flex items-center gap-1">
                        <span className={`px-1.5 py-px rounded ${c.bg} ${c.text} font-medium`}>
                          {nextAction(a)}
                        </span>
                      </p>
                      <p className="text-[11px] text-slate-400 mt-1">{timeAgo(a.created_at)}</p>
                    </div>

                    <button
                      onClick={() => onResolve(a.id)}
                      title="Mark as handled"
                      className="flex-shrink-0 text-[11px] px-2 py-1 rounded-lg border border-slate-200 text-slate-500 hover:bg-emerald-50 hover:text-emerald-700 hover:border-emerald-200 transition">
                      Done
                    </button>
                  </div>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </div>
  )
}
