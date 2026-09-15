# from fastapi import FastAPI, HTTPException
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel
# import httpx
# import json
# from pathlib import Path

# app = FastAPI(title="Yo")


# # =========================
# # CORS
# # =========================

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=[
#         "http://192.168.137.9:5560",
#         "http://localhost:5500",
#     ],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# # =========================
# # LOAD CANONICAL POLE+
# # =========================
# POLE_PLUS_PATH = Path(r"D:\SIH\Ranneti\Ranneeti_demo\case structure.json")

# try:
#     with open(POLE_PLUS_PATH, "r", encoding="utf-8") as f:
#         POLE_PLUS = json.load(f)

#     POLE_PLUS_TEXT = json.dumps(
#         POLE_PLUS,
#         ensure_ascii=False
#     )

# except Exception as e:
#     raise RuntimeError(
#         f"Failed to load POLE+ ontology: {e}"
#     )


# # =========================
# # Request Models
# # =========================

# class EvidenceRequest(BaseModel):
#     text: str


# # =========================
# # Basic Routes
# # =========================

# @app.get("/")
# def home():
#     return {
#         "message": " backend is running"
#     }


# @app.get("/health")
# def health():
#     return {
#         "status": "ok",
#         "ollama": "http://localhost:11434",
#         "model": "qwen3.5:9b",
#         "pole_plus": "0.2"
#     }


# # =========================
# # QWEN EXTRACTION
# # =========================

# @app.post("/ai/extract")
# async def ai_extract(request: EvidenceRequest):

#     evidence = request.text.strip()

#     if not evidence:
#         raise HTTPException(
#             status_code=400,
#             detail="Evidence text cannot be empty"
#         )

#     prompt = f"""
# You are the  intelligence extraction engine.

# ==================================================
# CANONICAL POLE+ ONTOLOGY
# ==================================================

# The following JSON is the authoritative POLE+ ontology.
# You MUST use it as the reference for this extraction.

# {POLE_PLUS_TEXT}

# ==================================================
# END POLE+ ONTOLOGY
# ==================================================

# ==================================================
# SOURCE EVIDENCE
# ==================================================

# {evidence}

# ==================================================
# END SOURCE EVIDENCE
# ==================================================

# TASK:

# Extract information from the SOURCE EVIDENCE according to
# the CANONICAL POLE+ ONTOLOGY.

# STRICT RULES:

# 1. Use ONLY information explicitly supported by the SOURCE EVIDENCE.
# 2. Do NOT use outside knowledge.
# 3. Do NOT hallucinate.
# 4. Do NOT infer unsupported facts.
# 5. Do NOT create relationships from mere co-occurrence.
# 6. Do NOT invent entities.
# 7. Do NOT invent relationship types.
# 8. Use the ontology's terminology and controlled relationship types.
# 9. Preserve raw source information.
# 10. Preserve epistemic distinctions.
# 11. Do not resolve identities without evidence.
# 12. Do not convert an allegation or inference into an established fact.
# 13. If information cannot be safely established from the evidence, omit it.
# 14. Do not duplicate entities.
# 15. Do not duplicate relationships.
# 16. Every relationship must be supported by the supplied evidence.
# 17. Return ONLY valid JSON.
# 18. Do not return Markdown or explanations.

# The POLE+ ontology is the authority.
# The SOURCE EVIDENCE is the only factual source.

# ==================================================
# OUTPUT
# ==================================================

# Return structured JSON containing the extracted
# entities, observations, events, relationships, and
# other information supported by the source.
# """


#     payload = {
#         "model": "qwen3.5:9b",
#         "messages": [
#             {
#                 "role": "user",
#                 "content": prompt
#             }
#         ],
#         "stream": False,
#         "think": False,
#         "format": "json"
#     }

#     try:

#         async with httpx.AsyncClient(
#             timeout=300.0
#         ) as client:

#             response = await client.post(
#                 "http://127.0.0.1:11434/api/chat",
#                 json=payload
#             )

#         response.raise_for_status()

#         ollama_result = response.json()

#         content = ollama_result["message"]["content"]

#         extracted = json.loads(content)

#         return {
#             "status": "AI_SUGGESTED",
#             "evidence": evidence,
#             "ontology_version": POLE_PLUS.get(
#                 "ontology_version",
#                 "unknown"
#             ),
#             "extraction": extracted
#         }

#     except httpx.ConnectError:
#         raise HTTPException(
#             status_code=503,
#             detail="Cannot connect to Ollama. Make sure Ollama is running."
#         )

#     except httpx.TimeoutException:
#         raise HTTPException(
#             status_code=504,
#             detail="Qwen took too long to respond."
#         )

#     except json.JSONDecodeError:
#         raise HTTPException(
#             status_code=500,
#             detail="Qwen returned invalid JSON."
#         )

#     except httpx.HTTPStatusError as e:
#         raise HTTPException(
#             status_code=502,
#             detail=f"Ollama returned an error: {e.response.text}"
#         )




import json
import os
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Ranneeti AI Extraction Backend")


# =========================
# CORS
# =========================
# The frontend (script.js) is a static site — it can be opened straight from
# disk, served by VS Code "Live Server", or served by any other local static
# file server. Add whatever origin you actually load index.html from here.

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:8080",
        "http://localhost:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# CONFIG — edit these for your deployment
# =========================
# Ollama server this backend talks to (usually localhost on the same
# machine, or the Pi's own address if Ollama runs there).
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3.5:9b")

# Path to the POLE+ ontology file. Defaults to "case structure.json" living
# one folder above this file (i.e. Ranneeti_demo/case structure.json, which
# is where it ships in this project). Override with the POLE_PLUS_PATH
# environment variable if you move it (e.g. on the Pi's own filesystem).
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_POLE_PLUS_PATH = BASE_DIR.parent / "case structure.json"
POLE_PLUS_PATH = Path(os.environ.get("POLE_PLUS_PATH", DEFAULT_POLE_PLUS_PATH))

try:
    with open(POLE_PLUS_PATH, "r", encoding="utf-8") as f:
        POLE_PLUS = json.load(f)
except Exception as e:
    raise RuntimeError(
        f"Failed to load POLE+ ontology from {POLE_PLUS_PATH}: {e}. "
        f"Set the POLE_PLUS_PATH environment variable if the file lives "
        f"somewhere else on this machine."
    )

# The frontend network graph only understands 5 entity types. The full
# POLE+ ontology defines many more (Vehicle, Weapon, Event, ...), but we
# only ask the model to extract what the UI can actually render, and we
# reuse the ontology's own controlled relationship vocabulary as guidance
# so labels stay consistent with POLE+ terminology.
SUPPORTED_ENTITY_TYPES = ["person", "organization", "location", "vehicle", "phone"]
CONTROLLED_RELATIONSHIP_TYPES = (
    POLE_PLUS.get("relationships", {}).get("controlled_relationship_types", {})
)

EXTRACTION_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "type": {"type": "string", "enum": SUPPORTED_ENTITY_TYPES},
                    "metadata": {"type": "object"},
                },
                "required": ["name", "type"],
            },
        },
        "relationships": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source": {"type": "string"},
                    "source_type": {"type": "string", "enum": SUPPORTED_ENTITY_TYPES},
                    "target": {"type": "string"},
                    "target_type": {"type": "string", "enum": SUPPORTED_ENTITY_TYPES},
                    "relationship_type": {"type": "string"},
                    "label": {"type": "string"},
                    "confidence": {"type": "number"},
                    "reasoning": {"type": "string"},
                },
                "required": ["source", "target", "relationship_type"],
            },
        },
    },
    "required": ["entities", "relationships"],
}


# =========================
# Request Models
# =========================

class EvidenceRequest(BaseModel):
    case_id: str | None = None
    document_name: str | None = None
    page: int | None = None
    text: str


# =========================
# Basic Routes
# =========================

@app.get("/")
def home():
    return {"message": "backend is running"}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "ollama": OLLAMA_BASE_URL,
        "model": OLLAMA_MODEL,
        "pole_plus": POLE_PLUS.get("ontology_version", "unknown"),
    }


# =========================
# AI EXTRACTION
# =========================

def build_prompt(evidence: str) -> str:
    return f"""
You are the intelligence extraction engine for a criminal network analysis
tool. You extract structured entities and relationships from a single piece
of approved evidence text, grounded in the POLE+ ontology used by this case.

==================================================
CONTROLLED VOCABULARY (POLE+ v{POLE_PLUS.get("ontology_version", "unknown")})
==================================================

Entity types you may use (nothing else): {json.dumps(SUPPORTED_ENTITY_TYPES)}

Controlled relationship types, for reference when choosing relationship_type
and writing the label (pick the closest match; if nothing fits, describe the
relationship briefly instead of inventing a new controlled type):
{json.dumps(CONTROLLED_RELATIONSHIP_TYPES, ensure_ascii=False)}

==================================================
SOURCE EVIDENCE
==================================================

{evidence}

==================================================
END SOURCE EVIDENCE
==================================================

STRICT RULES:

1. Use ONLY information explicitly supported by the SOURCE EVIDENCE.
2. Do NOT use outside knowledge and do NOT hallucinate.
3. Do NOT infer unsupported facts.
4. Do NOT create relationships from mere co-occurrence in the text unless
   the text actually states or clearly implies a connection.
5. Do NOT invent entities.
6. Do NOT duplicate entities or relationships.
7. Every relationship must be supported by the supplied evidence, and its
   "reasoning" must point to what in the text supports it.
8. "confidence" is 0-100: how certain you are this relationship is actually
   stated (not merely plausible) by the evidence.
9. Only use entity types from the controlled vocabulary above. If something
   doesn't fit one of those 5 types, omit it rather than forcing a type.
10. Return ONLY the JSON object described below. No markdown, no prose.

OUTPUT SHAPE:

{{
  "entities": [
    {{"name": "...", "type": "person|organization|location|vehicle|phone", "metadata": {{"...": "..."}}}}
  ],
  "relationships": [
    {{
      "source": "<entity name, must match an entry in entities>",
      "source_type": "person|organization|location|vehicle|phone",
      "target": "<entity name, must match an entry in entities>",
      "target_type": "person|organization|location|vehicle|phone",
      "relationship_type": "<controlled type from the vocabulary above>",
      "label": "<short human-readable label, e.g. 'Associate of'>",
      "confidence": 0-100,
      "reasoning": "<why the evidence supports this>"
    }}
  ]
}}

If no entities or relationships can be safely established, return
{{"entities": [], "relationships": []}}.
"""


@app.post("/ai/extract")
async def ai_extract(request: EvidenceRequest):
    evidence = request.text.strip()

    if not evidence:
        raise HTTPException(status_code=400, detail="Evidence text cannot be empty")

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": build_prompt(evidence)}],
        "stream": False,
        "think": False,
        "format": EXTRACTION_JSON_SCHEMA,
    }

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json=payload,
            )

        response.raise_for_status()
        ollama_result = response.json()
        content = ollama_result["message"]["content"]
        extracted = json.loads(content)

        # Defensive defaults in case the model still drifts from the schema.
        extracted.setdefault("entities", [])
        extracted.setdefault("relationships", [])

        return {
            "status": "AI_SUGGESTED",
            "case_id": request.case_id,
            "document_name": request.document_name,
            "page": request.page,
            "evidence": evidence,
            "ontology_version": POLE_PLUS.get("ontology_version", "unknown"),
            "extraction": extracted,
        }

    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail=f"Cannot connect to Ollama at {OLLAMA_BASE_URL}. Make sure Ollama is running.",
        )
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail=f"{OLLAMA_MODEL} took too long to respond.")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail=f"{OLLAMA_MODEL} returned invalid JSON.")
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Ollama returned an error: {e.response.text}",
        )