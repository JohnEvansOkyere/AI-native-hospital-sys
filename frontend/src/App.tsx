import { useState, useEffect, useRef, useCallback } from 'react'
import { api, Patient, Message, Escalation, LanguagePair, SttStatus } from './api/client'
import { ClinicDashboard } from './components/ClinicDashboard'
import { CareActionPanel } from './components/CareActionPanel'
import ReactMarkdown from 'react-markdown'
import {
  Activity, AlertTriangle, Bell, CheckCircle, ChevronRight,
  Clock, FileText, Heart, MessageCircle, Mic, Phone, Plus,
  RefreshCw, Send, Shield, Trash2, TrendingUp, User, X, Zap
} from 'lucide-react'

// ── Helpers ────────────────────────────────────────────────────────────────

const riskColors = {
  green: { bg: 'bg-emerald-100', text: 'text-emerald-700', dot: 'bg-emerald-500', border: 'border-emerald-200' },
  amber: { bg: 'bg-amber-100', text: 'text-amber-700', dot: 'bg-amber-500', border: 'border-amber-200' },
  red: { bg: 'bg-red-100', text: 'text-red-700', dot: 'bg-red-500', border: 'border-red-200' },
}

const riskLabel = { green: 'On Track', amber: 'Watch', red: 'Urgent' }

// ── Live connection ────────────────────────────────────────────────────────
//
// Serverless hosts cap a WebSocket's lifetime (5 minutes on Vercel's Hobby
// plan), so a socket dropping is normal operation, not an error — without
// reconnection the dashboard silently goes stale mid-demo.
//
// A socket is also pinned to one function instance. A WhatsApp message handled
// by another instance can't reach this one's sockets, so callers pair this with
// a slow poll: the socket gives instant updates in the common case, the poll
// guarantees the dashboard converges in the uncommon one.
function useLiveSocket(path: string, onEvent: (data: any) => void) {
  const handlerRef = useRef(onEvent)
  handlerRef.current = onEvent

  useEffect(() => {
    let ws: WebSocket | null = null
    let retry: ReturnType<typeof setTimeout> | undefined
    let attempt = 0
    let closed = false

    const open = () => {
      if (closed) return
      const proto = location.protocol === 'https:' ? 'wss' : 'ws'
      ws = new WebSocket(`${proto}://${location.host}${path}`)

      ws.onopen = () => { attempt = 0 }
      ws.onmessage = (e) => {
        try {
          handlerRef.current(JSON.parse(e.data))
        } catch {
          // A malformed frame must not kill the connection.
        }
      }
      ws.onclose = () => {
        if (closed) return
        // Exponential backoff to 15s, so a backend that is genuinely down
        // isn't hammered while a routine 5-minute cutoff reconnects promptly.
        const delay = Math.min(1000 * 2 ** attempt++, 15000)
        retry = setTimeout(open, delay)
      }
      ws.onerror = () => ws?.close()
    }

    open()
    return () => {
      closed = true
      if (retry) clearTimeout(retry)
      // Detach before closing: onclose would otherwise schedule a reconnect
      // for a socket this effect is tearing down.
      if (ws) { ws.onclose = null; ws.close() }
    }
  }, [path])
}

// How often to reconcile with the server when no socket event arrives. Slow
// enough to be negligible load, fast enough that a missed cross-instance
// broadcast is invisible in a live demo.
const POLL_MS = 10000

// Voice: the language hint attached to a voice note. This is a hint to the
// speech model, not a constraint on the patient — they code-switch however
// they actually talk, and the transcript reflects that.
const LANGUAGE_OPTIONS: { value: LanguagePair; label: string; short: string }[] = [
  { value: 'en', label: 'English', short: 'EN' },
  { value: 'tw-en', label: 'Twi–English', short: 'TW' },
  { value: 'pcm-en', label: 'Pidgin–English', short: 'PCM' },
]

function providerLabel(p: string): string {
  if (p.startsWith('local_whisper')) return 'Local Whisper'
  if (p === 'openai_whisper') return 'Whisper API'
  if (p === 'sahara') return 'Intron Sahara'
  if (p === 'cartesia') return 'Cartesia Ink'
  return p
}

function formatDuration(ms: number): string {
  const total = Math.floor(ms / 1000)
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, '0')}`
}

type CareCategory = 'dental' | 'eye' | 'chronic' | 'general'

const categoryLabels: Record<CareCategory, string> = {
  dental: 'Dental',
  eye: 'Eye care',
  chronic: 'Chronic care',
  general: 'General care',
}

const categoryDefaults: Record<CareCategory, {
  condition: string; service_type: string; care_instructions: string
}> = {
  dental: {
    condition: 'Dental care',
    service_type: 'Tooth extraction',
    care_instructions: 'Gargle gently morning and evening; avoid smoking and hard foods for 24 hours.',
  },
  eye: {
    condition: 'Eye care',
    service_type: 'Eye follow-up',
    care_instructions: 'Follow the eye-care instructions from your clinician.',
  },
  chronic: {
    condition: 'hypertension',
    service_type: 'Chronic-care follow-up',
    care_instructions: '',
  },
  general: {
    condition: 'General care',
    service_type: 'Clinic follow-up',
    care_instructions: '',
  },
}

function RiskBadge({ level }: { level: 'green' | 'amber' | 'red' }) {
  const c = riskColors[level]
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold ${c.bg} ${c.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot} ${level === 'red' ? 'pulse-red' : ''}`} />
      {riskLabel[level]}
    </span>
  )
}

function AdherenceRing({ pct, size = 48 }: { pct: number; size?: number }) {
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
        className="rotate-90" style={{ transform: `rotate(90deg) translate(0, -${size / 2}px) translate(${size / 2}px, 0)`, fontSize: size * 0.22, fontWeight: 700, fill: color }}>
        {pct}%
      </text>
    </svg>
  )
}

function formatTime(ts: string) {
  const d = new Date(ts)
  return d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
}

function formatDate(ts: string) {
  const d = new Date(ts)
  const today = new Date()
  const diff = Math.floor((today.getTime() - d.getTime()) / 86400000)
  if (diff === 0) return 'Today'
  if (diff === 1) return 'Yesterday'
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })
}

// ── WhatsApp Chat ──────────────────────────────────────────────────────────

function WhatsAppChat({ patient, onUpdate }: { patient: Patient; onUpdate: () => void }) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  // Bumped on every load; lets us ignore stale fetches that resolve out of order
  const loadSeq = useRef(0)

  // ── Voice notes ──
  const [stt, setStt] = useState<SttStatus | null>(null)
  const [language, setLanguage] = useState<LanguagePair>('en')
  const [recording, setRecording] = useState(false)
  const [recordMs, setRecordMs] = useState(0)
  const [transcribing, setTranscribing] = useState(false)
  const [voiceError, setVoiceError] = useState('')
  const recorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const timerRef = useRef<number | null>(null)
  // Set when the user hits the bin — tells the onstop handler to discard.
  const discardRef = useRef(false)

  // De-duplicating append: ignores messages we already have (by id)
  const addMessage = useCallback((msg: Message) => {
    setMessages(prev => prev.some(m => m.id === msg.id) ? prev : [...prev, msg])
  }, [])

  // The DB is the source of truth — refetch and reconcile. Stale loads are dropped.
  const loadMessages = useCallback(async () => {
    const seq = ++loadSeq.current
    const msgs = await api.getMessages(patient.id)
    if (seq === loadSeq.current) setMessages(msgs)
  }, [patient.id])

  useEffect(() => {
    loadMessages()
  }, [loadMessages])

  useLiveSocket(`/ws/${patient.id}`, useCallback((data: any) => {
    if (data.type === 'message') addMessage(data.message)
    if (data.type === 'patient_updated') onUpdate()
  }, [onUpdate, addMessage]))

  // Backstop for the open conversation: if a WhatsApp reply was handled by a
  // different function instance, its broadcast never reaches this socket. The
  // refetch de-duplicates by id, so a message already delivered live is a no-op.
  useEffect(() => {
    const id = setInterval(loadMessages, POLL_MS)
    return () => clearInterval(id)
  }, [loadMessages])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function sendMessage() {
    const msg = input.trim()
    if (!msg || sending) return
    setInput('')
    setSending(true)
    // Optimistic echo so the patient's message shows instantly (real one arrives on reconcile)
    const tempId = -Date.now()
    addMessage({ id: tempId, direction: 'inbound', body: msg, reason: null, created_at: new Date().toISOString() })
    try {
      await api.sendMessage(patient.id, msg)
      await loadMessages()   // authoritative reconcile from DB (inbound + reply)
      onUpdate()
    } catch {
      addMessage({
        id: -Date.now() - 1, direction: 'outbound',
        body: '⚠️ Could not reach the server. Is the API running on port 8000?',
        reason: null, created_at: new Date().toISOString(),
      })
    } finally {
      setSending(false)
    }
  }

  // Which speech models are actually live, so the demo bar can say so honestly
  useEffect(() => {
    api.getSttStatus().then(setStt).catch(() => setStt(null))
  }, [])

  // Never leave the mic hot if the component unmounts mid-recording
  useEffect(() => () => {
    if (timerRef.current) window.clearInterval(timerRef.current)
    recorderRef.current?.stream.getTracks().forEach(t => t.stop())
  }, [])

  async function startRecording() {
    if (recording || transcribing) return
    setVoiceError('')
    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch {
      setVoiceError('Microphone blocked. Allow mic access to send a voice note.')
      return
    }

    // Let the browser pick its supported container; the API accepts webm/ogg/mp4.
    const recorder = new MediaRecorder(stream)
    recorderRef.current = recorder
    chunksRef.current = []
    discardRef.current = false

    recorder.ondataavailable = e => { if (e.data.size) chunksRef.current.push(e.data) }
    recorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop())
      if (timerRef.current) window.clearInterval(timerRef.current)
      const blob = new Blob(chunksRef.current, { type: recorder.mimeType })
      setRecording(false)
      if (discardRef.current || blob.size < 1000) return   // cancelled or a stray tap
      await sendVoiceNote(blob)
    }

    recorder.start()
    setRecording(true)
    setRecordMs(0)
    const startedAt = Date.now()
    timerRef.current = window.setInterval(() => setRecordMs(Date.now() - startedAt), 200)
  }

  function stopRecording(discard = false) {
    discardRef.current = discard
    recorderRef.current?.stop()
  }

  async function sendVoiceNote(blob: Blob) {
    setTranscribing(true)
    try {
      const res = await api.sendVoiceNote(patient.id, blob, language)
      // Show the model that actually transcribed, not the one we hoped would.
      // The chain falls through on failure, so the configured "active" provider
      // and the real one diverge exactly when it matters most.
      if (res.transcription.provider && res.transcription.provider !== 'none') {
        setStt(prev => prev ? { ...prev, active: res.transcription.provider } : prev)
      }
      if (res.transcription.error) {
        // Graceful degradation: the bot already replied "I couldn't hear that",
        // so surface the technical reason to the operator only.
        setVoiceError(`Speech model unavailable — ${res.transcription.error}`)
      }
      await loadMessages()
      onUpdate()
    } catch (e) {
      setVoiceError(e instanceof Error ? e.message : 'Could not send voice note')
    } finally {
      setTranscribing(false)
    }
  }

  async function sendReminder() {
    await api.sendReminder(patient.id)
    await loadMessages()
  }

  async function sendCheckin() {
    await api.sendCheckin(patient.id)
    await loadMessages()
  }

  const firstName = patient.name.split(' ')[0]
  const initials = patient.name.split(' ').map((n: string) => n[0]).join('').slice(0, 2)
  const isDental = patient.category === 'dental'
  const isChronic = patient.category === 'chronic'
  const isFollowUp = patient.category !== 'chronic'

  return (
    <div className="flex flex-col h-full bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
      {/* WA Header */}
      <div className="bg-[#075E54] text-white px-4 py-3 flex items-center gap-3">
        <div className="w-10 h-10 rounded-full bg-[#128C7E] flex items-center justify-center font-bold text-sm flex-shrink-0">
          {initials}
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-sm">{patient.name}</div>
          <div className="text-xs text-green-200 flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-green-400 inline-block" />
            {patient.phone}
          </div>
        </div>
        <div className="flex gap-2">
          <button onClick={sendReminder} title={isDental ? 'Send aftercare reminder' : 'Send care reminder'}
            className="p-1.5 rounded-full hover:bg-white/20 transition" >
            <Bell size={16} />
          </button>
          <button onClick={sendCheckin} title={isDental ? 'Send recovery check-in' : 'Send care check-in'}
            className="p-1.5 rounded-full hover:bg-white/20 transition">
            <Activity size={16} />
          </button>
        </div>
      </div>

      {/* Demo action bar */}
      <div className="bg-[#ECE5DD] border-b border-[#d4c9bf] px-3 py-1.5 flex gap-2 items-center">
        <Zap size={12} className="text-amber-600" />
        <span className="text-xs text-slate-500 font-medium">Demo — type as {firstName}:</span>
        {isFollowUp ? (
          <>
            <button onClick={() => setInput('Done, I followed the instructions')} className="text-xs bg-white border border-slate-200 px-2 py-0.5 rounded-full hover:bg-slate-50">Care done ✅</button>
            <button onClick={() => setInput(isDental ? 'I have pain and swelling' : 'I have an eye concern')} className="text-xs bg-white border border-slate-200 px-2 py-0.5 rounded-full hover:bg-slate-50">{isDental ? 'Pain + swelling 🔴' : 'Eye concern 🔴'}</button>
            <button onClick={() => setInput('I need to reschedule my recall')} className="text-xs bg-white border border-slate-200 px-2 py-0.5 rounded-full hover:bg-slate-50">Reschedule 📅</button>
          </>
        ) : (
          <>
            <button onClick={() => setInput('Yes done!')} className="text-xs bg-white border border-slate-200 px-2 py-0.5 rounded-full hover:bg-slate-50">YES ✅</button>
            <button onClick={() => setInput("I can't afford it this week")} className="text-xs bg-white border border-slate-200 px-2 py-0.5 rounded-full hover:bg-slate-50">Cost 💸</button>
            {isChronic && <button onClick={() => setInput('168/102')} className="text-xs bg-white border border-slate-200 px-2 py-0.5 rounded-full hover:bg-slate-50">High BP 🔴</button>}
            {isChronic && <button onClick={() => setInput('128/82')} className="text-xs bg-white border border-slate-200 px-2 py-0.5 rounded-full hover:bg-slate-50">Good BP ✅</button>}
          </>
        )}
      </div>

      {/* Voice bar — language hint + which speech model is actually live */}
      <div className="bg-[#ECE5DD] border-b border-[#d4c9bf] px-3 py-1.5 flex gap-2 items-center flex-wrap">
        <Mic size={12} className="text-[#075E54]" />
        <span className="text-xs text-slate-500 font-medium">Voice note language:</span>
        {LANGUAGE_OPTIONS.map(opt => (
          <button key={opt.value} onClick={() => setLanguage(opt.value)}
            title={`Hint the speech model to expect ${opt.label}`}
            className={`text-xs px-2 py-0.5 rounded-full border transition ${
              language === opt.value
                ? 'bg-[#075E54] text-white border-[#075E54]'
                : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'}`}>
            {opt.label}
          </button>
        ))}
        <span className="ml-auto text-xs text-slate-500">
          {stt === null ? '…'
            : stt.active
              ? <>model: <span className="font-medium text-[#075E54]">{providerLabel(stt.active)}</span></>
              : <span className="text-amber-700">no speech model configured</span>}
        </span>
      </div>

      {voiceError && (
        <div className="bg-amber-50 border-b border-amber-200 px-3 py-1.5 text-xs text-amber-800 flex items-start gap-2">
          <AlertTriangle size={12} className="mt-0.5 flex-shrink-0" />
          <span className="flex-1">{voiceError}</span>
          <button onClick={() => setVoiceError('')} className="text-amber-500 hover:text-amber-700"><X size={12} /></button>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2" style={{ background: '#ECE5DD' }}>
        {messages.map((msg, i) => {
          const isOut = msg.direction === 'outbound'
          const showDate = i === 0 || formatDate(messages[i - 1].created_at) !== formatDate(msg.created_at)
          return (
            <div key={msg.id}>
              {showDate && (
                <div className="text-center my-2">
                  <span className="text-xs bg-white/70 text-slate-500 px-3 py-1 rounded-full shadow-sm">
                    {formatDate(msg.created_at)}
                  </span>
                </div>
              )}
              <div className={`flex ${isOut ? 'justify-start' : 'justify-end'}`}>
                <div className={`relative max-w-[78%] px-3 pt-2 pb-5 rounded-lg shadow-sm text-sm leading-snug
                  ${isOut ? 'bg-white text-slate-800 bubble-in' : 'bg-[#DCF8C6] text-slate-800 bubble-out'}`}
                  style={{ borderRadius: isOut ? '0px 12px 12px 12px' : '12px 0px 12px 12px' }}>
                  {msg.audio_file && (
                    // Voice note: play the original, then show what the model heard.
                    // Keeping both visible is the whole point — the gap between
                    // them is what the benchmark measures.
                    <div className="mb-1.5">
                      <audio controls src={api.voiceNoteUrl(msg.audio_file)} className="h-8 w-full max-w-[220px]" />
                      <div className="mt-1 flex items-center gap-1 flex-wrap text-[10px] text-slate-500">
                        <Mic size={9} />
                        <span>heard by</span>
                        <span className="font-medium text-slate-600">
                          {msg.stt_provider ? providerLabel(msg.stt_provider) : 'unknown'}
                        </span>
                        {msg.stt_language && (
                          <span className="px-1 py-px rounded bg-slate-100 text-slate-500">{msg.stt_language}</span>
                        )}
                        {!!msg.stt_latency_ms && <span>· {(msg.stt_latency_ms / 1000).toFixed(1)}s</span>}
                      </div>
                    </div>
                  )}
                  {msg.body}
                  {msg.reason && msg.reason !== 'null' && (
                    <span className={`ml-1 text-xs px-1.5 py-0.5 rounded-full font-medium
                      ${msg.reason === 'cost' ? 'bg-red-100 text-red-600' :
                        msg.reason === 'forgot' ? 'bg-blue-100 text-blue-600' :
                        msg.reason === 'side_effect' ? 'bg-purple-100 text-purple-600' :
                        'bg-slate-100 text-slate-500'}`}>
                      {msg.reason}
                    </span>
                  )}
                  <span className="absolute bottom-1 right-2 text-[10px] text-slate-400 flex items-center gap-0.5">
                    {formatTime(msg.created_at)}
                    {!isOut && <span className="text-[#4FC3F7]">✓✓</span>}
                  </span>
                </div>
              </div>
            </div>
          )
        })}
        {sending && (
          <div className="flex justify-end">
            <div className="bg-[#DCF8C6] px-4 py-2 rounded-lg text-sm text-slate-400 italic">sending…</div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="bg-[#F0F2F5] border-t border-[#d4c9bf] p-3 flex gap-2 items-center">
        {recording ? (
          <>
            <button onClick={() => stopRecording(true)} title="Discard recording"
              className="w-10 h-10 rounded-full flex items-center justify-center text-slate-500 hover:bg-slate-200 transition">
              <Trash2 size={16} />
            </button>
            <div className="flex-1 flex items-center gap-2 text-sm text-slate-600">
              <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse" />
              <span className="tabular-nums">{formatDuration(recordMs)}</span>
              <span className="text-xs text-slate-400">recording — speak as {firstName}</span>
            </div>
            <button onClick={() => stopRecording(false)} title="Send voice note"
              className="w-10 h-10 rounded-full bg-[#25D366] flex items-center justify-center text-white shadow-md hover:bg-[#22c55e] transition">
              <Send size={16} />
            </button>
          </>
        ) : (
          <>
            <input
              className="flex-1 bg-white rounded-full px-4 py-2 text-sm border border-slate-200 outline-none focus:border-[#25D366] transition disabled:opacity-60"
              placeholder={transcribing ? 'Transcribing voice note…' : `Type as ${firstName}…`}
              value={input}
              disabled={transcribing}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && sendMessage()}
            />
            {input.trim() ? (
              <button onClick={sendMessage} disabled={sending}
                className="w-10 h-10 rounded-full bg-[#25D366] flex items-center justify-center text-white shadow-md hover:bg-[#22c55e] disabled:opacity-40 transition">
                <Send size={16} />
              </button>
            ) : (
              <button onClick={startRecording} disabled={transcribing}
                title={`Record a voice note (${LANGUAGE_OPTIONS.find(o => o.value === language)?.label})`}
                className="w-10 h-10 rounded-full bg-[#25D366] flex items-center justify-center text-white shadow-md hover:bg-[#22c55e] disabled:opacity-40 transition">
                {transcribing
                  ? <RefreshCw size={16} className="animate-spin" />
                  : <Mic size={16} />}
              </button>
            )}
          </>
        )}
      </div>
    </div>
  )
}

// ── Patient Card ───────────────────────────────────────────────────────────

function PatientCard({ patient, selected, onClick }: { patient: Patient; selected: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick}
      className={`w-full text-left px-4 py-3 flex items-center gap-3 transition-all border-b border-slate-100
        ${selected ? 'bg-emerald-50 border-l-4 border-l-emerald-500' : 'hover:bg-slate-50 border-l-4 border-l-transparent'}`}>
      <div className="relative flex-shrink-0">
        <div className={`w-11 h-11 rounded-full flex items-center justify-center text-white font-bold text-sm
          ${patient.risk_level === 'red' ? 'bg-red-400' : patient.risk_level === 'amber' ? 'bg-amber-400' : 'bg-emerald-500'}`}>
          {patient.name.split(' ').map(n => n[0]).join('').slice(0, 2)}
        </div>
        <span className={`absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full border-2 border-white
          ${patient.risk_level === 'red' ? 'bg-red-500' : patient.risk_level === 'amber' ? 'bg-amber-500' : 'bg-emerald-500'}`} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="font-semibold text-sm text-slate-800 truncate">{patient.name}</div>
        <div className="text-xs text-slate-400 truncate">{patient.service_type || categoryLabels[patient.category]}</div>
      </div>
      <div className="flex flex-col items-end gap-1 flex-shrink-0">
        <RiskBadge level={patient.risk_level} />
        <span className="text-xs text-slate-400">{patient.care_completion_pct}% care completion</span>
      </div>
    </button>
  )
}

// ── Patient Detail ─────────────────────────────────────────────────────────

function PatientDetail({ patient }: { patient: Patient }) {
  const isDental = patient.category === 'dental'
  const isFollowUp = patient.category !== 'chronic'
  const last14 = (isFollowUp ? patient.care_logs : patient.adherence_logs).slice(0, 14).reverse()

  return (
    <div className="space-y-4">
      {/* Header card */}
      <div className="bg-white rounded-2xl p-5 shadow-sm border border-slate-100">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold text-slate-800">{patient.name}</h2>
            <p className="text-sm text-slate-500">{patient.age ? `${patient.age} yrs · ` : ''}{categoryLabels[patient.category]} · {patient.doctor_name}</p>
          </div>
          <RiskBadge level={patient.risk_level} />
        </div>
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center">
            <div className="flex justify-center mb-1">
              <AdherenceRing pct={patient.care_completion_pct} size={56} />
            </div>
            <p className="text-xs text-slate-500 font-medium">14-day care completion</p>
          </div>
          <div className="text-center py-1">
            <div className="text-2xl font-bold text-slate-800">{patient.service_type || 'Care follow-up'}</div>
            <div className="text-xs text-slate-500">{categoryLabels[patient.category]}</div>
            <div className="text-xs text-slate-400 mt-1">Next follow-up: {patient.next_follow_up || 'To be scheduled'}</div>
            <div className="text-xs text-slate-400">Recall: {patient.recall_date || 'To be scheduled'}</div>
          </div>
          <div className="text-center py-1">
            {!isFollowUp && patient.last_checkin ? (
              <>
                <div className={`text-xl font-bold ${patient.last_checkin.risk === 'red' ? 'text-red-600' : patient.last_checkin.risk === 'amber' ? 'text-amber-600' : 'text-emerald-600'}`}>
                  {patient.last_checkin.value}
                </div>
                <div className="text-xs text-slate-500">Last BP reading</div>
                <div className="text-xs text-slate-400">{formatDate(patient.last_checkin.at)}</div>
              </>
            ) : isFollowUp ? (
              <>
                <div className="text-xl font-bold text-slate-700">{patient.care_logs.length}</div>
                <div className="text-xs text-slate-500">care check-ins</div>
                <div className="text-xs text-slate-400">aftercare tracked</div>
              </>
            ) : (
              <>
                <div className="text-2xl text-slate-300">—</div>
                <div className="text-xs text-slate-400">No BP reading yet</div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Category-specific care history */}
      <div className="bg-white rounded-2xl p-4 shadow-sm border border-slate-100">
        <h3 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
          <TrendingUp size={14} /> {isDental ? 'Dental Aftercare — Last 14 days' : isFollowUp ? `${categoryLabels[patient.category]} Check-ins — Last 14 days` : 'Medication Adherence — Last 14 days'}
        </h3>
        <div className="flex gap-1.5">
          {last14.map((log, i) => {
            const response = log.response
            const color = isDental
              ? response === 'done' ? 'bg-emerald-400' : response === 'concern' ? 'bg-red-400' : 'bg-amber-300'
              : response === 'yes' ? 'bg-emerald-400' : response === 'cost' ? 'bg-red-400' : response === 'no_response' ? 'bg-slate-200' : response === 'forgot' ? 'bg-blue-300' : 'bg-amber-300'
            const label = isDental
              ? response === 'done' ? '✅' : response === 'concern' ? '🔴' : '…'
              : response === 'yes' ? '✅' : response === 'cost' ? '💸' : response === 'forgot' ? '😅' : '❌'
            return <div key={i} title={`${log.date}: ${response}`} className={`flex-1 h-8 rounded-md ${color} flex items-center justify-center text-[10px] cursor-help`}>{label}</div>
          })}
          {last14.length === 0 && <p className="text-xs text-slate-400">No logs yet</p>}
        </div>
        {isFollowUp ? (
          <div className="flex gap-4 mt-2 text-xs text-slate-400">
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-emerald-400" /> Aftercare done</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-red-400" /> Concern flagged</span>
          </div>
        ) : (
          <div className="flex gap-4 mt-2 text-xs text-slate-400">
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-emerald-400" /> Taken</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-red-400" /> Cost barrier</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-blue-300" /> Forgot</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-sm bg-slate-200" /> No response</span>
          </div>
        )}
        {isFollowUp && patient.care_instructions && (
          <div className="mt-3 rounded-lg bg-slate-50 border border-slate-100 p-3 text-xs text-slate-600">
            <span className="font-semibold text-slate-700">Approved aftercare: </span>{patient.care_instructions}
          </div>
        )}
      </div>

      {/* Active escalations */}
      {patient.escalations.length > 0 && (
        <div className="bg-white rounded-2xl p-4 shadow-sm border border-slate-100">
          <h3 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
            <AlertTriangle size={14} className="text-red-500" /> Active Flags
          </h3>
          <div className="space-y-2">
            {patient.escalations.map(esc => (
              <div key={esc.id} className={`p-3 rounded-xl text-sm border ${esc.risk_level === 'red' ? 'bg-red-50 border-red-200' : 'bg-amber-50 border-amber-200'}`}>
                <div className={`font-semibold ${esc.risk_level === 'red' ? 'text-red-700' : 'text-amber-700'}`}>{esc.reason}</div>
                {esc.details && Object.keys(esc.details).map(k => (
                  <div key={k} className="text-xs text-slate-500 mt-0.5">{k}: {String(esc.details[k])}</div>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Alerts Panel ───────────────────────────────────────────────────────────

function AlertsPanel({ alerts, onResolve }: { alerts: Escalation[]; onResolve: (id: number) => void }) {
  if (alerts.length === 0) return (
    <div className="flex flex-col items-center justify-center h-32 text-slate-300">
      <CheckCircle size={32} />
      <p className="text-sm mt-2">No active alerts</p>
    </div>
  )
  return (
    <div className="space-y-2">
      {alerts.map(a => (
        <div key={a.id} className={`flex items-start gap-3 p-3 rounded-xl border ${a.risk_level === 'red' ? 'bg-red-50 border-red-200' : 'bg-amber-50 border-amber-200'}`}>
          <AlertTriangle size={16} className={`mt-0.5 flex-shrink-0 ${a.risk_level === 'red' ? 'text-red-500' : 'text-amber-500'}`} />
          <div className="flex-1 min-w-0">
            <p className="font-semibold text-sm text-slate-800">{a.patient_name}</p>
            <p className="text-xs text-slate-600">{a.reason}</p>
            <p className="text-xs text-slate-400 mt-0.5">{formatDate(a.created_at)}</p>
          </div>
          <button onClick={() => onResolve(a.id)}
            className="text-xs bg-white border border-slate-200 px-2 py-1 rounded-lg hover:bg-slate-50 text-slate-600 flex-shrink-0">
            Resolve
          </button>
        </div>
      ))}
    </div>
  )
}

// ── Enroll Modal ───────────────────────────────────────────────────────────

function EnrollModal({ onClose, onEnrolled }: { onClose: () => void; onEnrolled: (p: Patient) => void }) {
  const [form, setForm] = useState({
    name: '', phone: '+233', age: '', category: 'dental' as CareCategory,
    condition: categoryDefaults.dental.condition,
    drug_name: '', drug_dosage: '', service_type: categoryDefaults.dental.service_type,
    care_instructions: categoryDefaults.dental.care_instructions,
    next_follow_up: '', recall_date: '', doctor_name: 'Dr. Mensah'
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const p = await api.enrollPatient({ ...form, age: form.age ? Number(form.age) : null })
      onEnrolled(p)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to enroll')
    } finally {
      setLoading(false)
    }
  }

  function changeCategory(category: CareCategory) {
    const defaults = categoryDefaults[category]
    setForm(f => ({
      ...f,
      category,
      condition: defaults.condition,
      service_type: defaults.service_type,
      care_instructions: defaults.care_instructions,
      drug_name: category === 'chronic' ? 'Amlodipine' : '',
      drug_dosage: category === 'chronic' ? '5mg once daily' : '',
    }))
  }

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[calc(100vh-2rem)] flex flex-col overflow-hidden">
        <div className="flex items-center justify-between p-5 border-b flex-shrink-0">
          <h2 className="font-bold text-lg text-slate-800 flex items-center gap-2">
            <User size={18} className="text-emerald-600" /> Add Patient to Follow-up
          </h2>
          <button onClick={onClose} className="p-1 hover:bg-slate-100 rounded-full"><X size={18} /></button>
        </div>
        <form onSubmit={submit} className="flex min-h-0 flex-col">
          <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {error && <div className="bg-red-50 border border-red-200 text-red-700 text-sm p-3 rounded-xl">{error}</div>}
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2">
              <label className="text-xs font-medium text-slate-600 block mb-1">Full Name</label>
              <input required className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-emerald-400"
                placeholder="Abena Owusu" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 block mb-1">Phone (WhatsApp)</label>
              <input required className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-emerald-400"
                placeholder="+233241234567" value={form.phone} onChange={e => setForm(f => ({ ...f, phone: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 block mb-1">Age <span className="text-slate-400">(optional)</span></label>
              <input type="number" min="0" max="120"
                className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-emerald-400"
                placeholder="52" value={form.age} onChange={e => setForm(f => ({ ...f, age: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 block mb-1">Care category</label>
              <select className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm bg-white focus:outline-none focus:border-emerald-400"
                value={form.category} onChange={e => changeCategory(e.target.value as CareCategory)}>
                {(Object.keys(categoryLabels) as CareCategory[]).map(category => (
                  <option key={category} value={category}>{categoryLabels[category]}</option>
                ))}
              </select>
            </div>
            <div className="col-span-2">
              <label className="text-xs font-medium text-slate-600 block mb-1">{form.category === 'dental' ? 'Procedure / service' : 'Care service'}</label>
              <input required className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-emerald-400"
                placeholder={form.category === 'dental' ? 'Tooth extraction' : 'Clinic follow-up'} value={form.service_type} onChange={e => setForm(f => ({ ...f, service_type: e.target.value }))} />
            </div>
            {form.category === 'chronic' && (
              <>
                <div>
                  <label className="text-xs font-medium text-slate-600 block mb-1">Condition</label>
                  <input required className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-emerald-400"
                    placeholder="hypertension" value={form.condition} onChange={e => setForm(f => ({ ...f, condition: e.target.value }))} />
                </div>
                <div>
                  <label className="text-xs font-medium text-slate-600 block mb-1">Medication</label>
                  <input required className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-emerald-400"
                    placeholder="Amlodipine" value={form.drug_name} onChange={e => setForm(f => ({ ...f, drug_name: e.target.value }))} />
                </div>
                <div className="col-span-2">
                  <label className="text-xs font-medium text-slate-600 block mb-1">Dosage</label>
                  <input required className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-emerald-400"
                    placeholder="5mg once daily" value={form.drug_dosage} onChange={e => setForm(f => ({ ...f, drug_dosage: e.target.value }))} />
                </div>
              </>
            )}
            {form.category !== 'chronic' && (
              <div className="col-span-2">
                <label className="text-xs font-medium text-slate-600 block mb-1">Approved care instructions</label>
                <textarea required rows={2} className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-emerald-400 resize-none"
                  placeholder="What should the patient do after the visit?" value={form.care_instructions} onChange={e => setForm(f => ({ ...f, care_instructions: e.target.value }))} />
              </div>
            )}
            <div>
              <label className="text-xs font-medium text-slate-600 block mb-1">Next follow-up</label>
              <input type="date" className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-emerald-400"
                value={form.next_follow_up} onChange={e => setForm(f => ({ ...f, next_follow_up: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs font-medium text-slate-600 block mb-1">Recall date</label>
              <input type="date" className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-emerald-400"
                value={form.recall_date} onChange={e => setForm(f => ({ ...f, recall_date: e.target.value }))} />
            </div>
            <div className="col-span-2">
              <label className="text-xs font-medium text-slate-600 block mb-1">Assigned Doctor</label>
              <input className="w-full border border-slate-200 rounded-xl px-3 py-2 text-sm focus:outline-none focus:border-emerald-400"
                placeholder="Dr. Mensah" value={form.doctor_name} onChange={e => setForm(f => ({ ...f, doctor_name: e.target.value }))} />
            </div>
          </div>
          </div>
          <div className="flex-shrink-0 border-t bg-white p-5 pt-3">
            <button type="submit" disabled={loading}
              className="w-full bg-emerald-600 text-white py-2.5 rounded-xl font-semibold text-sm hover:bg-emerald-700 disabled:opacity-50 transition">
              {loading ? 'Adding…' : 'Add Patient'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Report Modal ───────────────────────────────────────────────────────────

function ReportModal({ onClose }: { onClose: () => void }) {
  const [report, setReport] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [generatedAt, setGeneratedAt] = useState('')

  useEffect(() => {
    api.getWeeklyReport().then(r => {
      setReport(r.report)
      setGeneratedAt(r.generated_at)
      setLoading(false)
    })
  }, [])

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[85vh] flex flex-col">
        <div className="flex items-center justify-between p-5 border-b">
          <h2 className="font-bold text-lg text-slate-800 flex items-center gap-2">
            <FileText size={18} className="text-emerald-600" /> AI-Generated Weekly Report
          </h2>
          <button onClick={onClose} className="p-1 hover:bg-slate-100 rounded-full"><X size={18} /></button>
        </div>
        <div className="flex-1 overflow-y-auto p-5">
          {loading ? (
            <div className="flex flex-col items-center justify-center h-48 gap-3 text-slate-400">
              <RefreshCw size={28} className="animate-spin text-emerald-500" />
              <p className="text-sm">Claude is generating your report…</p>
            </div>
          ) : (
            <div className="prose prose-sm prose-emerald max-w-none">
              <ReactMarkdown>{report || ''}</ReactMarkdown>
            </div>
          )}
        </div>
        {!loading && (
          <div className="p-4 border-t flex items-center justify-between">
            <span className="text-xs text-slate-400">Generated by Claude AI · {generatedAt ? new Date(generatedAt).toLocaleString() : ''}</span>
            <button onClick={() => window.print()}
              className="text-sm bg-emerald-600 text-white px-4 py-2 rounded-xl hover:bg-emerald-700 flex items-center gap-2">
              <FileText size={14} /> Print / Save PDF
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Main App ───────────────────────────────────────────────────────────────

export default function App() {
  const [patients, setPatients] = useState<Patient[]>([])
  const [alerts, setAlerts] = useState<Escalation[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [showEnroll, setShowEnroll] = useState(false)
  const [showReport, setShowReport] = useState(false)
  const [activeAlert, setActiveAlert] = useState<Escalation | null>(null)
  const [loading, setLoading] = useState(true)
  // 'clinic' is the real product surface; 'demo' is the WhatsApp simulator kept
  // as a fallback for when the live webhook can't be reached.
  const [view, setView] = useState<'clinic' | 'demo'>('clinic')
  // Bumped whenever a message lands, so the open patient timeline refetches.
  const [refreshKey, setRefreshKey] = useState(0)

  const loadData = useCallback(async () => {
    const [ps, as] = await Promise.all([api.getPatients(), api.getAlerts()])
    setPatients(ps)
    setAlerts(as)
    if (!selectedId && ps.length > 0) setSelectedId(ps[0].id)
    setLoading(false)
  }, [selectedId])

  useEffect(() => { loadData() }, [])

  // Global WebSocket for cross-patient events
  useLiveSocket('/ws/-1', useCallback((data: any) => {
    if (data.type === 'patient_updated') {
      setPatients(prev => prev.map(p => p.id === data.patient.id ? data.patient : p))
    }
    if (data.type === 'patient_enrolled') {
      setPatients(prev => prev.some(p => p.id === data.patient.id)
        ? prev.map(p => p.id === data.patient.id ? data.patient : p)
        : [...prev, data.patient])
    }
    if (data.type === 'escalation') {
      setAlerts(prev => [data.escalation, ...prev])
    }
    if (data.type === 'alert_resolved') {
      setAlerts(prev => prev.filter(a => a.id !== data.alert_id))
      if (data.patient) {
        setPatients(prev => prev.map(p => p.id === data.patient.id ? data.patient : p))
      }
    }
    // A message landed on some channel — WhatsApp included. Nudge the open
    // timeline to refetch so the clinic view stays live.
    if (data.type === 'message') {
      setRefreshKey(k => k + 1)
    }
  }, []))

  // Backstop for the patient list and the alert queue. Escalations are the
  // safety-critical ones: a red flag raised on another instance must not sit
  // invisible on the clinic screen because a broadcast missed this socket.
  useEffect(() => {
    const id = setInterval(loadData, POLL_MS)
    return () => clearInterval(id)
  }, [loadData])

  const selected = patients.find(p => p.id === selectedId) || null

  const stats = {
    total: patients.length,
    green: patients.filter(p => p.risk_level === 'green').length,
    amber: patients.filter(p => p.risk_level === 'amber').length,
    red: patients.filter(p => p.risk_level === 'red').length,
    avgCareCompletion: patients.length ? Math.round(patients.reduce((s, p) => s + p.care_completion_pct, 0) / patients.length) : 0,
  }

  const handlePatientUpdate = useCallback(() => {
    if (selectedId) {
      api.getPatient(selectedId).then(p => {
        setPatients(prev => prev.map(pp => pp.id === p.id ? p : pp))
      })
    }
    api.getAlerts().then(setAlerts)
    setRefreshKey(k => k + 1)
  }, [selectedId])

  const openCareCase = useCallback((alert: Escalation) => {
    if (alert.patient_id) setSelectedId(alert.patient_id)
    setActiveAlert(alert)
  }, [])

  const handleResolve = useCallback((id: number) => {
    const alert = alerts.find(item => item.id === id)
    if (alert) openCareCase(alert)
  }, [alerts, openCareCase])

  const handleCaseResolved = useCallback((id: number) => {
    setAlerts(prev => prev.filter(alert => alert.id !== id))
    setActiveAlert(null)
    loadData()
    setRefreshKey(key => key + 1)
  }, [loadData])

  if (loading) return (
    <div className="flex items-center justify-center h-screen bg-slate-50">
      <div className="text-center">
        <Heart size={40} className="text-emerald-500 mx-auto mb-3 animate-pulse" />
        <p className="text-slate-500 font-medium">Loading VeloxaCare…</p>
      </div>
    </div>
  )

  return (
    <div className="h-screen flex flex-col bg-slate-50 overflow-hidden">
      {/* Top nav */}
      <header className="bg-white border-b border-slate-100 px-6 py-3 flex items-center justify-between flex-shrink-0 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-emerald-600 flex items-center justify-center">
            <Heart size={16} className="text-white" />
          </div>
          <div>
            <span className="font-bold text-slate-800 text-lg">VeloxaCare</span>
            <span className="text-xs text-slate-400 ml-2">Accra Family Clinic</span>
          </div>
        </div>

        {/* Stats bar */}
        <div className="hidden md:flex items-center gap-6">
          <div className="flex items-center gap-2 text-sm">
            <div className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              <span className="text-slate-600 font-medium">{stats.green}</span>
              <span className="text-slate-400">on track</span>
            </div>
            <div className="flex items-center gap-1 ml-3">
              <span className="w-2 h-2 rounded-full bg-amber-500" />
              <span className="text-slate-600 font-medium">{stats.amber}</span>
              <span className="text-slate-400">watch</span>
            </div>
            <div className="flex items-center gap-1 ml-3">
              <span className="w-2 h-2 rounded-full bg-red-500" />
              <span className="text-slate-600 font-medium">{stats.red}</span>
              <span className="text-slate-400">urgent</span>
            </div>
          </div>
          <div className="h-6 w-px bg-slate-200" />
          <div className="text-sm">
            <span className="font-bold text-emerald-600">{stats.avgCareCompletion}%</span>
            <span className="text-slate-400 ml-1">avg care completion</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {alerts.length > 0 && (
            <div className="flex items-center gap-1 bg-red-50 border border-red-200 text-red-700 text-xs font-semibold px-3 py-1.5 rounded-full">
              <Bell size={12} />
              {alerts.length} alert{alerts.length !== 1 ? 's' : ''}
            </div>
          )}

          {/* Clinic is the product; Demo is the simulator fallback. */}
          <div className="flex rounded-xl border border-slate-200 overflow-hidden text-sm">
            <button onClick={() => setView('clinic')}
              className={`px-3 py-2 font-medium transition ${
                view === 'clinic' ? 'bg-slate-800 text-white' : 'bg-white text-slate-500 hover:bg-slate-50'}`}>
              Clinic
            </button>
            <button onClick={() => setView('demo')}
              title="WhatsApp simulator — same backend path, for demos without the live webhook"
              className={`px-3 py-2 font-medium transition ${
                view === 'demo' ? 'bg-slate-800 text-white' : 'bg-white text-slate-500 hover:bg-slate-50'}`}>
              Demo
            </button>
          </div>

          <button onClick={() => setShowReport(true)}
            className="flex items-center gap-2 bg-emerald-600 text-white text-sm px-4 py-2 rounded-xl hover:bg-emerald-700 transition font-medium">
            <FileText size={14} /> Weekly Report
          </button>
          <button onClick={() => setShowEnroll(true)}
            className="flex items-center gap-2 bg-slate-800 text-white text-sm px-4 py-2 rounded-xl hover:bg-slate-900 transition font-medium">
              <Plus size={14} /> Add Patient
          </button>
        </div>
      </header>

      {/* Main layout */}
      {view === 'clinic' ? (
        <ClinicDashboard
          patients={patients}
          alerts={alerts}
          selectedId={selectedId}
          onSelect={setSelectedId}
          onOpenAlert={openCareCase}
          onActivity={handlePatientUpdate}
          refreshKey={refreshKey}
        />
      ) : (
        /* Demo mode: the WhatsApp simulator. Patients are on real WhatsApp, but
           this runs the identical backend path — keep it as the live fallback if
           the webhook is unreachable mid-demo. */
        <div className="flex flex-1 overflow-hidden">
          <div className="w-72 flex-shrink-0 bg-white border-r border-slate-100 flex flex-col overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-100">
              <h2 className="font-semibold text-sm text-slate-700 flex items-center gap-2">
                <User size={14} /> {stats.total} Patients
              </h2>
            </div>
            <div className="flex-1 overflow-y-auto">
              {patients.map(p => (
                <PatientCard key={p.id} patient={p} selected={p.id === selectedId}
                  onClick={() => setSelectedId(p.id)} />
              ))}
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4 min-w-0">
            {alerts.length > 0 && (
              <div className="bg-white rounded-2xl p-4 shadow-sm border border-slate-100">
                <h3 className="text-sm font-semibold text-slate-700 mb-3 flex items-center gap-2">
                  <AlertTriangle size={14} className="text-red-500" />
                  Active Alerts
                  <span className="ml-auto bg-red-100 text-red-700 text-xs px-2 py-0.5 rounded-full font-bold">{alerts.length}</span>
                </h3>
                <AlertsPanel alerts={alerts} onResolve={handleResolve} />
              </div>
            )}
            {selected ? (
              <PatientDetail patient={selected} />
            ) : (
              <div className="flex flex-col items-center justify-center h-64 text-slate-300">
                <MessageCircle size={40} />
                <p className="mt-2 text-sm">Select a patient</p>
              </div>
            )}
          </div>

          <div className="w-80 flex-shrink-0 p-4 flex flex-col">
            {selected ? (
              <WhatsAppChat patient={selected} onUpdate={handlePatientUpdate} />
            ) : (
              <div className="flex-1 bg-white rounded-2xl flex items-center justify-center text-slate-300 border border-slate-100">
                <div className="text-center">
                  <MessageCircle size={32} className="mx-auto" />
                  <p className="text-sm mt-2">Select a patient to chat</p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Modals */}
      {showEnroll && (
        <EnrollModal onClose={() => setShowEnroll(false)} onEnrolled={(p) => {
          setPatients(prev => prev.some(existing => existing.id === p.id)
            ? prev.map(existing => existing.id === p.id ? p : existing)
            : [...prev, p])
          setSelectedId(p.id)
          setShowEnroll(false)
        }} />
      )}
      {showReport && <ReportModal onClose={() => setShowReport(false)} />}
      {activeAlert && (
        <CareActionPanel
          alert={activeAlert}
          patient={patients.find(patient => patient.id === activeAlert.patient_id) || null}
          onClose={() => setActiveAlert(null)}
          onResolved={handleCaseResolved}
          onMessageSent={() => {
            setRefreshKey(key => key + 1)
            if (activeAlert.patient_id) {
              api.getPatient(activeAlert.patient_id).then(patient => {
                setPatients(prev => prev.map(existing => existing.id === patient.id ? patient : existing))
              })
            }
          }}
        />
      )}
    </div>
  )
}
