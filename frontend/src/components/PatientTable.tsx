/**
 * The clinic roster.
 *
 * Sorted by clinical urgency first — a nurse scanning this should never have to
 * hunt for the patient who needs them most. Search exists because a real clinic
 * has hundreds of patients, not six.
 */

import { useMemo, useState } from 'react'
import { Search, Users } from 'lucide-react'
import { Patient } from '../api/client'
import { RiskBadge, RiskLevel, riskRank, timeAgo } from './shared'

type Props = {
  patients: Patient[]
  selectedId: number | null
  onSelect: (id: number) => void
}

const FILTERS: Array<{ key: 'all' | RiskLevel; label: string }> = [
  { key: 'all', label: 'All' },
  { key: 'red', label: 'Urgent' },
  { key: 'amber', label: 'Watch' },
  { key: 'green', label: 'On track' },
]

function lastContact(p: Patient): string | null {
  const stamps = [
    p.last_checkin?.at,
    ...p.adherence_logs.map(l => l.date),
    ...p.care_logs.map(l => l.date),
  ].filter(Boolean) as string[]
  if (!stamps.length) return null
  return stamps.sort().reverse()[0]
}

export function PatientTable({ patients, selectedId, onSelect }: Props) {
  const [query, setQuery] = useState('')
  const [filter, setFilter] = useState<'all' | RiskLevel>('all')

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase()
    return patients
      .filter(p => filter === 'all' || p.risk_level === filter)
      .filter(p => !q || p.name.toLowerCase().includes(q) || p.phone.includes(q)
        || (p.condition || '').toLowerCase().includes(q))
      .sort((a, b) =>
        riskRank[a.risk_level] - riskRank[b.risk_level]
        || a.care_completion_pct - b.care_completion_pct
        || a.name.localeCompare(b.name))
  }, [patients, query, filter])

  const counts = useMemo(() => ({
    all: patients.length,
    red: patients.filter(p => p.risk_level === 'red').length,
    amber: patients.filter(p => p.risk_level === 'amber').length,
    green: patients.filter(p => p.risk_level === 'green').length,
  }), [patients])

  return (
    <div className="bg-white rounded-2xl border border-slate-100 shadow-sm flex flex-col overflow-hidden h-full">
      <div className="px-4 py-3 border-b border-slate-100 flex-shrink-0">
        <div className="flex items-center gap-2 mb-2">
          <Users size={16} className="text-slate-400" />
          <h2 className="font-semibold text-slate-800 text-sm">Patients</h2>
          <span className="ml-auto text-xs text-slate-400">{rows.length} shown</span>
        </div>

        <div className="relative mb-2">
          <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-300" />
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Search name, phone or condition…"
            className="w-full pl-7 pr-2 py-1.5 text-xs bg-slate-50 border border-slate-100 rounded-lg outline-none focus:border-emerald-300 focus:bg-white transition"
          />
        </div>

        <div className="flex gap-1">
          {FILTERS.map(f => (
            <button key={f.key} onClick={() => setFilter(f.key)}
              className={`text-[11px] px-2 py-0.5 rounded-full border transition ${
                filter === f.key
                  ? 'bg-slate-800 text-white border-slate-800'
                  : 'bg-white text-slate-500 border-slate-200 hover:bg-slate-50'}`}>
              {f.label} {counts[f.key] > 0 && <span className="opacity-60">{counts[f.key]}</span>}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {rows.length === 0 ? (
          <p className="p-6 text-center text-xs text-slate-400">No patients match.</p>
        ) : (
          <ul className="divide-y divide-slate-50">
            {rows.map(p => {
              const contact = lastContact(p)
              return (
                <li key={p.id}>
                  <button
                    onClick={() => onSelect(p.id)}
                    className={`w-full text-left px-4 py-2.5 transition border-l-2 ${
                      selectedId === p.id
                        ? 'bg-emerald-50/60 border-l-emerald-500'
                        : 'border-l-transparent hover:bg-slate-50'}`}>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-sm text-slate-800 truncate">{p.name}</span>
                          <RiskBadge level={p.risk_level} />
                        </div>
                        <p className="text-[11px] text-slate-500 truncate mt-0.5">
                          {p.condition || p.service_type || 'General care'}
                          {p.drug_name && <span className="text-slate-400"> · {p.drug_name}</span>}
                        </p>
                      </div>
                      <div className="text-right flex-shrink-0">
                        <div className={`text-sm font-semibold ${
                          p.care_completion_pct >= 75 ? 'text-emerald-600'
                          : p.care_completion_pct >= 50 ? 'text-amber-600' : 'text-red-600'}`}>
                          {p.care_completion_pct}%
                        </div>
                        <div className="text-[10px] text-slate-400">
                          {contact ? timeAgo(contact) : 'no contact'}
                        </div>
                      </div>
                    </div>
                  </button>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </div>
  )
}
