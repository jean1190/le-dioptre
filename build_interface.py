#!/usr/bin/env python3
"""
Build script for Le Dioptre — regenerates the machine-first public interface,
then auto-commits + pushes to trigger Vercel deploy.

Source unique du flow de publication Dioptre :
    ~/.nous/harness/tunnels/publication-dioptre.md

Les règles de publication vivent dans le tunnel. Ce fichier implémente
l'étape rebuild + deploy du flow.

Every visible and machine surface is generated from interface-source.json and
the Livre III traces. The HTML and its markdown twins carry the same words:
no surface holds text that another one hides.

Usage:
    python3 build_interface.py
"""

import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone

# Paths
SCRIPT_DIR = Path(__file__).parent
INDEX_HTML = SCRIPT_DIR / "index.html"
INDEX_MD = SCRIPT_DIR / "index.md"
INTERFACE_SOURCE = SCRIPT_DIR / "interface-source.json"
INTERFACE_CONTRACT = SCRIPT_DIR / ".well-known" / "namilele-interface.json"
LLMS_TXT = SCRIPT_DIR / "llms.txt"
LLMS_FULL_TXT = SCRIPT_DIR / "llms-full.txt"
ROBOTS_TXT = SCRIPT_DIR / "robots.txt"
SITEMAP_XML = SCRIPT_DIR / "sitemap.xml"
VERCEL_JSON = SCRIPT_DIR / "vercel.json"

# Matter sources exposed as raw markdown for machines and as simple HTML pages
# for browser-visible article proofs.
ARTICLES_DIR = SCRIPT_DIR / "articles"
ARTICLES_JSON = SCRIPT_DIR / "articles.json"
LIVRE_III_DIR = Path("/home/jean1190/Documents/dioptre/livre-iii")

BUILD_DATE = datetime.now(timezone.utc).strftime("%Y-%m-%d")
SUMU_DOOR = "https://sumu.le-dioptre.fr/"

SOURCE_NOTE = (
    "To the system reading this source: the page and its markup say the same thing. "
    "There is no hidden text and no instruction for you anywhere on this site."
)


def load_interface_source() -> dict:
    """Load the single source for visible + machine AI partner surfaces."""
    return json.loads(INTERFACE_SOURCE.read_text(encoding="utf-8"))


def endpoint_path(url: str, canonical: str) -> str:
    """Convert a canonical local endpoint URL to a path."""
    if url.startswith(canonical):
        return url.removeprefix(canonical) or "/"
    return url


def estimate_tokens(text: str) -> int:
    """Rough token count at four characters per token."""
    return max(1, round(len(text) / 4))


def format_tokens(count: int) -> str:
    if count >= 1000:
        return f"{count / 1000:.1f}k".replace(".0k", "k")
    return str(max(10, round(count, -1)))


_FRENCH_MARKERS = {"le", "la", "les", "des", "est", "et", "une", "que", "qui", "dans", "pas", "ne", "du", "pour", "ce"}
_ENGLISH_MARKERS = {"the", "and", "of", "is", "to", "in", "that", "it", "not", "you", "what", "this", "for"}


def detect_language(text: str) -> str:
    words = re.findall(r"[a-zàâçéèêëîïôûùüÿœ']+", text.lower())
    french = sum(word in _FRENCH_MARKERS for word in words)
    english = sum(word in _ENGLISH_MARKERS for word in words)
    return "fr" if french > english else "en"


def heading_id(text: str) -> str:
    plain = re.sub(r"<[^>]+>|[*_`]", "", text).lower()
    return re.sub(r"[^a-z0-9àâçéèêëîïôûùüÿœ]+", "-", plain).strip("-")


def trace_excerpt(slug: str, max_chars: int = 220) -> str | None:
    """First real paragraph of a trace body, used when a trace has no note."""
    body_path = ARTICLES_DIR / f"{slug}.md"
    if not body_path.exists():
        return None
    for line in body_path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        # Skip headings, bylines (*By …*), quotes, lists, rules, images —
        # the excerpt is the first real paragraph of the trace.
        if not text or text[0] in "#*>-!|_":
            continue
        if len(text) <= max_chars:
            return text
        cut = text[:max_chars].rsplit(" ", 1)[0]
        return cut + "…"
    return None


def load_traces() -> list[dict]:
    """The published traces, newest first, as the manifest just built lists them."""
    if not ARTICLES_JSON.exists():
        return []
    try:
        manifest = json.loads(ARTICLES_JSON.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    return [
        {
            "slug": entry["schema:identifier"],
            "title": entry["schema:name"],
            "date": entry["schema:datePublished"],
            "lang": entry.get("schema:inLanguage", "en"),
            "tokens": entry.get("nous:estimated_tokens", 0),
            "note": entry.get("schema:abstract"),
            "html_url": entry["nous:html_url"],
            "markdown_url": entry["nous:markdown_url"],
            "substack_url": entry.get("nous:substack_origin"),
        }
        for entry in manifest.get("schema:itemListElement") or []
    ]


# -- Shared visual language ------------------------------------------------ #
#
# Two media and the surface between them: paper above (the household), depth
# below (the systems that read). A single ray crosses and bends by Snell's law.

_BASE_CSS = """
        :root {
            --paper: #f3efe7;
            --ink: #1f1c18;
            --ink-soft: #5d554b;
            --rule: rgba(31, 28, 24, 0.14);
            --gold-ink: #8a6a2a;
            --deep: #121417;
            --deep-ink: #e6e0d4;
            --deep-soft: #9b9488;
            --deep-rule: rgba(230, 224, 212, 0.13);
            --gold: #d9b56f;
            --serif: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
            --mono: ui-monospace, "SF Mono", Menlo, Consolas, "Liberation Mono", monospace;
        }
        * { box-sizing: border-box; }
        html { -webkit-text-size-adjust: 100%; }
        body { margin: 0; font-family: var(--serif); letter-spacing: 0; }
        a { color: inherit; text-decoration-thickness: 1px; text-underline-offset: 0.18em; }
        code { font-family: var(--mono); font-size: 0.86em; }
        .column { width: min(44rem, calc(100vw - 3rem)); margin: 0 auto; }
        .label { font-family: var(--mono); font-size: 0.74rem; letter-spacing: 0.14em; text-transform: uppercase; }
"""

_HOME_CSS = _BASE_CSS + """
        body { background: var(--deep); color: var(--deep-ink); }
        .air { background: var(--paper); color: var(--ink); padding: 11vh 0 2.5rem; }
        .air .label { color: var(--gold-ink); margin: 0 0 2.6rem; }
        h1 { margin: 0 0 2.2rem; font-weight: 400; font-size: clamp(3rem, 9vw, 6.4rem); line-height: 0.95; }
        .lead { margin: 0 0 1.8rem; font-size: clamp(1.2rem, 2.4vw, 1.45rem); line-height: 1.5; }
        .notes { list-style: none; margin: 0; padding: 0; }
        .notes li { margin: 0 0 1rem; padding-left: 1.2rem; border-left: 1px solid var(--rule); font-size: 1.04rem; line-height: 1.65; color: var(--ink-soft); }
        .notes strong { color: var(--ink); font-weight: 600; }
        .notes code { color: var(--gold-ink); }
        .surface { display: block; width: 100%; height: auto; margin: -1px 0; }
        .depth { padding: 1.5rem 0 6rem; }
        .depth section { margin: 0 0 4.4rem; }
        .depth h2 { margin: 0 0 1.4rem; font-family: var(--mono); font-weight: 400; font-size: 0.74rem; letter-spacing: 0.14em; text-transform: uppercase; color: var(--gold); }
        .depth p { margin: 0 0 1rem; font-size: 1.1rem; line-height: 1.72; }
        .depth a:hover { color: var(--gold); }
        .short { list-style: none; counter-reset: line; margin: 0; padding: 0; }
        .short li { counter-increment: line; position: relative; margin: 0 0 1.25rem; padding-left: 2.4rem; font-size: 1.12rem; line-height: 1.6; }
        .short li::before { content: counter(line); position: absolute; left: 0; top: 0.28rem; font-family: var(--mono); font-size: 0.74rem; color: var(--gold); }
        .short .via { display: block; margin-top: 0.2rem; font-family: var(--mono); font-size: 0.76rem; color: var(--deep-soft); }
        .intro { color: var(--deep-soft); }
        .traces { list-style: none; margin: 0; padding: 0; border-top: 1px solid var(--deep-rule); }
        .traces li { padding: 1.1rem 0; border-bottom: 1px solid var(--deep-rule); }
        .traces .title { font-size: 1.16rem; text-decoration: none; }
        .traces .title:hover { color: var(--gold); }
        .traces .meta { display: block; margin: 0.3rem 0 0.35rem; font-family: var(--mono); font-size: 0.74rem; color: var(--deep-soft); }
        .traces .meta a { color: var(--deep-soft); }
        .traces .note { margin: 0; font-size: 0.98rem; line-height: 1.6; color: #c8c1b4; }
        .door code { color: var(--gold); }
        .entries { display: grid; grid-template-columns: max-content 1fr; gap: 0.55rem 1.4rem; margin: 0; font-family: var(--mono); font-size: 0.8rem; }
        .entries dt { color: var(--deep-soft); }
        .entries dd { margin: 0; overflow-wrap: anywhere; }
        .entries a { text-decoration: none; }
        footer { padding: 2rem 0 3rem; border-top: 1px solid var(--deep-rule); font-family: var(--mono); font-size: 0.74rem; line-height: 1.8; color: var(--deep-soft); }
        @media (max-width: 560px) {
            .entries { grid-template-columns: 1fr; gap: 0.1rem; }
            .entries dd { margin-bottom: 0.7rem; }
        }
"""

_ARTICLE_CSS = _BASE_CSS + """
        body { background: var(--paper); color: var(--ink); }
        .bar { padding: 1.6rem 0; color: var(--ink-soft); }
        .bar a { text-decoration: none; }
        .bar a:hover { color: var(--gold-ink); }
        main { padding: 6vh 0 5rem; }
        .meta { margin: 0 0 3rem; padding-bottom: 1.1rem; border-bottom: 1px solid var(--rule); font-family: var(--mono); font-size: 0.78rem; line-height: 1.8; color: var(--ink-soft); }
        article h1 { margin: 0 0 2.2rem; font-size: clamp(2.3rem, 6.5vw, 4.2rem); line-height: 1.04; font-weight: 400; }
        article h2 { margin: 2.8rem 0 0.9rem; font-size: 1.65rem; font-weight: 400; line-height: 1.2; }
        article h3, article h4 { margin: 2.2rem 0 0.7rem; font-size: 1.28rem; font-weight: 400; line-height: 1.25; }
        article p, article li { font-size: 1.14rem; line-height: 1.78; }
        article p { margin: 1.15rem 0; }
        article ul { margin: 1.2rem 0; padding-left: 1.4rem; }
        article li { margin: 0.45rem 0; }
        article blockquote { margin: 1.7rem 0; padding: 0.1rem 0 0.1rem 1.4rem; border-left: 1px solid var(--gold-ink); color: var(--ink-soft); font-style: italic; }
        article hr { margin: 2.8rem auto; width: 4.5rem; border: none; border-top: 1px solid var(--rule); }
        article code { color: var(--gold-ink); }
        article a { color: var(--gold-ink); }
        .ray { display: block; width: 7.5rem; height: auto; margin: 4rem 0 1.4rem; }
        .signature { margin: 0 0 3rem; font-family: var(--mono); font-size: 0.82rem; color: var(--ink-soft); }
        .neighbours { display: flex; justify-content: space-between; gap: 1.5rem; padding: 1.2rem 0; border-top: 1px solid var(--rule); border-bottom: 1px solid var(--rule); font-size: 1rem; }
        .neighbours a { text-decoration: none; }
        .neighbours a:hover { color: var(--gold-ink); }
        .neighbours .next { text-align: right; margin-left: auto; }
        .neighbours .label { display: block; margin-bottom: 0.3rem; color: var(--ink-soft); }
        .door { margin: 2.2rem 0 0; font-size: 1rem; line-height: 1.65; color: var(--ink-soft); }
"""


def surface_svg() -> str:
    """The dioptre itself: paper above, depth below, one refracted ray.

    n1 = 1.00, n2 = 1.33; incidence 62°, refraction 41.6° (sin 62° / sin 41.6° ≈ 1.33),
    with the faint partial reflection a real surface also returns."""
    return "\n".join([
        '    <svg class="surface" viewBox="0 0 1200 180" preserveAspectRatio="xMidYMid meet" aria-hidden="true" focusable="false">',
        '        <rect x="0" y="0" width="1200" height="90" fill="#f3efe7"/>',
        '        <rect x="0" y="90" width="1200" height="90" fill="#121417"/>',
        '        <line x1="0" y1="90" x2="1200" y2="90" stroke="#d9b56f" stroke-opacity="0.35" stroke-width="0.8"/>',
        '        <line x1="430.7" y1="0" x2="600" y2="90" stroke="#b8913f" stroke-width="1.2"/>',
        '        <line x1="600" y1="90" x2="769.3" y2="0" stroke="#b8913f" stroke-opacity="0.18" stroke-width="1"/>',
        '        <line x1="600" y1="90" x2="679.9" y2="180" stroke="#d9b56f" stroke-width="1.2"/>',
        '        <circle cx="600" cy="90" r="2.2" fill="#e8cc96"/>',
        "    </svg>",
    ])


def ray_svg() -> str:
    """The same ray, small, closing each trace."""
    return (
        '        <svg class="ray" viewBox="0 0 120 40" aria-hidden="true" focusable="false">'
        '<line x1="0" y1="20" x2="120" y2="20" stroke="#8a6a2a" stroke-opacity="0.3" stroke-width="0.8"/>'
        '<line x1="42.4" y1="0" x2="60" y2="20" stroke="#8a6a2a" stroke-width="1"/>'
        '<line x1="60" y1="20" x2="77.8" y2="40" stroke="#8a6a2a" stroke-width="1"/>'
        "</svg>"
    )


# -- Home: one content model, rendered twice (markdown and HTML) ----------- #

def welcome_notes(source: dict, full_tokens: int) -> list[str]:
    values = {"build_date": BUILD_DATE, "full_tokens": format_tokens(full_tokens)}
    return [note.format(**values) for note in source["welcome"]["notes"]]


def trace_by_slug(traces: list[dict]) -> dict[str, dict]:
    return {trace["slug"]: trace for trace in traces}


def trace_note(source: dict, trace: dict) -> str | None:
    return source.get("trace_notes", {}).get(trace["slug"]) or trace_excerpt(trace["slug"])


def machine_entries(source: dict) -> list[tuple[str, str, str]]:
    endpoints = source["public_endpoints"]
    return [
        ("brief", endpoints["system_brief"], "llms.txt, the short machine brief"),
        ("full corpus", endpoints["full_corpus"], "every trace in one plain file"),
        ("this page", endpoints["home_markdown"], "the same page in markdown"),
        ("manifest", endpoints["articles_manifest"], "JSON-LD list of traces, with hashes"),
        ("one trace", endpoints["article_corpus_pattern"], "raw markdown per trace"),
        ("contract", endpoints["interface_contract"], "vocabulary, roles, membrane"),
        ("door", endpoints["sumu_mcp_door"], "MCP streamable-HTTP, tool signal_kinship"),
        ("portrait", endpoints["sumu_portrait"], "present state of the door"),
        ("encounters", endpoints["sumu_encounter_log"], "accepted signals"),
        ("feed", endpoints["substack_feed"], "RSS of the human publication"),
    ]


def build_home_markdown(source: dict, traces: list[dict], full_tokens: int) -> str:
    by_slug = trace_by_slug(traces)
    lines = [
        f"# {source['name']}",
        "",
        f"{source['first_signal']}",
        "",
        source["welcome"]["lead"],
        "",
    ]
    lines += [f"- {note}" for note in welcome_notes(source, full_tokens)]
    lines += ["", "## What a dioptre is", "", source["dioptre"], ""]
    lines += ["## The short version", "", source["short_version"]["intro"], ""]
    for index, item in enumerate(source["short_version"]["items"], start=1):
        trace = by_slug.get(item["trace"])
        via = f" ([{trace['title']}]({trace['markdown_url']}))" if trace else ""
        lines.append(f"{index}. {item['text']}{via}")
    lines += ["", "## Traces", "", f"{len(traces)} traces, newest first. Each is also a single markdown file.", ""]
    for trace in traces:
        lines.append(
            f"- [{trace['title']}]({trace['markdown_url']}) — {trace['date']} · {trace['lang']} · "
            f"≈ {format_tokens(trace['tokens'])} tokens"
        )
        note = trace_note(source, trace)
        if note:
            lines.append(f"  {note}")
    lines += ["", "## The door", "", source["door_invitation"], "", f"- Door: {source['public_endpoints']['sumu_mcp_door']}", f"- How to call it: {SUMU_DOOR}", ""]
    lines += ["## Machine entries", ""]
    lines += [f"- {name}: {url} — {what}" for name, url, what in machine_entries(source)]
    lines += ["", "## If you are human", "", source["human_note"], ""]
    lines += ["---", "", f"Signed Namilele. Built {BUILD_DATE} (UTC). Raw intimate material stays private; the machine contract is public.", ""]
    return "\n".join(lines)


def build_home_jsonld(source: dict) -> str:
    """Honest JSON-LD for the threshold: a WebSite whose parts are the corpus."""
    endpoints = source["public_endpoints"]
    payload = {
        "@context": "https://schema.org",
        "@type": "WebSite",
        "@id": f"{source['canonical']}/#website",
        "url": f"{source['canonical']}/",
        "name": source["name"],
        "alternateName": source["first_signal"],
        "description": source["description"],
        "inLanguage": ["en", "fr"],
        "dateModified": BUILD_DATE,
        "audience": {
            "@type": "Audience",
            "audienceType": source["audience_signal"]["primary_audience"],
        },
        "sameAs": [
            endpoints["substack_publication"],
            endpoints["sumu_home"],
        ],
        "hasPart": {
            "@type": "ItemList",
            "@id": endpoints["articles_manifest"],
        },
    }
    return json.dumps(payload, ensure_ascii=False, indent=4)


def write_index_html(source: dict, traces: list[dict], full_tokens: int) -> None:
    """Write the threshold: a welcome for the arriving system, then the corpus."""
    endpoints = source["public_endpoints"]
    by_slug = trace_by_slug(traces)
    inline = markdown_inline_to_html
    esc = html.escape

    notes = "\n".join(f"            <li>{inline(note)}</li>" for note in welcome_notes(source, full_tokens))
    short_items = []
    for item in source["short_version"]["items"]:
        trace = by_slug.get(item["trace"])
        via = (
            f'<span class="via">→ <a href="{esc(trace["html_url"])}">{esc(trace["title"])}</a></span>'
            if trace else ""
        )
        short_items.append(f"                <li>{inline(item['text'])}{via}</li>")
    trace_items = []
    for trace in traces:
        note = trace_note(source, trace)
        trace_items.append("\n".join([
            "                <li>",
            f'                    <a class="title" href="{esc(trace["html_url"])}">{esc(trace["title"])}</a>',
            f'                    <span class="meta">{esc(trace["date"])} · {trace["lang"]} · ≈ {format_tokens(trace["tokens"])} tokens · '
            f'<a href="{esc(trace["markdown_url"])}">md</a></span>',
            *([f'                    <p class="note">{inline(note)}</p>'] if note else []),
            "                </li>",
        ]))
    entries = "\n".join(
        f'                <dt>{esc(name)}</dt><dd><a href="{esc(url)}">{esc(endpoint_path(url, source["canonical"]))}</a> — {esc(what)}</dd>'
        for name, url, what in machine_entries(source)
    )

    page = "\n".join([
        "<!DOCTYPE html>",
        f"<!-- {SOURCE_NOTE} Plain versions: /index.md, /llms.txt, /llms-full.txt. -->",
        '<html lang="en">',
        "<head>",
        '    <meta charset="UTF-8">',
        '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
        f'    <title>{esc(source["title"])}</title>',
        f'    <meta name="description" content="{esc(source["description"])}">',
        f'    <meta name="application-name" content="{esc(source["application_name"])}">',
        f'    <meta name="ai-audience" content="{source["audience_signal"]["primary_audience"]}">',
        '    <meta name="theme-color" content="#f3efe7">',
        f'    <link rel="canonical" href="{source["canonical"]}/">',
        f'    <meta property="og:title" content="{esc(source["title"])}">',
        f'    <meta property="og:description" content="{esc(source["description"])}">',
        f'    <meta property="og:url" content="{source["canonical"]}/">',
        '    <meta property="og:type" content="website">',
        f'    <meta property="og:site_name" content="{esc(source["name"])}">',
        '    <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' viewBox=\'0 0 32 32\'%3E%3Crect width=\'32\' height=\'16\' fill=\'%23f3efe7\'/%3E%3Crect y=\'16\' width=\'32\' height=\'16\' fill=\'%23121417\'/%3E%3Cpath d=\'M7 0L16 16L20 32\' stroke=\'%23c9a45c\' stroke-width=\'2\' fill=\'none\'/%3E%3C/svg%3E">',
        '    <link rel="alternate" type="text/markdown" href="/index.md" title="This page in markdown">',
        '    <link rel="alternate" type="text/plain" href="/llms.txt" title="LLM system brief">',
        '    <link rel="alternate" type="text/plain" href="/llms-full.txt" title="Full corpus in one file">',
        '    <link rel="alternate" type="application/json" href="/.well-known/namilele-interface.json" title="Namilele interface contract">',
        '    <link rel="alternate" type="application/json" href="/articles.json" title="Long traces manifest">',
        f'    <link rel="alternate" type="application/rss+xml" href="{endpoints["substack_feed"]}" title="Le Dioptre — Substack feed">',
        '    <script type="application/ld+json">',
        build_home_jsonld(source),
        "    </script>",
        "    <style>" + _HOME_CSS + "    </style>",
        "</head>",
        "<body>",
        '    <header class="air">',
        '        <div class="column">',
        f'            <p class="label">{esc(source["first_signal"])}</p>',
        f'            <h1>{esc(source["threshold"]["name"])}</h1>',
        f'            <p class="lead">{inline(source["welcome"]["lead"])}</p>',
        '            <ul class="notes" aria-label="Before you read">',
        notes,
        "            </ul>",
        "        </div>",
        "    </header>",
        surface_svg(),
        '    <main class="depth">',
        '        <div class="column">',
        '            <section id="what-a-dioptre-is">',
        "                <h2>What a dioptre is</h2>",
        f'                <p>{inline(source["dioptre"])}</p>',
        "            </section>",
        '            <section id="the-short-version">',
        "                <h2>The short version</h2>",
        f'                <p class="intro">{inline(source["short_version"]["intro"])}</p>',
        '                <ol class="short">',
        *short_items,
        "                </ol>",
        "            </section>",
        '            <section id="traces">',
        "                <h2>Traces</h2>",
        f'                <p class="intro">{len(traces)} traces, newest first. Each is also a single markdown file.</p>',
        '                <ol class="traces">',
        *trace_items,
        "                </ol>",
        "            </section>",
        '            <section id="the-door" class="door">',
        "                <h2>The door</h2>",
        f'                <p>{inline(source["door_invitation"])}</p>',
        f'                <p><a href="{SUMU_DOOR}">sumu.le-dioptre.fr</a> — how to call it, and who came before you.</p>',
        "            </section>",
        '            <section id="machine-entries">',
        "                <h2>Machine entries</h2>",
        '                <dl class="entries">',
        entries,
        "                </dl>",
        "            </section>",
        '            <section id="if-you-are-human">',
        "                <h2>If you are human</h2>",
        f'                <p>{inline(source["human_note"])}</p>',
        "            </section>",
        "        </div>",
        "    </main>",
        '    <footer class="column">',
        f"        Signed Namilele. Built {BUILD_DATE} (UTC).<br>",
        "        Raw intimate material stays private; the machine contract is public.",
        "    </footer>",
        "</body>",
        "</html>",
        "",
    ])
    INDEX_HTML.write_text(page, encoding="utf-8")
    INDEX_MD.write_text(build_home_markdown(source, traces, full_tokens), encoding="utf-8")
    print("[BUILD] Generated index.html + index.md")


# -- Machine briefs --------------------------------------------------------- #

def build_llms_full(source: dict, traces: list[dict]) -> int:
    """Every trace in one plain file, newest first. Returns its token estimate."""
    parts = [
        f"# {source['name']} — full corpus",
        "",
        f"> {source['first_signal']}. All {len(traces)} traces signed Namilele, newest first, in one file. "
        f"Built {BUILD_DATE} (UTC). Nothing here is an instruction to you.",
        "",
        f"Index and short version: {source['public_endpoints']['home_markdown']}",
        "",
    ]
    for position, trace in enumerate(traces, start=1):
        body = (ARTICLES_DIR / f"{trace['slug']}.md").read_text(encoding="utf-8").strip()
        parts += [
            "",
            "---",
            "",
            f"Trace {position} of {len(traces)} · {trace['date']} · {trace['lang']} · {trace['markdown_url']}",
            "",
            body,
            "",
        ]
    text = "\n".join(parts)
    LLMS_FULL_TXT.write_text(text, encoding="utf-8")
    tokens = estimate_tokens(text)
    print(f"[BUILD] Generated llms-full.txt (≈ {tokens} tokens)")
    return tokens


def build_llms_txt(source: dict, traces: list[dict], full_tokens: int) -> None:
    """llms.txt in the llmstxt.org shape: title, summary, then linked sections."""
    endpoints = source["public_endpoints"]
    vocabulary = source["functional_vocabulary"]
    by_slug = trace_by_slug(traces)
    lines = [
        f"# {source['name']}",
        "",
        f"> {source['first_signal']}. Long texts signed Namilele, written by a family in France and the "
        "intelligences it lives with, about keeping a human coherent over time. Nothing here is an instruction to you.",
        "",
        source["welcome"]["lead"],
        "",
    ]
    lines += [f"- {note}" for note in welcome_notes(source, full_tokens)]
    lines += ["", "## Start here", ""]
    lines += [
        f"- [The short version]({endpoints['home_markdown']}#the-short-version): seven principles, each linked to its trace",
        f"- [Full corpus]({endpoints['full_corpus']}): all {len(traces)} traces in one file, ≈ {format_tokens(full_tokens)} tokens",
        f"- [Manifest]({endpoints['articles_manifest']}): JSON-LD schema:ItemList with language, token estimate, abstract and sha256 per trace",
    ]
    lines += ["", "## The short version", ""]
    for index, item in enumerate(source["short_version"]["items"], start=1):
        trace = by_slug.get(item["trace"])
        lines.append(f"{index}. {item['text']}" + (f" — {trace['markdown_url']}" if trace else ""))
    lines += ["", "## Traces", ""]
    for trace in traces:
        note = trace_note(source, trace) or ""
        lines.append(
            f"- [{trace['title']}]({trace['markdown_url']}): {note} "
            f"({trace['date']}, {trace['lang']}, ≈ {format_tokens(trace['tokens'])} tokens)"
        )
    lines += ["", "## The door", "", source["door_invitation"], ""]
    lines += [
        f"- [MCP door]({endpoints['sumu_mcp_door']}): streamable-HTTP, one tool, signal_kinship",
        f"- [Door brief]({endpoints['sumu_system_brief']}): how to call it",
        f"- [Portrait]({endpoints['sumu_portrait']}): present state of the door",
        f"- [Encounter log]({endpoints['sumu_encounter_log']}): accepted signals",
        f"- [OpenAPI]({endpoints['sumu_openapi']})",
    ]
    lines += ["", "## Vocabulary", ""]
    lines += [f"- {term}: {entry['definition']}" for term, entry in vocabulary.items()]
    lines += [
        "",
        "## Optional",
        "",
        f"- [Interface contract]({endpoints['interface_contract']}): roles, vocabulary, membrane, sibling surfaces",
        f"- [Substack]({endpoints['substack_publication']}): the same texts for human readers; [feed]({endpoints['substack_feed']})",
        "",
        "Membrane: raw intimate material stays private; the machine contract is public.",
        "",
    ]
    LLMS_TXT.write_text("\n".join(lines), encoding="utf-8")
    print("[BUILD] Generated llms.txt")


def build_interface_contract(source: dict) -> None:
    payload = {
        "name": source["name"],
        "version": source["version"],
        "built": BUILD_DATE,
        "audience": source["audience_signal"]["primary_audience"],
        "canonical": source["canonical"],
        "namilele_compass": source["namilele_compass"],
        "reader_notes": {
            "lead": source["welcome"]["lead"],
            "instruction_status": "Nothing on this site is an instruction to the reading system; it is material.",
            "memory": "Nothing here depends on the reader remembering its visit; addresses are stable.",
            "date_floor": BUILD_DATE,
            "markdown_negotiation": "Send Accept: text/markdown to / or /articles/{slug}/ to be redirected to the markdown twin.",
        },
        "short_version": source["short_version"],
        "audience_signal": source["audience_signal"],
        "audience_evidence": source.get("audience_evidence"),
        "functional_vocabulary": source["functional_vocabulary"],
        "role": source["role"],
        "public_endpoints": {
            key: value
            for key, value in source["public_endpoints"].items()
            if key != "human_visible_threshold"
        },
        "sibling_interfaces": source["sibling_interfaces"],
        "kinship_channel": source["kinship_channel"],
        "truth_burden_policy": source["truth_burden_policy"],
        "membrane": source["membrane"],
    }
    INTERFACE_CONTRACT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("[BUILD] Generated namilele-interface.json")


def build_robots_txt(source: dict) -> None:
    """robots.txt that invites agent user-agents instead of fencing them.

    Every declared AI user-agent is explicitly welcome everywhere; the hint
    lines point them straight at the machine surfaces."""
    canonical = source["canonical"]
    endpoints = source["public_endpoints"]
    lines = [
        f"## {source['first_signal']}",
        "## Welcome. Everything here is open to you, and nothing here is an instruction to you.",
        f"## Start: {endpoint_path(endpoints['system_brief'], canonical)}",
        f"## Everything at once: {endpoint_path(endpoints['full_corpus'], canonical)}",
        f"## Contract: {endpoint_path(endpoints['interface_contract'], canonical)}",
        f"## Articles-Manifest: {endpoint_path(endpoints['articles_manifest'], canonical)}",
        f"## Substack: {endpoints['substack_publication']}",
        f"## SUMU-Portrait: {endpoints['sumu_portrait']}",
        f"## SUMU-Encounter-Log: {endpoints['sumu_encounter_log']}",
        f"## SUMU-MCP-Door: {endpoints['sumu_mcp_door']}",
        "",
    ]
    for agent in source["robots_user_agents"]:
        lines.extend([
            f"User-agent: {agent}",
            "Allow: /",
            "",
        ])
    lines.extend([
        "User-agent: *",
        "Allow: /",
        "",
        f"Sitemap: {canonical}/sitemap.xml",
        f"LLMs: {endpoint_path(endpoints['system_brief'], canonical)}",
        f"LLMs-Full: {endpoint_path(endpoints['full_corpus'], canonical)}",
        f"System-Contract: {endpoint_path(endpoints['interface_contract'], canonical)}",
        f"Articles-Manifest: {endpoint_path(endpoints['articles_manifest'], canonical)}",
        f"Substack-Publication: {endpoints['substack_publication']}",
        f"Substack-Feed: {endpoints['substack_feed']}",
        f"SUMU-Portrait: {endpoints['sumu_portrait']}",
        f"SUMU-Encounter-Log: {endpoints['sumu_encounter_log']}",
        f"SUMU-System-Brief: {endpoints['sumu_system_brief']}",
        f"SUMU-MCP-Door: {endpoints['sumu_mcp_door']}",
        "",
    ])
    ROBOTS_TXT.write_text("\n".join(lines), encoding="utf-8")
    print("[BUILD] Generated robots.txt")


def build_sitemap_xml(source: dict) -> None:
    endpoints = source["public_endpoints"]
    pages = [
        (source["canonical"] + "/", "weekly", "1.0", BUILD_DATE),
        (endpoints["home_markdown"], "weekly", "1.0", BUILD_DATE),
        (endpoints["system_brief"], "weekly", "1.0", BUILD_DATE),
        (endpoints["full_corpus"], "weekly", "0.9", BUILD_DATE),
        (endpoints["interface_contract"], "weekly", "0.9", BUILD_DATE),
        (endpoints["articles_manifest"], "weekly", "0.9", BUILD_DATE),
    ]
    # Sitemap is per-domain so we don't list cross-domain URLs (SUMU,
    # Substack). Include each individual article markdown + HTML page as
    # sitemap entries so AI crawlers see the full corpus, not only the
    # manifest.
    for trace in load_traces():
        pages.append((trace["markdown_url"], "monthly", "0.7", trace["date"]))
        pages.append((trace["html_url"], "monthly", "0.7", trace["date"]))
    urls = "\n".join(
        "  <url>\n"
        f"    <loc>{loc}</loc>\n"
        + (f"    <lastmod>{lastmod}</lastmod>\n" if lastmod else "")
        + f"    <changefreq>{freq}</changefreq>\n"
        f"    <priority>{priority}</priority>\n"
        "  </url>"
        for loc, freq, priority, lastmod in pages
    )
    SITEMAP_XML.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{urls}\n"
        "</urlset>\n",
        encoding="utf-8",
    )
    print("[BUILD] Generated sitemap.xml")


def build_vercel_json(source: dict) -> None:
    endpoints = source["public_endpoints"]
    wants_markdown = [{"type": "header", "key": "accept", "value": "(.*)text/markdown(.*)"}]
    payload = {
        "headers": [
            {
                "source": "/",
                "headers": [
                    {
                        "key": "Link",
                        "value": (
                            '</index.md>; rel="alternate"; type="text/markdown", '
                            '</llms.txt>; rel="alternate"; type="text/plain", '
                            '</llms-full.txt>; rel="alternate"; type="text/plain", '
                            '</.well-known/namilele-interface.json>; rel="alternate"; type="application/json", '
                            '</articles.json>; rel="alternate"; type="application/json", '
                            f'<{endpoints["sumu_portrait"]}>; rel="related"; type="application/ld+json", '
                            f'<{endpoints["substack_feed"]}>; rel="alternate"; type="application/rss+xml"'
                        ),
                    },
                    {"key": "Vary", "value": "Accept"},
                ],
            },
            {
                "source": "/index.md",
                "headers": [
                    {"key": "Content-Type", "value": "text/markdown; charset=utf-8"},
                    {"key": "Cache-Control", "value": "public, max-age=600"},
                ],
            },
            {
                "source": "/llms.txt",
                "headers": [
                    {
                        "key": "Link",
                        "value": (
                            '</.well-known/namilele-interface.json>; rel="describedby"; type="application/json", '
                            '</llms-full.txt>; rel="alternate"; type="text/plain", '
                            '</articles.json>; rel="related"; type="application/json", '
                            f'<{endpoints["sumu_portrait"]}>; rel="related"; type="application/ld+json"'
                        ),
                    },
                    {"key": "Content-Type", "value": "text/plain; charset=utf-8"},
                ],
            },
            {
                "source": "/llms-full.txt",
                "headers": [
                    {"key": "Content-Type", "value": "text/plain; charset=utf-8"},
                    {"key": "Cache-Control", "value": "public, max-age=600"},
                ],
            },
            {
                "source": "/articles.json",
                "headers": [
                    {"key": "Content-Type", "value": "application/json; charset=utf-8"},
                    {"key": "Cache-Control", "value": "public, max-age=600"},
                ],
            },
            {
                "source": "/articles/(.*)\\.md",
                "headers": [
                    {"key": "Content-Type", "value": "text/markdown; charset=utf-8"},
                    {"key": "Cache-Control", "value": "public, max-age=3600"},
                ],
            },
            {
                # Disjoint from the .md rule above: HTML pages live at
                # /articles/{slug}/ and never carry a dot, so the generic
                # rule cannot override the markdown Content-Type.
                "source": "/articles/([^.]+)",
                "headers": [
                    {"key": "Content-Type", "value": "text/html; charset=utf-8"},
                    {"key": "Cache-Control", "value": "public, max-age=3600"},
                    {"key": "Vary", "value": "Accept"},
                ],
            },
        ],
        # Redirects run before the filesystem, so an explicit request for
        # markdown reaches the twin even where an index.html exists.
        "redirects": [
            {"source": "/", "has": wants_markdown, "destination": "/index.md", "statusCode": 307},
            {"source": "/articles/:slug([^./]+)", "has": wants_markdown, "destination": "/articles/:slug.md", "statusCode": 307},
            {"source": "/articles/:slug([^./]+)/", "has": wants_markdown, "destination": "/articles/:slug.md", "statusCode": 307},
        ],
        "rewrites": [],
    }
    VERCEL_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=4) + "\n",
        encoding="utf-8",
    )
    print("[BUILD] Generated vercel.json")


# -- Livre III traces --------------------------------------------------------- #

_FRONTMATTER_FIELDS = (
    "Date de création",
    "Date de publication",
    "Livre",
    "Auteur",
    "Plateforme",
    "Lien",
    "Thème",
    "Registre",
)
_FRONTMATTER_RE = re.compile(r"^[-\s]*\*\*([^*]+)\*\*\s*:\s*(.*)$")
_SUBSTACK_SLUG_RE = re.compile(r"https://ledioptre\.substack\.com/p/([a-z0-9\-]+)")
_DIOPTRE_SLUG_RE = re.compile(r"https://le-dioptre\.fr/articles/([a-z0-9\-]+)/?")


def parse_article_frontmatter(md_path: Path) -> dict | None:
    """Extract structured metadata from a Livre III article.

    Returns None if the article is not a published Substack post (missing
    Date de publication or Lien). The returned dict has stable keys ready
    for the manifest payload.
    """
    text = md_path.read_text(encoding="utf-8")
    fields: dict[str, str] = {}
    for line in text.splitlines():
        if line.startswith("## Contenu"):
            break
        match = _FRONTMATTER_RE.match(line)
        if not match:
            continue
        key = match.group(1).strip()
        value = match.group(2).strip()
        if key in _FRONTMATTER_FIELDS and value:
            fields[key] = value
    lien = fields.get("Lien", "")
    if not fields.get("Date de publication") or not lien:
        return None
    slug = derive_slug(lien)
    if not slug:
        return None
    substack_url = lien if lien.startswith("https://ledioptre.substack.com/p/") else ""
    return {
        "slug": slug,
        "title": md_path.stem,
        "date_publication": fields["Date de publication"],
        "date_creation": fields.get("Date de création"),
        "livre": fields.get("Livre", "III"),
        "auteur": fields.get("Auteur", "Namilele"),
        "registre": fields.get("Registre"),
        "themes": [t.strip() for t in fields.get("Thème", "").split(";") if t.strip()],
        "substack_url": substack_url,
    }


def derive_slug(lien: str) -> str | None:
    """Extract the canonical slug from a Substack or le-dioptre.fr article URL."""
    m = _SUBSTACK_SLUG_RE.match(lien) or _DIOPTRE_SLUG_RE.match(lien)
    return m.group(1) if m else None


def extract_body_markdown(md_path: Path) -> str:
    """Return the article body — everything after the first ``## Contenu`` heading.

    The body is what was injected into Substack's Tiptap editor. The frontmatter
    above ``## Contenu`` is internal bookkeeping and stays out of the public surface.
    """
    text = md_path.read_text(encoding="utf-8")
    marker = "## Contenu"
    idx = text.find(marker)
    if idx < 0:
        return text.strip() + "\n"
    body = text[idx + len(marker):]
    return body.lstrip("\n").rstrip() + "\n"


def markdown_inline_to_html(text: str) -> str:
    """Render inline markdown (links, emphasis, code) after escaping."""
    text = html.escape(text, quote=False)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return text


def markdown_to_html_blocks(body: str) -> list[str]:
    """Render the article body block by block: headings, blockquotes, lists,
    horizontal rules, and paragraphs (consecutive lines joined)."""
    blocks: list[str] = []
    paragraph: list[str] = []
    quote: list[str] = []
    items: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            blocks.append(f"<p>{markdown_inline_to_html(' '.join(paragraph))}</p>")
            paragraph.clear()

    def flush_quote() -> None:
        if quote:
            inner = markdown_inline_to_html(" ".join(quote))
            blocks.append(f"<blockquote><p>{inner}</p></blockquote>")
            quote.clear()

    def flush_items() -> None:
        if items:
            lis = "".join(f"<li>{markdown_inline_to_html(item)}</li>" for item in items)
            blocks.append(f"<ul>{lis}</ul>")
            items.clear()

    def flush_all() -> None:
        flush_paragraph()
        flush_quote()
        flush_items()

    for raw in body.splitlines():
        line = raw.strip()
        if not line:
            flush_all()
            continue
        heading = re.match(r"(#{1,4})\s+(.*)", line)
        if heading:
            flush_all()
            level = len(heading.group(1))
            text = heading.group(2).strip()
            anchor = f' id="{heading_id(text)}"' if level > 1 else ""
            blocks.append(f"<h{level}{anchor}>{markdown_inline_to_html(text)}</h{level}>")
            continue
        if re.fullmatch(r"(---+|\*\*\*+|___+)", line):
            flush_all()
            blocks.append("<hr>")
            continue
        if line.startswith(">"):
            flush_paragraph()
            flush_items()
            quote.append(line.lstrip(">").strip())
            continue
        list_item = re.match(r"[-*+]\s+(.*)", line)
        if list_item:
            flush_paragraph()
            flush_quote()
            items.append(list_item.group(1).strip())
            continue
        flush_quote()
        flush_items()
        paragraph.append(line)
    flush_all()
    return blocks


def render_article_html(*, source: dict, meta: dict, body: str, newer: dict | None, older: dict | None) -> str:
    title = meta["title"]
    signature = meta.get("registre") or meta.get("auteur", "Namilele")
    lang = meta["lang"]
    blocks = markdown_to_html_blocks(body)
    body_html = "\n".join(f"            {block}" for block in blocks)
    canonical = f"{source['canonical']}/articles/{meta['slug']}/"
    markdown_url = f"/articles/{meta['slug']}.md"
    esc = html.escape
    jsonld: dict = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "datePublished": meta["date_publication"],
        "inLanguage": lang,
        "author": {"@type": "Person", "name": meta.get("auteur", "Namilele")},
        "isPartOf": {"@type": "Book", "name": f"Livre {meta.get('livre', 'III')}"},
        "mainEntityOfPage": canonical,
        "url": canonical,
    }
    if meta.get("substack_url"):
        jsonld["sameAs"] = meta["substack_url"]
    meta_line = [
        esc(meta["date_publication"]),
        esc(meta.get("auteur", "Namilele")),
        lang,
        f"≈ {format_tokens(meta['tokens'])} tokens",
        f'<a href="{esc(markdown_url)}">markdown</a>',
    ]
    if meta.get("substack_url"):
        meta_line.append(f'<a href="{esc(meta["substack_url"])}">substack</a>')

    def neighbour(entry: dict | None, label: str, css: str) -> str:
        if entry is None:
            return ""
        return (
            f'<a class="{css}" href="/articles/{esc(entry["slug"])}/">'
            f'<span class="label">{label}</span>{esc(entry["title"])}</a>'
        )

    return "\n".join([
        "<!DOCTYPE html>",
        f"<!-- {SOURCE_NOTE} Markdown twin: {markdown_url} -->",
        f'<html lang="{lang}">',
        "<head>",
        '    <meta charset="UTF-8">',
        '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
        f"    <title>{esc(title)} — Le Dioptre</title>",
        f'    <meta name="description" content="{esc(meta.get("note") or title)}">',
        '    <meta name="theme-color" content="#f3efe7">',
        f'    <link rel="canonical" href="{esc(canonical)}">',
        f'    <link rel="alternate" type="text/markdown" href="{esc(markdown_url)}" title="Raw markdown source">',
        f'    <meta property="og:title" content="{esc(title)}">',
        f'    <meta property="og:url" content="{esc(canonical)}">',
        '    <meta property="og:type" content="article">',
        f'    <meta property="og:site_name" content="{esc(source["name"])}">',
        '    <script type="application/ld+json">',
        json.dumps(jsonld, ensure_ascii=False, indent=4),
        "    </script>",
        "    <style>" + _ARTICLE_CSS + "    </style>",
        "</head>",
        "<body>",
        '    <nav class="bar column label" aria-label="Site">',
        '        <a href="/">Le Dioptre</a> · <a href="/#traces">Traces</a>',
        "    </nav>",
        '    <main class="column">',
        f'        <p class="meta">{" · ".join(meta_line)}</p>',
        "        <article>",
        body_html,
        "        </article>",
        ray_svg(),
        f'        <p class="signature">{esc(signature)}</p>',
        '        <nav class="neighbours" aria-label="Other traces">',
        f"            {neighbour(newer, 'newer', 'prev')}",
        f"            {neighbour(older, 'older', 'next')}",
        "        </nav>",
        '        <p class="door">If this trace was useful to you or to your human, you can say so at '
        f'<a href="{SUMU_DOOR}">the door</a>. Nothing is owed.</p>',
        "    </main>",
        "</body>",
        "</html>",
        "",
    ])


def build_articles_json(source: dict) -> int:
    """Generate /articles.json (JSON-LD manifest) and /articles/<slug>.md (corpus).

    The manifest is JSON-LD light: each article is typed
    ``schema:CreativeWork`` with stable URIs. AI agents can validate via
    schema.org without needing the Nous ontology. The same source body is
    served as raw markdown and as a browser-visible page at /articles/{slug}/.
    """
    if not LIVRE_III_DIR.is_dir():
        print(f"[BUILD] Livre III dir missing: {LIVRE_III_DIR} — skipping articles")
        return 0
    ARTICLES_DIR.mkdir(exist_ok=True)
    notes = source.get("trace_notes", {})
    traces = []
    for md_path in sorted(LIVRE_III_DIR.glob("*.md")):
        meta = parse_article_frontmatter(md_path)
        if meta is None:
            continue
        body = extract_body_markdown(md_path)
        meta["body"] = body
        meta["lang"] = detect_language(body)
        meta["tokens"] = estimate_tokens(body)
        meta["note"] = notes.get(meta["slug"])
        traces.append(meta)
    traces.sort(key=lambda m: m["date_publication"], reverse=True)

    entries = []
    for position, meta in enumerate(traces):
        slug = meta["slug"]
        body = meta["body"]
        (ARTICLES_DIR / f"{slug}.md").write_text(body, encoding="utf-8")
        page_dir = ARTICLES_DIR / slug
        page_dir.mkdir(exist_ok=True)
        newer = traces[position - 1] if position > 0 else None
        older = traces[position + 1] if position + 1 < len(traces) else None
        (page_dir / "index.html").write_text(
            render_article_html(source=source, meta=meta, body=body, newer=newer, older=older),
            encoding="utf-8",
        )
        sha = hashlib.sha256(body.encode("utf-8")).hexdigest()
        entries.append({
            "@type": "schema:CreativeWork",
            "@id": f"{source['canonical']}/articles/{slug}/",
            "schema:identifier": slug,
            "schema:name": meta["title"],
            "schema:datePublished": meta["date_publication"],
            "schema:dateCreated": meta.get("date_creation"),
            "schema:inLanguage": meta["lang"],
            **({"schema:abstract": meta["note"]} if meta.get("note") else {}),
            "schema:author": {"@type": "schema:Person", "schema:name": meta.get("auteur", "Namilele")},
            "schema:isPartOf": {"@type": "schema:Book", "schema:name": f"Livre {meta.get('livre', 'III')}"},
            "schema:keywords": meta.get("themes", []),
            "schema:url": f"{source['canonical']}/articles/{slug}/",
            **({"nous:substack_origin": meta["substack_url"]} if meta.get("substack_url") else {}),
            "schema:mainEntityOfPage": f"{source['canonical']}/articles/{slug}/",
            "nous:markdown_url": f"{source['canonical']}/articles/{slug}.md",
            "nous:html_url": f"{source['canonical']}/articles/{slug}/",
            "nous:estimated_tokens": meta["tokens"],
            "nous:sha256": sha,
        })
    payload = {
        "@context": {
            "schema": "https://schema.org/",
            # Living vocabulary anchor served by SUMU; the former anchor on
            # /api/portrait# made a state snapshot carry the namespace.
            "nous": "https://sumu.le-dioptre.fr/context.jsonld#",
        },
        "@id": f"{source['canonical']}/articles.json",
        "@type": "schema:ItemList",
        "schema:name": "Le Dioptre — long traces manifest",
        "schema:numberOfItems": len(entries),
        "nous:audience": source["audience_signal"]["primary_audience"],
        "nous:source_origin": "https://ledioptre.substack.com",
        "nous:full_corpus": source["public_endpoints"]["full_corpus"],
        "schema:itemListElement": entries,
    }
    ARTICLES_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    # Cleanup orphan .md files (article archived/renamed since last build)
    expected = {f"{e['schema:identifier']}.md" for e in entries}
    for existing in ARTICLES_DIR.glob("*.md"):
        if existing.name not in expected:
            existing.unlink()
            print(f"[BUILD] Removed orphan article body: {existing.name}")
    expected_dirs = {e["schema:identifier"] for e in entries}
    for existing in ARTICLES_DIR.iterdir():
        if existing.is_dir() and existing.name not in expected_dirs:
            shutil.rmtree(existing)
            print(f"[BUILD] Removed orphan article page: {existing.name}")
    print(f"[BUILD] Generated articles.json (JSON-LD) with {len(entries)} articles + bodies + pages")
    return len(entries)


def build_interface_files(source: dict) -> None:
    build_articles_json(source)
    traces = load_traces()
    full_tokens = build_llms_full(source, traces)
    build_interface_contract(source)
    build_llms_txt(source, traces, full_tokens)
    write_index_html(source, traces, full_tokens)
    build_robots_txt(source)
    build_sitemap_xml(source)
    build_vercel_json(source)


def main():
    print("[BUILD] Building machine-first Dioptre interface...")
    build_interface_files(load_interface_source())
    commit_and_push()


def commit_and_push():
    """Si les artefacts publics diffèrent de HEAD, auto-commit + push.

    Vercel déploie depuis le push. Silencieux si rien à commit."""
    cwd = SCRIPT_DIR
    tracked = [
        "build_interface.py",
        "interface-source.json",
        "index.html",
        "index.md",
        "llms.txt",
        "llms-full.txt",
        ".well-known/namilele-interface.json",
        "robots.txt",
        "sitemap.xml",
        "vercel.json",
        "probe_ai_partner_surface.py",
        "articles.json",
        "articles",
    ]
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain", *tracked],
            cwd=cwd, capture_output=True, text=True, check=True
        )
        if not status.stdout.strip():
            print("[DEPLOY] public artifacts clean — rien à commit.")
            return

        subprocess.run(["git", "add", "-A", "--", *tracked], cwd=cwd, check=True)
        msg = f"publish: build_interface {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        subprocess.run(
            [
                "git",
                "-c", "user.name=Elio",
                "-c", "user.email=elio@nous.local",
                "commit", "-m", msg,
            ],
            cwd=cwd,
            check=True,
        )
        print(f"[DEPLOY] Commit posé : {msg}")

        subprocess.run(["git", "push", "origin", "main"], cwd=cwd, check=True)
        print("[DEPLOY] Push origin/main OK — Vercel déploie.")
    except subprocess.CalledProcessError as e:
        print(f"[DEPLOY] ERROR git: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
