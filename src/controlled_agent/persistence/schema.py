from __future__ import annotations


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS agent_runs (
    run_id TEXT PRIMARY KEY,

    user_message TEXT NOT NULL,
    latest_user_message TEXT,

    order_id TEXT,
    order_status TEXT,
    days_delayed INTEGER,

    awaiting_approval INTEGER NOT NULL DEFAULT 0,
    human_approved INTEGER,

    ticket_id TEXT,

    steps INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,

    finished INTEGER NOT NULL DEFAULT 0,
    awaiting_user_input INTEGER NOT NULL DEFAULT 0,

    final_message TEXT,

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS tickets (
    ticket_id TEXT PRIMARY KEY,

    order_id TEXT NOT NULL,
    reason TEXT NOT NULL,

    idempotency_key TEXT NOT NULL UNIQUE,

    status TEXT NOT NULL,

    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS approvals (
    approval_id TEXT PRIMARY KEY,

    run_id TEXT NOT NULL,

    action TEXT NOT NULL,

    order_id TEXT,
    context_hash TEXT,

    approved INTEGER,

    requested_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    decided_at TEXT,
    consumed_at TEXT,

    FOREIGN KEY (run_id)
        REFERENCES agent_runs(run_id)
        ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    run_id TEXT,

    step INTEGER NOT NULL,

    event TEXT NOT NULL,
    detail TEXT NOT NULL,

    timestamp TEXT NOT NULL,

    FOREIGN KEY (run_id)
        REFERENCES agent_runs(run_id)
        ON DELETE CASCADE
);


CREATE INDEX IF NOT EXISTS idx_agent_runs_status
    ON agent_runs(status);


CREATE INDEX IF NOT EXISTS idx_agent_runs_order_id
    ON agent_runs(order_id);


CREATE INDEX IF NOT EXISTS idx_tickets_order_id
    ON tickets(order_id);


CREATE INDEX IF NOT EXISTS idx_audit_events_run_id
    ON audit_events(run_id);


CREATE INDEX IF NOT EXISTS idx_approvals_run_id
    ON approvals(run_id);
"""