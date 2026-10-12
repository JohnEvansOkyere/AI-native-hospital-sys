import type { ReactNode } from 'react'
import {
  Activity, CalendarDays, FileText, HeartPulse, LogOut, MessageCircle,
  Plus, Settings, ShieldCheck,
} from 'lucide-react'
import type { StaffUser } from '../api/client'

export type WorkspaceView = 'clinic' | 'conversations' | 'appointments' | 'settings' | 'demo'

type Props = {
  children: ReactNode
  view: WorkspaceView
  onNavigate: (view: WorkspaceView) => void
  clinicName: string
  user: StaffUser
  demoEnabled: boolean
  alertCount: number
  onWeeklyReport: () => void
  onAddPatient: () => void
  onSignOut: () => void
}

const VIEW_COPY: Record<WorkspaceView, { title: string; description: string }> = {
  clinic: { title: 'Care overview', description: 'A clear view of today’s patient needs and follow-up work.' },
  conversations: { title: 'Patient conversations', description: 'Review each patient’s care history and contact them.' },
  appointments: { title: 'Appointments', description: 'Manage upcoming visits and record their outcomes.' },
  settings: { title: 'Workspace settings', description: 'Manage clinic details and staff access.' },
  demo: { title: 'Message simulator', description: 'Exercise the patient conversation flow.' },
}

export function WorkspaceShell({
  children, view, onNavigate, clinicName, user, demoEnabled, alertCount,
  onWeeklyReport, onAddPatient, onSignOut,
}: Props) {
  const navItems = [
    { id: 'clinic' as const, label: 'Overview', icon: Activity },
    { id: 'conversations' as const, label: 'Patients & messages', icon: MessageCircle },
    { id: 'appointments' as const, label: 'Appointments', icon: CalendarDays },
    ...(demoEnabled ? [{ id: 'demo' as const, label: 'Simulator', icon: ShieldCheck }] : []),
    ...(user.role === 'admin' ? [{ id: 'settings' as const, label: 'Settings', icon: Settings }] : []),
  ]
  const copy = VIEW_COPY[view]
  const today = new Intl.DateTimeFormat('en-GH', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
    timeZone: 'Africa/Accra',
  }).format(new Date())

  const navigation = (compact = false) => (
    <nav aria-label="Workspace navigation" className={compact ? 'flex min-w-max gap-1' : 'space-y-1'}>
      {navItems.map(item => {
        const active = view === item.id
        return (
          <button key={item.id} onClick={() => onNavigate(item.id)}
            aria-current={active ? 'page' : undefined}
            className={`flex items-center gap-3 rounded-lg text-left font-medium transition focus:outline-none focus:ring-2 focus:ring-emerald-400 ${
              compact
                ? `px-3 py-2 text-xs ${active ? 'bg-slate-900 text-white' : 'text-slate-600 hover:bg-slate-100'}`
                : `w-full px-3 py-2.5 text-sm ${active ? 'bg-white/10 text-white' : 'text-slate-300 hover:bg-white/5 hover:text-white'}`
            }`}>
            <item.icon size={17} strokeWidth={1.8} />
            <span>{item.label}</span>
            {item.id === 'clinic' && alertCount > 0 && (
              <span className={`ml-auto rounded-md px-1.5 py-0.5 text-[10px] font-bold ${compact ? 'bg-red-100 text-red-700' : 'bg-red-500/15 text-red-200'}`}>
                {alertCount}
              </span>
            )}
          </button>
        )
      })}
    </nav>
  )

  return (
    <div className="flex h-dvh overflow-hidden bg-slate-100 text-slate-900">
      <aside className="hidden w-60 flex-shrink-0 flex-col bg-[#14272a] text-white lg:flex" aria-label="VeloxaCare workspace">
        <div className="border-b border-white/10 px-5 py-5">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500 text-white shadow-lg shadow-emerald-950/20">
              <HeartPulse size={21} />
            </span>
            <div>
              <p className="text-[17px] font-semibold tracking-tight">VeloxaCare</p>
              <p className="mt-0.5 text-[10px] font-semibold uppercase tracking-[0.17em] text-emerald-200/70">Care coordination</p>
            </div>
          </div>
          <div className="mt-5 rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2.5">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Clinic workspace</p>
            <p className="mt-1 truncate text-sm font-medium text-white">{clinicName}</p>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-3 py-5">
          <p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">Work</p>
          {navigation()}
        </div>

        <div className="border-t border-white/10 p-3">
          <div className="flex items-center gap-3 rounded-lg px-2 py-2">
            <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-slate-700 text-xs font-semibold text-white">
              {user.name.split(/\s+/).map(part => part[0]).join('').slice(0, 2).toUpperCase()}
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-semibold text-white">{user.name}</p>
              <p className="mt-0.5 text-[10px] capitalize text-slate-400">{user.role.replace('_', ' ')}</p>
            </div>
            <button onClick={onSignOut} title="Sign out" aria-label={`Sign out ${user.name}`}
              className="rounded-md p-2 text-slate-400 transition hover:bg-white/10 hover:text-white focus:outline-none focus:ring-2 focus:ring-emerald-400">
              <LogOut size={15} />
            </button>
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <header className="z-10 flex-shrink-0 border-b border-slate-200 bg-white px-4 py-3 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between gap-4">
            <div className="min-w-0">
              <div className="mb-1 flex items-center gap-2 text-[11px] font-medium text-slate-400">
                <span className="lg:hidden font-semibold text-emerald-800">VeloxaCare</span>
                <span className="hidden lg:inline">{clinicName}</span>
                <span aria-hidden="true">/</span>
                <span className="truncate text-slate-500">{copy.title}</span>
              </div>
              <h1 className="truncate text-xl font-semibold tracking-tight text-slate-900 sm:text-2xl">{copy.title}</h1>
              <p className="mt-1 hidden text-xs text-slate-500 sm:block">{copy.description}</p>
            </div>
            <div className="flex flex-shrink-0 items-center gap-2">
              <div className="hidden border-r border-slate-200 pr-4 text-right xl:block">
                <p className="text-xs font-medium text-slate-700">{today}</p>
                <p className="mt-0.5 text-[10px] text-slate-400">Accra time</p>
              </div>
              {alertCount > 0 && (
                <span className="hidden items-center gap-1.5 rounded-lg border border-red-200 bg-red-50 px-2.5 py-2 text-xs font-semibold text-red-700 sm:inline-flex">
                  <span className="h-1.5 w-1.5 rounded-full bg-red-500" />
                  {alertCount} open {alertCount === 1 ? 'case' : 'cases'}
                </span>
              )}
              <button onClick={onWeeklyReport}
                className="hidden items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-emerald-500 sm:inline-flex">
                <FileText size={15} /> <span className="hidden xl:inline">Weekly report</span><span className="xl:hidden">Report</span>
              </button>
              {user.role === 'admin' && (
                <button onClick={onAddPatient}
                  className="inline-flex items-center gap-2 rounded-lg bg-emerald-700 px-3 py-2 text-xs font-semibold text-white shadow-sm transition hover:bg-emerald-800 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2">
                  <Plus size={15} /><span className="hidden sm:inline">Add patient</span><span className="sm:hidden">Add</span>
                </button>
              )}
              <button onClick={onSignOut} title={`Sign out ${user.name}`} aria-label="Sign out"
                className="rounded-lg border border-slate-200 p-2 text-slate-500 hover:bg-slate-50 lg:hidden">
                <LogOut size={15} />
              </button>
            </div>
          </div>
          <div className="mt-3 overflow-x-auto border-t border-slate-100 pt-2 lg:hidden">{navigation(true)}</div>
        </header>
        <div className="flex min-h-0 flex-1 flex-col overflow-hidden">{children}</div>
      </div>
    </div>
  )
}
