CREATE SCHEMA IF NOT EXISTS app;

CREATE TABLE IF NOT EXISTS app.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id TEXT UNIQUE,
    display_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS app.saved_trips (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    query TEXT NOT NULL,
    location TEXT NOT NULL,
    date_str TEXT NOT NULL,
    resolved_location JSONB,
    response TEXT NOT NULL,
    graph_run_id TEXT,
    thread_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_saved_trips_user_created
    ON app.saved_trips (user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS app.trip_favorites (
    user_id TEXT NOT NULL,
    trip_id UUID NOT NULL REFERENCES app.saved_trips(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, trip_id)
);
