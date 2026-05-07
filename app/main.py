from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from .services.agent_controller import agent_controller
from .services.file_service import ensure_within_directory
from .services.ide_service import (
    close_ide,
    create_workspace_zip,
    ide_status,
    list_workspace_files,
    read_workspace_file,
    delete_workspace_file,
    rename_workspace_file,
    start_or_reuse_ide,
    validate_project_id,
    workspace_exists,
    write_workspace_file,
)


load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent
APP_DIR = ROOT_DIR / "app"
GENERATED_DIR = ROOT_DIR / "generated"
GENERATED_PROJECTS_DIR = ROOT_DIR / "generated_projects"
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
    source: str = ""
    runtimeTools: list[str] = Field(default_factory=list)
    packageManager: str = ""
    lastModifiedField: str = ""
    lastModifiedAt: float | None = None
    isUserConfirmedStack: bool = False
    isDirty: bool = False


class EnvVariablePayload(BaseModel):
    name: str
    value: str = ""
    description: str = ""


class RequiredInputPayload(BaseModel):
    name: str
    required: bool = True
    example: str = ""
    whereToAdd: str = ".env"
    whereToEnter: str = ".env"
    purpose: str = ""


class RequestedFilePayload(BaseModel):
    path: str
    purpose: str = ""
    required: bool = True


class FileRemovalPayload(BaseModel):
    path: str
    reason: str = ""


class SuggestRequest(BaseModel):
    idea: str = Field(..., min_length=1)
    selectedStack: StackSelectionPayload | None = None
    stackSelectionSource: str = ""
    isUserConfirmedStack: bool = False
    generationMode: str = "fast"
    generationQuality: str = "complete"
    finalRequirements: str = ""
    customFiles: list[RequestedFilePayload] = Field(default_factory=list)
    requestedFiles: list[RequestedFilePayload] = Field(default_factory=list)
    filesToRemove: list[FileRemovalPayload] = Field(default_factory=list)
    chatPendingCorrections: list[dict[str, Any]] = Field(default_factory=list)


class ChatMessagePayload(BaseModel):
    role: str = "user"
    content: str = ""


class AgentChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    conversation: list[ChatMessagePayload] = Field(default_factory=list)
    currentIdea: str = ""
    currentPreview: dict[str, Any] = Field(default_factory=dict)
    selectedStack: StackSelectionPayload = Field(default_factory=StackSelectionPayload)
    agentState: str = "idle"
    pendingCorrections: list[dict[str, Any]] = Field(default_factory=list)
    llmMode: str = "auto"


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
    projectType: str = ""
    templateFamily: str = ""
    recommendedIde: str = ""
    alternativeIde: str = ""
    runtimeTools: list[str] = Field(default_factory=list)
    packageManager: str = ""
    migrationSummary: dict[str, Any] = Field(default_factory=dict)
    stackAnalysis: dict[str, Any] = Field(default_factory=dict)
    detectedUserChoices: list[str] = Field(default_factory=list)
    selectedStack: StackSelectionPayload = Field(default_factory=StackSelectionPayload)
    generatedVersion: str = ""
    mainFile: str = ""
    primaryRunCommand: str = ""
    mainRunTarget: str = ""
    localUrl: str = ""
    runInstructions: list[str] = Field(default_factory=list)
    setupInstructions: list[str] = Field(default_factory=list)
    stackSelectionSource: str = ""
    isUserConfirmedStack: bool = False
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
    customFiles: list[RequestedFilePayload] = Field(default_factory=list)
    requestedFiles: list[RequestedFilePayload] = Field(default_factory=list)
    filesToRemove: list[FileRemovalPayload] = Field(default_factory=list)
    chatPendingCorrections: list[dict[str, Any]] = Field(default_factory=list)
    projectContract: dict[str, Any] = Field(default_factory=dict)
    validationStatus: dict[str, Any] = Field(default_factory=dict)
    generationQuality: str = "complete"


class ZipRequest(BaseModel):
    preview: PreviewPayload


class GenerateProjectRequest(BaseModel):
    idea: str = Field(..., min_length=1)
    generationMode: str = "fast"


class IdeFilePayload(BaseModel):
    path: str
    content: str = ""


class IdeRenamePayload(BaseModel):
    oldPath: str
    newPath: str


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "request": request,
            "title": "Project Agent",
            "question": "",
            "answer": "",
            "username": "",
            "messages": [],
        },
    )


@app.post("/api/suggest")
async def suggest_project(payload: SuggestRequest) -> JSONResponse:
    idea = payload.idea.strip()
    if not idea:
        raise HTTPException(status_code=400, detail="Please enter a project idea.")

    try:
        preview = await agent_controller.build_preview(
            idea,
            generation_mode=payload.generationMode,
            generation_quality=payload.generationQuality or "complete",
            selected_stack=payload.selectedStack.model_dump() if payload.selectedStack else None,
            stack_selection_source=payload.stackSelectionSource,
            is_user_confirmed_stack=payload.isUserConfirmedStack,
            final_requirements=payload.finalRequirements,
            custom_files=[
                item.model_dump()
                for item in [*payload.customFiles, *payload.requestedFiles]
            ],
            files_to_remove=[item.path for item in payload.filesToRemove],
            chat_pending_corrections=payload.chatPendingCorrections,
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


@app.post("/api/agent/chat")
async def chat_agent(payload: AgentChatRequest) -> JSONResponse:
    message = payload.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Please enter a chat message.")

    result = await agent_controller.chat(
        message=message,
        conversation=[item.model_dump() for item in payload.conversation],
        current_idea=payload.currentIdea,
        current_preview=payload.currentPreview,
        selected_stack=payload.selectedStack.model_dump(),
        agent_state=payload.agentState,
        pending_corrections=payload.pendingCorrections,
        llm_mode=payload.llmMode,
    )
    return JSONResponse(result)


@app.post("/api/zip")
async def build_zip(payload: ZipRequest) -> JSONResponse:
    try:
        result = agent_controller.package_zip(payload.preview.model_dump(), GENERATED_DIR)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Could not create ZIP: {exc}") from exc

    return JSONResponse(result)


@app.post("/generate-project", response_class=HTMLResponse)
async def generate_project(request: Request) -> HTMLResponse:
    if request.headers.get("content-type", "").startswith("application/json"):
        body = await request.json()
        idea = str(body.get("idea") or "").strip()
        generation_mode = str(body.get("generationMode") or "fast")
    else:
        form = await request.form()
        idea = str(form.get("idea") or "").strip()
        generation_mode = str(form.get("generationMode") or "fast")
    if not idea:
        raise HTTPException(status_code=400, detail="Please enter a project idea.")

    preview = await agent_controller.build_preview(idea, generation_mode=generation_mode)
    package_result = agent_controller.package_zip(preview, GENERATED_DIR)
    project_id = validate_project_id(package_result["projectId"])
    return templates.TemplateResponse(
        request=request,
        name="result.html",
        context={
            "request": request,
            "title": "Project Generated",
            "project_id": project_id,
            "project_name": preview.get("projectName") or "Generated Project",
            "ide_url": f"/open-ide/{project_id}",
            "download_url": f"/download/{project_id}",
        },
    )


@app.get("/result/{project_id}", response_class=HTMLResponse)
async def project_result(request: Request, project_id: str) -> HTMLResponse:
    project_id = validate_project_id(project_id)
    if not workspace_exists(project_id, GENERATED_PROJECTS_DIR):
        raise HTTPException(status_code=404, detail="Generated project not found.")
    return templates.TemplateResponse(
        request=request,
        name="result.html",
        context={
            "request": request,
            "title": "Project Generated",
            "project_id": project_id,
            "project_name": f"Project {project_id}",
            "ide_url": f"/open-ide/{project_id}",
            "download_url": f"/download/{project_id}",
        },
    )


@app.get("/open-ide/{project_id}")
async def open_ide(project_id: str) -> RedirectResponse:
    try:
        instance = start_or_reuse_ide(project_id, GENERATED_PROJECTS_DIR)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return RedirectResponse(instance.url)


@app.post("/close-ide/{project_id}")
async def close_project_ide(project_id: str) -> JSONResponse:
    try:
        stopped = close_ide(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return JSONResponse({"projectId": project_id, "stopped": stopped})


@app.get("/api/ide-status/{project_id}")
async def project_ide_status(project_id: str) -> JSONResponse:
    try:
        status = ide_status(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return JSONResponse(status)


@app.get("/api/files/{project_id}")
async def api_workspace_files(project_id: str) -> JSONResponse:
    try:
        return JSONResponse({"files": list_workspace_files(project_id, GENERATED_PROJECTS_DIR)})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/file/{project_id}")
async def api_workspace_file(project_id: str, path: str) -> JSONResponse:
    try:
        return JSONResponse({"path": path, "content": read_workspace_file(project_id, GENERATED_PROJECTS_DIR, path)})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/file/{project_id}/save")
async def api_workspace_file_save(project_id: str, payload: IdeFilePayload) -> JSONResponse:
    try:
        write_workspace_file(project_id, GENERATED_PROJECTS_DIR, payload.path, payload.content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return JSONResponse({"saved": True, "path": payload.path})


@app.post("/api/file/{project_id}/create")
async def api_workspace_file_create(project_id: str, payload: IdeFilePayload) -> JSONResponse:
    return await api_workspace_file_save(project_id, payload)


@app.post("/api/file/{project_id}/rename")
async def api_workspace_file_rename(project_id: str, payload: IdeRenamePayload) -> JSONResponse:
    try:
        rename_workspace_file(project_id, GENERATED_PROJECTS_DIR, payload.oldPath, payload.newPath)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return JSONResponse({"renamed": True, "oldPath": payload.oldPath, "newPath": payload.newPath})


@app.post("/api/file/{project_id}/delete")
async def api_workspace_file_delete(project_id: str, payload: IdeFilePayload) -> JSONResponse:
    try:
        delete_workspace_file(project_id, GENERATED_PROJECTS_DIR, payload.path)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return JSONResponse({"deleted": True, "path": payload.path})


@app.get("/download/{project_id}")
async def download_project_workspace(project_id: str) -> FileResponse:
    try:
        zip_info = create_workspace_zip(project_id, GENERATED_PROJECTS_DIR, GENERATED_DIR)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    download_path = GENERATED_DIR / zip_info["filename"]
    return FileResponse(download_path, media_type="application/zip", filename=download_path.name)


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
