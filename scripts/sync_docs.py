#!/usr/bin/env python3
"""Sync architecture docs and changelog to README and HTML."""

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
    :root {
      --font-display: "Cinzel Decorative", "Cinzel", Georgia, serif;
      --font-heading: "Cinzel", Georgia, serif;
      --font-body: "EB Garamond", Georgia, "Times New Roman", serif;
      --font-bump: 0pt;
      --poe-gold-light: #e8d48a;
      --poe-panel-border: #4a4030;
      --poe-text: #e8dcc4;
      --poe-text-muted: #a89f8c;
      --poe-link: #d4b86a;
    }
    body {
      font-family: var(--font-body);
      font-size: calc(1rem + var(--font-bump));
      max-width: 960px;
      margin: 2rem auto;
      padding: 0 1rem 2rem;
      line-height: 1.6;
      color: var(--poe-text);
      background: #0a0908;
    }
    h1, h2, h3, h4 { font-family: var(--font-heading); color: var(--poe-gold-light); font-weight: 600; }
    h1 { font-family: var(--font-display); font-size: calc(1.75rem + var(--font-bump)); }
    p, li { color: var(--poe-text); }
    table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
    th, td { border: 1px solid var(--poe-panel-border); padding: 0.5rem 0.75rem; text-align: left; vertical-align: top; }
    th { background: rgba(0, 0, 0, 0.4); color: var(--poe-gold-light); font-family: var(--font-heading); }
    code { background: rgba(255, 255, 255, 0.08); color: var(--poe-gold-light); padding: 0.1em 0.3em; border-radius: 3px; }
    pre { background: rgba(0, 0, 0, 0.45); color: var(--poe-text); padding: 1rem; overflow-x: auto; border: 1px solid var(--poe-panel-border); border-radius: 6px; }
    nav.docs-nav {
      display: flex;
      align-items: center;
      flex-wrap: wrap;
      gap: 0.65rem 1rem;
      margin-bottom: 1.5rem;
      padding: 0.75rem 1rem;
      background: rgba(10, 9, 8, 0.94);
      border: 1px solid var(--poe-panel-border);
      border-radius: 6px;
    }
    nav.docs-nav a:not(.nav-home-btn) {
      font-family: var(--font-heading);
      color: var(--poe-link);
      text-decoration: none;
    }
    nav.docs-nav a:not(.nav-home-btn):hover {
      color: var(--poe-gold-light);
      text-decoration: underline;
    }
    a.nav-home-btn {
      order: -1;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 2.35rem;
      height: 2.35rem;
      margin-right: 0.15rem;
      border: 1px solid var(--poe-panel-border);
      border-radius: 4px;
      background: rgba(0, 0, 0, 0.4);
      color: var(--poe-gold-light);
      text-decoration: none;
      flex-shrink: 0;
    }
    a.nav-home-btn:hover {
      border-color: var(--poe-gold-light);
      color: var(--poe-gold-light);
      text-decoration: none;
      background: rgba(92, 74, 32, 0.35);
    }
    a.nav-home-btn svg {
      width: 1.15rem;
      height: 1.15rem;
      fill: currentColor;
    }
    a { color: var(--poe-link); }
    a:hover { color: var(--poe-gold-light); }
    article { border-left: 4px solid #8b7028; padding-left: 1rem; margin-bottom: 2rem; }
    time { color: var(--poe-text-muted); font-size: calc(0.9rem + var(--font-bump)); display: block; margin-bottom: 0.25rem; font-family: var(--font-heading); }
    article h3 { margin-top: 0.25rem; }
    article ul { margin: 0.5rem 0 0 1.1rem; padding: 0; }
    article li { margin: 0.35rem 0; }
    .changelog-label { font-family: var(--font-heading); font-weight: 600; color: var(--poe-gold-light); }
    pre.mermaid { background: transparent; border: none; padding: 0.5rem 0; overflow-x: auto; text-align: center; }
    .mermaid { margin: 1.5rem 0; }
    .pipeline-interactive { margin-top: 0.35rem; }
    em { color: var(--poe-text-muted); }
    details { background: rgba(0, 0, 0, 0.35); border: 1px solid var(--poe-panel-border); border-radius: 6px; padding: 0.5rem 0.75rem; }
    details summary { font-family: var(--font-heading); color: var(--poe-gold-light); cursor: pointer; }
"""

ARCH_EXTRA_STYLES = """
    :root { --font-bump: 1pt; }
    body { max-width: 1100px; }
"""

HTML_HEAD_BASE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link
    href="https://fonts.googleapis.com/css2?family=Cinzel+Decorative:wght@700&family=Cinzel:wght@400;600&family=EB+Garamond:ital,wght@0,400;0,600;1,400&display=swap"
    rel="stylesheet"
  />
  <style>
{styles}
  </style>
{extra_head}
  <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
    mermaid.initialize({{ startOnLoad: true, theme: 'dark' }});
  </script>
</head>
<body>
  <nav class="docs-nav" aria-label="Documentation">
    <a href="/" class="nav-home-btn" title="Back to Siosa's Library" aria-label="Back to app">
      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8h5z"/></svg>
    </a>
    <a href="/docs/architecture.html">Architecture</a>
    <a href="/docs/changelog.html">Changelog</a>
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
    dev = (DOCS / "ARCHITECTURE_DEVELOPER.md").read_text(encoding="utf-8").strip()
    if "## License" in header:
        before, _, license_part = header.partition("## License")
        text = (
            before.rstrip()
            + "\n\n---\n\n"
            + dev
            + "\n\n---\n\n## License"
            + license_part
        )
    else:
        text = header.rstrip() + "\n\n---\n\n" + dev
    (ROOT / "README.md").write_text(text.rstrip() + "\n", encoding="utf-8")
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
