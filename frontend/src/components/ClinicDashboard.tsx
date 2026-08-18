/** The clinic overview: today's workload and the safety-critical alert queue. */

import { Escalation, Patient } from '../api/client'
import { AlertQueue } from './AlertQueue'
import { CareOverview } from './CareOverview'
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
    <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
      <CareOverview patients={patients} alerts={alerts} onOpenAlert={onOpenAlert} />
      <TodayQueue refreshKey={refreshKey} onOpenAlert={onOpenAlert} onSelectPatient={onOpenPatient} />
      <div className="flex-1 p-3 min-h-0 overflow-hidden">
        <AlertQueue alerts={alerts} onOpenAlert={onOpenAlert} onSelectPatient={onOpenPatient} />
      </div>
    </div>
  )
}
