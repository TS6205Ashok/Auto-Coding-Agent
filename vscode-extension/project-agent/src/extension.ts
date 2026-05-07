import * as vscode from "vscode";

type ChatMessage = { role: "user" | "agent"; text: string };

let provider: ProjectAgentViewProvider | undefined;

export function activate(context: vscode.ExtensionContext) {
  provider = new ProjectAgentViewProvider(context.extensionUri);
  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider("projectAgent.chatView", provider),
    vscode.commands.registerCommand("projectAgent.openChat", async () => {
      await vscode.commands.executeCommand("projectAgent.chatView.focus");
    }),
    vscode.commands.registerCommand("projectAgent.applyFix", async () => {
      await provider?.applyLastFix();
    }),
  );
}

export function deactivate() {}

class ProjectAgentViewProvider implements vscode.WebviewViewProvider {
  private view?: vscode.WebviewView;
  private history: ChatMessage[] = [];
  private lastCodeBlock = "";

  constructor(private readonly extensionUri: vscode.Uri) {}

  resolveWebviewView(webviewView: vscode.WebviewView) {
    this.view = webviewView;
    webviewView.webview.options = { enableScripts: true };
    webviewView.webview.html = this.html(webviewView.webview);
    webviewView.webview.onDidReceiveMessage(async (message) => {
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
        await this.ask("Explain the current active file and the selected code.");
      }
      if (message.type === "insertNewFile") {
        await this.insertAsNewFile();
      }
    });
    this.postState();
  }

  async ask(userText: string) {
    if (!userText.trim()) {
      return;
    }
    this.history.push({ role: "user", text: userText });
    this.postState();
    const context = await collectWorkspaceContext(userText);
    const answer = await callOllamaWithFallback(context.prompt);
    this.lastCodeBlock = extractFirstCodeBlock(answer);
    this.history.push({ role: "agent", text: answer });
    this.postState();
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
    const confirmed = await vscode.window.showWarningMessage(
      "Replace the full active file with the Project Agent fix?",
      { modal: true },
      "Replace File",
    );
    if (confirmed === "Replace File") {
      const fullRange = new vscode.Range(
        editor.document.positionAt(0),
        editor.document.positionAt(editor.document.getText().length),
      );
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
      vscode.window.showErrorMessage("Open a workspace before inserting a file.");
      return;
    }
    const name = await vscode.window.showInputBox({ prompt: "New file path", value: "generated-fix.txt" });
    if (!name) {
      return;
    }
    const target = vscode.Uri.joinPath(workspace.uri, name);
    await vscode.workspace.fs.writeFile(target, Buffer.from(this.lastCodeBlock, "utf8"));
    await vscode.window.showTextDocument(target);
  }

  private postState() {
    this.view?.webview.postMessage({ type: "state", history: this.history, hasCode: Boolean(this.lastCodeBlock) });
  }

  private html(webview: vscode.Webview) {
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
    textarea { min-height: 86px; width: 100%; box-sizing: border-box; color: var(--vscode-input-foreground); background: var(--vscode-input-background); border: 1px solid var(--vscode-input-border); }
    button { color: var(--vscode-button-foreground); background: var(--vscode-button-background); border: 0; padding: 7px 10px; }
    .actions { display: flex; flex-wrap: wrap; gap: 6px; }
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
  </div>
  <script nonce="${nonce}">
    const vscode = acquireVsCodeApi();
    const historyEl = document.getElementById("history");
    const inputEl = document.getElementById("input");
    document.getElementById("send").addEventListener("click", () => vscode.postMessage({ type: "send", text: inputEl.value }));
    document.getElementById("apply").addEventListener("click", () => vscode.postMessage({ type: "applyFix" }));
    document.getElementById("insert").addEventListener("click", () => vscode.postMessage({ type: "insertNewFile" }));
    document.getElementById("explain").addEventListener("click", () => vscode.postMessage({ type: "explain" }));
    document.getElementById("clear").addEventListener("click", () => vscode.postMessage({ type: "clear" }));
    window.addEventListener("message", (event) => {
      if (event.data.type !== "state") return;
      historyEl.innerHTML = "";
      event.data.history.forEach((msg) => {
        const item = document.createElement("div");
        item.className = "msg";
        item.textContent = msg.role.toUpperCase() + "\\n" + msg.text;
        historyEl.appendChild(item);
      });
    });
  </script>
</body>
</html>`;
  }
}

async function collectWorkspaceContext(userRequest: string): Promise<{ prompt: string }> {
  const editor = vscode.window.activeTextEditor;
  const workspace = vscode.workspace.workspaceFolders?.[0];
  const activeFile = editor ? editor.document.uri.fsPath : "";
  const selectedText = editor && !editor.selection.isEmpty ? editor.document.getText(editor.selection) : "";
  const activeContent = editor ? editor.document.getText().slice(0, 20000) : "";
  const files = await vscode.workspace.findFiles("**/*", "{**/node_modules/**,**/.venv/**,**/.git/**}", 200);
  const fileTree = files.map((file) => vscode.workspace.asRelativePath(file)).join("\\n");
  const prompt = `You are Project Agent, a coding assistant inside a VS Code-like IDE.
You help fix, explain, improve, and generate code.
Use the provided project context.
Return practical answers.
If giving a code fix, return the full corrected code in one code block.

Context:
Workspace: ${workspace?.uri.fsPath || ""}

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

async function callOllamaWithFallback(prompt: string): Promise<string> {
  const config = vscode.workspace.getConfiguration("projectAgent");
  const primary = config.get<string>("model") || process.env.PROJECT_AGENT_MODEL || "qwen2.5-coder:latest";
  const fallback = config.get<string>("fallbackModel") || process.env.PROJECT_AGENT_FALLBACK_MODEL || "codellama:7b";
  const url = config.get<string>("ollamaUrl") || process.env.PROJECT_AGENT_OLLAMA_URL || "http://host.docker.internal:11434/api/generate";
  try {
    return await callOllama(url, primary, prompt);
  } catch (firstError) {
    try {
      return await callOllama(url, fallback, prompt);
    } catch {
      return `Ollama is not running. Start Ollama and make sure qwen2.5-coder is installed. URL: ${url}. Original error: ${String(firstError)}`;
    }
  }
}

async function callOllama(url: string, model: string, prompt: string): Promise<string> {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model, prompt, stream: false }),
  });
  if (!response.ok) {
    throw new Error(`Ollama returned HTTP ${response.status}`);
  }
  const payload = await response.json() as { response?: string };
  return payload.response || "";
}

function extractFirstCodeBlock(text: string): string {
  const match = text.match(/```[a-zA-Z0-9_-]*\\n([\\s\\S]*?)```/);
  return match ? match[1].trim() : "";
}
