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
exports.resolveSafeWorkspacePath = resolveSafeWorkspacePath;
exports.normalizeRelativePath = normalizeRelativePath;
const path = __importStar(require("path"));
const vscode = __importStar(require("vscode"));
function resolveSafeWorkspacePath(workspaceFolder, relativePath) {
    const normalized = normalizeRelativePath(relativePath);
    const rootPath = workspaceFolder.uri.fsPath;
    const finalPath = path.resolve(rootPath, normalized);
    const relativeToRoot = path.relative(rootPath, finalPath);
    if (relativeToRoot.startsWith("..") ||
        path.isAbsolute(relativeToRoot)) {
        throw new Error(`Refusing to write outside the workspace: ${relativePath}`);
    }
    return vscode.Uri.file(finalPath);
}
function normalizeRelativePath(relativePath) {
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
//# sourceMappingURL=pathSafety.js.map