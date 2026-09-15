import os
import uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import psycopg2
from sqlalchemy import JSON, Column, Date, DateTime, ForeignKey, Numeric, String, Text, create_engine, inspect, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DEFAULT_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/investigation_db"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def build_sqlite_url() -> str:
    return "sqlite:///" + str(Path(__file__).resolve().parent / "vyuha.db")


def create_postgres_if_needed(database_url: str) -> bool:
    if not database_url.startswith("postgresql"):
        return False

    parsed = urlparse(database_url)
    db_name = parsed.path.lstrip("/") or "investigation_db"
    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user=parsed.username or "postgres",
            password=parsed.password or "postgres",
            host=parsed.hostname or "localhost",
            port=parsed.port or 5432,
        )
        conn.autocommit = True
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
            if cursor.fetchone() is None:
                cursor.execute(f'CREATE DATABASE "{db_name}"')
        conn.close()
        return True
    except Exception:
        return False


def initialize_engine(database_url: str):
    if database_url.startswith("postgresql"):
        create_postgres_if_needed(database_url)
        try:
            engine = create_engine(database_url, pool_pre_ping=True)
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return engine
        except Exception:
            pass
    return create_engine(build_sqlite_url(), pool_pre_ping=True)


engine = initialize_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def initialize_vyuha_schema() -> None:
    if engine.dialect.name != "postgresql":
        return

    expected_tables = {
        "users", "auth_logs", "cases", "documents", "extraction_runs",
        "entities", "relationships", "duplicate_candidates", "missing_links",
        "alerts", "checklist_items", "predictions", "prediction_outcomes", "audit_logs",
    }
    existing_tables = set(inspect(engine).get_table_names())
    if not existing_tables:
        should_initialize = True
    elif expected_tables.issubset(existing_tables):
        return
    else:
        missing_tables = ", ".join(sorted(expected_tables - existing_tables))
        raise RuntimeError(
            "PostgreSQL contains a partial or legacy schema. "
            f"Missing VYUHA tables: {missing_tables}. "
            "Create a fresh database and run vyuha_database_build_steps.sql before starting the API."
        )

    if not should_initialize:
        return

    schema_path = Path(__file__).resolve().parent.parent / "vyuha_database_build_steps.sql"
    schema_sql = schema_path.read_text(encoding="utf-8")
    raw_connection = engine.raw_connection()
    try:
        with raw_connection.cursor() as cursor:
            cursor.execute(schema_sql)
        raw_connection.commit()
    finally:
        raw_connection.close()


initialize_vyuha_schema()


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(64), nullable=False, unique=True)
    display_name = Column(String(120), nullable=False)
    role = Column(String(20), nullable=False, default="officer")
    badge_id = Column(String(30), nullable=True)
    division = Column(String(120), nullable=True)
    station = Column(String(120), nullable=True)
    password_hash = Column(Text, nullable=False, default="prototype-only")
    status = Column(String(10), nullable=False, default="active")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)


class CaseRecord(Base):
    __tablename__ = "cases"

    case_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_number = Column(String(40), nullable=False, unique=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="active")
    priority = Column(String(10), nullable=False, default="high")
    area = Column(String(150), nullable=True)
    lead_officer_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class DocumentRecord(Base):
    __tablename__ = "documents"

    document_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.case_id"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(30), nullable=False)
    storage_path = Column(Text, nullable=False)
    file_hash = Column(String(128), nullable=True)
    processing_status = Column(String(20), nullable=False, default="uploaded")
    pi_job_id = Column(String(64), nullable=True)
    approved_ocr_text = Column(Text, nullable=True)
    ocr_approved_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    ocr_approved_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class ExtractionRun(Base):
    __tablename__ = "extraction_runs"

    extraction_run_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.document_id"), nullable=False)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.case_id"), nullable=False)
    triggered_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    model_name = Column(String(60), nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    raw_output_json = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    started_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)


class Entity(Base):
    __tablename__ = "entities"

    entity_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.case_id"), nullable=False)
    entity_type = Column(String(20), nullable=False)
    name = Column(String(255), nullable=False)
    alias = Column(String(255), nullable=True)
    influence_score = Column(Numeric(5, 2), nullable=True)
    state = Column(String(20), nullable=False, default="ai_suggested")
    attributes_json = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    extraction_run_id = Column(UUID(as_uuid=True), ForeignKey("extraction_runs.extraction_run_id"), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    verified_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)


class Relationship(Base):
    __tablename__ = "relationships"

    relationship_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID(as_uuid=True), ForeignKey("cases.case_id"), nullable=False)
    source_entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.entity_id"), nullable=False)
    target_entity_id = Column(UUID(as_uuid=True), ForeignKey("entities.entity_id"), nullable=False)
    relationship_type = Column(String(40), nullable=False)
    state = Column(String(20), nullable=False, default="ai_suggested")
    confidence = Column(Numeric(5, 2), nullable=True)
    reasoning = Column(Text, nullable=True)
    source_type = Column(String(60), nullable=True)
    source_ref = Column(Text, nullable=True)
    recorded_on = Column(Date, nullable=True)
    extraction_run_id = Column(UUID(as_uuid=True), ForeignKey("extraction_runs.extraction_run_id"), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    verified_by = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


Base.metadata.create_all(bind=engine)


def seed_vyuha_context() -> tuple[uuid.UUID, uuid.UUID]:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "officer").first()
        if user is None:
            user = User(
                username="officer",
                display_name="I. Sharma",
                role="officer",
                badge_id="PB-4471",
                division="Women Safety Division",
                station="NCRB Cell, Ludhiana Range",
                password_hash="prototype-only",
            )
            db.add(user)
            db.flush()

        case = db.query(CaseRecord).filter(CaseRecord.case_number == "CASE-2026-NCRB-8842").first()
        if case is None:
            case = CaseRecord(
                case_number="CASE-2026-NCRB-8842",
                title="Op: Shadow Node (Inter-State Smuggling)",
                status="active",
                priority="high",
                lead_officer_id=user.user_id,
                created_by=user.user_id,
            )
            db.add(case)
        db.commit()
        return case.case_id, user.user_id
    finally:
        db.close()


DEFAULT_CASE_ID, DEFAULT_USER_ID = seed_vyuha_context()


def get_db() -> Session:
    return SessionLocal()
