/**
 * One patient, in full: who they are, how their readings are trending, and every
 * message exchanged.
 *
 * Voice notes show the audio, the transcript, and **which speech model produced
 * that transcript**. That provenance is a clinical record, not a debug detail —
 * if a nurse acts on "160 over 100", they should be able to see what was heard,
 * by which model, and play back what was actually said.
 */

import { useEffect, useRef, useState } from 'react'
import {
  Activity, AlertTriangle, Bell, CheckCircle2, ClipboardCheck, Loader2, Mic,
  MessageCircle, Phone, Pill, Radio, Send, User,
} from 'lucide-react'
import { api, Escalation, Message, Patient } from '../api/client'
import {
  AdherenceRing, RiskBadge, bpRisk, channelLabel, formatDate, formatTime,
  parseBP, providerLabel, reasonLabel, reasonStyle, riskColors, timeAgo,
} from './shared'

type Props = { patient: Patient; refreshKey?: number; onActivity?: () => void }

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-wide text-slate-400 font-semibold">{label}</p>
      <p className="text-sm font-semibold text-slate-800 mt-0.5">{value}</p>
      {sub && <p className="text-[11px] text-slate-400">{sub}</p>}
    </div>
  )
}

/** Readings as a sparkline-ish strip — trend matters more than any single value. */
function BPHistory({ patient }: { patient: Patient }) {
  const reading = patient.last_checkin?.value
  const bp = reading ? parseBP(reading) : null
  if (!bp) {
    return <p className="text-xs text-slate-400">No blood-pressure readings recorded yet.</p>
  }
  const level = bpRisk(bp.sys, bp.dia)
  const c = riskColors[level]
  return (
    <div className="flex items-center gap-3">
      <div className={`px-3 py-2 rounded-xl ${c.bg} ${c.border} border`}>
        <p className={`text-lg font-bold ${c.text} leading-none font-mono`}>{bp.sys}/{bp.dia}</p>
        <p className="text-[10px] text-slate-500 mt-1">
          {patient.last_checkin?.at ? timeAgo(patient.last_checkin.at) : ''}
        </p>
      </div>
      <div className="text-xs text-slate-500">
        <p>Target below <span className="font-medium text-slate-700">140/90</span></p>
        <p className="mt-0.5">
          {level === 'red' && <span className="text-red-600 font-medium">Above the urgent threshold (160/100)</span>}
          {level === 'amber' && <span className="text-amber-600 font-medium">Above target — monitor</span>}
          {level === 'green' && <span className="text-emerald-600 font-medium">Within target</span>}
        </p>
      </div>
    </div>
  )
}

function EscalationList({ escalations }: { escalations: Escalation[] }) {
  if (!escalations.length) return null
  return (
    <div className="space-y-1.5">
      {escalations.map(e => {
        const c = riskColors[e.risk_level]
        const reading = (e.details as Record<string, unknown>)?.reading
        return (
          <div key={e.id} className={`flex items-start gap-2 px-3 py-2 rounded-xl ${c.bg} border ${c.border}`}>
            <AlertTriangle size={13} className={`${c.text} mt-0.5 flex-shrink-0`} />
            <div className="min-w-0">
              <p className={`text-xs font-semibold ${c.text}`}>
                {reasonLabel[e.reason] || e.reason}
                {typeof reading === 'string' && !e.reason.includes(reading) && <span className="font-mono ml-1">{reading}</span>}
              </p>
              <p className="text-[11px] text-slate-500">{timeAgo(e.created_at)}</p>
            </div>
          </div>
        )
      })}
    </div>
  )
}

function MessageBubble({ msg }: { msg: Message }) {
  const isClinic = msg.direction === 'outbound'
  return (
    <div className={`flex ${isClinic ? 'justify-start' : 'justify-end'}`}>
      <div className={`max-w-[80%] rounded-2xl px-3 py-2 text-sm leading-snug shadow-sm ${
        isClinic ? 'bg-white border border-slate-100 text-slate-700' : 'bg-emerald-600 text-white'}`}>

        {msg.audio_file && (
          <div className="mb-2">
            <audio controls src={api.voiceNoteUrl(msg.audio_file)} className="h-8 w-full max-w-[230px]" />
            <div className={`mt-1 flex items-center gap-1 flex-wrap text-[10px] ${
              isClinic ? 'text-slate-500' : 'text-emerald-100'}`}>
              <Mic size={9} />
              <span>transcribed by</span>
              <span className="font-semibold">
                {msg.stt_provider ? providerLabel(msg.stt_provider) : 'unknown'}
              </span>
              {msg.stt_language && (
                <span className={`px-1 rounded ${isClinic ? 'bg-slate-100' : 'bg-emerald-700'}`}>
                  {msg.stt_language}
                </span>
              )}
              {!!msg.stt_latency_ms && <span>· {(msg.stt_latency_ms / 1000).toFixed(1)}s</span>}
            </div>
          </div>
        )}

        <p className={msg.audio_file ? 'italic' : ''}>{msg.body}</p>

        <div className={`mt-1 flex items-center gap-1.5 text-[10px] ${
          isClinic ? 'text-slate-400' : 'text-emerald-100'}`}>
          <span>{formatTime(msg.created_at)}</span>
          {msg.channel && msg.channel !== 'simulator' && (
            <span className="inline-flex items-center gap-0.5">
              <Radio size={8} /> {channelLabel(msg.channel)}
            </span>
          )}
          {msg.reason && msg.reason !== 'null' && (
            <span className={`px-1.5 rounded-full font-medium ${
              isClinic ? reasonStyle[msg.reason] || 'bg-slate-100 text-slate-500' : 'bg-emerald-700 text-white'}`}>
              {msg.reason}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

export function PatientTimeline({ patient, refreshKey = 0, onActivity }: Props) {
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(true)
  const [draft, setDraft] = useState('')
  const [actionBusy, setActionBusy] = useState<'reminder' | 'checkin' | 'message' | null>(null)
  const [actionStatus, setActionStatus] = useState<{ tone: 'success' | 'error'; text: string } | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const seq = useRef(0)

  useEffect(() => {
    const mine = ++seq.current
    setLoading(true)
    api.getMessages(patient.id).then(m => {
      if (mine === seq.current) { setMessages(m); setLoading(false) }
    })
  }, [patient.id, refreshKey])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages.length])

  const voiceCount = messages.filter(m => m.audio_file).length
  const whatsappCount = messages.filter(m => m.channel === 'whatsapp').length

  async function runAction(kind: 'reminder' | 'checkin') {
    setActionBusy(kind)
    setActionStatus(null)
    try {
      const result = kind === 'reminder'
        ? await api.sendReminder(patient.id)
        : await api.sendCheckin(patient.id)
      setActionStatus({ tone: 'success', text: result.delivery_note })
      onActivity?.()
    } catch (error) {
      setActionStatus({ tone: 'error', text: error instanceof Error ? error.message : 'Action failed' })
    } finally {
      setActionBusy(null)
    }
  }

  async function sendMessage(event: React.FormEvent) {
    event.preventDefault()
    if (!draft.trim()) return
    setActionBusy('message')
    setActionStatus(null)
    try {
      const result = await api.sendOutreach(patient.id, draft)
      setDraft('')
      setActionStatus({ tone: 'success', text: result.delivery_note })
      onActivity?.()
    } catch (error) {
      setActionStatus({ tone: 'error', text: error instanceof Error ? error.message : 'Message could not be sent' })
    } finally {
      setActionBusy(null)
    }
  }

  return (
    <div className="flex flex-col h-full gap-3 min-h-0">
      {/* Header card */}
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-4 flex-shrink-0">
        <div className="flex items-start gap-3">
          <div className="w-11 h-11 rounded-2xl bg-slate-100 flex items-center justify-center flex-shrink-0">
            <User size={18} className="text-slate-400" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="font-bold text-slate-800">{patient.name}</h2>
              <RiskBadge level={patient.risk_level} />
            </div>
            <p className="text-xs text-slate-500 mt-0.5 flex items-center gap-2 flex-wrap">
              <span className="inline-flex items-center gap-1"><Phone size={10} /> {patient.phone}</span>
              {patient.age ? <span>· {patient.age} yrs</span> : null}
              {patient.doctor_name && <span>· {patient.doctor_name}</span>}
            </p>
          </div>
          <AdherenceRing pct={patient.care_completion_pct} size={52} />
        </div>

        <div className="flex items-center gap-2 mt-3 pt-3 border-t border-slate-50">
          <button onClick={() => runAction('reminder')} disabled={actionBusy !== null}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-[11px] font-semibold text-slate-600 hover:border-emerald-200 hover:bg-emerald-50 hover:text-emerald-700 disabled:opacity-50 transition">
            {actionBusy === 'reminder' ? <Loader2 size={12} className="animate-spin" /> : <Bell size={12} />}
            Send care reminder
          </button>
          <button onClick={() => runAction('checkin')} disabled={actionBusy !== null}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-[11px] font-semibold text-slate-600 hover:border-blue-200 hover:bg-blue-50 hover:text-blue-700 disabled:opacity-50 transition">
            {actionBusy === 'checkin' ? <Loader2 size={12} className="animate-spin" /> : <ClipboardCheck size={12} />}
            Request check-in
          </button>
          <span className="ml-auto text-[10px] text-slate-400">Human-triggered · logged automatically</span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4 pt-3 border-t border-slate-50">
          <Stat label="Condition" value={patient.condition || patient.service_type || '—'} />
          <Stat label="Medication"
                value={patient.drug_name || '—'}
                sub={patient.drug_dosage || undefined} />
          <Stat label="Streak" value={`${patient.streak} days`} sub="doses confirmed" />
          <Stat label="Channel"
                value={whatsappCount > 0 ? 'WhatsApp' : 'Demo'}
                sub={voiceCount > 0 ? `${voiceCount} voice note${voiceCount > 1 ? 's' : ''}` : 'text only'} />
        </div>
      </div>

      {/* Readings + escalations */}
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-4 flex-shrink-0">
        <div className="flex items-center gap-2 mb-3">
          <Activity size={14} className="text-slate-400" />
          <h3 className="text-sm font-semibold text-slate-800">Latest reading</h3>
        </div>
        <BPHistory patient={patient} />
        {patient.escalations.length > 0 && (
          <div className="mt-3 pt-3 border-t border-slate-50">
            <div className="flex items-center gap-2 mb-2">
              <Pill size={13} className="text-slate-400" />
              <h3 className="text-xs font-semibold text-slate-700">Open escalations</h3>
            </div>
            <EscalationList escalations={patient.escalations} />
          </div>
        )}
        {(patient.recent_resolutions || []).length > 0 && (
          <div className="mt-3 pt-3 border-t border-slate-50">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle2 size={13} className="text-emerald-500" />
              <h3 className="text-xs font-semibold text-slate-700">Recently handled</h3>
            </div>
            <div className="space-y-1.5">
              {patient.recent_resolutions.slice(0, 2).map(item => (
                <div key={item.id} className="rounded-xl bg-emerald-50/70 border border-emerald-100 px-3 py-2">
                  <div className="flex items-center gap-2">
                    <p className="text-xs font-semibold text-emerald-800">
                      {(item.resolution_code || 'Handled').replace(/_/g, ' ')}
                    </p>
                    <span className="ml-auto text-[10px] text-emerald-600">{item.resolved_at ? timeAgo(item.resolved_at) : ''}</span>
                  </div>
                  {item.resolution_note && <p className="text-[11px] text-slate-600 mt-0.5">{item.resolution_note}</p>}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Conversation */}
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm flex-1 flex flex-col overflow-hidden min-h-0">
        <div className="px-4 py-2.5 border-b border-slate-100 flex items-center gap-2 flex-shrink-0">
          <MessageCircle size={14} className="text-slate-400" />
          <h3 className="text-sm font-semibold text-slate-800">Conversation</h3>
          <span className="ml-auto text-[11px] text-slate-400">{messages.length} messages</span>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-2 bg-slate-50/50">
          {loading ? (
            <p className="text-center text-xs text-slate-400 py-8">Loading…</p>
          ) : messages.length === 0 ? (
            <p className="text-center text-xs text-slate-400 py-8">No messages yet.</p>
          ) : (
            messages.map((m, i) => {
              const showDate = i === 0 || formatDate(messages[i - 1].created_at) !== formatDate(m.created_at)
              return (
                <div key={m.id}>
                  {showDate && (
                    <div className="text-center my-3">
                      <span className="text-[10px] bg-white text-slate-400 px-2 py-0.5 rounded-full border border-slate-100">
                        {formatDate(m.created_at)}
                      </span>
                    </div>
                  )}
                  <MessageBubble msg={m} />
                </div>
              )
            })
          )}
          <div ref={bottomRef} />
        </div>
        <form onSubmit={sendMessage} className="border-t border-slate-100 bg-white p-3 flex items-end gap-2">
          <div className="flex-1">
            <label className="block text-[10px] uppercase tracking-wide font-semibold text-slate-400 mb-1">Care-team message</label>
            <textarea value={draft} onChange={event => setDraft(event.target.value)} rows={2}
              placeholder={`Message ${patient.name.split(' ')[0]}…`}
              className="w-full resize-none rounded-xl border border-slate-200 px-3 py-2 text-xs text-slate-700 outline-none focus:border-emerald-400 focus:ring-2 focus:ring-emerald-100" />
          </div>
          <button type="submit" disabled={actionBusy !== null || !draft.trim()}
            className="h-9 inline-flex items-center gap-1.5 rounded-xl bg-emerald-600 px-3 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-50 transition">
            {actionBusy === 'message' ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />}
            Send
          </button>
        </form>
        {actionStatus && (
          <div className={`px-3 py-1.5 text-[10px] font-medium border-t ${
            actionStatus.tone === 'success'
              ? 'bg-emerald-50 border-emerald-100 text-emerald-700'
              : 'bg-red-50 border-red-100 text-red-700'
          }`}>
            {actionStatus.text}
          </div>
        )}
      </div>
    </div>
  )
}
