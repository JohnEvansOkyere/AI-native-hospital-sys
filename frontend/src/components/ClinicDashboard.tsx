/** The clinic overview: today's workload and the safety-critical alert queue. */

import { Escalation, Patient } from '../api/client'
import { AlertQueue } from './AlertQueue'
import { CareOverview } from './CareOverview'
import { PatientTable } from './PatientTable'
import { TodayQueue } from './TodayQueue'

type Props = {
  patients: Patient[]
  alerts: Escalation[]
  onOpenPatient: (id: number) => void
  onOpenAlert: (alert: Escalation) => void
  refreshKey: number
}

export function ClinicDashboard({
  patients, alerts, onOpenPatient, onOpenAlert, refreshKey,
}: Props) {
  return (
    <main className="min-h-0 flex-1 overflow-y-auto px-4 py-4 sm:px-6 lg:px-8" aria-label="Clinic care overview">
      <CareOverview patients={patients} alerts={alerts} onOpenAlert={onOpenAlert} />
      <div className="mt-4 grid grid-cols-1 gap-4 2xl:grid-cols-[minmax(0,1.2fr)_minmax(360px,0.8fr)]">
        <div className="flex min-w-0 flex-col gap-4">
          <TodayQueue refreshKey={refreshKey} onOpenAlert={onOpenAlert} onSelectPatient={onOpenPatient} />
          <section className="h-[500px] min-h-[420px]" aria-label="Patient roster">
            <PatientTable patients={patients} selectedId={null} onSelect={onOpenPatient} />
          </section>
        </div>
        <section className="min-h-[420px] 2xl:h-[680px]" aria-label="Open care cases">
          <AlertQueue alerts={alerts} onOpenAlert={onOpenAlert} onSelectPatient={onOpenPatient} />
        </section>
      </div>
    </main>
  )
}
