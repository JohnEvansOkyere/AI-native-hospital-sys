import { useEffect, useMemo, useState } from 'react'
import {
  AlertTriangle, CheckCircle2, ClipboardCheck, Loader2, MessageSquare,
  Send, ShieldCheck, X,
} from 'lucide-react'
import {
  api, DeliveryResult, Escalation, Patient, ResolutionCode,
} from '../api/client'
import { RiskBadge, timeAgo } from './shared'

type Props = {
  alert: Escalation
  patient: Patient | null
  onClose: () => void
  onResolved: (alertId: number) => void
  onMessageSent: (result: DeliveryResult) => void
  onAcknowledged: () => void
}

const OUTCOMES: Array<{ value: ResolutionCode; label: string }> = [
  { value: 'patient_contacted', label: 'Patient contacted' },
  { value: 'appointment_booked', label: 'Appointment booked' },
  { value: 'nhis_alternative_arranged', label: 'NHIS alternative arranged' },
  { value: 'refill_arranged', label: 'Medicine refill arranged' },
  { value: 'clinician_reviewed', label: 'Clinician reviewed' },
  { value: 'other', label: 'Other outcome' },
]

function caseKind(alert: Escalation): 'cost' | 'refill' | 'bp' | 'side_effect' | 'other' {
  const text = `${alert.reason} ${String(alert.details.reason || '')}`.toLowerCase()
  if (text.includes('cost') || text.includes('afford')) return 'cost'
  if (text.includes('ran out') || text.includes('refill')) return 'refill'
  if (text.includes('bp') || text.includes('pressure') || alert.details.reading) return 'bp'
  if (text.includes('side effect') || text.includes('reaction')) return 'side_effect'
  return 'other'
}

function defaultOutcome(kind: ReturnType<typeof caseKind>): ResolutionCode {
  if (kind === 'cost') return 'nhis_alternative_arranged'
  if (kind === 'refill') return 'refill_arranged'
  if (kind === 'bp' || kind === 'side_effect') return 'clinician_reviewed'
  return 'patient_contacted'
}

function suggestedMessage(kind: ReturnType<typeof caseKind>, firstName: string): string {
  if (kind === 'cost') {
    return `Hi ${firstName}, this is your VeloxaCare team. We saw that cost is stopping you from getting your medicine. We are checking an NHIS-covered option and will contact you with the next step. Please reply if you have no medicine left.`
  }
  if (kind === 'refill') {
    return `Hi ${firstName}, this is your VeloxaCare team. We saw that you have run out of medicine. We are arranging your refill. Please reply with the name of the pharmacy you normally use.`
  }
  if (kind === 'bp') {
    return `Hi ${firstName}, this is your VeloxaCare team. We received your high blood-pressure reading and a clinician needs to review it. Please keep your phone close so we can contact you. If you have chest pain, severe headache or difficulty breathing, seek urgent medical help now.`
  }
  if (kind === 'side_effect') {
    return `Hi ${firstName}, this is your VeloxaCare team. We received your report about a possible side effect. A clinician will review it and contact you. If your symptoms become severe, please seek urgent medical help now.`
  }
  return `Hi ${firstName}, this is your VeloxaCare team. We received your message and would like to follow up. Please reply when you are available for a call.`
}

function detailLabel(key: string): string {
  return key.replace(/_/g, ' ').replace(/^./, (letter: string) => letter.toUpperCase())
}

export function CareActionPanel({
  alert, patient, onClose, onResolved, onMessageSent, onAcknowledged,
}: Props) {
  const kind = useMemo(() => caseKind(alert), [alert])
  const firstName = (patient?.name || alert.patient_name || 'there').split(' ')[0]
  const [message, setMessage] = useState(() => suggestedMessage(kind, firstName))
  const [outcome, setOutcome] = useState<ResolutionCode>(() => defaultOutcome(kind))
  const [note, setNote] = useState('')
  const [sending, setSending] = useState(false)
  const [resolving, setResolving] = useState(false)
  const [acknowledging, setAcknowledging] = useState(false)
  const [acknowledged, setAcknowledged] = useState(Boolean(alert.acknowledged_at))
  const [status, setStatus] = useState<{ tone: 'success' | 'error'; text: string } | null>(null)

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => event.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  async function contactPatient() {
    if (!patient || !message.trim()) return
    setSending(true)
    setStatus(null)
    try {
      const result = await api.sendOutreach(patient.id, message)
      onMessageSent(result)
      setStatus({ tone: 'success', text: result.delivery_note })
    } catch (error) {
      setStatus({ tone: 'error', text: error instanceof Error ? error.message : 'Message could not be sent' })
    } finally {
      setSending(false)
    }
  }

  async function resolveCase() {
    if (!note.trim()) {
      setStatus({ tone: 'error', text: 'Add a short outcome note before closing this case.' })
      return
    }
    setResolving(true)
    setStatus(null)
    try {
      await api.resolveAlert(alert.id, {
        resolution_code: outcome,
        note,
      })
      onResolved(alert.id)
    } catch (error) {
      setStatus({ tone: 'error', text: error instanceof Error ? error.message : 'Case could not be closed' })
      setResolving(false)
    }
  }

  async function acknowledge() {
    setAcknowledging(true)
    setStatus(null)
    try {
      await api.acknowledgeAlert(alert.id)
      setAcknowledged(true)
      onAcknowledged()
      setStatus({ tone: 'success', text: 'Case assigned to you and acknowledged.' })
    } catch (error) {
      setStatus({ tone: 'error', text: error instanceof Error ? error.message : 'Case could not be acknowledged' })
    } finally {
      setAcknowledging(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-950/35 backdrop-blur-[1px]" onMouseDown={onClose}>
      <aside
        className="w-full max-w-xl h-full bg-slate-50 shadow-2xl overflow-y-auto"
        onMouseDown={event => event.stopPropagation()}>
        <div className="sticky top-0 z-10 bg-white border-b border-slate-100 px-5 py-4 flex items-start gap-3">
          <div className="w-10 h-10 rounded-xl bg-red-50 text-red-600 flex items-center justify-center flex-shrink-0">
            <AlertTriangle size={18} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-[10px] uppercase tracking-[0.16em] text-slate-400 font-bold">Care case</p>
            <div className="flex items-center gap-2 mt-0.5 flex-wrap">
              <h2 className="font-bold text-slate-900">{patient?.name || alert.patient_name}</h2>
              <RiskBadge level={alert.risk_level} />
            </div>
            <p className="text-xs text-slate-500 mt-1">Opened {timeAgo(alert.created_at)}</p>
            {alert.assigned_to_name && <p className="mt-1 text-xs font-medium text-emerald-700">Owned by {alert.assigned_to_name}</p>}
          </div>
          <button onClick={onClose} aria-label="Close care case"
            className="p-2 rounded-lg text-slate-400 hover:bg-slate-100 hover:text-slate-700 transition">
            <X size={18} />
          </button>
        </div>

        <div className="p-5 space-y-4">
          {!acknowledged && (
            <button onClick={acknowledge} disabled={acknowledging}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-red-600 px-4 py-2.5 text-sm font-bold text-white hover:bg-red-700 disabled:opacity-60">
              {acknowledging ? <Loader2 size={15} className="animate-spin" /> : <ShieldCheck size={15} />}
              {acknowledging ? 'Acknowledging…' : 'Acknowledge & assign to me'}
            </button>
          )}
          <section className="bg-white border border-slate-100 rounded-2xl p-4 shadow-sm">
            <div className="flex items-center gap-2 mb-3">
              <ShieldCheck size={15} className="text-emerald-600" />
              <h3 className="text-sm font-semibold text-slate-800">Signal and evidence</h3>
              <span className="ml-auto text-[10px] text-slate-400">AI structures · rules escalate</span>
            </div>
            <p className="text-sm font-semibold text-slate-800">{alert.reason}</p>
            {Object.keys(alert.details).length > 0 && (
              <dl className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-2">
                {Object.entries(alert.details).map(([key, value]) => (
                  <div key={key} className="rounded-xl bg-slate-50 px-3 py-2">
                    <dt className="text-[10px] uppercase tracking-wide text-slate-400 font-semibold">{detailLabel(key)}</dt>
                    <dd className="text-xs text-slate-700 mt-0.5 break-words">{String(value)}</dd>
                  </div>
                ))}
              </dl>
            )}
          </section>

          <section className="bg-white border border-slate-100 rounded-2xl p-4 shadow-sm">
            <div className="flex items-center gap-2 mb-1">
              <span className="w-5 h-5 rounded-full bg-slate-900 text-white text-[11px] font-bold flex items-center justify-center">1</span>
              <MessageSquare size={14} className="text-slate-500" />
              <h3 className="text-sm font-semibold text-slate-800">Contact the patient</h3>
            </div>
            <p className="text-xs text-slate-500 mb-3 ml-7">
              Edit the approved care-team message before sending. A configured clinic sends on WhatsApp; demo mode records the same action safely.
            </p>
            <textarea value={message} onChange={event => setMessage(event.target.value)} rows={5}
              className="w-full resize-none rounded-xl border border-slate-200 p-3 text-sm text-slate-700 outline-none focus:border-emerald-400 focus:ring-2 focus:ring-emerald-100"
              placeholder="Write a patient message…" />
            <div className="mt-3 flex justify-end">
              <button onClick={contactPatient} disabled={sending || !patient || !message.trim()}
                className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50 transition">
                {sending ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
                {sending ? 'Sending…' : 'Send care message'}
              </button>
            </div>
          </section>

          <section className="bg-white border border-slate-100 rounded-2xl p-4 shadow-sm">
            <div className="flex items-center gap-2 mb-1">
              <span className="w-5 h-5 rounded-full bg-slate-900 text-white text-[11px] font-bold flex items-center justify-center">2</span>
              <ClipboardCheck size={14} className="text-slate-500" />
              <h3 className="text-sm font-semibold text-slate-800">Record the outcome</h3>
            </div>
            <p className="text-xs text-slate-500 mb-3 ml-7">
              Closing a case updates the patient’s active risk from any alerts still open and preserves this action in the patient record.
            </p>
            <label className="block text-xs font-semibold text-slate-600 mb-1">Outcome</label>
            <select value={outcome} onChange={event => setOutcome(event.target.value as ResolutionCode)}
              className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-700 outline-none focus:border-emerald-400">
              {OUTCOMES.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
            <label className="block text-xs font-semibold text-slate-600 mt-3 mb-1">Care-team note</label>
            <textarea value={note} onChange={event => setNote(event.target.value)} rows={3}
              className="w-full resize-none rounded-xl border border-slate-200 p-3 text-sm text-slate-700 outline-none focus:border-emerald-400 focus:ring-2 focus:ring-emerald-100"
              placeholder="What was done, and what happens next?" />
            <div className="mt-3 flex justify-end">
              <button onClick={resolveCase} disabled={resolving}
                className="inline-flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-50 transition">
                {resolving ? <Loader2 size={14} className="animate-spin" /> : <CheckCircle2 size={14} />}
                {resolving ? 'Closing case…' : 'Save outcome & close'}
              </button>
            </div>
          </section>

          {status && (
            <div className={`rounded-xl border px-3 py-2 text-xs font-medium ${
              status.tone === 'success'
                ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
                : 'bg-red-50 border-red-200 text-red-700'
            }`}>
              {status.text}
            </div>
          )}
        </div>
      </aside>
    </div>
  )
}
