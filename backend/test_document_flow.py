from pathlib import Path

import requests

API = 'http://127.0.0.1:8000'

sample_text = 'Suspect visited warehouse on 2026-09-08 and met with logistics coordinator. The subject had multiple cash transfers and unknown phone contact logs.'
file_path = Path(r'd:\downloads\demo_web\sample.txt')
file_path.write_text(sample_text, encoding='utf-8')

with file_path.open('rb') as f:
    upload = requests.post(
        f'{API}/api/upload',
        files={'file': ('sample.txt', f, 'text/plain')},
        timeout=30,
    )
    print('UPLOAD', upload.status_code)
    print(upload.json())
    payload = upload.json()
    doc_id = payload['id']

approve = requests.post(
    f'{API}/api/documents/{doc_id}/approve',
    json={'approved_text': sample_text},
    timeout=30,
)
print('APPROVE', approve.status_code)
print(approve.json())

process = requests.post(
    f'{API}/api/documents/{doc_id}/process',
    timeout=30,
)
print('PROCESS', process.status_code)
print(process.json())
