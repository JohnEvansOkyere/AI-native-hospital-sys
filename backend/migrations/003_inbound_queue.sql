-- Durable inbound queue: the webhook stores each WhatsApp message and returns
-- at once; a background task or the per-minute sweep processes it.
ALTER TABLE inbound_events
    ADD COLUMN IF NOT EXISTS payload TEXT NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS attempts INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS started_at TEXT;

CREATE INDEX IF NOT EXISTS idx_inbound_events_status ON inbound_events(status, received_at);
CREATE INDEX IF NOT EXISTS idx_messages_external_id ON messages(external_message_id);
