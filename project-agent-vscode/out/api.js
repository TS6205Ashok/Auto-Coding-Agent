"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.getApiUrl = getApiUrl;
exports.fetchProjectPreview = fetchProjectPreview;
const vscode = __importStar(require("vscode"));
function getApiUrl() {
    const config = vscode.workspace.getConfiguration("projectAgent");
    const rawUrl = config.get("apiUrl", "http://localhost:8000");
    return rawUrl.replace(/\/+$/, "");
}
async function fetchProjectPreview(apiUrl, idea) {
    const payload = {
        idea,
        generationMode: "fast",
    };
    let response;
    try {
        response = await fetch(`${apiUrl}/api/suggest`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify(payload),
        });
    }
    catch (error) {
        throw new Error("Project Agent API is not reachable. Check API URL in settings.");
    }
    let data;
    try {
        data = await response.json();
    }
    catch {
        throw new Error("Project Agent API returned an invalid response.");
    }
    if (!response.ok) {
        const detail = extractDetailMessage(data);
        throw new Error(detail || "Project Agent API is not reachable. Check API URL in settings.");
    }
    return normalizePreview(data);
}
function extractDetailMessage(value) {
    if (!value || typeof value !== "object") {
        return "";
    }
    const detail = value.detail;
    return typeof detail === "string" ? detail : "";
}
function normalizePreview(value) {
    if (!value || typeof value !== "object") {
        throw new Error("Project Agent API returned an invalid preview payload.");
    }
    const preview = value;
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
function normalizeStack(value) {
    const stack = (value && typeof value === "object" ? value : {});
    return {
        language: stringValue(stack.language, "Auto"),
        frontend: stringValue(stack.frontend, "Auto"),
        backend: stringValue(stack.backend, "Auto"),
        database: stringValue(stack.database, "Auto"),
        aiTools: stringValue(stack.aiTools, "Auto"),
        deployment: stringValue(stack.deployment, "Auto"),
    };
}
function normalizeFiles(value) {
    if (!Array.isArray(value)) {
        return [];
    }
    return value
        .filter((item) => !!item && typeof item === "object")
        .map((item) => ({
        path: stringValue(item.path),
        content: stringValue(item.content),
    }))
        .filter((item) => item.path.length > 0);
}
function normalizeRequiredInputs(value) {
    if (!Array.isArray(value)) {
        return [];
    }
    return value
        .filter((item) => !!item && typeof item === "object")
        .map((item) => ({
        name: stringValue(item.name),
        required: typeof item.required === "boolean" ? item.required : true,
        example: stringValue(item.example),
        whereToAdd: stringValue(item.whereToAdd, ".env"),
        purpose: stringValue(item.purpose),
    }))
        .filter((item) => item.name.length > 0);
}
function stringArray(value) {
    if (!Array.isArray(value)) {
        return [];
    }
    return value
        .map((item) => (typeof item === "string" ? item.trim() : ""))
        .filter((item) => item.length > 0);
}
function stringValue(value, fallback = "") {
    return typeof value === "string" ? value : fallback;
}
//# sourceMappingURL=api.js.map