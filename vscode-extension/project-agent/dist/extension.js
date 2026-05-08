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
const http = __importStar(require("http"));
const https = __importStar(require("https"));
const vscode = __importStar(require("vscode"));
let provider;
function activate(context) {
    provider = new ProjectAgentViewProvider(context.extensionUri);
    context.subscriptions.push(vscode.window.registerWebviewViewProvider("projectAgent.chatView", provider), vscode.commands.registerCommand("projectAgent.openChat", async () => {
        await vscode.commands.executeCommand("projectAgent.chatView.focus");
    }), vscode.commands.registerCommand("projectAgent.applyFix", async () => {
        await provider?.applyLastFix();
    }));
    setTimeout(() => {
        void vscode.commands.executeCommand("projectAgent.chatView.focus");
    }, 1200);
}
function deactivate() { }
class ProjectAgentViewProvider {
    extensionUri;
    view;
    history = [];
    lastCodeBlock = "";
    busy = false;
    constructor(extensionUri) {
        this.extensionUri = extensionUri;
    }
    resolveWebviewView(webviewView) {
        this.view = webviewView;
        webviewView.webview.options = { enableScripts: true };
        webviewView.webview.html = this.html(webviewView.webview);
        webviewView.webview.onDidReceiveMessage(async (message) => {
            try {
                if (message.type === "send") {
                    await this.ask(String(message.text || ""));
                }
                if (message.type === "applyFix") {
                    await this.applyLastFix();
                }
                if (message.type === "clear") {
                    this.history = [];
                    this.lastCodeBlock = "";
                    this.postState();
                }
                if (message.type === "explain") {
                    await this.ask("Explain this project and the current active file.");
                }
                if (message.type === "insertNewFile") {
                    await this.insertAsNewFile();
                }
            }
            catch (error) {
                this.addError(`Extension message handler failed: ${formatError(error)}`);
            }
        });
        this.postState();
    }
    async ask(userText) {
        if (!userText.trim() || this.busy) {
            return;
        }
        this.history.push({ role: "user", text: userText });
        this.busy = true;
        this.postState();
        try {
            const context = await collectWorkspaceContext(userText);
            const answer = await callOllamaWithFallback(context.prompt);
            this.lastCodeBlock = extractFirstCodeBlock(answer);
            this.history.push({ role: "agent", text: answer });
        }
        catch (error) {
            this.addError(formatError(error), false);
        }
        finally {
            this.busy = false;
            this.postState();
        }
    }
    async applyLastFix() {
        if (!this.lastCodeBlock) {
            vscode.window.showInformationMessage("Project Agent did not find a code block to apply.");
            return;
        }
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showErrorMessage("Open a file before applying a fix.");
            return;
        }
        const selection = editor.selection;
        if (!selection.isEmpty) {
            await editor.edit((builder) => builder.replace(selection, this.lastCodeBlock));
            return;
        }
        const confirmed = await vscode.window.showWarningMessage("Replace the full active file with the Project Agent fix?", { modal: true }, "Replace File");
        if (confirmed === "Replace File") {
            const fullRange = new vscode.Range(editor.document.positionAt(0), editor.document.positionAt(editor.document.getText().length));
            await editor.edit((builder) => builder.replace(fullRange, this.lastCodeBlock));
        }
    }
    async insertAsNewFile() {
        if (!this.lastCodeBlock) {
            vscode.window.showInformationMessage("Project Agent did not find a code block to insert.");
            return;
        }
        const workspace = vscode.workspace.workspaceFolders?.[0];
        if (!workspace) {
            this.addError("No active workspace found. Open a generated project workspace before inserting files.");
            return;
        }
        const name = await vscode.window.showInputBox({ prompt: "New file path", value: "generated-fix.txt" });
        if (!name) {
            return;
        }
        if (!isSafeWorkspacePath(name)) {
            this.addError("Unsafe file path blocked. Use a relative path inside the workspace without ../ or an absolute drive path.");
            return;
        }
        const target = vscode.Uri.joinPath(workspace.uri, ...name.replace(/\\/g, "/").split("/"));
        await vscode.workspace.fs.writeFile(target, Buffer.from(this.lastCodeBlock, "utf8"));
        await vscode.window.showTextDocument(target);
    }
    addError(message, post = true) {
        const text = message.startsWith("Project Agent error:") ? message : `Project Agent error: ${message}`;
        this.history.push({ role: "error", text });
        vscode.window.showErrorMessage(text);
        if (post) {
            this.postState();
        }
    }
    postState() {
        this.view?.webview.postMessage({
            type: "state",
            history: this.history,
            hasCode: Boolean(this.lastCodeBlock),
            busy: this.busy,
        });
    }
    html(webview) {
        const nonce = String(Date.now());
        return `<!doctype html>
<html>
<head>
  <meta charset="UTF-8">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'nonce-${nonce}';">
  <style>
    body { color: var(--vscode-foreground); font-family: var(--vscode-font-family); margin: 0; }
    .wrap { display: grid; gap: 8px; padding: 10px; }
    .history { display: grid; gap: 8px; max-height: 55vh; overflow: auto; }
    .msg { border: 1px solid var(--vscode-panel-border); border-radius: 6px; padding: 8px; white-space: pre-wrap; }
    .msg.error { border-color: var(--vscode-errorForeground); color: var(--vscode-errorForeground); }
    .role { display: block; font-size: 11px; opacity: 0.75; margin-bottom: 5px; }
    textarea { min-height: 86px; width: 100%; box-sizing: border-box; color: var(--vscode-input-foreground); background: var(--vscode-input-background); border: 1px solid var(--vscode-input-border); }
    button { color: var(--vscode-button-foreground); background: var(--vscode-button-background); border: 0; padding: 7px 10px; }
    button:disabled { opacity: 0.55; }
    .actions { display: flex; flex-wrap: wrap; gap: 6px; }
    .status { min-height: 18px; opacity: 0.78; }
  </style>
</head>
<body>
  <div class="wrap">
    <div id="history" class="history"></div>
    <textarea id="input" placeholder="Ask Project Agent to fix, explain, improve, generate files, or suggest commands..."></textarea>
    <div class="actions">
      <button id="send">Send</button>
      <button id="apply">Apply Fix</button>
      <button id="insert">Insert as New File</button>
      <button id="explain">Explain</button>
      <button id="clear">Clear Chat</button>
    </div>
    <div id="status" class="status"></div>
  </div>
  <script nonce="${nonce}">
    const vscode = acquireVsCodeApi();
    const historyEl = document.getElementById("history");
    const inputEl = document.getElementById("input");
    const statusEl = document.getElementById("status");
    const sendButton = document.getElementById("send");
    function sendMessage() {
      const text = inputEl.value;
      if (!text.trim()) return;
      vscode.postMessage({ type: "send", text });
      inputEl.value = "";
    }
    sendButton.addEventListener("click", sendMessage);
    inputEl.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
      }
    });
    document.getElementById("apply").addEventListener("click", () => vscode.postMessage({ type: "applyFix" }));
    document.getElementById("insert").addEventListener("click", () => vscode.postMessage({ type: "insertNewFile" }));
    document.getElementById("explain").addEventListener("click", () => vscode.postMessage({ type: "explain" }));
    document.getElementById("clear").addEventListener("click", () => vscode.postMessage({ type: "clear" }));
    window.addEventListener("message", (event) => {
      if (event.data.type !== "state") return;
      historyEl.innerHTML = "";
      event.data.history.forEach((msg) => {
        const item = document.createElement("div");
        item.className = "msg " + (msg.role === "error" ? "error" : "");
        const role = document.createElement("strong");
        role.className = "role";
        role.textContent = msg.role.toUpperCase();
        const text = document.createElement("div");
        text.textContent = msg.text;
        item.appendChild(role);
        item.appendChild(text);
        historyEl.appendChild(item);
      });
      sendButton.disabled = Boolean(event.data.busy);
      statusEl.textContent = event.data.busy ? "Project Agent is thinking..." : "";
      historyEl.scrollTop = historyEl.scrollHeight;
    });
  </script>
</body>
</html>`;
    }
}
async function collectWorkspaceContext(userRequest) {
    const editor = vscode.window.activeTextEditor;
    const workspace = vscode.workspace.workspaceFolders?.[0];
    if (!workspace) {
        throw new Error("No active workspace found. Open the generated project workspace before asking Project Agent.");
    }
    const activeFile = editor ? editor.document.uri.fsPath : "";
    const selectedText = editor && !editor.selection.isEmpty ? editor.document.getText(editor.selection) : "";
    const activeContent = editor ? editor.document.getText().slice(0, 20000) : "";
    const files = await vscode.workspace.findFiles("**/*", "{**/node_modules/**,**/.venv/**,**/.git/**}", 200);
    const fileTree = files.map((file) => vscode.workspace.asRelativePath(file)).join("\n");
    const prompt = `You are Project Agent, a coding assistant inside Project Agent IDE.
You help fix, explain, improve, and generate code.
Use the provided project context.
Return practical answers.
If giving a code fix, return the full corrected code in one code block.

Context:
Workspace: ${workspace.uri.fsPath}

Active file: ${activeFile}

Selected text: ${selectedText}

Active file content: ${activeContent}

File tree: ${fileTree}

User request: ${userRequest}

Return:
- explanation
- steps
- corrected code block if needed`;
    return { prompt };
}
async function callOllamaWithFallback(prompt) {
    const config = vscode.workspace.getConfiguration("projectAgent");
    const primary = config.get("model") || process.env.PROJECT_AGENT_MODEL || "qwen2.5-coder:latest";
    const fallback = config.get("fallbackModel") || process.env.PROJECT_AGENT_FALLBACK_MODEL || "codellama:7b";
    const url = config.get("ollamaUrl") || process.env.PROJECT_AGENT_OLLAMA_URL || "http://host.docker.internal:11434/api/generate";
    try {
        return await callOllama(url, primary, prompt);
    }
    catch (firstError) {
        try {
            return await callOllama(url, fallback, prompt);
        }
        catch (secondError) {
            throw new Error(`Ollama is not reachable or the configured models are not installed. URL: ${url}. Primary model: ${primary}. Fallback model: ${fallback}. First error: ${formatError(firstError)}. Fallback error: ${formatError(secondError)}`);
        }
    }
}
async function callOllama(url, model, prompt) {
    const payload = { model, prompt, stream: false };
    const response = await postJson(url, payload);
    if (!response.ok) {
        throw new Error(`Ollama returned HTTP ${response.status}: ${response.body.slice(0, 500)}`);
    }
    let parsed;
    try {
        parsed = JSON.parse(response.body);
    }
    catch (error) {
        throw new Error(`Ollama returned invalid JSON: ${formatError(error)}`);
    }
    if (parsed.error) {
        throw new Error(parsed.error);
    }
    if (!parsed.response) {
        throw new Error(`Ollama returned an empty response for model ${model}.`);
    }
    return parsed.response;
}
async function postJson(url, payload) {
    if (typeof fetch === "function") {
        try {
            const response = await fetch(url, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload),
            });
            return { ok: response.ok, status: response.status, body: await response.text() };
        }
        catch (error) {
            try {
                return await postJsonWithNode(url, payload);
            }
            catch (fallbackError) {
                throw new Error(`Network request failed: ${formatError(error)}. Node HTTP fallback failed: ${formatError(fallbackError)}`);
            }
        }
    }
    return postJsonWithNode(url, payload);
}
function postJsonWithNode(url, payload) {
    return new Promise((resolve, reject) => {
        const target = new URL(url);
        const body = JSON.stringify(payload);
        const client = target.protocol === "https:" ? https : http;
        const request = client.request({
            method: "POST",
            hostname: target.hostname,
            port: target.port,
            path: `${target.pathname}${target.search}`,
            headers: {
                "Content-Type": "application/json",
                "Content-Length": Buffer.byteLength(body),
            },
            timeout: 30000,
        }, (response) => {
            const chunks = [];
            response.on("data", (chunk) => chunks.push(chunk));
            response.on("end", () => {
                const status = response.statusCode || 0;
                resolve({ ok: status >= 200 && status < 300, status, body: Buffer.concat(chunks).toString("utf8") });
            });
        });
        request.on("timeout", () => {
            request.destroy(new Error("Network request failed: Ollama request timed out."));
        });
        request.on("error", (error) => reject(new Error(`Network request failed: ${formatError(error)}`)));
        request.write(body);
        request.end();
    });
}
function extractFirstCodeBlock(text) {
    const match = text.match(/```[a-zA-Z0-9_-]*\n([\s\S]*?)```/);
    return match ? match[1].trim() : "";
}
function isSafeWorkspacePath(rawPath) {
    const normalized = rawPath.replace(/\\/g, "/").trim();
    if (!normalized || normalized.startsWith("/") || /^[a-zA-Z]:\//.test(normalized)) {
        return false;
    }
    return normalized.split("/").every((part) => part && part !== "." && part !== "..");
}
function formatError(error) {
    if (error instanceof Error) {
        return error.message;
    }
    return String(error);
}
//# sourceMappingURL=extension.js.map