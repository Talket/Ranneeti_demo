import os
from pathlib import Path

import requests

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")


def upload_document_to_backend(file_path: str | Path):
    file_path = Path(file_path)
    with file_path.open("rb") as handle:
        files = {"file": (file_path.name, handle, "application/octet-stream")}
        response = requests.post(f"{BACKEND_URL}/api/upload", files=files, timeout=60)
        response.raise_for_status()
        return response.json()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Raspberry Pi file uploader")
    parser.add_argument("file_path", help="Path to the document to upload")
    args = parser.parse_args()

    result = upload_document_to_backend(args.file_path)
    print(result)
