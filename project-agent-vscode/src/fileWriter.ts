import * as vscode from "vscode";
import * as path from "path";
import { PreviewFile } from "./api";
import { normalizeRelativePath, resolveSafeWorkspacePath } from "./pathSafety";

export interface WriteSummary {
  written: string[];
  skipped: string[];
  cancelled: boolean;
}

const encoder = new TextEncoder();

export async function writePreviewFiles(
  workspaceFolder: vscode.WorkspaceFolder,
  files: PreviewFile[],
): Promise<WriteSummary> {
  const summary: WriteSummary = {
    written: [],
    skipped: [],
    cancelled: false,
  };

  for (const file of files) {
    const safeRelativePath = normalizeRelativePath(file.path);
    const targetUri = resolveSafeWorkspacePath(workspaceFolder, safeRelativePath);

    const exists = await pathExists(targetUri);
    if (exists) {
      const choice = await vscode.window.showWarningMessage(
        `${safeRelativePath} already exists.`,
        { modal: true },
        "Overwrite",
        "Skip",
        "Cancel",
      );

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

export async function maybeCreateEnvFile(
  workspaceFolder: vscode.WorkspaceFolder,
): Promise<boolean> {
  const envExampleUri = resolveSafeWorkspacePath(workspaceFolder, ".env.example");
  const envUri = resolveSafeWorkspacePath(workspaceFolder, ".env");

  if (!(await pathExists(envExampleUri)) || (await pathExists(envUri))) {
    return false;
  }

  const choice = await vscode.window.showInformationMessage(
    "Create .env from .env.example now?",
    "Create .env",
    "Skip",
  );
  if (choice !== "Create .env") {
    return false;
  }

  const bytes = await vscode.workspace.fs.readFile(envExampleUri);
  await vscode.workspace.fs.writeFile(envUri, bytes);
  return true;
}

async function pathExists(uri: vscode.Uri): Promise<boolean> {
  try {
    await vscode.workspace.fs.stat(uri);
    return true;
  } catch {
    return false;
  }
}
