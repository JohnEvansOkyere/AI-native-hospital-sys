import { useMemo, useState } from 'react'
import {
  CalendarCheck, CalendarClock, CheckCircle2, Clock, Loader2, UserRound,
  XCircle,
} from 'lucide-react'
import { Appointment } from '../api/client'

type Props = {
  appointments: Appointment[]
  onOpenPatient: (patientId: number) => void
  onUpdate: (appointmentId: number, status: Appointment['status']) => Promise<void>
}

type Filter = 'today' | 'upcoming' | 'history'

function localDate(value = new Date()): string {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function formatDate(value: string): string {
  const parsed = new Date(`${value}T12:00:00`)
  return parsed.toLocaleDateString('en-GH', { weekday: 'short', day: 'numeric', month: 'short' })
}

function formatTime(value: string): string {
  const [hour, minute] = value.split(':').map(Number)
  return new Date(2000, 0, 1, hour, minute).toLocaleTimeString('en-GH', {
    hour: 'numeric', minute: '2-digit',
  })
}

const statusStyle: Record<Appointment['status'], string> = {
  confirmed: 'bg-emerald-50 text-emerald-700 border-emerald-100',
  completed: 'bg-blue-50 text-blue-700 border-blue-100',
  cancelled: 'bg-slate-100 text-slate-500 border-slate-200',
  no_show: 'bg-red-50 text-red-700 border-red-100',
}

export function AppointmentsPanel({ appointments, onOpenPatient, onUpdate }: Props) {
  const [filter, setFilter] = useState<Filter>('upcoming')
  const [busyId, setBusyId] = useState<number | null>(null)
  const [error, setError] = useState('')
  const today = localDate()

  const confirmed = appointments.filter(item => item.status === 'confirmed')
  const counts = {
    today: confirmed.filter(item => item.appointment_date === today).length,
    upcoming: confirmed.filter(item => item.appointment_date >= today).length,
    completed: appointments.filter(item => item.status === 'completed').length,
  }

  const rows = useMemo(() => appointments.filter(item => {
    if (filter === 'today') return item.status === 'confirmed' && item.appointment_date === today
    if (filter === 'upcoming') return item.status === 'confirmed' && item.appointment_date >= today
    return item.status !== 'confirmed' || item.appointment_date < today
  }), [appointments, filter, today])

  async function changeStatus(id: number, status: Appointment['status']) {
    setBusyId(id)
    setError('')
    try {
      await onUpdate(id, status)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Appointment could not be updated')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <main className="flex-1 min-h-0 overflow-y-auto p-4">
      <div className="max-w-6xl mx-auto space-y-4">
        <section className="rounded-2xl border border-slate-100 bg-white shadow-sm p-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-emerald-600">Clinic schedule</p>
              <h1 className="text-xl font-bold text-slate-900 mt-1">Appointments</h1>
              <p className="text-sm text-slate-500 mt-1">Bookings created by the patient agent appear here immediately.</p>
            </div>
            <div className="hidden sm:flex items-center gap-5 text-center">
              <div><p className="text-xl font-bold text-slate-900">{counts.today}</p><p className="text-[10px] text-slate-400">Today</p></div>
              <div><p className="text-xl font-bold text-slate-900">{counts.upcoming}</p><p className="text-[10px] text-slate-400">Upcoming</p></div>
              <div><p className="text-xl font-bold text-slate-900">{counts.completed}</p><p className="text-[10px] text-slate-400">Completed</p></div>
            </div>
          </div>

          <div className="flex gap-1 mt-4 pt-4 border-t border-slate-100">
            {([
              ['today', `Today ${counts.today}`],
              ['upcoming', `Upcoming ${counts.upcoming}`],
              ['history', 'History'],
            ] as Array<[Filter, string]>).map(([key, label]) => (
              <button key={key} onClick={() => setFilter(key)}
                className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                  filter === key ? 'bg-slate-900 text-white' : 'text-slate-500 hover:bg-slate-100'
                }`}>
                {label}
              </button>
            ))}
          </div>
        </section>

        {error && <div className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}

        <section className="rounded-2xl border border-slate-100 bg-white shadow-sm overflow-hidden">
          {rows.length === 0 ? (
            <div className="py-16 text-center px-6">
              <CalendarClock size={34} className="mx-auto text-slate-300" />
              <p className="mt-3 font-semibold text-slate-600">No appointments in this view</p>
              <p className="text-sm text-slate-400 mt-1">
                In Demo, send: “Please book me an appointment for Tuesday morning.”
              </p>
            </div>
          ) : (
            <ul className="divide-y divide-slate-100">
              {rows.map(item => (
                <li key={item.id} className="p-4 flex items-center gap-4 hover:bg-slate-50/70 transition">
                  <div className="w-20 text-center flex-shrink-0">
                    <p className="text-base font-bold text-slate-800 leading-none whitespace-nowrap">{formatTime(item.appointment_time)}</p>
                    <p className="text-[10px] text-slate-400 mt-1">{formatDate(item.appointment_date)}</p>
                  </div>
                  <div className="h-10 w-px bg-slate-100" />
                  <button onClick={() => onOpenPatient(item.patient_id)} className="flex-1 min-w-0 text-left group">
                    <p className="font-semibold text-sm text-slate-800 group-hover:text-emerald-700">{item.patient_name}</p>
                    <p className="text-xs text-slate-500 mt-0.5 truncate">{item.visit_type} · {item.clinician_name}</p>
                  </button>
                  <span className={`hidden sm:inline-flex rounded-full border px-2 py-1 text-[10px] font-semibold capitalize ${statusStyle[item.status]}`}>
                    {item.status.replace('_', ' ')}
                  </span>
                  {item.status === 'confirmed' && (
                    <div className="flex items-center gap-1.5">
                      <button onClick={() => changeStatus(item.id, 'completed')} disabled={busyId === item.id}
                        title="Mark visit completed"
                        className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1.5 text-[11px] font-semibold text-slate-600 hover:bg-emerald-50 hover:text-emerald-700 hover:border-emerald-200 disabled:opacity-50">
                        {busyId === item.id ? <Loader2 size={12} className="animate-spin" /> : <CheckCircle2 size={12} />}
                        Complete
                      </button>
                      <button onClick={() => changeStatus(item.id, 'cancelled')} disabled={busyId === item.id}
                        title="Cancel appointment"
                        className="inline-flex items-center gap-1 rounded-lg border border-slate-200 px-2.5 py-1.5 text-[11px] font-semibold text-slate-500 hover:bg-red-50 hover:text-red-700 hover:border-red-200 disabled:opacity-50">
                        <XCircle size={12} /> Cancel
                      </button>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>

        <div className="flex items-center justify-center gap-6 text-[11px] text-slate-400">
          <span className="inline-flex items-center gap-1"><CalendarCheck size={12} /> Saved to the patient record</span>
          <span className="inline-flex items-center gap-1"><UserRound size={12} /> Human staff remain in control</span>
          <span className="inline-flex items-center gap-1"><Clock size={12} /> Clinic hours: 9 AM–4 PM, weekdays</span>
        </div>
      </div>
    </main>
  )
}
