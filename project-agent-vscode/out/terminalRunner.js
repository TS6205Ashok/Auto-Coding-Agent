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
exports.findScriptUri = findScriptUri;
exports.confirmAndRunScript = confirmAndRunScript;
const vscode = __importStar(require("vscode"));
async function findScriptUri(workspaceFolder, kind) {
    const fileName = getScriptFileName(kind);
    const uri = vscode.Uri.joinPath(workspaceFolder.uri, fileName);
    try {
        await vscode.workspace.fs.stat(uri);
        return uri;
    }
    catch {
        return undefined;
    }
}
async function confirmAndRunScript(workspaceFolder, kind) {
    const scriptUri = await findScriptUri(workspaceFolder, kind);
    if (!scriptUri) {
        const label = kind === "setup" ? "setup" : "run";
        await vscode.window.showErrorMessage(`Could not find ${getScriptFileName(kind)} in the workspace root.`);
        return false;
    }
    const actionLabel = kind === "setup" ? "Run Setup" : "Run Project";
    const confirmation = await vscode.window.showInformationMessage(`Do you want to ${kind === "setup" ? "run setup" : "run the project"} now?`, { modal: true }, actionLabel, "Cancel");
    if (confirmation !== actionLabel) {
        return false;
    }
    const terminal = vscode.window.createTerminal({
        name: `Project Agent ${kind === "setup" ? "Setup" : "Run"}`,
        cwd: workspaceFolder.uri.fsPath,
    });
    terminal.show(true);
    terminal.sendText(buildTerminalCommand(kind));
    return true;
}
function getScriptFileName(kind) {
    if (process.platform === "win32") {
        return kind === "setup" ? "setup.bat" : "run.bat";
    }
    return kind === "setup" ? "setup.sh" : "run.sh";
}
function buildTerminalCommand(kind) {
    if (process.platform === "win32") {
        return kind === "setup" ? ".\\setup.bat" : ".\\run.bat";
    }
    return kind === "setup" ? 'bash "./setup.sh"' : 'bash "./run.sh"';
}
//# sourceMappingURL=terminalRunner.js.map