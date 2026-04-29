#!/usr/bin/env python3
"""Discover Cursor agent transcript JSONL files and export them to Markdown.

Cursor stores **parent** Agent chat transcripts (this workspace) under::

    ~/.cursor/projects/<workspace-directory-slug>/agent-transcripts/
        <conversation-uuid>/<conversation-uuid>.jsonl

Each line is one JSON object: ``role`` is ``user`` or ``assistant``; ``message``
may contain ``text`` and ``tool_use`` blocks. Some assistant text is stored as
``[REDACTED]`` by Cursor.

This script is meant to be re-run whenever you want a fresh dump for docs.

CLI flags ``--workspace-match`` and ``--output`` override defaults (repo name
and ``docs/cursor-agent-chat-export.md``).
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path

HOME = Path.home().resolve()


def tilde_home(path: Path) -> str:
    """Render an absolute path under ``HOME`` as ``~/...`` for readability."""
    resolved = path.expanduser().resolve()
    try:
        rel = resolved.relative_to(HOME)
    except ValueError:
        return str(path)
    return "~/" + str(rel)


def _find_repo_root(start: Path) -> Path:
    """Walk upward from *start* until ``pyproject.toml`` is found."""
    for parent in [start, *start.parents]:
        if (parent / "pyproject.toml").is_file():
            return parent
    return start


def discover_transcript_files(workspace_match: str) -> list[tuple[Path, Path]]:
    """Return sorted list of (jsonl_path, project_dir) under ~/.cursor/projects."""
    projects = HOME / ".cursor" / "projects"
    if not projects.is_dir():
        return []

    found: list[tuple[Path, Path]] = []
    for proj in sorted(projects.iterdir()):
        if not proj.is_dir():
            continue
        if workspace_match not in proj.name:
            continue
        at = proj / "agent-transcripts"
        if not at.is_dir():
            continue
        for p in sorted(at.rglob("*.jsonl")):
            found.append((p, proj))

    found.sort(key=lambda x: x[0].stat().st_mtime, reverse=True)
    return found


_USER_QUERY_RE = re.compile(
    r"<user_query>\s*(.*?)\s*</user_query>",
    re.DOTALL | re.IGNORECASE,
)


def _strip_user_query_xml(text: str) -> str:
    """Remove Cursor's ``<user_query>`` wrapper when present.

    :param text: Raw text block from a user message.
    :returns: Inner prompt text or stripped *text*.
    """
    m = _USER_QUERY_RE.search(text)
    return m.group(1).strip() if m else text.strip()


def _sanitize_json_paths(obj: object) -> object:
    """Rewrite absolute filesystem paths in JSON-like structures to ``~/`` form."""
    if isinstance(obj, str):
        if not obj.startswith("/"):
            return obj
        return tilde_home(Path(obj))
    if isinstance(obj, dict):
        return {k: _sanitize_json_paths(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_json_paths(v) for v in obj]
    return obj


def content_blocks_to_markdown(blocks: list[dict[str, object]]) -> str:
    """Serialize transcript ``content`` blocks to Markdown (text plus tool JSON).

    :param blocks: Content array from one JSONL line's ``message``.
    :returns: Concatenated Markdown string.
    """
    parts: list[str] = []
    for block in blocks:
        btype = block.get("type")
        if btype == "text":
            parts.append(str(block.get("text") or ""))
        elif btype == "tool_use":
            name = block.get("name", "?")
            inp = _sanitize_json_paths(block.get("input"))
            parts.append(
                f"\n\n**Tool:** `{name}`\n\n```json\n{json.dumps(inp, indent=2)}\n```\n"
            )
        else:
            parts.append(f"\n\n<!-- block type: {btype} -->\n")
    return "".join(parts).strip()


def jsonl_to_markdown_sections(jsonl_path: Path) -> tuple[str, int]:
    """Parse one JSONL transcript file into Markdown sections.

    :param jsonl_path: Path to a ``*.jsonl`` Cursor transcript file.
    :returns: Markdown body and total message count.
    """
    lines_out: list[str] = []
    turn = 0
    with jsonl_path.open(encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                lines_out.append(f"\n<!-- JSON parse error line {line_no}: {e} -->\n")
                continue

            role = obj.get("role", "?")
            msg = obj.get("message") or {}
            content = msg.get("content")
            if not isinstance(content, list):
                lines_out.append(f"\n<!-- non-list content line {line_no} -->\n")
                continue

            turn += 1
            body = content_blocks_to_markdown(content)
            if role == "user":
                body = _strip_user_query_xml(body)

            lines_out.append(f"\n### Turn {turn} — {role}\n\n{body}\n")

    return "".join(lines_out), turn


def main() -> None:
    """Discover transcripts from CLI arguments and write Markdown to disk."""
    repo = _find_repo_root(Path(__file__).resolve().parent)
    default_match = repo.name

    parser = argparse.ArgumentParser(
        description="Export Cursor agent transcript JSONL files to Markdown.",
    )
    parser.add_argument(
        "--workspace-match",
        default=default_match,
        help=f"Substring of ~/.cursor/projects/<dir> name (default: {default_match})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=repo / "docs" / "cursor-agent-chat-export.md",
        help="Output Markdown path",
    )
    args = parser.parse_args()

    pairs = discover_transcript_files(args.workspace_match)

    out_lines: list[str] = [
        "# Cursor Agent chat export\n",
        "\nThis file is **generated**. Re-run:\n\n",
        "```bash\n",
        "pixi run python scripts/export_cursor_agent_transcripts.py\n",
        "```\n\n",
        f"Generated at **{datetime.now(tz=UTC).strftime('%Y-%m-%d %H:%M UTC')}**.\n\n",
        "---\n\n",
        "## Where Cursor stores these transcripts\n\n",
        "On macOS/Linux, Cursor keeps **workspace-scoped** Agent transcripts under:\n\n",
        "```text\n",
        "~/.cursor/projects/<workspace-directory-slug>/agent-transcripts/\n",
        "    <conversation-uuid>/<conversation-uuid>.jsonl\n",
        "```\n\n",
        "The `<workspace-directory-slug>` for this repo is typically derived from the "
        "absolute path (for example `Users-you-github-repo-name`). "
        f"This exporter matched projects containing **`{args.workspace_match}`**.\n\n",
        "---\n\n",
    ]

    if not pairs:
        out_lines.append(
            f"_No `*.jsonl` files found under `~/.cursor/projects/*{args.workspace_match}*/agent-transcripts/`._\n"
        )
    else:
        out_lines.append(f"Found **{len(pairs)}** transcript file(s).\n\n")

    for jsonl_path, project_dir in pairs:
        rel_hint = (
            jsonl_path.relative_to(project_dir)
            if jsonl_path.is_relative_to(project_dir)
            else jsonl_path
        )
        stat = jsonl_path.stat()
        mtime = datetime.fromtimestamp(stat.st_mtime, tz=UTC).strftime(
            "%Y-%m-%d %H:%M UTC"
        )

        out_lines.extend(
            [
                f"## Session `{jsonl_path.parent.name}`\n\n",
                f"- **Source file:** `{tilde_home(jsonl_path)}`\n",
                f"- **Project cache dir:** `{tilde_home(project_dir)}`\n",
                f"- **Relative path:** `{rel_hint}`\n",
                f"- **Modified:** {mtime}\n",
                f"- **Size:** {stat.st_size:,} bytes\n\n",
                "> Assistant turns may contain `[REDACTED]` placeholders where Cursor "
                "did not persist full model text.\n\n",
            ]
        )

        sections, n_turns = jsonl_to_markdown_sections(jsonl_path)
        out_lines.append(f"_({n_turns} messages)_\n\n")
        out_lines.append(sections)
        out_lines.append("\n---\n\n")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(out_lines), encoding="utf-8")
    print(f"Wrote {args.output} ({len(pairs)} transcript file(s))")


if __name__ == "__main__":
    main()
