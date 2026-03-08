DO $$
BEGIN
    CREATE TYPE user_role AS ENUM ('admin', 'member', 'support');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role user_role NOT NULL DEFAULT 'member',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS users_email_idx ON users (email);

CREATE TABLE IF NOT EXISTS audit_events (
    id SERIAL PRIMARY KEY,
    actor_email VARCHAR(255) NOT NULL,
    target_email VARCHAR(255) NOT NULL,
    event_type VARCHAR(128) NOT NULL,
    event_payload TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
