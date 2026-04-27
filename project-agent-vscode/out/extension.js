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
exports.activate = activate;
exports.deactivate = deactivate;
const vscode = __importStar(require("vscode"));
const api_1 = require("./api");
const fileWriter_1 = require("./fileWriter");
const terminalRunner_1 = require("./terminalRunner");
const LATEST_PREVIEW_KEY = "projectAgent.latestPreview";
const LATEST_WORKSPACE_URI_KEY = "projectAgent.latestWorkspaceUri";
function activate(context) {
    context.subscriptions.push(vscode.commands.registerCommand("projectAgent.generateProject", async () => {
        await handleGenerateProject(context);
    }), vscode.commands.registerCommand("projectAgent.installDependencies", async () => {
        await handleScriptCommand(context, "setup");
    }), vscode.commands.registerCommand("projectAgent.runProject", async () => {
        await handleScriptCommand(context, "run");
    }), vscode.commands.registerCommand("projectAgent.showRequiredInputs", async () => {
        await handleShowRequiredInputs(context);
    }), vscode.commands.registerCommand("projectAgent.openReadme", async () => {
        await handleOpenReadme(context);
    }));
}
function deactivate() { }
async function handleGenerateProject(context) {
    const workspaceFolder = await pickWorkspaceFolder();
    if (!workspaceFolder) {
        return;
    }
    const idea = await vscode.window.showInputBox({
        title: "Project Agent: Generate Project",
        prompt: "Enter the project description",
        placeHolder: "Example: Build a full-stack task tracker with React and FastAPI",
        ignoreFocusOut: true,
    });
    if (!idea || !idea.trim()) {
        return;
    }
    const preview = await withProgress("Generating project preview...", async () => {
        return (0, api_1.fetchProjectPreview)((0, api_1.getApiUrl)(), idea.trim());
    });
    if (!preview) {
        return;
    }
    const summaryMessage = buildPreviewSummary(preview);
    const confirm = await vscode.window.showInformationMessage(summaryMessage, { modal: true, detail: "Write the generated files into the selected workspace folder?" }, "Generate Files", "Cancel");
    if (confirm !== "Generate Files") {
        return;
    }
    const writeSummary = await (0, fileWriter_1.writePreviewFiles)(workspaceFolder, preview.files);
    if (writeSummary.cancelled) {
        await vscode.window.showInformationMessage("Project generation was cancelled. Files already written were kept.");
        return;
    }
    await context.globalState.update(LATEST_PREVIEW_KEY, preview);
    await context.globalState.update(LATEST_WORKSPACE_URI_KEY, workspaceFolder.uri.toString());
    const createdEnv = await (0, fileWriter_1.maybeCreateEnvFile)(workspaceFolder);
    await openWorkspaceFileIfPresent(workspaceFolder, "README.md");
    const detailParts = [
        `Written: ${writeSummary.written.length}`,
        `Skipped: ${writeSummary.skipped.length}`,
        `Required inputs: ${preview.requiredInputs.length}`,
    ];
    if (createdEnv) {
        detailParts.push(".env created from .env.example");
    }
    const action = await vscode.window.showInformationMessage("Project generated successfully.", { detail: detailParts.join(" | ") }, "Install Dependencies", "Run Project", "Open README", "Show Required Inputs");
    if (action === "Install Dependencies") {
        await vscode.commands.executeCommand("projectAgent.installDependencies");
    }
    else if (action === "Run Project") {
        await vscode.commands.executeCommand("projectAgent.runProject");
    }
    else if (action === "Open README") {
        await vscode.commands.executeCommand("projectAgent.openReadme");
    }
    else if (action === "Show Required Inputs") {
        await vscode.commands.executeCommand("projectAgent.showRequiredInputs");
    }
}
async function handleScriptCommand(context, kind) {
    const workspaceFolder = await resolvePreferredWorkspaceFolder(context);
    if (!workspaceFolder) {
        return;
    }
    const preview = getLatestPreview(context);
    const scriptUri = await (0, terminalRunner_1.findScriptUri)(workspaceFolder, kind);
    if (!preview && !scriptUri) {
        await vscode.window.showErrorMessage("Generate a project first.");
        return;
    }
    if (!scriptUri) {
        await vscode.window.showErrorMessage(`Could not find ${kind === "setup" ? "setup" : "run"} script in the workspace root.`);
        return;
    }
    await (0, terminalRunner_1.confirmAndRunScript)(workspaceFolder, kind);
}
async function handleShowRequiredInputs(context) {
    const workspaceFolder = await resolvePreferredWorkspaceFolder(context);
    if (!workspaceFolder) {
        return;
    }
    const requiredInputsUri = vscode.Uri.joinPath(workspaceFolder.uri, "REQUIRED_INPUTS.md");
    if (await fileExists(requiredInputsUri)) {
        await openDocument(requiredInputsUri);
        return;
    }
    const preview = getLatestPreview(context);
    if (!preview) {
        await vscode.window.showErrorMessage("Generate a project first.");
        return;
    }
    const markdown = buildRequiredInputsDocument(preview.requiredInputs);
    const document = await vscode.workspace.openTextDocument({
        content: markdown,
        language: "markdown",
    });
    await vscode.window.showTextDocument(document, { preview: false });
}
async function handleOpenReadme(context) {
    const workspaceFolder = await resolvePreferredWorkspaceFolder(context);
    if (!workspaceFolder) {
        return;
    }
    const opened = await openWorkspaceFileIfPresent(workspaceFolder, "README.md");
    if (!opened) {
        await vscode.window.showErrorMessage("README.md was not found in the selected workspace.");
    }
}
async function pickWorkspaceFolder() {
    const folders = vscode.workspace.workspaceFolders;
    if (!folders || folders.length === 0) {
        await vscode.window.showErrorMessage("Open a folder first.");
        return undefined;
    }
    if (folders.length === 1) {
        return folders[0];
    }
    const picked = await vscode.window.showQuickPick(folders.map((folder) => ({
        label: folder.name,
        description: folder.uri.fsPath,
        folder,
    })), {
        title: "Choose the workspace folder for Project Agent output",
        ignoreFocusOut: true,
    });
    return picked?.folder;
}
async function resolvePreferredWorkspaceFolder(context) {
    const folders = vscode.workspace.workspaceFolders;
    if (!folders || folders.length === 0) {
        await vscode.window.showErrorMessage("Open a folder first.");
        return undefined;
    }
    const storedUri = context.globalState.get(LATEST_WORKSPACE_URI_KEY);
    if (storedUri) {
        const matchingFolder = folders.find((folder) => folder.uri.toString() === storedUri);
        if (matchingFolder) {
            return matchingFolder;
        }
    }
    return pickWorkspaceFolder();
}
function getLatestPreview(context) {
    return context.globalState.get(LATEST_PREVIEW_KEY);
}
function buildPreviewSummary(preview) {
    const stack = preview.selectedStack;
    const stackSummary = [
        `Language: ${stack.language}`,
        `Frontend: ${stack.frontend}`,
        `Backend: ${stack.backend}`,
        `Database: ${stack.database}`,
    ].join(" | ");
    return [
        `Project: ${preview.projectName}`,
        preview.summary,
        stackSummary,
        `Files: ${preview.files.length}`,
        `Required inputs: ${preview.requiredInputs.length}`,
    ].join("\n\n");
}
function buildRequiredInputsDocument(requiredInputs) {
    if (requiredInputs.length === 0) {
        return [
            "# Required Inputs",
            "",
            "No required inputs were detected in the latest preview.",
        ].join("\n");
    }
    const rows = requiredInputs.map((item) => `| ${item.name} | ${item.required ? "Required" : "Optional"} | ${escapeCell(item.example)} | ${escapeCell(item.whereToAdd)} | ${escapeCell(item.purpose)} |`);
    return [
        "# Required Inputs",
        "",
        "Fill these values in `.env` before running the project.",
        "",
        "| Name | Required | Example | Where To Add | Purpose |",
        "|---|---|---|---|---|",
        ...rows,
    ].join("\n");
}
function escapeCell(value) {
    return value.replace(/\|/g, "\\|");
}
async function openWorkspaceFileIfPresent(workspaceFolder, relativePath) {
    const fileUri = vscode.Uri.joinPath(workspaceFolder.uri, relativePath);
    if (!(await fileExists(fileUri))) {
        return false;
    }
    await openDocument(fileUri);
    return true;
}
async function openDocument(uri) {
    const document = await vscode.workspace.openTextDocument(uri);
    await vscode.window.showTextDocument(document, { preview: false });
}
async function fileExists(uri) {
    try {
        await vscode.workspace.fs.stat(uri);
        return true;
    }
    catch {
        return false;
    }
}
async function withProgress(title, task) {
    try {
        return await vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title,
        }, task);
    }
    catch (error) {
        const message = error instanceof Error
            ? error.message
            : "Project Agent API is not reachable. Check API URL in settings.";
        await vscode.window.showErrorMessage(message);
        return undefined;
    }
}
//# sourceMappingURL=extension.js.map