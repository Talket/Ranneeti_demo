-- ============================================================================
-- VYUHA — Step-by-Step Database Build Script
-- Source: vyuha_schema.sql + vyuha_schema_reference.xlsx (uploaded files)
-- Run each numbered step in order (top to bottom). Every table is created
-- only after the tables it references (via FOREIGN KEY) already exist.
-- Target: PostgreSQL (uses UUID, TIMESTAMPTZ, JSONB, gen_random_uuid()).
-- ============================================================================

-- ----------------------------------------------------------------------------
-- No extensions required. gen_random_uuid() (used as the DEFAULT for every
-- primary key below) is a built-in core function on PostgreSQL 13+.
-- Requires: PostgreSQL 13 or later.
-- ----------------------------------------------------------------------------

-- ----------------------------------------------------------------------------
-- STEP 1 — users
-- Login identity + officer-profile fields (badge_id, division, station).
-- No dependencies — first table to create.
-- ----------------------------------------------------------------------------
CREATE TABLE users (
    user_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username        VARCHAR(64)  NOT NULL UNIQUE,
    display_name    VARCHAR(120) NOT NULL,
    role            VARCHAR(20)  NOT NULL,      -- officer, viewer, admin
    badge_id        VARCHAR(30),
    division        VARCHAR(120),
    station         VARCHAR(120),
    password_hash   TEXT         NOT NULL,
    status          VARCHAR(10)  NOT NULL DEFAULT 'active',  -- active, disabled
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    last_login_at   TIMESTAMPTZ
);


-- ----------------------------------------------------------------------------
-- STEP 2 — auth_logs
-- Login/logout/failed-login history. Depends on: users.
-- ----------------------------------------------------------------------------
CREATE TABLE auth_logs (
    auth_log_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(user_id),   -- nullable: unknown failed login
    event_type      VARCHAR(20) NOT NULL,              -- login, logout, failed_login
    success         BOOLEAN     NOT NULL,
    occurred_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- ----------------------------------------------------------------------------
-- STEP 3 — cases
-- Matches the Cases page. Depends on: users (lead_officer_id, created_by).
-- ----------------------------------------------------------------------------
CREATE TABLE cases (
    case_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_number     VARCHAR(40)  NOT NULL UNIQUE,      -- e.g. NCRB-2026-0143
    title           VARCHAR(200) NOT NULL,
    description     TEXT,
    status          VARCHAR(20)  NOT NULL,             -- active, pending_review, closed
    priority        VARCHAR(10)  NOT NULL DEFAULT 'medium', -- high, medium, low
    area            VARCHAR(150),                      -- free-text location, as rendered
    lead_officer_id UUID REFERENCES users(user_id),
    created_by      UUID REFERENCES users(user_id),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);


-- ----------------------------------------------------------------------------
-- STEP 4 — documents
-- Upload -> Pi OCR -> officer-approval pipeline. Depends on: cases, users.
-- ----------------------------------------------------------------------------
CREATE TABLE documents (
    document_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id             UUID NOT NULL REFERENCES cases(case_id),
    file_name           VARCHAR(255) NOT NULL,
    file_type           VARCHAR(30)  NOT NULL,
    storage_path        TEXT         NOT NULL,
    file_hash           VARCHAR(128),
    processing_status   VARCHAR(20)  NOT NULL DEFAULT 'uploaded', -- uploaded, processing, ocr_ready, approved, failed
    pi_job_id           VARCHAR(64),
    approved_ocr_text   TEXT,        -- authoritative text sent to Qwen; null until approved
    ocr_approved_by     UUID REFERENCES users(user_id),
    ocr_approved_at     TIMESTAMPTZ,
    created_by          UUID REFERENCES users(user_id),
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT now(),

    -- OCR approval is one atomic event: text, approver, and timestamp
    -- must arrive together, or not at all.
    CONSTRAINT documents_ocr_approval_consistency CHECK (
        (approved_ocr_text IS NULL AND ocr_approved_by IS NULL AND ocr_approved_at IS NULL)
        OR
        (approved_ocr_text IS NOT NULL AND ocr_approved_by IS NOT NULL AND ocr_approved_at IS NOT NULL)
    )
);


-- ----------------------------------------------------------------------------
-- STEP 5 — extraction_runs
-- One row per Qwen extraction call. Depends on: documents, cases, users.
-- ----------------------------------------------------------------------------
CREATE TABLE extraction_runs (
    extraction_run_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id         UUID NOT NULL REFERENCES documents(document_id),
    case_id             UUID NOT NULL REFERENCES cases(case_id),
    triggered_by         UUID REFERENCES users(user_id),
    model_name           VARCHAR(60) NOT NULL,           -- e.g. qwen3.5:9b
    status               VARCHAR(20) NOT NULL,           -- pending, success, failed
    raw_output_json      JSONB,                          -- exact Qwen response, pre-verification
    started_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at         TIMESTAMPTZ,
    error_message        TEXT
);


-- ----------------------------------------------------------------------------
-- STEP 6 — entities
-- Authoritative + AI-suggested entities in the investigation graph.
-- Depends on: cases, extraction_runs, users.
-- ----------------------------------------------------------------------------
CREATE TABLE entities (
    entity_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id           UUID NOT NULL REFERENCES cases(case_id),
    entity_type       VARCHAR(20) NOT NULL,   -- PERSON, ORGANIZATION, LOCATION, PHONE, EMAIL, VEHICLE, DATE, OTHER
    name              VARCHAR(255) NOT NULL,
    alias             VARCHAR(255),
    influence_score   NUMERIC(5,2),
    state             VARCHAR(20) NOT NULL DEFAULT 'ai_suggested', -- ai_suggested, verified, deleted, merged
    attributes_json   JSONB,
    extraction_run_id UUID REFERENCES extraction_runs(extraction_run_id),  -- null if manually created
    created_by        UUID REFERENCES users(user_id),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    verified_by       UUID REFERENCES users(user_id),
    verified_at       TIMESTAMPTZ,
    deleted_by        UUID REFERENCES users(user_id),
    deleted_at        TIMESTAMPTZ,

    -- an entity cannot be in the 'verified' (authoritative) state without
    -- a recorded human approval — mirrors the same guarantee relationships
    -- already has via its own verified_by/verified_at columns.
    CONSTRAINT entities_verified_requires_approval CHECK (
        state <> 'verified' OR (verified_by IS NOT NULL AND verified_at IS NOT NULL)
    )
);


-- ----------------------------------------------------------------------------
-- STEP 7 — relationships
-- Review queue's "Relationships" tab + graph edges shown in Investigation.
-- Depends on: cases, entities, extraction_runs, users.
-- ----------------------------------------------------------------------------
CREATE TABLE relationships (
    relationship_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id           UUID NOT NULL REFERENCES cases(case_id),
    source_entity_id  UUID NOT NULL REFERENCES entities(entity_id),
    target_entity_id  UUID NOT NULL REFERENCES entities(entity_id),
    relationship_type VARCHAR(40) NOT NULL,   -- WORKS_FOR, MET, USES, CONTACTED, ...
    state             VARCHAR(20) NOT NULL DEFAULT 'ai_suggested', -- ai_suggested, verified, rejected, removed
    confidence        NUMERIC(5,2),
    reasoning         TEXT,
    source_type       VARCHAR(60),            -- e.g. FIR, CDR, Uploaded Document
    source_ref        TEXT,
    recorded_on       DATE,
    extraction_run_id UUID REFERENCES extraction_runs(extraction_run_id),
    created_by        UUID REFERENCES users(user_id),
    verified_by       UUID REFERENCES users(user_id),
    verified_at       TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- ----------------------------------------------------------------------------
-- STEP 8 — duplicate_candidates
-- Review queue's "Duplicate entities" tab. Depends on: cases, entities, users.
-- ----------------------------------------------------------------------------
CREATE TABLE duplicate_candidates (
    duplicate_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id           UUID NOT NULL REFERENCES cases(case_id),
    entity_a_id       UUID NOT NULL REFERENCES entities(entity_id),  -- one of the two candidate entities
    entity_b_id       UUID NOT NULL REFERENCES entities(entity_id),  -- the other candidate entity; no fixed role until resolved
    status            VARCHAR(20) NOT NULL DEFAULT 'pending',  -- pending, merged, kept_separate, later
    resolved_by       UUID REFERENCES users(user_id),
    resolved_at       TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- ----------------------------------------------------------------------------
-- STEP 9 — missing_links
-- Review queue's "Missing links" tab.
-- Depends on: cases, entities, extraction_runs, users.
-- ----------------------------------------------------------------------------
CREATE TABLE missing_links (
    missing_link_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id                     UUID NOT NULL REFERENCES cases(case_id),
    source_entity_id            UUID NOT NULL REFERENCES entities(entity_id),
    target_entity_id            UUID REFERENCES entities(entity_id),  -- may not be identified yet
    suggested_relationship_type VARCHAR(40),
    evidence_text               TEXT,
    status                      VARCHAR(20) NOT NULL DEFAULT 'open',  -- open, resolved, rejected
    suggested_by_run_id         UUID REFERENCES extraction_runs(extraction_run_id),
    resolved_by                 UUID REFERENCES users(user_id),
    resolved_at                 TIMESTAMPTZ,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- ----------------------------------------------------------------------------
-- STEP 10 — alerts
-- Matches the Alerts page. Depends on: cases, entities, users.
-- ----------------------------------------------------------------------------
CREATE TABLE alerts (
    alert_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id       UUID REFERENCES cases(case_id),
    entity_id     UUID REFERENCES entities(entity_id),
    severity      VARCHAR(10) NOT NULL,   -- critical, warning, info
    status        VARCHAR(10) NOT NULL DEFAULT 'open',  -- open, reviewing, resolved
    title         VARCHAR(200) NOT NULL,
    description   TEXT,
    reasoning     TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_by   UUID REFERENCES users(user_id),
    resolved_at   TIMESTAMPTZ
);


-- ----------------------------------------------------------------------------
-- STEP 11 — checklist_items
-- Backs the "Personal checklist" page. Depends on: users, cases.
-- ----------------------------------------------------------------------------
CREATE TABLE checklist_items (
    checklist_item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assigned_to       UUID NOT NULL REFERENCES users(user_id),
    case_id           UUID REFERENCES cases(case_id),   -- nullable: not every task is case-linked
    task              TEXT NOT NULL,
    status            VARCHAR(15) NOT NULL DEFAULT 'pending',  -- pending, in_progress, done
    priority          VARCHAR(10) NOT NULL DEFAULT 'medium',   -- high, medium, low
    assigned_by       VARCHAR(120),        -- NOT a user FK: real data includes "System — review queue"
                                            -- alongside named officers, so this isn't always a user record
    due_date          DATE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at      TIMESTAMPTZ
);


-- ----------------------------------------------------------------------------
-- STEP 12 — predictions
-- Matches the Predictions page. Depends on: cases.
-- ----------------------------------------------------------------------------
CREATE TABLE predictions (
    prediction_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id           UUID NOT NULL REFERENCES cases(case_id),
    model_name        VARCHAR(60) NOT NULL,
    prediction_type   VARCHAR(60) NOT NULL,
    predicted_event   TEXT NOT NULL,
    probability       NUMERIC(5,4),
    explanation       TEXT,
    status            VARCHAR(15) NOT NULL DEFAULT 'active',  -- active, closed
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- ----------------------------------------------------------------------------
-- STEP 13 — prediction_outcomes
-- Backs the "Log outcome" action on the Predictions page.
-- Depends on: predictions, users.
-- ----------------------------------------------------------------------------
CREATE TABLE prediction_outcomes (
    outcome_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prediction_id   UUID NOT NULL REFERENCES predictions(prediction_id),
    outcome_status  VARCHAR(20) NOT NULL,  -- occurred, did_not_occur, unknown
    actual_outcome  TEXT,
    outcome_notes   TEXT,
    submitted_by    UUID REFERENCES users(user_id),
    submitted_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- ----------------------------------------------------------------------------
-- STEP 14 — audit_logs
-- Central audit trail for important actions across the system.
-- Depends on: users, cases. (Last table — created after everything it
-- could reasonably need to log actions against already exists.)
-- ----------------------------------------------------------------------------
CREATE TABLE audit_logs (
    audit_log_id   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        UUID REFERENCES users(user_id),
    case_id        UUID REFERENCES cases(case_id),
    action         VARCHAR(60) NOT NULL,   -- CASE_CREATED, DOCUMENT_APPROVED, ENTITY_MERGED, ...
    target_type    VARCHAR(30) NOT NULL,   -- case, entity, document, ...
    target_id      UUID,
    changes        JSONB,                  -- relevant before/after values, when applicable
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================================
-- END OF BUILD SCRIPT — 14 tables created. No extensions used.
-- Tables intentionally NOT present (per vyuha_schema.sql notes):
--   notifications, ai_suggestions, entity_merges, entity_evidence
--   (each was superseded by alerts / entities.state & relationships.state /
--    duplicate_candidates / relationships' own source_type-source_ref-reasoning
--    columns, respectively).
-- ============================================================================
