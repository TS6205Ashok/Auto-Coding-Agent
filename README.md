---
title: Project Agent
emoji: 🚀
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
---

# Project Agent

Project Agent is a FastAPI web app that turns a rough project idea into a **100% runnable starter project** preview, then creates a ZIP only after the user confirms it. The deployed app is designed to stay usable for free on Hugging Face Spaces even when no Ollama service is available.

## Features

- Suggest -> Preview -> Regenerate -> Confirm ZIP workflow
- Fast/Deep generation modes with Fast Mode as the default
- Template-first project generation with required docs, scripts, and dependency files
- Safe fallback previews when AI is unavailable, slow, or invalid
- ZIP output that contains generated source, config, scripts, and docs only
- Safe path validation and generated output constrained to `generated/`
- Docker-ready deployment for Hugging Face Spaces

## Requirements

The app depends on:

- `fastapi`
- `uvicorn[standard]`
- `jinja2`
- `python-dotenv`
- `httpx`

## Run Locally

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the app with the default Hugging Face-friendly port:

```bash
python -m app.main
```

Or run Uvicorn directly:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 7860
```

To use a different port:

```bash
PORT=8000 python -m app.main
```

Then open `http://127.0.0.1:7860` or the port you set.

## Environment Variables

Optional app/runtime variables:

```env
PORT=7860
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder
```

Notes:

- `PORT` defaults to `7860`, which matches Hugging Face Spaces.
- If `OLLAMA_BASE_URL` is missing or unreachable, Fast Mode still works by returning a complete template-based preview.
- Deep Mode remains optional. If AI is unavailable, the app still returns a valid preview and notes that Deep AI enrichment was skipped.

## Hugging Face Spaces Deployment

Deploy this project as a **Docker Space**.

### 1. Create the Space

- Create a new Space on Hugging Face
- Choose **Docker** as the Space SDK
- Push this repository to the Space

### 2. Container Runtime

The included `Dockerfile` starts the app with:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 7860
```

The container also supports `PORT` overrides through the environment and defaults to `7860`.

### 3. Free Deployment Behavior

For the free public version, you do **not** need cloud Ollama.

- Fast Mode works without Ollama by using template fallback
- Deep Mode attempts AI enrichment only if Ollama is reachable
- If Ollama is unavailable, the app still returns a complete preview instead of failing
- ZIP downloads still work from the generated fallback preview

### 4. Optional AI Configuration

If you later want AI-backed planning on a deployment that can reach Ollama, set:

```env
OLLAMA_BASE_URL=https://your-ollama-endpoint
OLLAMA_MODEL=qwen2.5-coder
```

If those values are not set, the app remains usable in fallback mode.

## ZIP Output Behavior

Generated ZIPs:

- do not include installed libraries
- do not include `.venv`
- do not include `node_modules`
- do include generated source, config, dependency manifests, setup scripts, run scripts, and generated docs

This keeps ZIP creation compatible with Hugging Face temporary storage.

## API Endpoints

- `GET /` renders the frontend
- `POST /api/suggest` returns a normalized project preview
- `POST /api/zip` writes the confirmed project into `generated/` and returns a download URL
- `GET /downloads/{filename}` downloads the generated ZIP

## Deployment Notes

- Generated project artifacts are written only inside `generated/`
- The app assumes ephemeral writable storage is acceptable for preview ZIP downloads
- No dependency installation happens during preview or ZIP creation
