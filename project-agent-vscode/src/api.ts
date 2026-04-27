import * as vscode from "vscode";

export interface StackSelection {
  language: string;
  frontend: string;
  backend: string;
  database: string;
  aiTools: string;
  deployment: string;
}

export interface PreviewFile {
  path: string;
  content: string;
}

export interface RequiredInput {
  name: string;
  required: boolean;
  example: string;
  whereToAdd: string;
  purpose: string;
}

export interface ProjectPreview {
  projectName: string;
  summary: string;
  selectedStack: StackSelection;
  files: PreviewFile[];
  installCommands: string[];
  runCommands: string[];
  requiredInputs: RequiredInput[];
}

interface SuggestRequest {
  idea: string;
  generationMode: "fast";
}

export function getApiUrl(): string {
  const config = vscode.workspace.getConfiguration("projectAgent");
  const rawUrl = config.get<string>("apiUrl", "http://localhost:8000");
  return rawUrl.replace(/\/+$/, "");
}

export async function fetchProjectPreview(
  apiUrl: string,
  idea: string,
): Promise<ProjectPreview> {
  const payload: SuggestRequest = {
    idea,
    generationMode: "fast",
  };

  let response: Response;
  try {
    response = await fetch(`${apiUrl}/api/suggest`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
  } catch (error) {
    throw new Error("Project Agent API is not reachable. Check API URL in settings.");
  }

  let data: unknown;
  try {
    data = await response.json();
  } catch {
    throw new Error("Project Agent API returned an invalid response.");
  }

  if (!response.ok) {
    const detail = extractDetailMessage(data);
    throw new Error(detail || "Project Agent API is not reachable. Check API URL in settings.");
  }

  return normalizePreview(data);
}

function extractDetailMessage(value: unknown): string {
  if (!value || typeof value !== "object") {
    return "";
  }

  const detail = (value as { detail?: unknown }).detail;
  return typeof detail === "string" ? detail : "";
}

function normalizePreview(value: unknown): ProjectPreview {
  if (!value || typeof value !== "object") {
    throw new Error("Project Agent API returned an invalid preview payload.");
  }

  const preview = value as Record<string, unknown>;
  return {
    projectName: stringValue(preview.projectName, "Generated Project"),
    summary: stringValue(preview.summary, "No summary available."),
    selectedStack: normalizeStack(preview.selectedStack),
    files: normalizeFiles(preview.files),
    installCommands: stringArray(preview.installCommands),
    runCommands: stringArray(preview.runCommands),
    requiredInputs: normalizeRequiredInputs(preview.requiredInputs),
  };
}

function normalizeStack(value: unknown): StackSelection {
  const stack = (value && typeof value === "object" ? value : {}) as Record<string, unknown>;
  return {
    language: stringValue(stack.language, "Auto"),
    frontend: stringValue(stack.frontend, "Auto"),
    backend: stringValue(stack.backend, "Auto"),
    database: stringValue(stack.database, "Auto"),
    aiTools: stringValue(stack.aiTools, "Auto"),
    deployment: stringValue(stack.deployment, "Auto"),
  };
}

function normalizeFiles(value: unknown): PreviewFile[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .filter((item): item is Record<string, unknown> => !!item && typeof item === "object")
    .map((item) => ({
      path: stringValue(item.path),
      content: stringValue(item.content),
    }))
    .filter((item) => item.path.length > 0);
}

function normalizeRequiredInputs(value: unknown): RequiredInput[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .filter((item): item is Record<string, unknown> => !!item && typeof item === "object")
    .map((item) => ({
      name: stringValue(item.name),
      required: typeof item.required === "boolean" ? item.required : true,
      example: stringValue(item.example),
      whereToAdd: stringValue(item.whereToAdd, ".env"),
      purpose: stringValue(item.purpose),
    }))
    .filter((item) => item.name.length > 0);
}

function stringArray(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }

  return value
    .map((item) => (typeof item === "string" ? item.trim() : ""))
    .filter((item) => item.length > 0);
}

function stringValue(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}
