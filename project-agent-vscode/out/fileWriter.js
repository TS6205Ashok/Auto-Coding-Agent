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
exports.writePreviewFiles = writePreviewFiles;
exports.maybeCreateEnvFile = maybeCreateEnvFile;
const vscode = __importStar(require("vscode"));
const path = __importStar(require("path"));
const pathSafety_1 = require("./pathSafety");
const encoder = new TextEncoder();
async function writePreviewFiles(workspaceFolder, files) {
    const summary = {
        written: [],
        skipped: [],
        cancelled: false,
    };
    for (const file of files) {
        const safeRelativePath = (0, pathSafety_1.normalizeRelativePath)(file.path);
        const targetUri = (0, pathSafety_1.resolveSafeWorkspacePath)(workspaceFolder, safeRelativePath);
        const exists = await pathExists(targetUri);
        if (exists) {
            const choice = await vscode.window.showWarningMessage(`${safeRelativePath} already exists.`, { modal: true }, "Overwrite", "Skip", "Cancel");
            if (choice === "Cancel" || !choice) {
                summary.cancelled = true;
                return summary;
            }
            if (choice === "Skip") {
                summary.skipped.push(safeRelativePath);
                continue;
            }
        }
        await vscode.workspace.fs.createDirectory(vscode.Uri.file(path.dirname(targetUri.fsPath)));
        await vscode.workspace.fs.writeFile(targetUri, encoder.encode(file.content));
        summary.written.push(safeRelativePath);
    }
    return summary;
}
async function maybeCreateEnvFile(workspaceFolder) {
    const envExampleUri = (0, pathSafety_1.resolveSafeWorkspacePath)(workspaceFolder, ".env.example");
    const envUri = (0, pathSafety_1.resolveSafeWorkspacePath)(workspaceFolder, ".env");
    if (!(await pathExists(envExampleUri)) || (await pathExists(envUri))) {
        return false;
    }
    const choice = await vscode.window.showInformationMessage("Create .env from .env.example now?", "Create .env", "Skip");
    if (choice !== "Create .env") {
        return false;
    }
    const bytes = await vscode.workspace.fs.readFile(envExampleUri);
    await vscode.workspace.fs.writeFile(envUri, bytes);
    return true;
}
async function pathExists(uri) {
    try {
        await vscode.workspace.fs.stat(uri);
        return true;
    }
    catch {
        return false;
    }
}
//# sourceMappingURL=fileWriter.js.map