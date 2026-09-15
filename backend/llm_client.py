import json
import os

import requests


def create_stub_json(document_text: str) -> dict:
    cleaned = (document_text or "").strip()
    summary = cleaned[:220].replace("\n", " ") if cleaned else "No content extracted"

    return {
        "document_id": "pending",
        "summary": summary,
        "risk_level": "medium",
        "confidence": 0.81,
        "source": "offline-prototype-stub",
        "extraction_status": "completed",
        "entities": [
            {"type": "person", "name": "Unknown subject", "confidence": 0.78},
            {"type": "organization", "name": "Unspecified organization", "confidence": 0.72},
            {"type": "location", "name": "Unspecified location", "confidence": 0.68},
            {"type": "date", "name": "2026-09-08", "confidence": 0.75},
        ],
        "relationships": [
            {"source": "Unknown subject", "target": "Unspecified location", "type": "visited", "confidence": 0.74},
            {"source": "Unknown subject", "target": "Unspecified organization", "type": "met_with", "confidence": 0.71},
        ],
    }


def call_reasoning_llm(document_text: str) -> dict:
    provider = os.getenv("REASONING_LLM_PROVIDER", "api").lower()
    timeout_seconds = float(os.getenv("REASONING_LLM_TIMEOUT_SECONDS", "180"))

    if provider == "ollama":
        return call_ollama(document_text, timeout_seconds)

    llm_url = os.getenv("REASONING_LLM_URL", "http://127.0.0.1:7000/ai/extract")

    try:
        response = requests.post(
            llm_url,
            json={"text": document_text},
            headers={"Accept": "application/json"},
            timeout=timeout_seconds,
        )
    except requests.RequestException as error:
        raise RuntimeError(f"Reasoning LLM is unreachable at {llm_url}: {error}") from error

    if not response.ok:
        detail = response.text.strip()[:500] or "empty response"
        if response.status_code == 500 and "invalid json" in detail.lower():
            detail = (
                f"{detail} The remote wrapper must parse Ollama's response or thinking field "
                "with think disabled and format=json."
            )
        raise RuntimeError(f"Reasoning LLM returned HTTP {response.status_code}: {detail}")

    try:
        payload = response.json()
    except ValueError as error:
        raise RuntimeError("Reasoning LLM returned a non-JSON response") from error

    if not isinstance(payload, dict):
        raise RuntimeError("Reasoning LLM response must be a JSON object")

    return payload


def call_ollama(document_text: str, timeout_seconds: float) -> dict:
    ollama_url = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
    model_name = os.getenv("REASONING_LLM_MODEL", "qwen3.5:9b")
    prompt = f"""
Extract investigation data from the approved source text below.
Return only valid JSON with these keys:
source_records, acquisition_events, evidence_items, assertions, candidate_links, inferences, analytical_results.
Preserve uncertainty, do not invent facts, and retain raw source wording when available.

Source text:
{document_text}
"""

    try:
        response = requests.post(
            f"{ollama_url}/api/generate",
            json={
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "think": False,
            },
            headers={"Accept": "application/json"},
            timeout=timeout_seconds,
        )
    except requests.RequestException as error:
        raise RuntimeError(f"Ollama is unreachable at {ollama_url}: {error}") from error

    if not response.ok:
        detail = response.text.strip()[:500] or "empty response"
        raise RuntimeError(f"Ollama returned HTTP {response.status_code}: {detail}")

    try:
        payload = response.json()
        generated_text = payload.get("response") or payload.get("thinking")
        if not generated_text:
            raise ValueError("Ollama returned neither response nor thinking content")
        result = json.loads(generated_text)
    except (ValueError, KeyError, TypeError) as error:
        raise RuntimeError("Ollama returned a response that was not valid JSON") from error

    if not isinstance(result, dict):
        raise RuntimeError("Ollama JSON output must be an object")

    result["model_name"] = model_name
    result["source"] = "ollama"
    return result
