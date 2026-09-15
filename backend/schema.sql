CREATE TABLE IF NOT EXISTS documents (
    id SERIAL PRIMARY KEY,
    file_name VARCHAR(255) NOT NULL,
    storage_path TEXT NOT NULL,
    original_text TEXT,
    approved_text TEXT,
    status VARCHAR(50) DEFAULT 'uploaded',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP,
    json_output JSONB
);

CREATE TABLE IF NOT EXISTS extraction_runs (
    extraction_run_id BIGSERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    model_name VARCHAR(255) NOT NULL,
    ontology_version VARCHAR(32) NOT NULL DEFAULT '0.2',
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    raw_output_json JSONB,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS document_entities (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    entity_type VARCHAR(80) NOT NULL,
    entity_name VARCHAR(255) NOT NULL,
    entity_id VARCHAR(255) NOT NULL,
    alias VARCHAR(255),
    state VARCHAR(50) NOT NULL DEFAULT 'suggested',
    attributes_json JSONB,
    extraction_run_id BIGINT NOT NULL REFERENCES extraction_runs(extraction_run_id) ON DELETE CASCADE,
    confidence NUMERIC(4,3) DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS document_relationships (
    id SERIAL PRIMARY KEY,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    source_name VARCHAR(255) NOT NULL,
    target_name VARCHAR(255) NOT NULL,
    relationship_type VARCHAR(80) NOT NULL,
    relationship_id VARCHAR(255) NOT NULL,
    state VARCHAR(50) NOT NULL DEFAULT 'suggested',
    reasoning TEXT,
    source_ref TEXT,
    extraction_run_id BIGINT NOT NULL REFERENCES extraction_runs(extraction_run_id) ON DELETE CASCADE,
    confidence NUMERIC(4,3) DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS observations (
    id BIGSERIAL PRIMARY KEY,
    observation_id VARCHAR(255) NOT NULL UNIQUE,
    document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    observation_type VARCHAR(120) NOT NULL,
    raw_text TEXT NOT NULL,
    normalized_value JSONB,
    extraction_confidence NUMERIC(4,3),
    epistemic_state VARCHAR(50) NOT NULL DEFAULT 'SOURCE_ASSERTION',
    source_location JSONB,
    extraction_run_id BIGINT NOT NULL REFERENCES extraction_runs(extraction_run_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_document_entities_document_id ON document_entities(document_id);
CREATE INDEX IF NOT EXISTS idx_document_relationships_document_id ON document_relationships(document_id);
CREATE INDEX IF NOT EXISTS idx_extraction_runs_document_id ON extraction_runs(document_id);
CREATE INDEX IF NOT EXISTS idx_observations_document_id ON observations(document_id);
