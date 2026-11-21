"""Standalone end-to-end demo for AI Automation MCP.

Boots all six servers on fake backends and calls their headline tools
through the real MCP protocol, then prints a summary report. Works from
a clone without installing the package (it adds ``src/`` to the path);
with the package installed, ``ai-mcp demo`` does the same thing.

Usage: python scripts/demo.py
"""


def main() -> None:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

    from ai_automation_mcp.demo import run_full_demo

    print(run_full_demo())


if __name__ == "__main__":
    main()
