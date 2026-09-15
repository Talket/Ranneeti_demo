import os
import uuid
import hashlib
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

try:
    from .database import DocumentRecord, Entity, ExtractionRun, Relationship, DEFAULT_CASE_ID, DEFAULT_USER_ID, get_db
    from .llm_client import call_reasoning_llm
except ImportError:
    from database import DocumentRecord, Entity, ExtractionRun, Relationship, DEFAULT_CASE_ID, DEFAULT_USER_ID, get_db
    from llm_client import call_reasoning_llm
try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None

try:
    from docx import Document as DocxDocument
except Exception:
    DocxDocument = None

UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads")))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Document Intake Prototype")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("CORS_ORIGINS", "*").split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
def document_ui():
    return FileResponse(BASE_DIR.parent / "index.html")


class LLMRequest(BaseModel):
    document_id: uuid.UUID
    text: str


class ApprovalRequest(BaseModel):
    approved_text: str


class ApprovedEvidenceRequest(BaseModel):
    case_id: str | None = None
    document_name: str
    page: int | None = None
    text: str


def extract_text(file_path: Path) -> str:
    suffix = file_path.suffix.lower()

    if suffix in {".txt", ".md", ".csv", ".log"}:
        return file_path.read_text(encoding="utf-8", errors="ignore")

    if suffix == ".pdf":
        if PdfReader is None:
            return "PDF parsing library is not installed in this environment."
        reader = PdfReader(str(file_path))
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        return "\n\n".join(pages).strip()

    if suffix == ".docx":
        if DocxDocument is None:
            return "DOCX parsing library is not installed in this environment."
        doc = DocxDocument(str(file_path))
        return "\n".join(paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip())

    if suffix in {".png", ".jpg", ".jpeg", ".bmp"}:
        return "OCR for uploaded image is not enabled in this prototype. Please use a text-based document for now."

    return "The file was accepted, but no text extraction handler is registered for this extension yet."


@app.get("/health")
def health():
    return {"status": "ok", "database": "configured"}


def latest_json_output(db, document_id):
    extraction_run = (
        db.query(ExtractionRun)
        .filter(ExtractionRun.document_id == document_id)
        .order_by(ExtractionRun.started_at.desc())
        .first()
    )
    return extraction_run.raw_output_json if extraction_run else None


@app.get("/api/documents")
def list_documents():
    db = get_db()
    try:
        records = db.query(DocumentRecord).order_by(DocumentRecord.created_at.desc()).all()
        return [
            {
                "id": str(record.document_id),
                "file_name": record.file_name,
                "status": record.processing_status,
                "original_text": None,
                "approved_text": record.approved_ocr_text,
                "json_output": latest_json_output(db, record.document_id),
            }
            for record in records
        ]
    finally:
        db.close()


@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    safe_name = file.filename.replace(" ", "_")
    unique_name = f"{uuid.uuid4()}_{safe_name}"
    file_path = UPLOAD_DIR / unique_name

    with file_path.open("wb") as buffer:
        content = await file.read()
        buffer.write(content)

    extracted_text = extract_text(file_path)

    db = get_db()
    try:
        record = DocumentRecord(
            case_id=DEFAULT_CASE_ID,
            file_name=safe_name,
            file_type=(file.content_type or file_path.suffix.lstrip(".") or "unknown").upper()[:30],
            storage_path=str(file_path),
            file_hash=hashlib.sha256(content).hexdigest(),
            processing_status="ocr_ready",
            created_by=DEFAULT_USER_ID,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
    finally:
        db.close()

    return {
        "id": str(record.document_id),
        "file_name": safe_name,
        "extracted_text": extracted_text,
        "status": record.processing_status,
        "message": "File uploaded and text extracted for officer review.",
    }


@app.post("/process")
async def legacy_process_document(file: UploadFile = File(...)):
    """Adapt the original VYUHA Pi upload contract to the current document intake flow."""
    uploaded = await upload_document(file)
    return {
        "document_id": uploaded["id"],
        "document_type": file.content_type or "unknown",
        "status": "success",
        "total_pages": 1,
        "processing_summary": {
            "pages_successful": 1,
            "pages_failed": 0,
            "total_processing_time": 0,
        },
        "pages": [{
            "page": 1,
            "status": "success",
            "page_processing_time": 0,
            "errors": [],
            "extracted_text": uploaded["extracted_text"],
            "stage3": {"source_text": uploaded["extracted_text"]},
        }],
    }


@app.post("/api/documents/{document_id}/approve")
async def approve_document(document_id: uuid.UUID, payload: ApprovalRequest):
    document_id = uuid.UUID(str(document_id))
    db = get_db()
    try:
        record = db.query(DocumentRecord).filter(DocumentRecord.document_id == document_id).first()
        if not record:
            raise HTTPException(status_code=404, detail="Document not found")

        record.approved_ocr_text = payload.approved_text
        record.processing_status = "approved"
        record.ocr_approved_by = DEFAULT_USER_ID
        record.ocr_approved_at = datetime.utcnow()
        db.commit()
        db.refresh(record)

        return {
            "id": str(record.document_id),
            "status": "approved",
            "approved_text": record.approved_ocr_text,
            "message": "Document approved by investigator and stored as authoritative OCR text.",
        }
    finally:
        db.close()


@app.post("/api/documents/{document_id}/process")
async def process_document(document_id: uuid.UUID):
    document_id = uuid.UUID(str(document_id))
    db = get_db()
    try:
        record = db.query(DocumentRecord).filter(DocumentRecord.document_id == document_id).first()
        if not record:
            raise HTTPException(status_code=404, detail="Document not found")

        if not record.approved_ocr_text:
            raise HTTPException(status_code=409, detail="Document must be approved before LLM processing")

        approved_text = record.approved_ocr_text
        extraction_run = ExtractionRun(
            document_id=document_id,
            case_id=record.case_id,
            triggered_by=DEFAULT_USER_ID,
            model_name=os.getenv("REASONING_LLM_MODEL", "offline-reasoning-model")[:60],
            status="pending",
        )
        db.add(extraction_run)
        db.flush()

        try:
            raw_llm_result = call_reasoning_llm(approved_text)
        except RuntimeError as error:
            extraction_run.status = "failed"
            extraction_run.error_message = str(error)
            extraction_run.completed_at = datetime.utcnow()
            db.commit()
            raise HTTPException(status_code=502, detail=str(error)) from error

        raw_llm_result = dict(raw_llm_result)
        extraction_run.raw_output_json = raw_llm_result
        extraction_run.status = "success"
        extraction_run.completed_at = datetime.utcnow()
        llm_result = dict(raw_llm_result.get("extraction") or raw_llm_result)
        llm_result["llm_status"] = raw_llm_result.get("status")
        llm_result["evidence"] = raw_llm_result.get("evidence")
        llm_result["document_id"] = str(document_id)

        entity_lookup = {}
        for entity in llm_result.get("entities", []):
            entity_name = entity.get("name") or entity.get("name_raw") or entity.get("value") or "Unknown entity"
            entity_type = str(entity.get("type") or entity.get("entity_type") or "OTHER").upper()[:20]
            entity_record = Entity(
                case_id=record.case_id,
                entity_type=entity_type,
                name=str(entity_name),
                alias=entity.get("alias"),
                influence_score=entity.get("influence_score"),
                state="ai_suggested",
                attributes_json=entity,
                extraction_run_id=extraction_run.extraction_run_id,
                created_by=DEFAULT_USER_ID,
            )
            db.add(entity_record)
            entity_lookup[str(entity_name).strip().lower()] = entity_record

        db.flush()

        for relationship in llm_result.get("relationships", []):
            source_name = str(relationship.get("source") or relationship.get("source_entity_id") or "unknown")
            target_name = str(relationship.get("target") or relationship.get("target_entity_id") or "unknown")
            source_entity = entity_lookup.get(source_name.strip().lower())
            target_entity = entity_lookup.get(target_name.strip().lower())
            if not source_entity or not target_entity:
                continue
            db.add(
                Relationship(
                    case_id=record.case_id,
                    source_entity_id=source_entity.entity_id,
                    target_entity_id=target_entity.entity_id,
                    relationship_type=str(relationship.get("type") or relationship.get("relationship_type") or "RELATED_TO").upper()[:40],
                    state="ai_suggested",
                    confidence=relationship.get("confidence"),
                    reasoning=relationship.get("reasoning"),
                    source_type="Uploaded Document",
                    source_ref=str(document_id),
                    extraction_run_id=extraction_run.extraction_run_id,
                    created_by=DEFAULT_USER_ID,
                )
            )

        db.commit()
        db.refresh(record)

        return {
            "id": str(record.document_id),
            "status": "approved",
            "json_output": llm_result,
            "message": "Approved document sent to the reasoning LLM and JSON saved to PostgreSQL.",
        }
    finally:
        db.close()


@app.post("/ai/extract")
async def legacy_extract_evidence(payload: ApprovedEvidenceRequest):
    db = get_db()
    try:
        record = (
            db.query(DocumentRecord)
            .filter(DocumentRecord.file_name == payload.document_name)
            .order_by(DocumentRecord.created_at.desc())
            .first()
        )
        if not record:
            raise HTTPException(status_code=404, detail="Uploaded document not found")

        record.approved_ocr_text = payload.text
        record.processing_status = "approved"
        record.ocr_approved_by = DEFAULT_USER_ID
        record.ocr_approved_at = datetime.utcnow()
        db.commit()
        document_id = record.document_id
    finally:
        db.close()

    processed = await process_document(document_id)
    return {"status": "ok", "extraction": processed["json_output"]}


@app.post("/api/llm/analyze")
async def analyze_document(payload: LLMRequest):
    result = call_reasoning_llm(payload.text)
    result["document_id"] = str(payload.document_id)
    return {"status": "ok", "json_output": result}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
