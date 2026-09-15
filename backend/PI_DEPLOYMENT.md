# Raspberry Pi deployment

The Raspberry Pi runs the FastAPI service and serves the document page. The investigator's browser connects to the Pi over the local network.

## Network flow

```text
Browser -> http://<PI_IP>:8000/ -> FastAPI on Raspberry Pi
                                      |
                                      +-- uploads/<file>
                                      +-- OCR/text extraction
                                      +-- PostgreSQL
                                      +-- offline reasoning LLM
```

## Install

Copy the project to the Pi, then run from the project directory:

```bash
chmod +x backend/install_pi.sh
./backend/install_pi.sh
```

The service listens on all network interfaces at port `8000`.

Find the Pi address:

```bash
hostname -I
```

Open the page from an investigator computer:

```text
http://<PI_IP>:8000/
```

The page uses its own origin as the API address, so upload requests go to the Pi automatically.

## Environment

Edit `/opt/demo_web/backend/.env`:

```env
DATABASE_URL=postgresql://postgres:<password>@<postgres-host>:5432/investigation_db
UPLOAD_DIR=/opt/demo_web/backend/uploads
REASONING_LLM_PROVIDER=api
OLLAMA_URL=http://<friend-computer-ip>:11434
REASONING_LLM_URL=http://<friend-computer-ip>:7000/ai/extract
REASONING_LLM_MODEL=qwen3.5:9b
REASONING_LLM_TIMEOUT_SECONDS=180
CORS_ORIGINS=http://<pi-ip>:8000
```

If PostgreSQL is running on the Pi, use `postgres` or `localhost` as the database host. If it is on another machine, that machine must allow PostgreSQL connections from the Pi.

The website uses the friend's FastAPI wrapper. Set `REASONING_LLM_URL` to its LAN address, for example `http://192.168.1.25:7000/ai/extract`. The wrapper receives the approved document text as `{ "text": "..." }`, calls Ollama locally, and returns the ontology JSON. From the Pi, verify the connection with:

```bash
curl http://192.168.1.25:7000/health
```

The friend must allow inbound TCP port `7000` through the operating-system firewall. `127.0.0.1` or `localhost` on the Pi refers to the Pi itself, not the friend's computer. The selected model must be installed on Ollama, for example:

```bash
ollama pull qwen3.5:9b
```

The direct Ollama option remains available by setting `REASONING_LLM_PROVIDER=ollama` and using port `11434`, but the current deployment uses the wrapper on port `7000`.

### Wrapper returns `Qwen returned invalid JSON`

This error is produced by the friend's `/ai/extract` service, not by the website. Its Ollama call should use JSON mode and disable thinking:

```python
ollama_response = requests.post(
        "http://127.0.0.1:11434/api/generate",
        json={
                "model": "qwen3.5:9b",
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "think": False,
        },
)
payload = ollama_response.json()
generated = payload.get("response") or payload.get("thinking")
result = json.loads(generated)
```

The wrapper should return the parsed `result` from `/ai/extract`. After changing it, verify from the Pi:

```bash
curl -X POST http://<friend-computer-ip>:7000/ai/extract \
    -H 'Content-Type: application/json' \
    -d '{"text":"test"}'
```

## Raspberry Pi upload client

The optional worker client can upload a local Pi file to the API:

```bash
BACKEND_URL=http://127.0.0.1:8000 python3 backend/pi_client.py /path/to/document.pdf
```

For the normal browser workflow, the browser uploads directly to the FastAPI service running on the Pi; `pi_client.py` is only needed for files collected by a Pi sensor, watched folder, or scanner.

## Check the service

```bash
curl http://127.0.0.1:8000/health
sudo journalctl -u demo-web.service -f
```
