ALTER TABLE patients
    ADD COLUMN IF NOT EXISTS patient_context TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS profile_updated_at TEXT,
    ADD COLUMN IF NOT EXISTS profile_updated_by TEXT NOT NULL DEFAULT '';
