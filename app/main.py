from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from .services.agent_controller import agent_controller
from .services.file_service import ensure_within_directory
from .services.zip_service import create_project_zip


load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent
APP_DIR = ROOT_DIR / "app"
GENERATED_DIR = ROOT_DIR / "generated"
DEFAULT_PORT = 7860

app = FastAPI(title="Project Agent")
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))


class StackSelectionPayload(BaseModel):
    language: str = "Auto"
    frontend: str = "Auto"
    backend: str = "Auto"
    database: str = "Auto"
    aiTools: str = "Auto"
    deployment: str = "Auto"


class EnvVariablePayload(BaseModel):
    name: str
    value: str = ""
    description: str = ""


class RequiredInputPayload(BaseModel):
    name: str
    required: bool = True
    example: str = ""
    whereToAdd: str = ".env"
    purpose: str = ""


class SuggestRequest(BaseModel):
    idea: str = Field(..., min_length=1)
    selectedStack: StackSelectionPayload | None = None
    generationMode: str = "fast"
    finalRequirements: str = ""


class AgentAnalyzeRequest(BaseModel):
    idea: str = Field(..., min_length=1)


class AgentQuestionPayload(BaseModel):
    id: str
    question: str
    type: str
    options: list[str] = Field(default_factory=list)
    default: str = ""
    reason: str = ""


class AgentAnalyzeResponse(BaseModel):
    understanding: str
    assumptions: list[str] = Field(default_factory=list)
    suggestedStack: StackSelectionPayload = Field(default_factory=StackSelectionPayload)
    stackReasons: list[str] = Field(default_factory=list)
    questions: list[AgentQuestionPayload] = Field(default_factory=list)
    detectedProjectType: str = "full-stack"
    confidence: int = 0


class AgentFinalizeRequest(BaseModel):
    idea: str = Field(..., min_length=1)
    answers: dict[str, Any] = Field(default_factory=dict)
    suggestedStack: StackSelectionPayload = Field(default_factory=StackSelectionPayload)


class AgentFinalizeResponse(BaseModel):
    finalRequirements: str = ""
    selectedStack: StackSelectionPayload = Field(default_factory=StackSelectionPayload)
    assumptions: list[str] = Field(default_factory=list)


class ModulePayload(BaseModel):
    name: str
    purpose: str = ""
    keyFiles: list[str] = Field(default_factory=list)


class FilePayload(BaseModel):
    path: str
    content: str = ""


class PreviewPayload(BaseModel):
    projectName: str
    detectedUserChoices: list[str] = Field(default_factory=list)
    selectedStack: StackSelectionPayload = Field(default_factory=StackSelectionPayload)
    chosenStack: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    summary: str = ""
    problemStatement: str = ""
    architecture: list[str] = Field(default_factory=list)
    modules: list[ModulePayload] = Field(default_factory=list)
    packageRequirements: list[str] = Field(default_factory=list)
    installCommands: list[str] = Field(default_factory=list)
    runCommands: list[str] = Field(default_factory=list)
    requiredInputs: list[RequiredInputPayload] = Field(default_factory=list)
    envVariables: list[EnvVariablePayload] = Field(default_factory=list)
    fileTree: str = ""
    files: list[FilePayload] = Field(default_factory=list)


class ZipRequest(BaseModel):
    preview: PreviewPayload


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request},
    )


@app.post("/api/suggest")
async def suggest_project(payload: SuggestRequest) -> JSONResponse:
    idea = payload.idea.strip()
    if not idea:
        raise HTTPException(status_code=400, detail="Please enter a project idea.")

    try:
        preview = await agent_controller.generate_files(
            idea,
            payload.selectedStack.model_dump() if payload.selectedStack else None,
            payload.generationMode,
            payload.finalRequirements,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return JSONResponse(preview)


@app.post("/api/agent/analyze")
async def analyze_agent(payload: AgentAnalyzeRequest) -> JSONResponse:
    idea = payload.idea.strip()
    if not idea:
        raise HTTPException(status_code=400, detail="Please enter a project idea.")

    return JSONResponse(agent_controller.analyze_idea(idea))


@app.post("/api/agent/finalize")
async def finalize_agent(payload: AgentFinalizeRequest) -> JSONResponse:
    idea = payload.idea.strip()
    if not idea:
        raise HTTPException(status_code=400, detail="Please enter a project idea.")

    finalized = agent_controller.finalize_requirements(
        idea,
        payload.answers,
        payload.suggestedStack.model_dump(),
    )
    return JSONResponse(finalized)


@app.post("/api/zip")
async def build_zip(payload: ZipRequest) -> JSONResponse:
    try:
        normalized_preview = agent_controller.validate_project(payload.preview.model_dump())
        result = create_project_zip(normalized_preview, GENERATED_DIR)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Could not create ZIP: {exc}") from exc

    return JSONResponse(result)


@app.get("/downloads/{filename}")
async def download_zip(filename: str) -> FileResponse:
    download_path = GENERATED_DIR / filename
    if download_path.name != filename:
        raise HTTPException(status_code=404, detail="File not found.")
    if download_path.suffix != ".zip":
        raise HTTPException(status_code=404, detail="File not found.")
    if not download_path.exists():
        raise HTTPException(status_code=404, detail="File not found.")
    if not ensure_within_directory(GENERATED_DIR, download_path):
        raise HTTPException(status_code=404, detail="File not found.")

    return FileResponse(
        download_path,
        media_type="application/zip",
        filename=download_path.name,
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    if exc.status_code == 404:
        return JSONResponse(status_code=404, content={"detail": exc.detail})
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": f"Unexpected server error: {exc}"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", str(DEFAULT_PORT))),
    )
