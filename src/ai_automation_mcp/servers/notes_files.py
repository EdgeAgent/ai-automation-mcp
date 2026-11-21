"""Server 03 — notes-files.

File tools with a hard sandbox, in the spirit of the official Filesystem
reference server: every path is resolved against one workspace
directory, and anything that would land outside it — ``..`` segments,
absolute paths, symlinked escapes — is refused before a single byte is
read or written. The tests try to break out; the sandbox is the point.

- ``write_note`` overwrites a note (annotated destructive: it replaces
  content).
- ``read_note`` / ``list_notes`` / ``search_notes`` are read-only.

The workspace root is injected, so tests use a temp directory and live
runs use ``AI_MCP_NOTES_DIR``.
"""

from __future__ import annotations

from pathlib import Path

from ai_automation_mcp.protocol import ToolError
from ai_automation_mcp.server import (
    JsonDict,
    McpServer,
    Prompt,
    PromptArgument,
    Resource,
    Tool,
    ToolAnnotations,
    ToolResult,
)

READ_ONLY = ToolAnnotations(read_only=True, destructive=False, idempotent=True, open_world=False)


class NotesWorkspace:
    """A directory of text notes with containment enforced on every path."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, name: str) -> Path:
        """Resolve ``name`` inside the sandbox or raise ToolError."""
        if not name.strip():
            raise ToolError("Note name must not be empty.")
        candidate = Path(name)
        if candidate.is_absolute():
            raise ToolError(f"Absolute paths are outside the sandbox: {name!r}")
        resolved = (self.root / candidate).resolve()
        if resolved != self.root and self.root not in resolved.parents:
            raise ToolError(f"Path escapes the notes sandbox: {name!r}")
        return resolved

    def write(self, name: str, content: str) -> Path:
        path = self._resolve(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def read(self, name: str) -> str:
        path = self._resolve(name)
        if not path.is_file():
            raise ToolError(f"No such note: {name!r}")
        return path.read_text(encoding="utf-8")

    def list_names(self) -> list[str]:
        names = [
            str(path.relative_to(self.root))
            for path in sorted(self.root.rglob("*"))
            if path.is_file()
        ]
        return names

    def search(self, query: str) -> list[tuple[str, str]]:
        """Return (name, first matching line) pairs for a substring query."""
        needle = query.lower()
        hits: list[tuple[str, str]] = []
        for name in self.list_names():
            for line in self.read(name).splitlines():
                if needle in line.lower():
                    hits.append((name, line.strip()))
                    break
        return hits


def create_server(root: Path) -> McpServer:
    """Build the notes-files server rooted at ``root`` (the sandbox)."""
    workspace = NotesWorkspace(root)
    server = McpServer(
        "notes-files",
        instructions=f"Notes live in one sandboxed directory: {workspace.root}",
    )

    def write_note(arguments: JsonDict) -> ToolResult:
        name = str(arguments["name"])
        workspace.write(name, str(arguments["content"]))
        return ToolResult(text=f"Wrote note {name!r} in the sandbox.")

    def read_note(arguments: JsonDict) -> ToolResult:
        name = str(arguments["name"])
        return ToolResult(text=workspace.read(name))

    def list_notes(arguments: JsonDict) -> ToolResult:
        names = workspace.list_names()
        text = "\n".join(names) if names else "(no notes yet)"
        return ToolResult(text=text, structured={"notes": names})

    def search_notes(arguments: JsonDict) -> ToolResult:
        hits = workspace.search(str(arguments["query"]))
        lines = [f"{name}: {line}" for name, line in hits]
        text = "\n".join(lines) if lines else "No matches."
        return ToolResult(
            text=text,
            structured={"matches": [{"note": name, "line": line} for name, line in hits]},
        )

    server.add_tool(
        Tool(
            name="write_note",
            description=(
                "Create or overwrite a note inside the sandboxed notes "
                "directory. Paths outside the sandbox are refused."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Relative note path, e.g. ideas.md"},
                    "content": {"type": "string"},
                },
                "required": ["name", "content"],
            },
            handler=write_note,
            annotations=ToolAnnotations(
                read_only=False,
                destructive=True,
                idempotent=True,
                open_world=False,
                title="Write a note (overwrites)",
            ),
        )
    )
    server.add_tool(
        Tool(
            name="read_note",
            description="Read one note from the sandbox by relative path.",
            input_schema={
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            },
            handler=read_note,
            annotations=READ_ONLY,
        )
    )
    server.add_tool(
        Tool(
            name="list_notes",
            description="List every note in the sandbox, recursively.",
            input_schema={"type": "object", "properties": {}},
            handler=list_notes,
            annotations=READ_ONLY,
        )
    )
    server.add_tool(
        Tool(
            name="search_notes",
            description="Find notes containing a substring (case-insensitive).",
            input_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            handler=search_notes,
            annotations=READ_ONLY,
        )
    )
    server.add_resource(
        Resource(
            uri="notes://index",
            name="Notes index",
            description="The current list of notes in the sandbox.",
            reader=lambda: "\n".join(workspace.list_names()) or "(no notes yet)",
        )
    )
    server.add_prompt(
        Prompt(
            name="summarize_note",
            description="Read a note with read_note and summarize it faithfully.",
            arguments=[
                PromptArgument(name="name", description="Note path in the sandbox.", required=True)
            ],
            getter=lambda arguments: [
                {
                    "role": "user",
                    "content": {
                        "type": "text",
                        "text": (
                            f"Use read_note to read {arguments['name']!r}, then summarize "
                            "it in three bullet points. Use only what the note says — "
                            "if the note is missing, tell me instead of inventing content."
                        ),
                    },
                }
            ],
        )
    )
    return server
