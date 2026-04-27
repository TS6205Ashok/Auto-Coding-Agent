import * as path from "path";
import * as vscode from "vscode";

export function resolveSafeWorkspacePath(
  workspaceFolder: vscode.WorkspaceFolder,
  relativePath: string,
): vscode.Uri {
  const normalized = normalizeRelativePath(relativePath);
  const rootPath = workspaceFolder.uri.fsPath;
  const finalPath = path.resolve(rootPath, normalized);
  const relativeToRoot = path.relative(rootPath, finalPath);

  if (
    relativeToRoot.startsWith("..") ||
    path.isAbsolute(relativeToRoot)
  ) {
    throw new Error(`Refusing to write outside the workspace: ${relativePath}`);
  }

  return vscode.Uri.file(finalPath);
}

export function normalizeRelativePath(relativePath: string): string {
  const trimmed = relativePath.replace(/\\/g, "/").trim();
  if (!trimmed) {
    throw new Error("Generated file path is empty.");
  }
  if (trimmed.startsWith("/") || path.isAbsolute(trimmed)) {
    throw new Error(`Absolute paths are not allowed: ${relativePath}`);
  }

  const segments = trimmed.split("/").filter(Boolean);
  if (segments.length === 0) {
    throw new Error(`Generated file path is invalid: ${relativePath}`);
  }
  if (segments.some((segment) => segment === "..")) {
    throw new Error(`Path traversal is not allowed: ${relativePath}`);
  }

  return segments.join(path.sep);
}
