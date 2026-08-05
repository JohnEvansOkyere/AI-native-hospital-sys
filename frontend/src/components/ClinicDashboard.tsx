/**
 * The clinic-staff view: alert queue, patient roster, patient detail.
 *
 * This is the product surface a nurse actually uses. The WhatsApp pane is a
 * demo aid and lives elsewhere — patients are on real WhatsApp.
 */

import { Escalation, Patient } from '../api/client'
import { AlertQueue } from './AlertQueue'
import { CareOverview } from './CareOverview'
import { PatientTable } from './PatientTable'
import { PatientTimeline } from './PatientTimeline'

type Props = {
  patients: Patient[]
  alerts: Escalation[]
  selectedId: number | null
  onSelect: (id: number) => void
  onOpenAlert: (alert: Escalation) => void
  onActivity: () => void
  refreshKey: number
}

export function ClinicDashboard({
  patients, alerts, selectedId, onSelect, onOpenAlert, onActivity, refreshKey,
}: Props) {
  const selected = patients.find(p => p.id === selectedId) || null

  return (
    <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
      <CareOverview patients={patients} alerts={alerts} onOpenAlert={onOpenAlert} />
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-3 p-3 min-h-0 overflow-hidden">
      {/* Triage first — on narrow screens it stacks above everything else,
          because an urgent patient must never be below the fold. */}
      <div className="lg:col-span-3 min-h-0 order-1">
        <AlertQueue alerts={alerts} onOpenAlert={onOpenAlert} onSelectPatient={onSelect} />
      </div>

      <div className="lg:col-span-3 min-h-0 order-3 lg:order-2">
        <PatientTable patients={patients} selectedId={selectedId} onSelect={onSelect} />
      </div>

      <div className="lg:col-span-6 min-h-0 order-2 lg:order-3">
        {selected ? (
          <PatientTimeline patient={selected} refreshKey={refreshKey} onActivity={onActivity} />
        ) : (
          <div className="bg-white rounded-2xl border border-slate-100 shadow-sm h-full flex items-center justify-center">
            <p className="text-sm text-slate-400">Select a patient to see their record.</p>
          </div>
        )}
      </div>
      </div>
    </div>
  )
}
