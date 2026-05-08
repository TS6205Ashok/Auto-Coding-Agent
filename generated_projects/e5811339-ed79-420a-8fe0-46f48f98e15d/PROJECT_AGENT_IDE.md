# Project Agent IDE

Welcome to **Project Agent IDE** for `Create Sudoku Web`.

This workspace is powered by real code-server, so you still have the VS Code file explorer, tabs, terminal, settings, extensions, and command palette.

## Start Here

1. Open the **Project Agent** icon in the Activity Bar.
2. Ask the assistant to explain files, suggest fixes, or generate focused code snippets.
3. Use the Explorer to inspect generated files.
4. Use the integrated terminal to run setup and start commands from the project README.

## Login

Project Agent IDE uses code-server password auth.

```text
1234$
```

## Project Agent Assistant

- **Open Chat** focuses the Project Agent assistant.
- **Apply Fix** can apply the last code block to the active editor after confirmation.
- **Insert as New File** asks for a workspace-relative path before writing.
- The assistant sends local workspace context to Ollama only.

## Ollama From Docker

Inside the IDE container, Project Agent calls:

```text
http://host.docker.internal:11434/api/generate
```

Make sure Ollama is running on the host and the configured model is available.

Test Ollama from the IDE terminal:

```bash
curl http://host.docker.internal:11434/api/tags
```

Test generation:

```bash
curl http://host.docker.internal:11434/api/generate -d "{"model":"qwen2.5-coder:latest","prompt":"Say hello","stream":false}"
```

If the model is missing, run this on the host:

```bash
ollama pull qwen2.5-coder
```

## ZIP and Workspace

The original generated ZIP is available from Project Agent. If you edit files in this IDE, use the workspace download endpoint to download the edited workspace.
