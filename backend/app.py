import os
import uuid
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
    from .database import DocumentEntity, DocumentRecord, DocumentRelationship, ExtractionRun, Observation, get_db
    from .llm_client import call_reasoning_llm
except ImportError:
    from database import DocumentEntity, DocumentRecord, DocumentRelationship, ExtractionRun, Observation, get_db
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
    document_id: int
    text: str


class ApprovalRequest(BaseModel):
    approved_text: str


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


@app.get("/api/documents")
def list_documents():
    db = get_db()
    try:
        records = db.query(DocumentRecord).order_by(DocumentRecord.created_at.desc()).all()
        return [
            {
                "id": record.id,
                "file_name": record.file_name,
                "status": record.status,
                "original_text": record.original_text,
                "approved_text": record.approved_text,
                "json_output": record.json_output,
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
            file_name=safe_name,
            storage_path=str(file_path),
            original_text=extracted_text,
            status="uploaded",
        )
        db.add(record)
        db.commit()
        db.refresh(record)
    finally:
        db.close()

    return {
        "id": record.id,
        "file_name": safe_name,
        "extracted_text": extracted_text,
        "status": "uploaded",
        "message": "File uploaded to the Raspberry Pi prototype storage and text extracted for review.",
    }


@app.post("/api/documents/{document_id}/approve")
async def approve_document(document_id: int, payload: ApprovalRequest):
    db = get_db()
    try:
        record = db.query(DocumentRecord).filter(DocumentRecord.id == document_id).first()
        if not record:
            raise HTTPException(status_code=404, detail="Document not found")

        record.approved_text = payload.approved_text
        record.status = "approved"
        record.approved_at = datetime.utcnow()
        db.commit()
        db.refresh(record)

        return {
            "id": record.id,
            "status": "approved",
            "approved_text": record.approved_text,
            "message": "Document approved by investigator and queued for PostgreSQL storage.",
        }
    finally:
        db.close()


@app.post("/api/documents/{document_id}/process")
async def process_document(document_id: int):
    db = get_db()
    try:
        record = db.query(DocumentRecord).filter(DocumentRecord.id == document_id).first()
        if not record:
            raise HTTPException(status_code=404, detail="Document not found")

        if not record.approved_text:
            raise HTTPException(status_code=409, detail="Document must be approved before LLM processing")

        approved_text = record.approved_text
        extraction_run = ExtractionRun(
            document_id=document_id,
            model_name=os.getenv("REASONING_LLM_MODEL", "offline-reasoning-model"),
            ontology_version="0.2",
            status="running",
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
        extraction_run.status = "succeeded"
        extraction_run.completed_at = datetime.utcnow()
        llm_result = dict(raw_llm_result.get("extraction") or raw_llm_result)
        llm_result["llm_status"] = raw_llm_result.get("status")
        llm_result["evidence"] = raw_llm_result.get("evidence")
        llm_result["document_id"] = f"document:{document_id}"
        record.json_output = llm_result
        record.status = "reasoned"

        for entity in llm_result.get("entities", []):
            entity_name = entity.get("name") or entity.get("name_raw") or entity.get("value") or "Unknown entity"
            entity_type = str(entity.get("type") or entity.get("entity_type") or "unknown").lower()
            entity_id = entity.get("entity_id") or f"{entity_type}:{uuid.uuid5(uuid.NAMESPACE_URL, f'{document_id}:{entity_type}:{entity_name}')}"
            db.add(
                DocumentEntity(
                    document_id=document_id,
                    entity_type=entity_type,
                    entity_name=str(entity_name),
                    entity_id=entity_id,
                    alias=entity.get("alias"),
                    state=str(entity.get("state", "suggested")),
                    attributes_json=entity,
                    extraction_run_id=extraction_run.id,
                    confidence=str(entity.get("confidence", 0.0)),
                )
            )

        for relationship in llm_result.get("relationships", []):
            source_name = str(relationship.get("source") or relationship.get("source_entity_id") or "unknown")
            target_name = str(relationship.get("target") or relationship.get("target_entity_id") or "unknown")
            relationship_type = str(relationship.get("type") or relationship.get("relationship_type") or "RELATED_TO")
            relationship_id = relationship.get("relationship_id") or f"rel:{uuid.uuid5(uuid.NAMESPACE_URL, f'{document_id}:{source_name}:{relationship_type}:{target_name}')}"
            db.add(
                DocumentRelationship(
                    document_id=document_id,
                    source_name=source_name,
                    target_name=target_name,
                    relationship_type=relationship_type,
                    relationship_id=relationship_id,
                    state=str(relationship.get("resolution_status", "CANDIDATE")).lower(),
                    reasoning=relationship.get("reasoning"),
                    source_ref=relationship.get("source_ref"),
                    extraction_run_id=extraction_run.id,
                    confidence=str(relationship.get("confidence", 0.0)),
                )
            )

        observation_id = f"obs:{uuid.uuid5(uuid.NAMESPACE_URL, f'{document_id}:{extraction_run.id}:document') }"
        db.add(
            Observation(
                observation_id=observation_id,
                document_id=document_id,
                observation_type="LLM_EXTRACTION_SOURCE",
                raw_text=approved_text,
                normalized_value={"entity_count": len(llm_result.get("entities", [])), "relationship_count": len(llm_result.get("relationships", []))},
                extraction_confidence=str(llm_result.get("confidence", "")),
                epistemic_state="SOURCE_ASSERTION",
                source_location={"character_start": 0, "character_end": len(approved_text)},
                extraction_run_id=extraction_run.id,
            )
        )

        db.commit()
        db.refresh(record)

        return {
            "id": record.id,
            "status": "reasoned",
            "json_output": llm_result,
            "message": "Approved document sent to the reasoning LLM and JSON saved to PostgreSQL.",
        }
    finally:
        db.close()


@app.post("/api/llm/analyze")
async def analyze_document(payload: LLMRequest):
    result = call_reasoning_llm(payload.text)
    result["document_id"] = payload.document_id
    return {"status": "ok", "json_output": result}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
