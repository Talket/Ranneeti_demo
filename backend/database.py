import os
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import psycopg2
from sqlalchemy import JSON, Column, DateTime, Integer, String, Text, create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DEFAULT_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/investigation_db"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def build_sqlite_url() -> str:
    return "sqlite:///" + str(Path(__file__).resolve().parent / "prototype.db")


def create_postgres_if_needed() -> bool:
    if not DATABASE_URL.startswith("postgresql"):
        return False

    parsed = urlparse(DATABASE_URL)
    db_name = parsed.path.lstrip("/") or "investigation_db"
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    user = parsed.username or "postgres"
    password = parsed.password or "postgres"

    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user=user,
            password=password,
            host=host,
            port=port,
        )
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
            exists = cur.fetchone()
            if not exists:
                cur.execute(f'CREATE DATABASE "{db_name}"')
        conn.close()
        return True
    except Exception:
        return False


def initialize_engine(database_url: str):
    if database_url.startswith("postgresql"):
        created = create_postgres_if_needed()
        if created or database_url.startswith("postgresql"):
            try:
                engine = create_engine(database_url, pool_pre_ping=True)
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1")).fetchone()
                return engine
            except Exception:
                pass

    fallback_db = build_sqlite_url()
    return create_engine(fallback_db, pool_pre_ping=True)


engine = initialize_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


class DocumentRecord(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    file_name = Column(String, nullable=False)
    storage_path = Column(String, nullable=False)
    original_text = Column(Text, nullable=True)
    approved_text = Column(Text, nullable=True)
    status = Column(String, default="uploaded")
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    json_output = Column(JSON, nullable=True)


class ExtractionRun(Base):
    __tablename__ = "extraction_runs"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, nullable=False, index=True)
    model_name = Column(String, nullable=False)
    ontology_version = Column(String, nullable=False, default="0.2")
    status = Column(String, nullable=False, default="pending")
    raw_output_json = Column(JSON, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)


class DocumentEntity(Base):
    __tablename__ = "document_entities"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, nullable=False, index=True)
    entity_type = Column(String, nullable=False)
    entity_name = Column(String, nullable=False)
    entity_id = Column(String, nullable=False, index=True)
    alias = Column(String, nullable=True)
    state = Column(String, nullable=False, default="suggested")
    attributes_json = Column(JSON, nullable=True)
    extraction_run_id = Column(Integer, nullable=False, index=True)
    confidence = Column(String, default="0.0")
    created_at = Column(DateTime, default=datetime.utcnow)


class DocumentRelationship(Base):
    __tablename__ = "document_relationships"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, nullable=False, index=True)
    source_name = Column(String, nullable=False)
    target_name = Column(String, nullable=False)
    relationship_type = Column(String, nullable=False)
    relationship_id = Column(String, nullable=False, index=True)
    state = Column(String, nullable=False, default="suggested")
    reasoning = Column(Text, nullable=True)
    source_ref = Column(String, nullable=True)
    extraction_run_id = Column(Integer, nullable=False, index=True)
    confidence = Column(String, default="0.0")
    created_at = Column(DateTime, default=datetime.utcnow)


class Observation(Base):
    __tablename__ = "observations"

    id = Column(Integer, primary_key=True, index=True)
    observation_id = Column(String, nullable=False, unique=True, index=True)
    document_id = Column(Integer, nullable=False, index=True)
    observation_type = Column(String, nullable=False)
    raw_text = Column(Text, nullable=False)
    normalized_value = Column(JSON, nullable=True)
    extraction_confidence = Column(String, nullable=True)
    epistemic_state = Column(String, nullable=False, default="SOURCE_ASSERTION")
    source_location = Column(JSON, nullable=True)
    extraction_run_id = Column(Integer, nullable=False, index=True)


Base.metadata.create_all(bind=engine)


def migrate_projection_columns():
    table_columns = {
        "document_entities": {
            "entity_id": "VARCHAR",
            "alias": "VARCHAR",
            "state": "VARCHAR DEFAULT 'suggested'",
            "attributes_json": "JSON",
            "extraction_run_id": "INTEGER DEFAULT 0",
        },
        "document_relationships": {
            "relationship_id": "VARCHAR",
            "state": "VARCHAR DEFAULT 'suggested'",
            "reasoning": "TEXT",
            "source_ref": "VARCHAR",
            "extraction_run_id": "INTEGER DEFAULT 0",
        },
    }

    inspector = inspect(engine)
    with engine.begin() as connection:
        for table_name, columns in table_columns.items():
            existing = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, column_type in columns.items():
                if column_name not in existing:
                    connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))


migrate_projection_columns()


def get_db() -> Session:
    db = SessionLocal()
    try:
        return db
    finally:
        pass
