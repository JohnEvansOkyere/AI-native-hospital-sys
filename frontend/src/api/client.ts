const BASE = '/api'

export interface Patient {
  id: number
  name: string
  phone: string
  age: number
  condition: string
  drug_name: string
  drug_dosage: string
  category: 'dental' | 'eye' | 'chronic' | 'general'
  service_type: string
  care_instructions: string
  next_follow_up: string
  recall_date: string
  enrolled_at: string
  doctor_name: string
  status: string
  risk_level: 'green' | 'amber' | 'red'
  adherence_pct: number
  care_completion_pct: number
  adherence_logs: { date: string; response: string }[]
  care_logs: { date: string; activity: string; response: string; details: string | null }[]
  streak: number
  last_checkin: { type: string; value: string; risk: string; at: string } | null
  escalations: Escalation[]
  recent_resolutions: Escalation[]
  current_flow: string
}

export interface Message {
  id: number
  direction: 'inbound' | 'outbound'
  body: string
  reason: string | null
  created_at: string
  /** Transport it arrived on / went out over: simulator | whatsapp | sms | ussd. */
  channel?: string | null
  // Voice notes only: body holds the transcript, these record how we heard it.
  audio_file?: string | null
  stt_provider?: string | null
  stt_language?: string | null
  stt_latency_ms?: number | null
}

/** Benchmark language_pair codes — a hint to the model, not a constraint on
 *  the patient. The transcript is whatever was actually said, code-switch included. */
export type LanguagePair = 'en' | 'tw-en' | 'pcm-en'

export interface SttStatus {
  configured: string[]
  pinned: string | null
  active: string | null
  /** Providers configured but failing in practice, mapped to the reason. */
  degraded?: Record<string, string>
  languages: Record<string, string>
}

export interface Transcription {
  text: string
  provider: string
  language: string
  latency_ms: number
  error: string
}

export interface VoiceNoteResult {
  inbound: Message | null
  reply: Message
  escalation_created: boolean
  transcription: Transcription
}

export interface Escalation {
  id: number
  patient_id?: number
  patient_name?: string
  reason: string
  risk_level: 'amber' | 'red'
  details: Record<string, unknown>
  created_at: string
  resolution_code?: ResolutionCode | ''
  resolution_note?: string
  resolved_by?: string
  resolved_at?: string | null
}

export type ResolutionCode =
  | 'patient_contacted'
  | 'appointment_booked'
  | 'nhis_alternative_arranged'
  | 'refill_arranged'
  | 'clinician_reviewed'
  | 'other'

export interface DeliveryResult {
  message: Message
  delivered: boolean
  channel: string
  delivery_note: string
}

export const api = {
  async getPatients(): Promise<Patient[]> {
    const r = await fetch(`${BASE}/patients`)
    return r.json()
  },

  async getPatient(id: number): Promise<Patient> {
    const r = await fetch(`${BASE}/patients/${id}`)
    return r.json()
  },

  async enrollPatient(data: {
    name: string; phone: string; age: number | null;
    category: 'dental' | 'eye' | 'chronic' | 'general'; condition: string;
    drug_name: string; drug_dosage: string; service_type: string;
    care_instructions: string; next_follow_up: string; recall_date: string;
    doctor_name: string
  }): Promise<Patient> {
    const r = await fetch(`${BASE}/patients`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    if (!r.ok) {
      const err = await r.json()
      throw new Error(err.detail || 'Enrollment failed')
    }
    return r.json()
  },

  async getMessages(patientId: number): Promise<Message[]> {
    const r = await fetch(`${BASE}/patients/${patientId}/messages?limit=80`)
    return r.json()
  },

  async sendMessage(patientId: number, message: string) {
    const r = await fetch(`${BASE}/patients/${patientId}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    })
    return r.json()
  },

  /** Send a recorded voice note. `language` is a hint to the speech model;
   *  `provider` pins one model so the same utterance can be demoed through
   *  Sahara and Whisper side by side. */
  async sendVoiceNote(
    patientId: number, audio: Blob,
    language: LanguagePair = 'en', provider?: string,
  ): Promise<VoiceNoteResult> {
    const form = new FormData()
    // Extension matters: the API validates it and the provider SDKs sniff it.
    const ext = audio.type.includes('ogg') ? 'ogg' : audio.type.includes('mp4') ? 'mp4' : 'webm'
    form.append('audio', audio, `note.${ext}`)
    form.append('language', language)
    if (provider) form.append('provider', provider)

    const r = await fetch(`${BASE}/patients/${patientId}/voice`, { method: 'POST', body: form })
    if (!r.ok) {
      const err = await r.json().catch(() => ({}))
      throw new Error(err.detail || 'Voice note failed')
    }
    return r.json()
  },

  async getSttStatus(): Promise<SttStatus> {
    const r = await fetch(`${BASE}/stt/status`)
    return r.json()
  },

  voiceNoteUrl(filename: string) {
    return `${BASE}/voice/${filename}`
  },

  async sendOutreach(patientId: number, message: string): Promise<DeliveryResult> {
    const r = await fetch(`${BASE}/patients/${patientId}/outreach`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    })
    if (!r.ok) {
      const err = await r.json().catch(() => ({}))
      throw new Error(err.detail || 'Message could not be sent')
    }
    return r.json()
  },

  async sendReminder(patientId: number): Promise<DeliveryResult> {
    const r = await fetch(`${BASE}/patients/${patientId}/remind`, { method: 'POST' })
    if (!r.ok) throw new Error('Care reminder could not be sent')
    return r.json()
  },

  async sendCheckin(patientId: number): Promise<DeliveryResult> {
    const r = await fetch(`${BASE}/patients/${patientId}/checkin`, { method: 'POST' })
    if (!r.ok) throw new Error('Check-in could not be sent')
    return r.json()
  },

  async getAlerts(): Promise<Escalation[]> {
    const r = await fetch(`${BASE}/alerts`)
    return r.json()
  },

  async resolveAlert(id: number, data: {
    resolution_code: ResolutionCode
    note?: string
    resolved_by?: string
  }): Promise<{ resolved: boolean; patient_id: number; risk_level: string; resolved_at: string }> {
    const r = await fetch(`${BASE}/alerts/${id}/resolve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
    if (!r.ok) {
      const err = await r.json().catch(() => ({}))
      throw new Error(err.detail || 'Alert could not be resolved')
    }
    return r.json()
  },

  async getWeeklyReport(): Promise<{ report: string; generated_at: string }> {
    const r = await fetch(`${BASE}/reports/weekly`)
    return r.json()
  },
}
