import { FormEvent, useState } from 'react'
import { HeartPulse, Loader2, LockKeyhole } from 'lucide-react'
import { api, AuthSession } from '../api/client'

export function LoginScreen({ onSignedIn }: { onSignedIn: (session: AuthSession) => void }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function submit(event: FormEvent) {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      onSignedIn(await api.login(email, password))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Sign-in failed')
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 flex items-center justify-center p-5">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center text-white">
          <span className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-500">
            <HeartPulse size={24} />
          </span>
          <h1 className="text-2xl font-bold">VeloxaCare</h1>
          <p className="mt-1 text-sm text-slate-400">Secure clinic care workspace</p>
        </div>
        <form onSubmit={submit} className="rounded-3xl bg-white p-6 shadow-2xl">
          <div className="mb-5 flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-50 text-emerald-700">
              <LockKeyhole size={17} />
            </span>
            <div>
              <h2 className="font-bold text-slate-900">Staff sign in</h2>
              <p className="text-xs text-slate-500">Use your clinic-issued account.</p>
            </div>
          </div>
          <label htmlFor="staff-email" className="mb-1 block text-xs font-semibold text-slate-600">Email</label>
          <input id="staff-email" type="email" autoComplete="username" required value={email}
            onChange={event => setEmail(event.target.value)}
            className="mb-4 w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100" />
          <label htmlFor="staff-password" className="mb-1 block text-xs font-semibold text-slate-600">Password</label>
          <input id="staff-password" type="password" autoComplete="current-password" required value={password}
            onChange={event => setPassword(event.target.value)}
            className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100" />
          {error && <p role="alert" className="mt-3 rounded-xl bg-red-50 px-3 py-2 text-xs font-medium text-red-700">{error}</p>}
          <button type="submit" disabled={loading}
            className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-600 py-2.5 text-sm font-bold text-white hover:bg-emerald-700 disabled:opacity-60">
            {loading && <Loader2 size={15} className="animate-spin" />}
            {loading ? 'Signing in…' : 'Sign in securely'}
          </button>
        </form>
      </div>
    </main>
  )
}
