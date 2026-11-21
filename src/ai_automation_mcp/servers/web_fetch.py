"""Server 04 — web-fetch.

One tool, honestly bounded: ``fetch_url`` downloads a page through an
injectable HTTP client and returns the readable text (title + body,
scripts and styles stripped, standard library only — the same pattern
as the official Fetch reference server).

- The HTTP client is a backend: demos and tests use the canned fake;
  live runs use httpx.
- An optional domain allowlist restricts which hosts may be fetched.
- A failed fetch is an error result with the reason. Content is never
  invented to fill a gap.
"""

from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import urlparse

from ai_automation_mcp.backends import FetchError, HttpClient
from ai_automation_mcp.protocol import ToolError
from ai_automation_mcp.server import (
    JsonDict,
    McpServer,
    Resource,
    Tool,
    ToolAnnotations,
    ToolResult,
)

_SKIP_TAGS = {"script", "style", "noscript", "template", "svg"}


class _TextExtractor(HTMLParser):
    """Collects visible text and the <title> from an HTML document."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.chunks: list[str] = []
        self._skip_depth = 0
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        elif tag == "title":
            self._in_title = True
        elif tag in {"p", "div", "section", "article", "li", "h1", "h2", "h3", "br"}:
            self.chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS and self._skip_depth:
            self._skip_depth -= 1
        elif tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = data.strip()
        if not text:
            return
        if self._in_title:
            self.title = text
        else:
            self.chunks.append(text)


def extract_text(html: str) -> tuple[str, str]:
    """Return (title, readable text) for an HTML document."""
    parser = _TextExtractor()
    parser.feed(html)
    lines = [line.strip() for line in " ".join(parser.chunks).splitlines()]
    text = "\n".join(line for line in lines if line)
    return parser.title, text


def create_server(client: HttpClient, *, allowlist: list[str] | None = None) -> McpServer:
    """Build the web-fetch server around an injected HTTP client."""
    allowed = [domain.lower() for domain in (allowlist or [])]
    server = McpServer(
        "web-fetch",
        instructions="Fetch pages and return readable text. Failures are reported, never faked.",
    )

    def fetch_url(arguments: JsonDict) -> ToolResult:
        url = str(arguments["url"])
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ToolError(f"Not a fetchable URL: {url!r}")
        host = (parsed.hostname or "").lower()
        if allowed and host not in allowed:
            raise ToolError(
                f"Domain {host!r} is not on this server's allowlist ({', '.join(allowed)})."
            )
        try:
            html = client.get(url)
        except FetchError as exc:
            raise ToolError(str(exc)) from exc
        title, text = extract_text(html)
        header = f"# {title}\nSource: {url}\n\n" if title else f"Source: {url}\n\n"
        return ToolResult(
            text=header + text,
            structured={"url": url, "title": title, "characters": len(text)},
        )

    server.add_tool(
        Tool(
            name="fetch_url",
            description=(
                "Fetch a web page and return its readable text (title + body). "
                "Read-only, but reaches the network when wired to the live "
                "HTTP backend — hence openWorldHint."
            ),
            input_schema={
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
            handler=fetch_url,
            annotations=ToolAnnotations(
                read_only=True,
                destructive=False,
                idempotent=True,
                open_world=True,
                title="Fetch a page",
            ),
        )
    )

    def policy() -> str:
        domains = ", ".join(allowed) if allowed else "(no allowlist — any public domain)"
        return (
            "# Fetch policy\n\n"
            f"- Allowlist: {domains}\n"
            "- Only http/https URLs are fetched.\n"
            "- Scripts, styles, and templates are stripped; the tool returns text.\n"
            "- A failed fetch returns an error. The server never fabricates page content."
        )

    server.add_resource(
        Resource(
            uri="docs://fetch-policy",
            name="Fetch policy",
            description="Which domains this fetch server may read, and its failure rules.",
            reader=policy,
            mime_type="text/markdown",
        )
    )
    return server
