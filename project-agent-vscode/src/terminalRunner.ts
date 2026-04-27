import * as vscode from "vscode";

export type ScriptKind = "setup" | "run";

export async function findScriptUri(
  workspaceFolder: vscode.WorkspaceFolder,
  kind: ScriptKind,
): Promise<vscode.Uri | undefined> {
  const fileName = getScriptFileName(kind);
  const uri = vscode.Uri.joinPath(workspaceFolder.uri, fileName);

  try {
    await vscode.workspace.fs.stat(uri);
    return uri;
  } catch {
    return undefined;
  }
}

export async function confirmAndRunScript(
  workspaceFolder: vscode.WorkspaceFolder,
  kind: ScriptKind,
): Promise<boolean> {
  const scriptUri = await findScriptUri(workspaceFolder, kind);
  if (!scriptUri) {
    const label = kind === "setup" ? "setup" : "run";
    await vscode.window.showErrorMessage(`Could not find ${getScriptFileName(kind)} in the workspace root.`);
    return false;
  }

  const actionLabel = kind === "setup" ? "Run Setup" : "Run Project";
  const confirmation = await vscode.window.showInformationMessage(
    `Do you want to ${kind === "setup" ? "run setup" : "run the project"} now?`,
    { modal: true },
    actionLabel,
    "Cancel",
  );

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

function getScriptFileName(kind: ScriptKind): string {
  if (process.platform === "win32") {
    return kind === "setup" ? "setup.bat" : "run.bat";
  }
  return kind === "setup" ? "setup.sh" : "run.sh";
}

function buildTerminalCommand(kind: ScriptKind): string {
  if (process.platform === "win32") {
    return kind === "setup" ? ".\\setup.bat" : ".\\run.bat";
  }
  return kind === "setup" ? 'bash "./setup.sh"' : 'bash "./run.sh"';
}
