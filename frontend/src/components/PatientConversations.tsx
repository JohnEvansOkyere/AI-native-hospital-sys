/**
 * Dedicated patient conversation workspace.
 *
 * The roster is only a selector; the longitudinal record and chat own the
 * remaining page so care staff can read, track and respond without competing
 * dashboard panels.
 */

import { MessageCircle } from 'lucide-react'
import { Patient } from '../api/client'
import { PatientTable } from './PatientTable'
import { PatientTimeline } from './PatientTimeline'

type Props = {
  patients: Patient[]
  selectedId: number | null
  onSelect: (id: number) => void
  onActivity: () => void
  refreshKey: number
}

export function PatientConversations({
  patients, selectedId, onSelect, onActivity, refreshKey,
}: Props) {
  const selected = patients.find(patient => patient.id === selectedId) || null

  return (
    <main className="flex-1 min-h-0 overflow-hidden p-3" aria-label="Patient conversations">
      <div className="flex h-full min-h-0 flex-col gap-3 lg:flex-row">
        <aside className="h-64 min-h-0 flex-shrink-0 lg:h-full lg:w-80" aria-label="Patient roster">
          <PatientTable patients={patients} selectedId={selectedId} onSelect={onSelect} />
        </aside>

        <section className="flex-1 min-h-0" aria-label="Selected patient conversation">
          {selected ? (
            <PatientTimeline patient={selected} refreshKey={refreshKey} onActivity={onActivity} />
          ) : (
            <div className="flex h-full items-center justify-center rounded-2xl border border-slate-100 bg-white shadow-sm">
              <div className="text-center text-slate-400">
                <MessageCircle size={32} className="mx-auto mb-3 text-slate-300" />
                <p className="text-sm font-medium text-slate-600">
                  {patients.length ? 'Select a patient to open their conversation.' : 'No patients enrolled yet.'}
                </p>
                <p className="mt-1 text-xs">
                  {patients.length ? 'Their complete message history will appear here.' : 'Add a patient to start tracking care messages.'}
                </p>
              </div>
            </div>
          )}
        </section>
      </div>
    </main>
  )
}
