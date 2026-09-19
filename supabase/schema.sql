-- ================================================================
-- AegisBot — Phase 1 Supabase Schema
-- Run this ONCE in the Supabase SQL editor before first launch.
-- ================================================================

-- customers: one row per WhatsApp number
CREATE TABLE IF NOT EXISTS customers (
    id              BIGSERIAL PRIMARY KEY,
    wa_id           TEXT UNIQUE NOT NULL,
    name            TEXT DEFAULT '',
    phone           TEXT DEFAULT '',
    city            TEXT DEFAULT '',
    budget          TEXT DEFAULT '',
    timeline        TEXT DEFAULT '',
    interest        TEXT DEFAULT '',
    source          TEXT DEFAULT 'whatsapp',
    status          TEXT DEFAULT 'lead',
    lead_score      INTEGER DEFAULT 0,
    qualified       INTEGER DEFAULT 0,
    last_active_at  TEXT,
    created_at      TEXT
);

-- conversations: per-user state machine (JSON blob in `state`)
CREATE TABLE IF NOT EXISTS conversations (
    id          BIGSERIAL PRIMARY KEY,
    customer_id INTEGER,
    wa_id       TEXT UNIQUE,
    state       TEXT DEFAULT '{}',
    mode        TEXT DEFAULT 'bot',
    created_at  TEXT,
    updated_at  TEXT
);

-- messages: full message log
CREATE TABLE IF NOT EXISTS messages (
    id              BIGSERIAL PRIMARY KEY,
    customer_id     INTEGER,
    wa_id           TEXT,
    direction       TEXT,       -- 'in' | 'out'
    sender          TEXT,       -- 'customer' | 'bot'
    text            TEXT DEFAULT '',
    timestamp       TEXT
);

-- leads: ONE row per captured lead (the main Phase 1 output)
CREATE TABLE IF NOT EXISTS leads (
    id          BIGSERIAL PRIMARY KEY,
    customer_id INTEGER,
    wa_id       TEXT,
    name        TEXT DEFAULT '',
    phone       TEXT DEFAULT '',
    interest    TEXT DEFAULT '',
    budget      TEXT DEFAULT '',
    timeline    TEXT DEFAULT '',
    location    TEXT DEFAULT '',
    source      TEXT DEFAULT 'whatsapp',
    score       INTEGER DEFAULT 0,
    qualified   INTEGER DEFAULT 0,      -- 1 = hot lead
    status      TEXT DEFAULT 'new',     -- new | qualified | won | lost
    notes       TEXT DEFAULT '',
    created_at  TEXT
);

-- orders: Phase 7 order taking & product purchases
CREATE TABLE IF NOT EXISTS orders (
    id              BIGSERIAL PRIMARY KEY,
    wa_id           TEXT NOT NULL,
    customer_name   TEXT DEFAULT '',
    items           TEXT DEFAULT '[]',   -- JSON array of cart items
    subtotal        NUMERIC(12, 2) DEFAULT 0.00,
    tax             NUMERIC(12, 2) DEFAULT 0.00,
    total           NUMERIC(12, 2) DEFAULT 0.00,
    status          TEXT DEFAULT 'pending', -- pending | confirmed | fulfilled | cancelled
    notes           TEXT DEFAULT '',
    created_at      TEXT
);

-- appointments: Phase 7 showroom visit & consultation bookings
CREATE TABLE IF NOT EXISTS appointments (
    id              BIGSERIAL PRIMARY KEY,
    wa_id           TEXT NOT NULL,
    customer_name   TEXT DEFAULT '',
    service         TEXT DEFAULT 'Showroom Visit',
    slot_start      TEXT NOT NULL,
    slot_end        TEXT NOT NULL,
    location        TEXT DEFAULT '',
    status          TEXT DEFAULT 'confirmed', -- confirmed | completed | cancelled
    created_at      TEXT
);

-- ── Access grants (anon key has full access; RLS off for this deploy) ────────
GRANT USAGE ON SCHEMA public TO anon, authenticated, service_role;
GRANT ALL ON ALL TABLES IN SCHEMA public TO anon, authenticated, service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO anon, authenticated, service_role;

ALTER TABLE public.customers      DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversations  DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages       DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.leads          DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.orders         DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.appointments   DISABLE ROW LEVEL SECURITY;
