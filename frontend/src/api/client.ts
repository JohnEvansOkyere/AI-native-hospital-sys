const BASE = '/api'
let csrfToken = ''

export class AuthenticationRequired extends Error {}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method || 'GET').toUpperCase()
  const headers = new Headers(init.headers)
  if (!['GET', 'HEAD', 'OPTIONS'].includes(method) && csrfToken) {
    headers.set('X-CSRF-Token', csrfToken)
  }
  const response = await fetch(`${BASE}${path}`, { ...init, headers, credentials: 'include' })
  if (response.status === 401) throw new AuthenticationRequired('Please sign in again')
  if (response.status === 204) return undefined as T
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(payload.detail || 'Request failed')
  return payload as T
}

export interface StaffUser {
  id: number
  email: string
  name: string
  role: 'admin' | 'care_team'
}

export interface AuthSession {
  user: StaffUser
  csrf_token: string
  expires_at: string
  demo_enabled: boolean
}

export interface StaffRecord extends StaffUser {
  active: boolean
  last_login_at?: string | null
  created_at: string
}

export interface ClinicSettings {
  clinic_name: string
  timezone: string
  escalation_phone: string
  updated_at?: string
}

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
  preferred_language: LanguagePair
  reminder_time: string
  consent_status: 'pending' | 'granted' | 'withdrawn'
  consent_recorded_at?: string | null
  consent_recorded_by?: string
  communication_opt_in: number | boolean
  paused: number | boolean
  consent_history: Array<{ status: string; method: string; recorded_by: string; note: string; created_at: string }>
  adherence_pct: number
  care_completion_pct: number
  adherence_logs: { date: string; response: string }[]
  care_logs: { date: string; activity: string; response: string; details: string | null }[]
  streak: number
  last_checkin: { type: string; value: string; risk: string; at: string } | null
  escalations: Escalation[]
  recent_resolutions: Escalation[]
  current_flow: string
  /** Present only on the enrollment response; reports the real Meta send attempt. */
  welcome_delivery?: {
    delivered: boolean
    channel: string
    mode: 'template' | 'free_text' | 'consent_pending'
    message_id: string
    note: string
  }
}

export interface Message {
  id: number
  direction: 'inbound' | 'outbound'
  body: string
  reason: string | null
  created_at: string
  /** Transport it arrived on / went out over: simulator | whatsapp | sms | ussd. */
  channel?: string | null
  /** The audio for this message, whichever way it travelled: the patient's
   *  voice note on an inbound message, the agent's spoken reply on an outbound
   *  one. The stt_* fields describe the first case, the tts_* fields the second. */
  audio_file?: string | null
  stt_provider?: string | null
  stt_language?: string | null
  stt_latency_ms?: number | null
  tts_provider?: string | null
  tts_voice?: string | null
  tts_latency_ms?: number | null
  /** When the spoken reply was translated (e.g. into Twi), the exact words the voice said. */
  spoken_body?: string | null
  /** Meta lifecycle for outbound WhatsApp: accepted → sent → delivered/read, or failed. */
  delivery_status?: 'accepted' | 'sent' | 'delivered' | 'read' | 'failed' | null
  delivery_error?: string | null
  external_message_id?: string | null
}

/** Benchmark language_pair codes — a hint to the model, not a constraint on
 *  the patient. The transcript is whatever was actually said, code-switch included. */
export type LanguagePair = 'en' | 'tw-en' | 'pcm-en' | 'gaa-en' | 'ewe-en'

export interface SttStatus {
  configured: string[]
  pinned: string | null
  active: string | null
  /** Providers configured but failing in practice, mapped to the reason. */
  degraded?: Record<string, string>
  languages: Record<string, string>
}

export interface TtsStatus {
  configured: string[]
  pinned: string | null
  active: string | null
  degraded?: Record<string, string>
  /** mirror = speak only when the patient spoke; always; off. */
  mode: 'mirror' | 'always' | 'off'
  enabled: boolean
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
  assigned_to?: number | null
  assigned_to_name?: string | null
  acknowledged_at?: string | null
  due_at?: string | null
  notification_status?: string
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

export interface Appointment {
  id: number
  patient_id: number
  patient_name: string
  appointment_date: string
  appointment_time: string
  clinician_name: string
  visit_type: string
  status: 'confirmed' | 'cancelled' | 'completed' | 'no_show'
  created_at: string
  updated_at: string
}

export interface TodayWorklist {
  date: string
  alerts: Array<Escalation & { overdue: boolean }>
  appointments: Array<Pick<Appointment, 'id' | 'patient_id' | 'patient_name' | 'appointment_time' | 'clinician_name' | 'visit_type' | 'status'>>
  failed_deliveries: Array<{ id: number; patient_id: number; patient_name: string; body: string; delivery_error: string; created_at: string }>
  reminders_due: Array<{ patient_id: number; patient_name: string; reminder_time: string }>
  counts: { open_alerts: number; unacknowledged: number; appointments: number; failed_deliveries: number; reminders_due: number }
}

export const api = {
  async login(email: string, password: string): Promise<AuthSession> {
    const session = await request<AuthSession>('/auth/login', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    csrfToken = session.csrf_token
    return session
  },

  async me(): Promise<AuthSession> {
    const session = await request<AuthSession>('/auth/me')
    csrfToken = session.csrf_token
    return session
  },

  async logout(): Promise<void> {
    await request<void>('/auth/logout', { method: 'POST' })
    csrfToken = ''
  },

  async getStaff(): Promise<StaffRecord[]> {
    return request('/staff')
  },

  async createStaff(data: { email: string; name: string; role: StaffUser['role']; password: string }): Promise<StaffRecord> {
    return request('/staff', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
    })
  },

  async setStaffActive(id: number, active: boolean): Promise<{ id: number; active: boolean }> {
    return request(`/staff/${id}/status`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ active }),
    })
  },

  async resetStaffPassword(id: number, password: string): Promise<void> {
    return request(`/staff/${id}/password`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ password }),
    })
  },

  async getClinicSettings(): Promise<ClinicSettings> {
    return request('/settings/clinic')
  },

  async updateClinicSettings(data: ClinicSettings): Promise<ClinicSettings> {
    return request('/settings/clinic', {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
    })
  },

  async getPatients(): Promise<Patient[]> {
    return request('/patients')
  },

  async getPatient(id: number): Promise<Patient> {
    return request(`/patients/${id}`)
  },

  async enrollPatient(data: {
    name: string; phone: string; age: number | null;
    category: 'dental' | 'eye' | 'chronic' | 'general'; condition: string;
    drug_name: string; drug_dosage: string; service_type: string;
    care_instructions: string; next_follow_up: string; recall_date: string;
    doctor_name: string; preferred_language: LanguagePair; reminder_time: string;
    consent_granted: boolean
  }): Promise<Patient> {
    return request('/patients', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
  },

  async updateCommunication(id: number, data: Partial<{
    preferred_language: LanguagePair; reminder_time: string;
    consent_status: 'pending' | 'granted' | 'withdrawn';
    communication_opt_in: boolean; paused: boolean
  }>): Promise<Patient> {
    return request(`/patients/${id}/communication`, {
      method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data),
    })
  },

  async getMessages(patientId: number): Promise<Message[]> {
    return request(`/patients/${patientId}/messages?limit=80`)
  },

  async sendMessage(patientId: number, message: string) {
    return request(`/patients/${patientId}/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    })
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

    return request(`/patients/${patientId}/voice`, { method: 'POST', body: form })
  },

  async getSttStatus(): Promise<SttStatus> {
    return request('/stt/status')
  },

  async getTtsStatus(): Promise<TtsStatus> {
    return request('/tts/status')
  },

  voiceNoteUrl(filename: string) {
    return `${BASE}/voice/${filename}`
  },

  async sendOutreach(patientId: number, message: string): Promise<DeliveryResult> {
    return request(`/patients/${patientId}/outreach`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    })
  },

  async sendReminder(patientId: number): Promise<DeliveryResult> {
    return request(`/patients/${patientId}/remind`, { method: 'POST' })
  },

  async sendCheckin(patientId: number): Promise<DeliveryResult> {
    return request(`/patients/${patientId}/checkin`, { method: 'POST' })
  },

  async getAlerts(): Promise<Escalation[]> {
    return request('/alerts')
  },

  async acknowledgeAlert(id: number): Promise<Record<string, unknown>> {
    return request(`/alerts/${id}/acknowledge`, { method: 'POST' })
  },

  async getTodayWorklist(): Promise<TodayWorklist> {
    return request('/worklist/today')
  },

  async getAppointments(): Promise<Appointment[]> {
    return request('/appointments')
  },

  async updateAppointment(
    id: number,
    data: Partial<Pick<Appointment, 'appointment_date' | 'appointment_time' | 'status'>>,
  ): Promise<Appointment> {
    return request(`/appointments/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
  },

  async resolveAlert(id: number, data: {
    resolution_code: ResolutionCode
    note?: string
    resolved_by?: string
  }): Promise<{ resolved: boolean; patient_id: number; risk_level: string; resolved_at: string }> {
    return request(`/alerts/${id}/resolve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    })
  },

  async getWeeklyReport(): Promise<{ report: string; generated_at: string }> {
    return request('/reports/weekly')
  },
}
