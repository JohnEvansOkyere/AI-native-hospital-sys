import { FormEvent, useEffect, useState } from 'react'
import { Building2, Loader2, Plus, ShieldCheck, Users } from 'lucide-react'
import { api, ClinicSettings, StaffRecord, StaffUser } from '../api/client'

export function AdminSettings({ currentUserId }: { currentUserId: number }) {
  const [staff, setStaff] = useState<StaffRecord[]>([])
  const [settings, setSettings] = useState<ClinicSettings>({
    clinic_name: '', timezone: 'Africa/Accra', escalation_phone: '',
  })
  const [newStaff, setNewStaff] = useState({ name: '', email: '', role: 'care_team' as StaffUser['role'], password: '' })
  const [reset, setReset] = useState({ staffId: '', password: '' })
  const [busy, setBusy] = useState<'clinic' | 'staff' | null>(null)
  const [status, setStatus] = useState('')

  useEffect(() => {
    Promise.all([api.getStaff(), api.getClinicSettings()]).then(([users, clinic]) => {
      setStaff(users)
      setSettings(clinic)
    }).catch(error => setStatus(error instanceof Error ? error.message : 'Settings could not be loaded'))
  }, [])

  async function saveClinic(event: FormEvent) {
    event.preventDefault()
    setBusy('clinic'); setStatus('')
    try {
      setSettings(await api.updateClinicSettings(settings))
      setStatus('Clinic settings saved.')
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Settings could not be saved')
    } finally { setBusy(null) }
  }

  async function addStaff(event: FormEvent) {
    event.preventDefault()
    setBusy('staff'); setStatus('')
    try {
      const created = await api.createStaff(newStaff)
      setStaff(current => [...current, created])
      setNewStaff({ name: '', email: '', role: 'care_team', password: '' })
      setStatus('Staff account created. Share the password through a secure channel.')
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Staff account could not be created')
    } finally { setBusy(null) }
  }

  async function toggleStaff(person: StaffRecord) {
    setBusy('staff'); setStatus('')
    try {
      const result = await api.setStaffActive(person.id, !person.active)
      setStaff(current => current.map(item => item.id === person.id ? { ...item, active: result.active } : item))
      setStatus(result.active ? 'Staff account reactivated.' : 'Staff account deactivated and sessions revoked.')
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Staff account could not be updated')
    } finally { setBusy(null) }
  }

  async function resetPassword(event: FormEvent) {
    event.preventDefault()
    setBusy('staff'); setStatus('')
    try {
      await api.resetStaffPassword(Number(reset.staffId), reset.password)
      setReset({ staffId: '', password: '' })
      setStatus('Password reset and all sessions for that account were revoked.')
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'Password could not be reset')
    } finally { setBusy(null) }
  }

  return (
    <main className="flex-1 overflow-y-auto p-4">
      <div className="mx-auto grid max-w-5xl gap-4 lg:grid-cols-2">
        <form onSubmit={saveClinic} className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
          <div className="mb-4 flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700"><Building2 size={17} /></span>
            <div><h2 className="font-bold text-slate-900">Clinic settings</h2><p className="text-xs text-slate-500">Used for ownership and durable staff alerts.</p></div>
          </div>
          <label className="mb-1 block text-xs font-semibold text-slate-600">Clinic name</label>
          <input required value={settings.clinic_name} onChange={event => setSettings(s => ({ ...s, clinic_name: event.target.value }))}
            className="mb-3 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-emerald-400" />
          <label className="mb-1 block text-xs font-semibold text-slate-600">Timezone</label>
          <input required value={settings.timezone} onChange={event => setSettings(s => ({ ...s, timezone: event.target.value }))}
            className="mb-3 w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-emerald-400" />
          <label className="mb-1 block text-xs font-semibold text-slate-600">Escalation WhatsApp number</label>
          <input value={settings.escalation_phone} onChange={event => setSettings(s => ({ ...s, escalation_phone: event.target.value }))}
            placeholder="+233…" className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-emerald-400" />
          <button disabled={busy !== null} className="mt-4 flex items-center gap-2 rounded-xl bg-slate-900 px-4 py-2 text-sm font-bold text-white disabled:opacity-50">
            {busy === 'clinic' && <Loader2 size={14} className="animate-spin" />} Save clinic settings
          </button>
        </form>

        <section className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
          <div className="mb-4 flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-blue-50 text-blue-700"><Users size={17} /></span>
            <div><h2 className="font-bold text-slate-900">Staff accounts</h2><p className="text-xs text-slate-500">Individual identities make care actions auditable.</p></div>
          </div>
          <div className="space-y-2">
            {staff.map(person => (
              <div key={person.id} className="flex items-center gap-3 rounded-xl bg-slate-50 px-3 py-2">
                <ShieldCheck size={14} className={person.role === 'admin' ? 'text-purple-600' : 'text-emerald-600'} />
                <div className="min-w-0 flex-1"><p className="truncate text-sm font-semibold text-slate-800">{person.name}</p><p className="truncate text-[11px] text-slate-500">{person.email}</p></div>
                <div className="text-right">
                  <span className="block text-[10px] font-bold uppercase tracking-wide text-slate-400">{person.role.replace('_', ' ')}</span>
                  <button type="button" disabled={busy !== null || person.id === currentUserId}
                    onClick={() => toggleStaff(person)}
                    className={`mt-1 text-[10px] font-semibold disabled:opacity-40 ${person.active ? 'text-red-600' : 'text-emerald-700'}`}>
                    {person.active ? 'Deactivate' : 'Reactivate'}
                  </button>
                </div>
              </div>
            ))}
          </div>
          <form onSubmit={addStaff} className="mt-4 grid grid-cols-2 gap-2 border-t border-slate-100 pt-4">
            <input required placeholder="Full name" value={newStaff.name} onChange={event => setNewStaff(s => ({ ...s, name: event.target.value }))}
              className="rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-emerald-400" />
            <input required type="email" placeholder="Email" value={newStaff.email} onChange={event => setNewStaff(s => ({ ...s, email: event.target.value }))}
              className="rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-emerald-400" />
            <select value={newStaff.role} onChange={event => setNewStaff(s => ({ ...s, role: event.target.value as StaffUser['role'] }))}
              className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none">
              <option value="care_team">Care team</option><option value="admin">Administrator</option>
            </select>
            <input required minLength={12} type="password" placeholder="Temporary password (12+)" value={newStaff.password}
              onChange={event => setNewStaff(s => ({ ...s, password: event.target.value }))}
              className="rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-emerald-400" />
            <button disabled={busy !== null} className="col-span-2 flex items-center justify-center gap-2 rounded-xl bg-emerald-600 py-2 text-sm font-bold text-white disabled:opacity-50">
              {busy === 'staff' ? <Loader2 size={14} className="animate-spin" /> : <Plus size={14} />} Add staff account
            </button>
          </form>
          <form onSubmit={resetPassword} className="mt-4 grid grid-cols-2 gap-2 border-t border-slate-100 pt-4">
            <select required value={reset.staffId} onChange={event => setReset(value => ({ ...value, staffId: event.target.value }))}
              className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm outline-none">
              <option value="">Reset password for…</option>
              {staff.filter(person => person.active).map(person => <option key={person.id} value={person.id}>{person.name}</option>)}
            </select>
            <input required minLength={12} type="password" placeholder="New password (12+)" value={reset.password}
              onChange={event => setReset(value => ({ ...value, password: event.target.value }))}
              className="rounded-xl border border-slate-200 px-3 py-2 text-sm outline-none focus:border-emerald-400" />
            <button disabled={busy !== null} className="col-span-2 rounded-xl border border-slate-300 bg-white py-2 text-sm font-bold text-slate-700 hover:bg-slate-50 disabled:opacity-50">
              Reset password & revoke sessions
            </button>
          </form>
        </section>
        {status && <p role="status" className="lg:col-span-2 rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700">{status}</p>}
      </div>
    </main>
  )
}
