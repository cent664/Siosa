#!/usr/bin/env python3
"""Sync docs/ARCHITECTURE.md and docs/CHANGELOG.md to README and HTML."""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

try:
    import markdown
except ImportError:
    print("Install markdown: pip install markdown", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ASSETS = DOCS / "assets"
PIPELINE_MARKER = "<!-- INTERACTIVE_PIPELINE -->"

SHARED_STYLES = """
    body { font-family: system-ui, sans-serif; max-width: 960px; margin: 2rem auto; padding: 0 1rem; line-height: 1.6; }
    h1, h2, h3 { color: #1a1a2e; }
    table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
    th, td { border: 1px solid #ccc; padding: 0.5rem 0.75rem; text-align: left; vertical-align: top; }
    th { background: #f0f0f8; }
    code { background: #f4f4f4; padding: 0.1em 0.3em; border-radius: 3px; }
    pre { background: #f8f8fc; padding: 1rem; overflow-x: auto; }
    nav { margin-bottom: 1.5rem; padding: 0.75rem; background: #f0f4ff; border-radius: 6px; }
    nav a { margin-right: 1rem; }
    a { color: #2563eb; }
    article { border-left: 4px solid #2563eb; padding-left: 1rem; margin-bottom: 2rem; }
    time { color: #666; font-size: 0.9rem; display: block; margin-bottom: 0.25rem; }
    article h3 { margin-top: 0.25rem; }
    article ul { margin: 0.5rem 0 0 1.1rem; padding: 0; }
    article li { margin: 0.35rem 0; }
    .changelog-label { font-weight: 600; color: #333; }
    pre.mermaid { background: transparent; border: none; padding: 0.5rem 0; overflow-x: auto; text-align: center; }
    .mermaid { margin: 1.5rem 0; }
"""

ARCH_EXTRA_STYLES = """
    body { max-width: 1100px; }
"""

HTML_HEAD_BASE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>
{styles}
  </style>
{extra_head}
  <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
    mermaid.initialize({{ startOnLoad: true, theme: 'neutral' }});
  </script>
</head>
<body>
  <nav>
    <a href="/docs/">Docs hub</a>
    <a href="/docs/architecture.html">Architecture</a>
    <a href="/docs/changelog.html">Changelog</a>
    <a href="/">App UI</a>
  </nav>
"""

HTML_FOOT = """
</body>
</html>
"""


def _head(title: str, *, architecture: bool = False) -> str:
    styles = SHARED_STYLES
    if architecture:
        styles += ARCH_EXTRA_STYLES
    extra = ""
    if architecture:
        extra = (
            '  <link rel="stylesheet" href="/docs/assets/architecture-pipeline.css" />\n'
            '  <script defer src="/docs/assets/architecture-pipeline.js"></script>'
        )
    return HTML_HEAD_BASE.format(title=title, styles=styles, extra_head=extra)


DETAILS_PATTERN = re.compile(
    r'<details class="arch-collapse">\s*'
    r"<summary>(.*?)</summary>\s*"
    r"(.*?)\s*"
    r"</details>",
    re.DOTALL | re.IGNORECASE,
)

SUMMARY_ANCHORS = {
    "Quality metrics reference": "quality-metrics-reference",
    "Scaling to the full wiki": "scaling-to-the-full-wiki",
}


def _md_fragment(inner: str) -> str:
    return markdown.markdown(
        inner.strip(),
        extensions=["tables", "fenced_code", "nl2br"],
    )


def _preprocess_details_blocks(md_text: str) -> str:
    def repl(match: re.Match) -> str:
        summary = match.group(1).strip()
        inner_md = match.group(2).strip()
        inner_html = _md_fragment(inner_md)
        anchor = SUMMARY_ANCHORS.get(summary, "")
        id_attr = f' id="{anchor}"' if anchor else ""
        return (
            f'<details class="arch-collapse">'
            f"<summary{id_attr}>{html.escape(summary)}</summary>\n"
            f'<div class="arch-collapse-body">{inner_html}</div>\n'
            f"</details>"
        )

    return DETAILS_PATTERN.sub(repl, md_text)


def md_to_html_body(md_text: str) -> str:
    md_text = _preprocess_details_blocks(md_text)
    body = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "nl2br"],
    )
    body = _fix_mermaid_blocks(body)
    return _add_heading_anchors(body)


def _add_heading_anchors(html_body: str) -> str:
    replacements = {
        "Pipeline overview": "pipeline-overview",
    }
    for title, anchor_id in replacements.items():
        html_body = html_body.replace(
            f"<h2>{title}</h2>",
            f'<h2 id="{anchor_id}">{title}</h2>',
        )
    return html_body


def _fix_mermaid_blocks(html_body: str) -> str:
    pattern = r'<pre><code class="language-mermaid">(.*?)</code></pre>'

    def repl(match: re.Match) -> str:
        content = html.unescape(match.group(1))
        for old, new in [("<p>", ""), ("</p>", "\n"), ("<br />", "\n"), ("<br>", "\n")]:
            content = content.replace(old, new)
        return f'<pre class="mermaid">{content.strip()}</pre>'

    return re.sub(pattern, repl, html_body, flags=re.DOTALL)


def _normalize_changelog_bullet(line: str) -> str | None:
    line = line.strip()
    if not line.startswith("- "):
        return None
    rest = line[2:].strip()
    m = re.match(r"\*\*(.+?)\*\*\s*:\s*(.+)", rest)
    if m:
        label, desc = m.groups()
        return (
            f'<li><span class="changelog-label">{html.escape(label)}</span>'
            f" — {html.escape(desc)}</li>"
        )
    m = re.match(r"\*\*(.+?)\*\*\s*—\s*(.+)", rest)
    if m:
        label, desc = m.groups()
        return (
            f'<li><span class="changelog-label">{html.escape(label)}</span>'
            f" — {html.escape(desc)}</li>"
        )
    m = re.match(r"(.+?)\s*—\s*(.+)", rest)
    if m:
        label, desc = m.groups()
        return (
            f'<li><span class="changelog-label">{html.escape(label)}</span>'
            f" — {html.escape(desc)}</li>"
        )
    return f"<li>{html.escape(rest)}</li>"


def _render_changelog_body(body: str) -> str:
    lines = body.split("\n")
    items: list[str] = []
    paragraphs: list[str] = []

    for line in lines:
        bullet = _normalize_changelog_bullet(line)
        if bullet:
            items.append(bullet)
        elif line.strip():
            paragraphs.append(f"<p>{html.escape(line.strip())}</p>")

    parts: list[str] = []
    if items:
        parts.append("<ul>" + "".join(items) + "</ul>")
    parts.extend(paragraphs)
    return "\n".join(parts) if parts else ""


def _alt_html(alt: dict, detail_id: str) -> str:
    opaque = " pipeline-alt--opaque" if alt.get("opaque") else ""
    label = html.escape(alt["label"])
    return (
        f'<div class="pipeline-alt{opaque}" tabindex="0" data-detail-id="{detail_id}">'
        f"{label}</div>"
    )


def _render_interactive_pipeline() -> str:
    config_path = ASSETS / "pipeline-config.json"
    data = json.loads(config_path.read_text(encoding="utf-8"))
    stages_html: list[str] = []
    details_map: dict[str, dict[str, str]] = {}

    for stage in data["stages"]:
        sid = stage["id"]
        core_id = f"{sid}-core"
        details_map[core_id] = {
            "title": f'{sid} {stage["title"]} — {stage["chosen"]}',
            "html": stage["detail"],
        }

        alts = stage.get("alternatives", [])
        alt_items: list[str] = []
        for i, alt in enumerate(alts):
            aid = f"{sid}-alt-{i}"
            detail = alt.get("detail") or f"<p>{alt.get('tooltip', '')}</p>"
            details_map[aid] = {"title": alt["label"], "html": detail}
            alt_items.append(_alt_html(alt, aid))

        dropdown = ""
        if alt_items:
            dropdown = f'<div class="pipeline-alts-dropdown">{"".join(alt_items)}</div>'

        stages_html.append(
            f'<div class="pipeline-stage-wrap">'
            f'<div class="pipeline-stage pipeline-stage--core" tabindex="0" '
            f'data-detail-id="{core_id}">'
            f'<div class="pipeline-stage-id">{html.escape(stage["id"])}</div>'
            f'<div class="pipeline-stage-title">{html.escape(stage["title"])}</div>'
            f'<div class="pipeline-stage-chosen">{html.escape(stage["chosen"])}</div>'
            f'<div class="pipeline-stage-summary">{html.escape(stage.get("summary", ""))}</div>'
            f"</div>"
            f"{dropdown}"
            f"</div>"
        )

    track = "".join(stages_html)
    details_json = json.dumps(details_map).replace("</", "<\\/")
    return (
        f'<section id="pipeline-interactive" class="pipeline-interactive">'
        f"<h2>Interactive pipeline</h2>"
        f'<p class="pipeline-hint">Hover a step to open alternatives we did not choose. '
        f"Hover an alternative or the step itself to read details below. "
        f'Click a step to pin its details.</p>'
        f'<div class="pipeline-track">{track}</div>'
        f'<div class="pipeline-detail-strip" aria-live="polite">'
        f'<div class="pipeline-detail-strip-title">Select a step</div>'
        f'<div class="pipeline-detail-strip-body">'
        f"<p>Move the pointer over any stage to see where your data came from, "
        f"how retrieval and generation work, and what alternatives exist.</p>"
        f"</div></div>"
        f'<script type="application/json" id="pipeline-details-data">{details_json}</script>'
        f"</section>"
    )


def sync_readme() -> None:
    header = (DOCS / "README_HEADER.md").read_text(encoding="utf-8")
    arch = (DOCS / "ARCHITECTURE.md").read_text(encoding="utf-8")
    arch = arch.replace(PIPELINE_MARKER, "")
    (ROOT / "README.md").write_text(header + "\n" + arch, encoding="utf-8")
    print("Wrote README.md")


def sync_architecture_html() -> None:
    arch = (DOCS / "ARCHITECTURE.md").read_text(encoding="utf-8")
    interactive = _render_interactive_pipeline()
    if PIPELINE_MARKER in arch:
        before, _, after = arch.partition(PIPELINE_MARKER)
        body = md_to_html_body(before) + interactive + md_to_html_body(after)
    else:
        body = md_to_html_body(arch)

    page = _head("PoE Wiki Agent — Architecture", architecture=True) + body + HTML_FOOT
    (DOCS / "architecture.html").write_text(page, encoding="utf-8")
    print("Wrote docs/architecture.html")


def sync_changelog_html() -> None:
    cl = (DOCS / "CHANGELOG.md").read_text(encoding="utf-8")
    articles: list[str] = []
    for block in re.split(r"\n## ", cl.strip()):
        if not block.strip():
            continue
        lines = block.strip().split("\n", 1)
        heading = lines[0]
        body = lines[1].strip() if len(lines) > 1 else ""
        date_match = re.match(r"(\d{4}-\d{2}-\d{2})\s+—\s+(.+)", heading)
        if date_match:
            dt, title = date_match.groups()
            body_html = _render_changelog_body(body)
            articles.append(
                f'<article><time datetime="{dt}">{dt}</time>'
                f"<h3>{html.escape(title)}</h3>{body_html}</article>"
            )
    inner = (
        "<h1>Changelog</h1>"
        "<p>Newest first. Source: <code>docs/CHANGELOG.md</code>. "
        "Use <code>Label — description</code> bullets when adding entries.</p>\n"
        + "\n".join(articles)
    )
    page = _head("PoE Wiki Agent — Changelog") + inner + HTML_FOOT
    (DOCS / "changelog.html").write_text(page, encoding="utf-8")
    print("Wrote docs/changelog.html")


def main() -> None:
    sync_readme()
    sync_architecture_html()
    sync_changelog_html()
    print("Done.")


if __name__ == "__main__":
    main()
