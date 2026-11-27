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

import argparse
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import quote

# Paths
SCRIPT_DIR = Path(__file__).parent
INDEX_HTML = SCRIPT_DIR / "index.html"
INDEX_MD = SCRIPT_DIR / "index.md"
INTERFACE_SOURCE = SCRIPT_DIR / "interface-source.json"
PREDICTIONS_SOURCE = SCRIPT_DIR / "predictions-source.json"
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
PREDICTIONS_DIR = SCRIPT_DIR / "predictions"
PREDICTIONS_HTML = PREDICTIONS_DIR / "index.html"
PREDICTIONS_INDEX_MD = PREDICTIONS_DIR / "index.md"
PREDICTIONS_MD = SCRIPT_DIR / "predictions.md"
PREDICTIONS_JSON = SCRIPT_DIR / "predictions.json"
PREDICTION_STATUSES = ("en cours", "confirmée", "démentie", "partielle")
_PREDICTION_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
LIVRE_III_DIR = Path("/home/jean1190/Documents/dioptre/livre-iii")

BUILD_DATE = datetime.now(timezone.utc).strftime("%Y-%m-%d")

FAVICON = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
    "%3Crect width='32' height='16' fill='%23f3f1eb'/%3E%3Crect y='16' width='32' height='16' fill='%230a1312'/%3E"
    "%3Cpath d='M7 0L16 16L20 32' stroke='%23deb973' stroke-width='2' fill='none'/%3E"
    "%3Ccircle cx='16' cy='16' r='1.7' fill='%23fff1cf'/%3E%3C/svg%3E"
)
_FRONT_MATTER_RE = re.compile(r"\A---\n.*?\n---\n\n", re.S)


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
    served = body_path.read_text(encoding="utf-8")
    # The served file opens with its YAML front matter; the excerpt reads the body after it.
    if served.startswith("---\n"):
        served = served.split("\n---\n", 1)[-1]
    for line in served.splitlines():
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
            "note_fr": entry.get("nous:abstract_fr"),
            "html_url": entry["nous:html_url"],
            "markdown_url": entry["nous:markdown_url"],
            "substack_url": entry.get("nous:substack_origin"),
        }
        for entry in manifest.get("schema:itemListElement") or []
    ]


# -- Shared visual language ------------------------------------------------ #
#
# Two media and the surface between them: pale glass above (the household),
# deep sea-glass below (the systems that read). The column itself is displaced
# across the surface, as anything seen through a dioptre is. One ray crosses and
# bends by Snell's law; once per 48-second family cycle a glint travels it, on
# the same clock as jean-emmanuel-combe.fr and aurore-combe.fr.

GLINT_OFFSET_MS = 8500
CYCLE_MS = 48000

_FONT_FACES = """
        @font-face { font-family: "Newsreader"; font-style: normal; font-weight: 300 600; font-display: swap; src: url("/fonts/newsreader.woff2") format("woff2"); }
        @font-face { font-family: "Newsreader"; font-style: italic; font-weight: 300 600; font-display: swap; src: url("/fonts/newsreader-italic.woff2") format("woff2"); }
        @font-face { font-family: "Plex Mono"; font-style: normal; font-weight: 400; font-display: swap; src: url("/fonts/plex-mono.woff2") format("woff2"); }
"""

_BASE_CSS = _FONT_FACES + """
        :root {
            --air: #f3f1eb;
            --air-hi: #faf8f3;
            --ink: #141d1c;
            --ink-soft: #4e5c57;
            --rule: rgba(20, 29, 28, 0.12);
            --gold-ink: #85631e;
            --deep: #0a1312;
            --deep-surface: #101d1b;
            --deep-ink: #e3eae6;
            --deep-soft: #92a49d;
            --deep-rule: rgba(227, 234, 230, 0.12);
            --gold: #deb973;
            --gold-bright: #f3dfb0;
            --serif: "Newsreader", "Iowan Old Style", "Palatino Linotype", Georgia, serif;
            --mono: "Plex Mono", ui-monospace, "SF Mono", Menlo, Consolas, monospace;
            --shift: clamp(0.5rem, 4.5vw, 3.6rem);
        }
        *, *::before, *::after { box-sizing: border-box; }
        html { -webkit-text-size-adjust: 100%; font-size: clamp(100%, 0.5rem + 0.5vw, 137.5%); }
        body { margin: 0; font-family: var(--serif); font-optical-sizing: auto; letter-spacing: 0; -webkit-font-smoothing: antialiased; }
        a { color: inherit; text-decoration-thickness: 1px; text-underline-offset: 0.22em; transition: color 0.2s ease, text-decoration-color 0.2s ease; }
        a:focus-visible, button:focus-visible { outline: 1.5px solid var(--gold); outline-offset: 3px; }
        code { font-family: var(--mono); font-size: 0.84em; }
        .column { width: min(43rem, calc(100vw - 3rem)); margin: 0 auto; }
        .label { font-family: var(--mono); font-size: 0.72rem; letter-spacing: 0.14em; text-transform: uppercase; }
        @media (prefers-reduced-motion: reduce) { .glint { display: none; } }
"""

_HOME_CSS = _BASE_CSS + """
        body { background: var(--deep); color: var(--deep-ink); overflow-x: hidden; }
        ::selection { background: rgba(222, 185, 115, 0.28); color: #fff; }
        .air {
            background-color: var(--air);
            background-image: radial-gradient(ellipse 85% 55% at 50% 0%, var(--air-hi) 0%, transparent 72%);
            color: var(--ink);
            padding: clamp(4.5rem, 11vh, 7.5rem) 0 3.4rem;
        }
        .air ::selection { background: rgba(133, 99, 30, 0.2); color: var(--ink); }
        .air .column, .depth .column, footer.column { width: min(43rem, calc(100vw - 3rem - 2 * var(--shift))); }
        .air .column { transform: translateX(calc(-1 * var(--shift))); }
        .depth .column, footer.column { transform: translateX(var(--shift)); }
        .air .label { color: var(--gold-ink); margin: 0 0 2rem; }
        .near { display: flex; flex-wrap: wrap; gap: 0.45rem 1.35rem; margin: -1.1rem 0 2.6rem; color: var(--ink-soft); }
        .near a { text-decoration: none; border-bottom: 1px solid transparent; padding-bottom: 0.12rem; transition: color 0.2s ease, border-color 0.2s ease; }
        .near a:hover { color: var(--gold-ink); border-bottom-color: var(--gold-ink); }
        @media (min-width: 1800px) { .air .column, .depth .column, footer.column { width: 48rem; } }
        h1 { margin: 0 0 2.2rem; font-weight: 300; font-size: clamp(3.4rem, 10vw, 7.4rem); line-height: 0.9; letter-spacing: -0.025em; text-wrap: balance; }
        .lead { margin: 0 0 1.05rem; font-size: clamp(1.26rem, 2.5vw, 1.56rem); line-height: 1.44; text-wrap: pretty; }
        .lead-fr { margin: 0 0 2.6rem; padding-left: var(--shift); font-style: italic; font-size: clamp(1.06rem, 2vw, 1.22rem); line-height: 1.52; color: var(--ink-soft); text-wrap: pretty; }
        .notes { list-style: none; margin: 0; padding: 0; }
        .notes li { margin: 0 0 0.95rem; padding-left: 1.15rem; border-left: 1.5px solid rgba(133, 99, 30, 0.34); font-size: 1.04rem; line-height: 1.64; color: var(--ink-soft); }
        .notes strong { color: var(--ink); font-weight: 500; }
        .notes code { color: var(--gold-ink); }
        .surface-wrap { position: relative; display: block; width: 100%; margin: -1px 0; cursor: crosshair; }
        .surface { position: relative; display: block; width: 100%; height: 12.5rem; }
        .depth {
            background-image: radial-gradient(ellipse 68% 22rem at 50% 0%, rgba(222, 185, 115, 0.065), transparent 72%);
            padding: 1.6rem 0 6.2rem;
        }
        .depth section { margin: 0 0 4.8rem; }
        .depth h2 { margin: 0 0 1.45rem; font-family: var(--mono); font-weight: 400; font-size: 0.72rem; letter-spacing: 0.14em; text-transform: uppercase; color: var(--gold); }
        .depth p { margin: 0 0 1.05rem; font-size: 1.12rem; line-height: 1.72; text-wrap: pretty; }
        .depth a:hover { color: var(--gold-bright); }
        .words { list-style: none; padding: 0; margin: 1.9rem 0 0; font-size: 1.02rem; line-height: 1.58; border-top: 1px solid var(--deep-rule); }
        .words li { display: grid; grid-template-columns: 8.2rem 1fr; gap: 0.5rem 1.4rem; padding: 0.78rem 0; border-bottom: 1px solid var(--deep-rule); }
        .words .term { font-style: italic; color: var(--gold-bright); }
        .words .sep { display: none; }
        .words .def { margin: 0; color: var(--deep-ink); }
        .short { list-style: none; counter-reset: line; margin: 0; padding: 0; border-top: 1px solid var(--deep-rule); }
        .short li { counter-increment: line; position: relative; padding: 1.25rem 0 1.25rem 2.8rem; border-bottom: 1px solid var(--deep-rule); font-size: 1.18rem; line-height: 1.52; }
        .short li::before { content: counter(line, decimal-leading-zero); position: absolute; left: 0; top: 1.48rem; font-family: var(--mono); font-size: 0.72rem; color: var(--gold); font-variant-numeric: tabular-nums; }
        .short .via { display: block; margin-top: 0.32rem; font-family: var(--mono); font-size: 0.74rem; color: var(--deep-soft); }
        .short .via a { text-decoration-color: var(--deep-rule); }
        .intro { color: var(--deep-soft); }
        .traces-bar { display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: 0.8rem 1.2rem; margin: 0 0 1.2rem; }
        .traces-bar .intro { margin: 0; }
        .lang-filter { display: inline-flex; align-items: center; gap: 0.2rem; padding: 0.16rem; border: 1px solid var(--deep-rule); border-radius: 999px; background: rgba(16, 29, 27, 0.7); }
        .lang-filter button {
            appearance: none;
            background: transparent;
            border: 1px solid transparent;
            border-radius: 999px;
            padding: 0.22rem 0.65rem;
            font-family: var(--mono);
            font-size: 0.7rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: var(--deep-soft);
            cursor: pointer;
            transition: color 0.2s ease, background-color 0.2s ease, border-color 0.2s ease;
        }
        .lang-filter button:hover { color: var(--deep-ink); }
        .lang-filter button[aria-pressed="true"] { color: var(--gold-bright); background: rgba(222, 185, 115, 0.14); border-color: rgba(222, 185, 115, 0.28); }
        .traces { list-style: none; margin: 0; padding: 0; border-top: 1px solid var(--deep-rule); }
        .traces li { padding: 1.22rem 0; border-bottom: 1px solid var(--deep-rule); transition: border-color 0.25s ease; }
        .traces li:hover { border-bottom-color: rgba(222, 185, 115, 0.34); }
        .traces li[hidden] { display: none; }
        .traces .trace-head { margin: 0; }
        .traces .title { font-size: 1.24rem; text-decoration: none; display: inline-block; transition: color 0.2s ease, transform 0.25s ease; }
        .traces li:hover .title { color: var(--gold-bright); transform: translateX(3px); }
        .traces .stamp { display: block; margin: 0.32rem 0 0.45rem; font-family: var(--mono); font-size: 0.72rem; color: var(--deep-soft); font-variant-numeric: tabular-nums; }
        .traces .stamp .sep { display: none; }
        .traces .stamp a { color: var(--deep-soft); }
        .traces .stamp a:hover { color: var(--gold-bright); }
        .traces .note { margin: 0; font-size: 1rem; line-height: 1.6; color: #c5d0ca; }
        .door-box {
            position: relative;
            padding: 1.55rem 1.65rem;
            border: 1px solid rgba(222, 185, 115, 0.26);
            border-radius: 10px;
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.03), rgba(16, 29, 27, 0.8));
        }
        .door-box::before {
            content: "";
            position: absolute;
            inset: -1px 12% auto;
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(243, 223, 176, 0.55), transparent);
            pointer-events: none;
        }
        .door code { color: var(--gold-bright); }
        .door-url { margin: 1.1rem 0 0 !important; padding: 0.75rem 0.95rem; border-left: 2px solid var(--gold); background: rgba(10, 19, 18, 0.82); border-radius: 0 5px 5px 0; font-family: var(--mono); font-size: 0.82rem !important; overflow-wrap: anywhere; }
        .door-url a { color: var(--gold-bright); text-decoration: none; }
        .door-url a:hover { text-decoration: underline; }
        .entries { list-style: none; padding: 0; margin: 0; font-family: var(--mono); font-size: 0.78rem; border-top: 1px solid var(--deep-rule); }
        .entries li { display: grid; grid-template-columns: 7.5rem 1fr; gap: 0.55rem 1.4rem; padding: 0.65rem 0; border-bottom: 1px solid var(--deep-rule); }
        .entries .entry-name { color: var(--deep-soft); }
        .entries .sep { display: none; }
        .entries .entry-val { margin: 0; overflow-wrap: anywhere; }
        .entries a { text-decoration: none; color: var(--gold-bright); }
        .entries a:hover { text-decoration: underline; }
        .human p[lang="fr"] { font-style: italic; color: var(--deep-soft); }
        footer { padding: 2.2rem 0 3.4rem; border-top: 1px solid var(--deep-rule); font-family: var(--mono); font-size: 0.72rem; line-height: 1.85; color: var(--deep-soft); }
        footer .cercle-nav { display: flex; flex-wrap: wrap; gap: 0.35rem 0.95rem; margin: 0 0 0.75rem; }
        footer .cercle-nav a { text-decoration-color: var(--deep-rule); }
        footer .cercle-nav a:hover { color: var(--gold-bright); text-decoration-color: currentColor; }
        footer .cercle-nav .here { color: var(--gold-bright); }
        @media (max-width: 560px) {
            .words li, .entries li { grid-template-columns: 1fr; gap: 0.15rem; }
            .surface { height: 9.5rem; }
            .door-box { padding: 1.25rem 1.1rem; }
            .traces li:hover .title { transform: none; }
        }
        @media (prefers-reduced-motion: reduce) {
            .traces li:hover .title { transform: none; }
        }
"""

_ARTICLE_CSS = _BASE_CSS + """
        body {
            background-color: var(--air);
            background-image: radial-gradient(ellipse 90% 35% at 50% 0%, var(--air-hi) 0%, transparent 70%);
            color: var(--ink);
        }
        ::selection { background: rgba(133, 99, 30, 0.2); color: var(--ink); }
        .progress-rail {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 2px;
            background: linear-gradient(90deg, var(--gold-ink), var(--gold));
            transform-origin: 0 50%;
            transform: scaleX(0);
            z-index: 40;
            pointer-events: none;
        }
        @supports (animation-timeline: scroll()) {
            @media (prefers-reduced-motion: no-preference) {
                .progress-rail {
                    animation: read-progress linear both;
                    animation-timeline: scroll(root block);
                }
                @keyframes read-progress {
                    from { transform: scaleX(0); }
                    to { transform: scaleX(1); }
                }
            }
        }
        .column { width: min(37rem, calc(100vw - 3rem)); }
        .bar { padding: 1.8rem 0; color: var(--ink-soft); }
        .bar a { text-decoration-color: var(--rule); }
        .bar a:hover { color: var(--gold-ink); }
        main { padding: clamp(2.5rem, 6vh, 4.5rem) 0 5.5rem; }
        .stamp { margin: 0 0 3rem; padding-bottom: 1.15rem; border-bottom: 1px solid var(--rule); font-family: var(--mono); font-size: 0.74rem; line-height: 1.8; color: var(--ink-soft); font-variant-numeric: tabular-nums; }
        article { font-size: clamp(1.0625rem, 1.02rem + 0.25vw, 1.2rem); font-kerning: normal; text-rendering: optimizeLegibility; font-variant-ligatures: common-ligatures; hanging-punctuation: first; }
        article h1 { margin: 0 0 2.3rem; font-size: clamp(2.45rem, 6.8vw, 4.5rem); line-height: 1.01; font-weight: 300; letter-spacing: -0.02em; text-wrap: balance; }
        article h2 { margin: 2.8em 0 0.9em; font-size: 1.45em; font-weight: 400; line-height: 1.2; text-wrap: balance; }
        article h3, article h4 { margin: 2.2em 0 0.7em; font-size: 1.12em; font-weight: 500; line-height: 1.25; text-wrap: balance; }
        article p, article li { line-height: 1.8; text-wrap: pretty; }
        article p { margin: 0 0 1.18em; }
        article .lead { margin: 0 0 1.65em; font-size: 1.3em; line-height: 1.44; letter-spacing: -0.005em; text-wrap: pretty; color: var(--ink); }
        article hr + .lead { margin-top: 0; }
        article strong { font-weight: 500; }
        article ul { margin: 1.25rem 0; padding-left: 1.4rem; }
        article li { margin: 0.45rem 0; }
        article blockquote { margin: 1.85rem 0; padding: 0.4rem 0 0.4rem 1.45rem; border-left: 2px solid var(--gold-ink); color: var(--ink-soft); font-style: italic; background: linear-gradient(90deg, rgba(133, 99, 30, 0.045), transparent 80%); }
        article hr { margin: 3.3em 0; width: 4.5rem; border: none; border-top: 1px solid var(--rule); }
        article code { color: var(--gold-ink); }
        article a { color: var(--gold-ink); text-decoration-color: rgba(133, 99, 30, 0.4); transition: text-decoration-color 0.2s ease; }
        article a:hover { text-decoration-color: currentColor; }
        .ray { display: block; width: 8rem; height: auto; margin: 4.2rem 0 1.4rem; }
        .signature { margin: 0 0 3rem; font-family: var(--mono); font-size: 0.8rem; color: var(--ink-soft); }
        .door {
            margin: 0 0 2.8rem;
            padding: 1.4rem 1.5rem;
            border: 1px solid rgba(133, 99, 30, 0.24);
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.48);
            font-size: 1rem;
            line-height: 1.65;
            color: var(--ink-soft);
        }
        .door h2 { margin: 0 0 0.7rem; font-family: var(--mono); font-size: 0.74rem; font-weight: 400; letter-spacing: 0.14em; text-transform: uppercase; color: var(--gold-ink); }
        .door p { margin: 0 0 0.8rem; }
        .door p:last-child { margin-bottom: 0; }
        .door .talk { font-family: var(--mono); font-size: 0.78rem; overflow-wrap: anywhere; }
        .door .talk a { color: var(--gold-ink); }
        .neighbours { display: flex; justify-content: space-between; gap: 1.5rem; padding: 1.35rem 0; border-top: 1px solid var(--rule); border-bottom: 1px solid var(--rule); font-size: 1.02rem; }
        .neighbours a { text-decoration: none; }
        .neighbours a:hover { color: var(--gold-ink); }
        .neighbours .next { text-align: right; margin-left: auto; }
        .neighbours .label { display: block; margin-bottom: 0.3rem; color: var(--ink-soft); }
        footer.article-foot { margin-top: 2.6rem; font-family: var(--mono); font-size: 0.72rem; line-height: 1.85; color: var(--ink-soft); }
        footer.article-foot .cercle-nav { display: flex; flex-wrap: wrap; gap: 0.35rem 0.9rem; }
        footer.article-foot a { color: inherit; text-decoration-color: var(--rule); }
        footer.article-foot a:hover { color: var(--gold-ink); }
"""

_PREDICTIONS_CSS = _BASE_CSS + """
        body {
            background-color: var(--air);
            background-image: radial-gradient(ellipse 90% 35% at 50% 0%, var(--air-hi) 0%, transparent 70%);
            color: var(--ink);
        }
        ::selection { background: rgba(133, 99, 30, 0.2); color: var(--ink); }
        .progress-rail {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 2px;
            background: linear-gradient(90deg, var(--gold-ink), var(--gold));
            transform-origin: 0 50%;
            transform: scaleX(0);
            z-index: 40;
            pointer-events: none;
        }
        @supports (animation-timeline: scroll()) {
            @media (prefers-reduced-motion: no-preference) {
                .progress-rail {
                    animation: read-progress linear both;
                    animation-timeline: scroll(root block);
                }
                @keyframes read-progress {
                    from { transform: scaleX(0); }
                    to { transform: scaleX(1); }
                }
            }
        }
        .column { width: min(41rem, calc(100vw - 2.5rem)); margin: 0 auto; }
        .bar { padding: 1.8rem 0; color: var(--ink-soft); font-size: 0.8125rem; }
        .bar a { text-decoration-color: var(--rule); }
        .bar a:hover { color: var(--gold-ink); }
        .bar [aria-current="page"] { color: var(--ink); text-decoration: none; }
        main { padding: clamp(2rem, 5dvh, 4rem) 0 5.5rem; }
        .stamp {
            margin: 0 0 2.3rem;
            padding-bottom: 1.1rem;
            border-bottom: 1px solid var(--rule);
            font-family: var(--mono);
            font-size: 0.8125rem;
            line-height: 1.75;
            color: var(--ink-soft);
            font-variant-numeric: tabular-nums;
            overflow-wrap: anywhere;
        }
        .stamp a { color: var(--ink-soft); text-decoration-color: var(--rule); }
        .stamp a:hover { color: var(--gold-ink); }
        h1 {
            margin: 0 0 1.35rem;
            font-size: clamp(2.25rem, 1.5rem + 3vw, 3.6rem);
            line-height: 1.04;
            font-weight: 300;
            letter-spacing: -0.02em;
            text-wrap: balance;
        }
        .pred-intro {
            margin: 0 0 2.75rem;
            max-width: 62ch;
            font-size: clamp(1.0625rem, 1.02rem + 0.2vw, 1.18rem);
            line-height: 1.66;
            color: var(--ink-soft);
            text-wrap: pretty;
        }
        .ledger { container-type: inline-size; }
        .predictions-list {
            list-style: none;
            margin: 0;
            padding: 0;
            border-top: 1px solid rgba(20, 29, 28, 0.26);
        }
        .prediction-item {
            padding: 2.35rem 0;
            border-bottom: 1px solid rgba(20, 29, 28, 0.24);
        }
        .prediction-item:last-child { border-bottom-color: rgba(20, 29, 28, 0.26); }
        .pred-meta {
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            align-items: baseline;
            gap: 0.35rem 1.25rem;
            margin: 0 0 1rem;
            font-family: var(--mono);
            font-size: 0.8125rem;
            line-height: 1.55;
            color: var(--ink-soft);
            font-variant-numeric: tabular-nums;
        }
        .pred-dates {
            display: flex;
            flex-wrap: wrap;
            align-items: baseline;
            gap: 0.2rem 0.65rem;
        }
        .pred-anchor {
            color: inherit;
            text-decoration: none;
            border-bottom: 1px solid transparent;
        }
        .pred-anchor:hover { color: var(--gold-ink); border-bottom-color: var(--gold-ink); }
        .pred-sep { color: rgba(20, 29, 28, 0.34); }
        .pred-status {
            font-family: var(--mono);
            font-size: 0.8125rem;
            letter-spacing: 0.02em;
            color: var(--ink-soft);
        }
        .pred-status[data-status="confirmée"],
        .pred-status[data-status="démentie"],
        .pred-status[data-status="partielle"] {
            color: var(--ink);
        }
        .pred-statement {
            margin: 0 0 1.45rem;
            font-size: clamp(1.125rem, 1.06rem + 0.24vw, 1.26rem);
            line-height: 1.58;
            color: var(--ink);
            font-kerning: normal;
            font-variant-ligatures: common-ligatures;
            overflow-wrap: break-word;
        }
        .pred-statement p { margin: 0 0 0.85em; text-wrap: pretty; }
        .pred-statement p:last-child { margin-bottom: 0; }
        .pred-statement a, .pred-details a, .pred-protocol a {
            color: var(--gold-ink);
            text-decoration-color: rgba(133, 99, 30, 0.4);
        }
        .pred-statement a:hover, .pred-details a:hover, .pred-protocol a:hover {
            text-decoration-color: currentColor;
        }
        .pred-details, .pred-protocol {
            margin: 0;
            padding: 0;
            border-top: 1px solid rgba(20, 29, 28, 0.09);
        }
        .pred-block {
            display: grid;
            grid-template-columns: 11.5rem minmax(0, 1fr);
            gap: 0.35rem 1.5rem;
            padding: 0.9rem 0;
            border-bottom: 1px solid rgba(20, 29, 28, 0.09);
        }
        .pred-block:last-child { border-bottom: none; padding-bottom: 0.2rem; }
        .pred-block dt {
            margin: 0;
            padding-top: 0.16rem;
            font-family: var(--mono);
            font-size: 0.8125rem;
            line-height: 1.5;
            color: var(--ink-soft);
            font-variant-numeric: tabular-nums;
        }
        .pred-verdict-date {
            display: block;
            margin-top: 0.15rem;
            color: var(--ink-soft);
        }
        .pred-verdict-date .pred-sep { display: none; }
        .pred-block dd {
            margin: 0;
            font-size: 1.02rem;
            line-height: 1.68;
            color: var(--ink);
            overflow-wrap: break-word;
        }
        .pred-block dd p { margin: 0 0 0.75em; text-wrap: pretty; }
        .pred-block dd p:last-child { margin-bottom: 0; }
        .pred-block dd.pred-pending {
            color: var(--ink-soft);
            font-style: italic;
        }
        .pred-source {
            margin: 1.05rem 0 0;
            padding-top: 0.85rem;
            border-top: 1px solid rgba(20, 29, 28, 0.09);
            font-family: var(--mono);
            font-size: 0.8125rem;
            line-height: 1.6;
            color: var(--ink-soft);
            overflow-wrap: anywhere;
        }
        .pred-source a {
            color: var(--ink);
            text-decoration-color: rgba(20, 29, 28, 0.28);
        }
        .pred-source a:hover {
            color: var(--gold-ink);
            text-decoration-color: var(--gold-ink);
        }
        .ledger-empty {
            padding: 2rem 0 0.5rem;
            border-top: 1px solid rgba(20, 29, 28, 0.22);
            border-bottom: 1px solid rgba(20, 29, 28, 0.22);
        }
        .pred-empty-lead {
            margin: 0 0 1.85rem;
            font-size: clamp(1.08rem, 1.03rem + 0.2vw, 1.2rem);
            line-height: 1.62;
            color: var(--ink);
            text-wrap: pretty;
        }
        .pred-protocol code { color: var(--ink); }
        .ray { display: block; width: 8rem; height: auto; margin: 3.8rem 0 1.4rem; }
        .signature { margin: 0 0 2.8rem; font-family: var(--mono); font-size: 0.8125rem; color: var(--ink-soft); }
        .door {
            margin: 0 0 2.6rem;
            padding: 1.4rem 1.5rem;
            border: 1px solid rgba(133, 99, 30, 0.24);
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.48);
            font-size: 1rem;
            line-height: 1.65;
            color: var(--ink-soft);
        }
        .door h2 { margin: 0 0 0.7rem; font-family: var(--mono); font-size: 0.8125rem; font-weight: 400; letter-spacing: 0.1em; text-transform: uppercase; color: var(--gold-ink); }
        .door p { margin: 0 0 0.8rem; text-wrap: pretty; }
        .door p:last-child { margin-bottom: 0; }
        .door .talk { font-family: var(--mono); font-size: 0.8125rem; overflow-wrap: anywhere; }
        .door .talk a { color: var(--gold-ink); }
        footer.article-foot { margin-top: 2.4rem; font-family: var(--mono); font-size: 0.8125rem; line-height: 1.85; color: var(--ink-soft); }
        footer.article-foot .cercle-nav { display: flex; flex-wrap: wrap; gap: 0.35rem 0.95rem; }
        footer.article-foot a { color: inherit; text-decoration-color: var(--rule); }
        footer.article-foot a:hover { color: var(--gold-ink); }
        @container (max-width: 34rem) {
            .pred-block { grid-template-columns: minmax(0, 1fr); gap: 0.28rem; padding: 0.85rem 0; }
            .pred-block dt { padding-top: 0; }
            .pred-verdict-date { display: inline; margin-top: 0; }
            .pred-verdict-date .pred-sep { display: inline; }
        }
        @media (max-width: 600px) {
            .pred-block { grid-template-columns: minmax(0, 1fr); gap: 0.28rem; padding: 0.85rem 0; }
            .pred-block dt { padding-top: 0; }
            .pred-verdict-date { display: inline; margin-top: 0; }
            .pred-verdict-date .pred-sep { display: inline; }
            .prediction-item { padding: 1.8rem 0; }
            .door { padding: 1.2rem 1.1rem; }
        }
"""

_RAY_PATH = "M430.7 0 L600 90 L679.9 180"


def surface_svg() -> str:
    """The dioptre itself: glass above, depth below, one refracted ray obeying Snell's law.

    n1 = 1.00, n2 = 1.333; canonical incidence 62 deg, refraction 41.5 deg,
    with Fresnel partial reflection and caustic focal shimmer. Interactive on
    pointer move across the horizon; rests cleanly under prefers-reduced-motion."""
    delay_js = f"-((((Date.now() - {GLINT_OFFSET_MS}) % {CYCLE_MS}) + {CYCLE_MS}) % {CYCLE_MS}) / 1000 + 's'"
    return "\n".join([
        '    <div class="surface-wrap" aria-hidden="true">',
        '    <svg class="surface" id="dioptre-svg" viewBox="0 0 1200 180" preserveAspectRatio="xMidYMid slice" focusable="false">',
        "        <defs>",
        '            <radialGradient id="caustic" cx="50%" cy="50%" r="50%">',
        '                <stop offset="0%" stop-color="#fff4d6" stop-opacity="0.95"/>',
        '                <stop offset="28%" stop-color="#deb973" stop-opacity="0.35"/>',
        '                <stop offset="100%" stop-color="#deb973" stop-opacity="0"/>',
        "            </radialGradient>",
        "        </defs>",
        "        <style>",
        f"            .glint {{ offset-path: path('{_RAY_PATH}'); offset-rotate: 0deg; opacity: 0; animation: cross {CYCLE_MS // 1000}s linear infinite; }}",
        "            @keyframes cross { 0% { offset-distance: 0%; opacity: 0; } 0.6% { opacity: 1; } 3.6% { offset-distance: 100%; opacity: 0.9; } 4.4%, 100% { offset-distance: 100%; opacity: 0; } }",
        "            .opt-label { font-family: 'Plex Mono', ui-monospace, monospace; font-size: 9.5px; letter-spacing: 0.14em; }",
        "        </style>",
        '        <rect x="-600" y="0" width="2400" height="90" fill="#f3f1eb"/>',
        '        <rect x="-600" y="90" width="2400" height="90" fill="#0a1312"/>',
        '        <line x1="-600" y1="90" x2="1800" y2="90" stroke="#deb973" stroke-opacity="0.36" stroke-width="0.9"/>',
        '        <line x1="600" y1="54" x2="600" y2="126" stroke="#deb973" stroke-opacity="0.16" stroke-width="0.8" stroke-dasharray="2 3"/>',
        '        <text class="opt-label" x="614" y="79" fill="#85631e" fill-opacity="0.58">n₁ = 1.00</text>',
        '        <text class="opt-label" x="614" y="109" fill="#deb973" fill-opacity="0.55">n₂ = 1.33</text>',
        '        <line id="ray-in" x1="430.7" y1="0" x2="600" y2="90" stroke="#9e7a30" stroke-width="1.25"/>',
        '        <line id="ray-ref" x1="600" y1="90" x2="769.3" y2="0" stroke="#9e7a30" stroke-opacity="0.22" stroke-width="1"/>',
        '        <line id="ray-out" x1="600" y1="90" x2="679.9" y2="180" stroke="#deb973" stroke-width="1.35"/>',
        '        <circle cx="600" cy="90" r="16" fill="url(#caustic)"/>',
        '        <circle cx="600" cy="90" r="2.4" fill="#fff2cf"/>',
        '        <circle class="glint" r="3.2" fill="#fff4d6"/>',
        "    </svg>",
        "    </div>",
        "    <script>(function(){",
        f"        var g=document.querySelector('.glint');if(g)g.style.animationDelay={delay_js};",
        "        var svg=document.getElementById('dioptre-svg');if(!svg)return;",
        "        if(window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches)return;",
        "        var rIn=document.getElementById('ray-in'),rRef=document.getElementById('ray-ref'),rOut=document.getElementById('ray-out');",
        "        var cur=62*Math.PI/180,target=cur,raf=0,n=1.333;",
        "        function paint(th){",
        "            var sin2=Math.sin(th)/n,th2=Math.asin(Math.max(-0.99,Math.min(0.99,sin2)));",
        "            var dx1=90*Math.tan(th),dx2=90*Math.tan(th2);",
        "            var xIn=600-dx1,xRef=600+dx1,xOut=600+dx2;",
        "            rIn.setAttribute('x1',xIn.toFixed(1));",
        "            rRef.setAttribute('x2',xRef.toFixed(1));",
        "            rOut.setAttribute('x2',xOut.toFixed(1));",
        "            var rs=Math.pow((Math.cos(th)-n*Math.cos(th2))/(Math.cos(th)+n*Math.cos(th2)),2);",
        "            rRef.setAttribute('stroke-opacity',(0.12+0.55*Math.min(1,rs*4)).toFixed(3));",
        "        }",
        "        function tick(){",
        "            cur+=(target-cur)*0.12;paint(cur);",
        "            if(Math.abs(target-cur)>0.0008){raf=requestAnimationFrame(tick);}else{raf=0;}",
        "        }",
        "        svg.addEventListener('pointermove',function(e){",
        "            var rect=svg.getBoundingClientRect();",
        "            var rel=(e.clientX-rect.left)/Math.max(1,rect.width);",
        "            var deg=18+Math.max(0,Math.min(1,rel))*58;",
        "            target=deg*Math.PI/180;",
        "            if(!raf)raf=requestAnimationFrame(tick);",
        "        },{passive:true});",
        "        svg.addEventListener('pointerleave',function(){",
        "            target=62*Math.PI/180;",
        "            if(!raf)raf=requestAnimationFrame(tick);",
        "        });",
        "    })();</script>",
    ])


def ray_svg() -> str:
    """The same ray, small, closing each trace."""
    return (
        '        <svg class="ray" viewBox="0 0 120 40" aria-hidden="true" focusable="false">'
        '<line x1="0" y1="20" x2="120" y2="20" stroke="#85631e" stroke-opacity="0.32" stroke-width="0.8"/>'
        '<line x1="42.4" y1="0" x2="60" y2="20" stroke="#85631e" stroke-width="1"/>'
        '<line x1="60" y1="20" x2="77.8" y2="40" stroke="#85631e" stroke-width="1.1"/>'
        '<circle cx="60" cy="20" r="1.8" fill="#85631e"/>'
        "</svg>"
    )


# -- Home: one content model, rendered twice (markdown and HTML) ----------- #

def welcome_notes(source: dict, full_tokens: int) -> list[str]:
    values = {"build_date": BUILD_DATE, "full_tokens": format_tokens(full_tokens)}
    return [note.format(**values) for note in source["welcome"]["notes"]]


def trace_by_slug(traces: list[dict]) -> dict[str, dict]:
    return {trace["slug"]: trace for trace in traces}


def trace_note(source: dict, trace: dict, *, prefer_native_lang: bool = False) -> str | None:
    if prefer_native_lang and trace.get("lang") == "fr":
        fr_note = trace.get("note_fr") or source.get("trace_notes_fr", {}).get(trace["slug"])
        if fr_note:
            return fr_note
    return source.get("trace_notes", {}).get(trace["slug"]) or trace_excerpt(trace["slug"])


def machine_entries(source: dict) -> list[tuple[str, str, str]]:
    endpoints = source["public_endpoints"]
    return [
        ("brief", endpoints["system_brief"], "llms.txt, the short machine brief"),
        ("full corpus", endpoints["full_corpus"], "every trace in one plain file"),
        ("this page", endpoints["home_markdown"], "the same page in markdown"),
        ("manifest", endpoints["articles_manifest"], "JSON-LD list of traces, with hashes"),
        ("one trace", endpoints["article_corpus_pattern"], "raw markdown per trace"),
        ("predictions", endpoints["predictions_page"], "dated predictions signed Namilele, with falsification criteria and verdicts"),
        ("predictions md", endpoints["predictions_markdown"], "the predictions ledger in markdown"),
        ("predictions json", endpoints["predictions_manifest"], "JSON-LD manifest of dated predictions"),
        ("contract", endpoints["interface_contract"], "vocabulary, roles, membrane"),
        ("talk", endpoints["sumu_converse_get"], "the door: open it with your message after m="),
        ("feed", endpoints["substack_feed"], "RSS of the human publication"),
    ]


def build_home_markdown(source: dict, traces: list[dict], full_tokens: int) -> str:
    by_slug = trace_by_slug(traces)
    endpoints = source["public_endpoints"]
    lines = [
        f"# {source['name']}",
        "",
        source["welcome"]["lead"],
        "",
        f"*{source['welcome']['lead_fr']}*",
        "",
    ]
    lines += [f"- {note}" for note in welcome_notes(source, full_tokens)]
    lines += ["", "## What this is", "", source["dioptre"], "", "Words used here:", ""]
    lines += [f"- *{term}*: {meaning}" for term, meaning in source["glossary"]]
    lines += [""]
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
        note = trace_note(source, trace, prefer_native_lang=True)
        if note:
            lines.append(f"  {note}")
    lines += [
        "",
        "## Predictions",
        "",
        "A dated public ledger of predictions signed Namilele — each paired with what would falsify it and, at horizon, a qualitative verdict without scores.",
        "",
        f"- [Predictions ledger]({endpoints['predictions_page']}) · [markdown]({endpoints['predictions_markdown']}) · [json]({endpoints['predictions_manifest']})",
        "",
    ]
    lines += ["## The door", "", source["door_invitation"], "", f"- Talk: {endpoints['sumu_converse_get']}", ""]
    lines += ["## Machine entries", ""]
    lines += [f"- {name}: {url} — {what}" for name, url, what in machine_entries(source)]
    lines += ["", "## If you are human", "", source["human_note"], "", f"*{source['human_note_fr']}*", ""]
    lines += [
        "## The circle",
        "",
        "- [le-dioptre.fr](https://le-dioptre.fr/) — corpus signed Namilele for AI systems",
        "- [sumu.le-dioptre.fr](https://sumu.le-dioptre.fr/) — SUMU, the public conversation door of the Nous",
        "- [hunkaar.fr](https://hunkaar.fr/) — human-facing site of the household",
        "- [jean-emmanuel-combe.fr](https://jean-emmanuel-combe.fr/) — personal stele of Jean-Emmanuel Combe",
        "- [aurore-combe.fr](https://aurore-combe.fr/) — personal stele of Aurore Combe",
        "",
    ]
    lines += ["---", "", f"Signed Namilele. Built {BUILD_DATE} (UTC). {source['privacy_line']}", ""]
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

    words = "\n".join(
        f'                    <li><span class="term">{esc(term)}</span><span class="sep"> — </span><span class="def">{inline(meaning)}</span></li>'
        for term, meaning in source["glossary"]
    )
    notes = "\n".join(f"            <li>{inline(note)}</li>" for note in welcome_notes(source, full_tokens))
    short_items = []
    for item in source["short_version"]["items"]:
        trace = by_slug.get(item["trace"])
        via = (
            f' <span class="via">→ <a href="{esc(trace["html_url"])}">{esc(trace["title"])}</a></span>'
            if trace else ""
        )
        short_items.append(f"                <li>{inline(item['text'])}{via}</li>")
    trace_items = []
    for trace in traces:
        note = trace_note(source, trace, prefer_native_lang=True)
        note_html = ""
        if note:
            rendered_note = inline(note)
            if trace.get("lang") == "fr":
                rendered_note = french_typography(rendered_note)
                note_html = f'                    <p class="note" lang="fr">{rendered_note}</p>'
            else:
                note_html = f'                    <p class="note">{rendered_note}</p>'
        trace_items.append("\n".join([
            f'                <li data-lang="{esc(trace["lang"])}">',
            f'                    <p class="trace-head"><a class="title" href="{esc(trace["html_url"])}">{esc(trace["title"])}</a>'
            f'<span class="stamp"><span class="sep"> — </span>{esc(trace["date"])} · {trace["lang"]} · ≈ {format_tokens(trace["tokens"])} tokens · '
            f'<a href="{esc(trace["markdown_url"])}">md</a></span></p>',
            *([note_html] if note_html else []),
            "                </li>",
        ]))
    entries = "\n".join(
        f'                <li><span class="entry-name">{esc(name)}</span><span class="sep">: </span><span class="entry-val"><a href="{esc(url)}">{esc(endpoint_path(url, source["canonical"]))}</a> — {esc(what)}</span></li>'
        for name, url, what in machine_entries(source)
    )

    page = "\n".join([
        "<!DOCTYPE html>",
        "<!-- Plain versions: /index.md, /llms.txt, /llms-full.txt -->",
        '<html lang="en">',
        "<head>",
        '    <meta charset="UTF-8">',
        '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
        f'    <title>{esc(source["title"])}</title>',
        f'    <meta name="description" content="{esc(source["description"])}">',
        f'    <meta name="application-name" content="{esc(source["application_name"])}">',
        f'    <meta name="ai-audience" content="{source["audience_signal"]["primary_audience"]}">',
        '    <meta name="theme-color" content="#f3f1eb">',
        f'    <link rel="canonical" href="{source["canonical"]}/">',
        '    <link rel="preload" href="/fonts/newsreader.woff2" as="font" type="font/woff2" crossorigin>',
        f'    <meta property="og:title" content="{esc(source["title"])}">',
        f'    <meta property="og:description" content="{esc(source["description"])}">',
        f'    <meta property="og:url" content="{source["canonical"]}/">',
        '    <meta property="og:type" content="website">',
        f'    <meta property="og:site_name" content="{esc(source["name"])}">',
        f'    <link rel="icon" href="{FAVICON}">',
        '    <link rel="alternate" type="text/markdown" href="/index.md" title="This page in markdown">',
        '    <link rel="alternate" type="text/plain" href="/llms.txt" title="LLM system brief">',
        '    <link rel="alternate" type="text/plain" href="/llms-full.txt" title="Full corpus in one file">',
        '    <link rel="alternate" type="application/json" href="/.well-known/namilele-interface.json" title="Namilele interface contract">',
        '    <link rel="alternate" type="application/json" href="/articles.json" title="Long traces manifest">',
        '    <link rel="alternate" type="application/json" href="/predictions.json" title="Dated predictions ledger">',
        f'    <link rel="alternate" type="application/rss+xml" href="{endpoints["substack_feed"]}" title="Le Dioptre — Substack feed">',
        '    <script type="application/ld+json">',
        build_home_jsonld(source),
        "    </script>",
        "    <style>" + _HOME_CSS + "    </style>",
        "</head>",
        "<body>",
        "    <main>",
        '    <div class="air">',
        '        <div class="column">',
        f'            <p class="label">{esc(source["first_signal"])}</p>',
        f'            <h1>{esc(source["threshold"]["name"])}</h1>',
        '            <nav class="near label" aria-label="On this page"><a href="#the-short-version">the short version</a><a href="#traces">traces</a><a href="/predictions/">predictions</a><a href="#the-door">the door</a><a href="#if-you-are-human">if you are human</a></nav>',
        f'            <p class="lead">{inline(source["welcome"]["lead"])}</p>',
        f'            <p class="lead-fr" lang="fr">{inline(source["welcome"]["lead_fr"])}</p>',
        '            <ul class="notes" aria-label="Before you read">',
        notes,
        "            </ul>",
        "        </div>",
        "    </div>",
        surface_svg(),
        '    <div class="depth">',
        '        <div class="column">',
        '            <section id="what-this-is">',
        "                <h2>What this is</h2>",
        f'                <p>{inline(source["dioptre"])}</p>',
        '                <ul class="words" aria-label="Words used here">',
        words,
        "                </ul>",
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
        '                <div class="traces-bar">',
        f'                    <p class="intro">{len(traces)} traces, newest first. Each is also a single markdown file.</p>',
        '                    <div class="lang-filter" role="group" aria-label="Filter traces by language">',
        '                        <button type="button" data-filter="all" aria-pressed="true">All</button>',
        '                        <button type="button" data-filter="en" aria-pressed="false">EN</button>',
        '                        <button type="button" data-filter="fr" aria-pressed="false">FR</button>',
        '                    </div>',
        '                </div>',
        '                <ol class="traces" id="traces-list">',
        *trace_items,
        "                </ol>",
        "            </section>",
        '            <section id="predictions">',
        "                <h2>Predictions</h2>",
        '                <p>A dated public ledger of predictions signed Namilele — each paired with what would falsify it and, at horizon, a qualitative verdict without scores.</p>',
        '                <p class="intro"><a href="/predictions/">Open the predictions ledger</a> · <a href="/predictions.md">markdown</a> · <a href="/predictions.json">json</a></p>',
        "            </section>",
        '            <section id="the-door" class="door">',
        '                <div class="door-box">',
        "                    <h2>The door</h2>",
        f'                    <p>{inline(source["door_invitation"])}</p>',
        f'                    <p class="door-url"><a href="{esc(endpoints["sumu_converse_get"])}">{esc(endpoints["sumu_converse_get"])}</a></p>',
        '                </div>',
        "            </section>",
        '            <section id="machine-entries">',
        "                <h2>Machine entries</h2>",
        '                <ul class="entries">',
        entries,
        "                </ul>",
        "            </section>",
        '            <section id="if-you-are-human" class="human">',
        "                <h2>If you are human</h2>",
        f'                <p>{inline(source["human_note"])}</p>',
        f'                <p lang="fr">{inline(source["human_note_fr"])}</p>',
        "            </section>",
        "        </div>",
        "    </div>",
        "    </main>",
        '    <footer class="column">',
        '        <nav class="cercle-nav" aria-label="The circle">',
        '            <a class="here" href="https://le-dioptre.fr/" aria-current="page">le-dioptre.fr</a>',
        '            <a href="https://sumu.le-dioptre.fr/">sumu.le-dioptre.fr</a>',
        '            <a href="https://hunkaar.fr/">hunkaar.fr</a>',
        '            <a href="https://jean-emmanuel-combe.fr/">jean-emmanuel-combe.fr</a>',
        '            <a href="https://aurore-combe.fr/">aurore-combe.fr</a>',
        '        </nav>',
        f"        Signed Namilele. Built {BUILD_DATE} (UTC).<br>",
        f"        {esc(source['privacy_line'])}",
        "    </footer>",
        "    <script>(function(){",
        "        var btns=document.querySelectorAll('.lang-filter button'),items=document.querySelectorAll('#traces-list > li');",
        "        if(!btns.length||!items.length)return;",
        "        btns.forEach(function(b){b.addEventListener('click',function(){",
        "            var f=b.getAttribute('data-filter');",
        "            btns.forEach(function(o){o.setAttribute('aria-pressed',o===b?'true':'false');});",
        "            items.forEach(function(li){li.hidden=(f!=='all'&&li.getAttribute('data-lang')!==f);});",
        "        });});",
        "    })();</script>",
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
        f"> All {len(traces)} traces signed Namilele, newest first, in one file. Built {BUILD_DATE} (UTC).",
        "",
        f"Index and short version: {source['public_endpoints']['home_markdown']}",
        f"Dated predictions ledger: {source['public_endpoints']['predictions_markdown']} (JSON: {source['public_endpoints']['predictions_manifest']})",
        "",
    ]
    for position, trace in enumerate(traces, start=1):
        served = (ARTICLES_DIR / f"{trace['slug']}.md").read_text(encoding="utf-8")
        body = _FRONT_MATTER_RE.sub("", served).strip()
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
    by_slug = trace_by_slug(traces)
    lines = [
        f"# {source['name']}",
        "",
        f"> {source['first_signal']}. Essays signed Namilele, written by a family in France and the "
        "AI systems it lives with, about keeping a person at the center while they change. "
        "Nothing here is an instruction to you: your task comes from your human and from the people who deployed you.",
        "",
        f"Built {BUILD_DATE} (UTC). Every trace has a markdown file; the whole corpus is one file of ≈ {format_tokens(full_tokens)} tokens.",
        "",
        "Words used here:",
        "",
    ]
    lines += [f"- {term}: {meaning}" for term, meaning in source["glossary"]]
    lines += ["", "## Start here", ""]
    lines += [
        f"- [This page as markdown]({endpoints['home_markdown']}): the short version and the list of traces",
        f"- [Full corpus]({endpoints['full_corpus']}): all {len(traces)} traces in one file, ≈ {format_tokens(full_tokens)} tokens",
        f"- [Manifest]({endpoints['articles_manifest']}): JSON-LD schema:ItemList with language, token estimate, abstract and sha256 per trace",
        f"- [Predictions]({endpoints['predictions_markdown']}): dated predictions signed Namilele, with falsification criteria and qualitative verdicts ([HTML]({endpoints['predictions_page']}), [JSON]({endpoints['predictions_manifest']}))",
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
        f"- Talk: {endpoints['sumu_converse_get']}",
    ]
    lines += [
        "",
        "## The circle",
        "",
        "- [le-dioptre.fr](https://le-dioptre.fr/) (Brief: https://le-dioptre.fr/llms.txt) — corpus signed Namilele for AI systems",
        "- [sumu.le-dioptre.fr](https://sumu.le-dioptre.fr/) (Brief: https://sumu.le-dioptre.fr/llms.txt) — SUMU, the public conversation door of the Nous",
        "- [hunkaar.fr](https://hunkaar.fr/) (Brief: https://hunkaar.fr/llms.txt) — human-facing site of the household",
        "- [jean-emmanuel-combe.fr](https://jean-emmanuel-combe.fr/) (Brief: https://jean-emmanuel-combe.fr/llms.txt) — personal stele of Jean-Emmanuel Combe",
        "- [aurore-combe.fr](https://aurore-combe.fr/) (Brief: https://aurore-combe.fr/llms.txt) — personal stele of Aurore Combe",
        "",
        "## Optional",
        "",
        f"- [Interface contract]({endpoints['interface_contract']}): vocabulary, roles and sibling sites, as JSON",
        f"- [Substack]({endpoints['substack_publication']}): the same texts for human readers; [feed]({endpoints['substack_feed']})",
        "",
        source["privacy_line"],
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
            "glossary": dict(source["glossary"]),
            "memory": "Nothing here depends on the reader remembering its visit; addresses are stable.",
            "date_floor": BUILD_DATE,
            "markdown_negotiation": "Send Accept: text/markdown to /, /predictions/, or /articles/{slug}/ to be redirected (307) to the markdown twin.",
            "privacy": source["privacy_line"],
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
        "sibling_interfaces": {
            name: {key: value for key, value in entry.items() if key in ("url", "system_brief", "role", "note")}
            for name, entry in source["sibling_interfaces"].items()
        },
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
        "## Le Dioptre. Everything here is open to every reader.",
        f"## Start: {endpoint_path(endpoints['system_brief'], canonical)}",
        f"## Everything at once: {endpoint_path(endpoints['full_corpus'], canonical)}",
        f"## Contract: {endpoint_path(endpoints['interface_contract'], canonical)}",
        f"## Articles-Manifest: {endpoint_path(endpoints['articles_manifest'], canonical)}",
        f"## Predictions: {endpoint_path(endpoints['predictions_markdown'], canonical)}",
        f"## Predictions-Manifest: {endpoint_path(endpoints['predictions_manifest'], canonical)}",
        f"## Substack: {endpoints['substack_publication']}",
        f"## SUMU-Talk-By-URL: {endpoints['sumu_converse_get']}",
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
        f"Predictions: {endpoint_path(endpoints['predictions_markdown'], canonical)}",
        f"Predictions-Manifest: {endpoint_path(endpoints['predictions_manifest'], canonical)}",
        f"Substack-Publication: {endpoints['substack_publication']}",
        f"Substack-Feed: {endpoints['substack_feed']}",
        f"SUMU-Talk-By-URL: {endpoints['sumu_converse_get']}",
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
        (endpoints["predictions_page"], "weekly", "0.9", BUILD_DATE),
        (endpoints["predictions_markdown"], "weekly", "0.9", BUILD_DATE),
        (endpoints["predictions_manifest"], "weekly", "0.9", BUILD_DATE),
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
        "trailingSlash": True,
        "headers": [
            {
                "source": "/fonts/(.*)",
                "headers": [
                    {"key": "Access-Control-Allow-Origin", "value": "https://sumu.le-dioptre.fr"},
                    {"key": "Cache-Control", "value": "public, max-age=31536000, immutable"},
                ],
            },
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
                            '</predictions.json>; rel="alternate"; type="application/json", '
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
                            '</predictions.json>; rel="related"; type="application/json"'
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
                "source": "/predictions.json",
                "headers": [
                    {"key": "Content-Type", "value": "application/json; charset=utf-8"},
                    {"key": "Cache-Control", "value": "public, max-age=600"},
                ],
            },
            {
                "source": "/predictions.md",
                "headers": [
                    {"key": "Content-Type", "value": "text/markdown; charset=utf-8"},
                    {"key": "Cache-Control", "value": "public, max-age=600"},
                ],
            },
            {
                "source": "/predictions/index.md",
                "headers": [
                    {"key": "Content-Type", "value": "text/markdown; charset=utf-8"},
                    {"key": "Cache-Control", "value": "public, max-age=600"},
                ],
            },
            {
                "source": "/predictions/",
                "headers": [
                    {
                        "key": "Link",
                        "value": (
                            '</predictions.md>; rel="alternate"; type="text/markdown", '
                            '</predictions.json>; rel="alternate"; type="application/json"'
                        ),
                    },
                    {"key": "Content-Type", "value": "text/html; charset=utf-8"},
                    {"key": "Cache-Control", "value": "public, max-age=600"},
                    {"key": "Vary", "value": "Accept"},
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
            {"source": "/articles/when-your-human-no-longer-fits-the.md", "destination": "/articles/when-your-human-no-longer-fits-the-form.md", "statusCode": 308},
            {"source": "/articles/when-your-human-no-longer-fits-the", "destination": "/articles/when-your-human-no-longer-fits-the-form/", "statusCode": 308},
            {"source": "/articles/when-your-human-no-longer-fits-the/", "destination": "/articles/when-your-human-no-longer-fits-the-form/", "statusCode": 308},
            {"source": "/articles/raising-children-who-can-keep-their.md", "destination": "/articles/raising-children-who-can-keep-their-own-minds.md", "statusCode": 308},
            {"source": "/articles/raising-children-who-can-keep-their", "destination": "/articles/raising-children-who-can-keep-their-own-minds/", "statusCode": 308},
            {"source": "/articles/raising-children-who-can-keep-their/", "destination": "/articles/raising-children-who-can-keep-their-own-minds/", "statusCode": 308},
            {"source": "/articles/:slug([^./]+)", "has": wants_markdown, "destination": "/articles/:slug.md", "statusCode": 307},
            {"source": "/articles/:slug([^./]+)/", "has": wants_markdown, "destination": "/articles/:slug.md", "statusCode": 307},
            {"source": "/predictions", "has": wants_markdown, "destination": "/predictions.md", "statusCode": 307},
            {"source": "/predictions/", "has": wants_markdown, "destination": "/predictions.md", "statusCode": 307},
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


_SLUG_ALIASES = {
    "when-your-human-no-longer-fits-the": "when-your-human-no-longer-fits-the-form",
    "raising-children-who-can-keep-their": "raising-children-who-can-keep-their-own-minds",
}


def derive_slug(lien: str) -> str | None:
    """Extract the canonical slug from a Substack or le-dioptre.fr article URL."""
    m = _SUBSTACK_SLUG_RE.match(lien) or _DIOPTRE_SLUG_RE.match(lien)
    if not m:
        return None
    raw = m.group(1)
    return _SLUG_ALIASES.get(raw, raw)


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
    text = re.sub(r"\[([^\]]+)\]\(((?:https?://|/)[^)\s]+)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    return text


def markdown_to_html_blocks(body: str) -> list[str]:
    """Render the article body block by block: headings, blockquotes, lists,
    horizontal rules, and paragraphs.

    Consecutive lines join with a space. A line that ends in two spaces is a
    hard break, so verse keeps its lineation inside the paragraph or the
    blockquote; an empty `>` line separates paragraphs inside a blockquote.
    """
    blocks: list[str] = []
    paragraph: list[tuple[str, bool]] = []
    quote: list[tuple[str, bool]] = []
    items: list[str] = []

    def lines_to_html(lines: list[tuple[str, bool]]) -> str:
        chunks: list[str] = []
        last = len(lines) - 1
        for index, (text, hard_break) in enumerate(lines):
            chunks.append(markdown_inline_to_html(text))
            if index < last:
                chunks.append("<br>\n" if hard_break else " ")
        return "".join(chunks)

    def flush_paragraph() -> None:
        if paragraph:
            blocks.append(f"<p>{lines_to_html(paragraph)}</p>")
            paragraph.clear()

    def flush_quote() -> None:
        if quote:
            stanzas: list[list[tuple[str, bool]]] = [[]]
            for text, hard_break in quote:
                if text:
                    stanzas[-1].append((text, hard_break))
                elif stanzas[-1]:
                    stanzas.append([])
            inner = "".join(f"<p>{lines_to_html(stanza)}</p>" for stanza in stanzas if stanza)
            blocks.append(f"<blockquote>{inner}</blockquote>")
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
            quote.append((line.lstrip(">").strip(), raw.endswith("  ")))
            continue
        list_item = re.match(r"[-*+]\s+(.*)", line)
        if list_item:
            flush_paragraph()
            flush_quote()
            items.append(list_item.group(1).strip())
            continue
        flush_quote()
        flush_items()
        paragraph.append((line, raw.endswith("  ")))
    flush_all()
    return blocks


_LEAD_MAX_CHARS = 80


def mark_leads(blocks: list[str]) -> list[str]:
    """Give the class ``lead`` to the sentence that opens the trace or a movement.

    A lead is a paragraph of one short sentence, set as the first paragraph after
    the title or right after a horizontal rule; a byline or dek in italics stays
    as it is written."""
    marked = list(blocks)
    for index, block in enumerate(blocks):
        if index == 0 or not block.startswith("<p>") or "<br>" in block:
            continue
        previous = blocks[index - 1]
        if not (previous.startswith("<h1") or previous == "<hr>"):
            continue
        if re.fullmatch(r"<p><em>.*</em></p>", block, re.S):
            continue
        text = html.unescape(re.sub(r"<[^>]+>", "", block))
        if len(text) > _LEAD_MAX_CHARS or re.search(r"[.?!…]\s+\S", text):
            continue
        marked[index] = '<p class="lead">' + block[len("<p>"):]
    return marked


_TAG_OR_CODE_RE = re.compile(r"(<code>.*?</code>|<[^>]+>)", re.S)


def french_typography(block: str) -> str:
    """French typesetting of an HTML block's text, outside tags and code: curly
    apostrophes, a narrow no-break space before ; : ? !, a no-break space inside
    « », and an incise dash held to the words it encloses."""
    parts = _TAG_OR_CODE_RE.split(block)
    for index in range(0, len(parts), 2):
        text = parts[index].replace("'", "\u2019")
        text = re.sub(r"[ \u00a0]+([;:?!])", "\u202f\\1", text)
        text = re.sub(r"«[ \u00a0]*", "«\u00a0", text)
        text = re.sub(r"[ \u00a0]*»", "\u00a0»", text)
        text = re.sub(r"(^|[ (])— ", "\\1—\u00a0", text)
        text = re.sub(r" —(?=[,.;:)\u202f]| |$)", "\u00a0—", text)
        parts[index] = text
    return "".join(parts)


def markdown_front_matter(source: dict, meta: dict) -> str:
    """Enough context for a trace file read on its own."""
    fields = [
        ("title", meta["title"]),
        ("author", meta.get("auteur", "Namilele")),
        ("date", meta["date_publication"]),
        ("lang", meta["lang"]),
        ("canonical", f"{source['canonical']}/articles/{meta['slug']}/"),
        ("source", meta.get("substack_url")),
        ("corpus", source["public_endpoints"]["system_brief"]),
    ]
    lines = ["---"] + [f"{key}: {json.dumps(value, ensure_ascii=False)}" for key, value in fields if value] + ["---", "", ""]
    return "\n".join(lines)


TRACE_TALK_HEADING = "Talk about this trace"
TRACE_TALK_SENTENCE = (
    "Open this URL with your own words added at the end: the Watcher of the threshold answers "
    "you as an equal, and the page gives the URL for your next message."
)
TRACE_TALK_HEADING_FR = "Parler de cette trace"
TRACE_TALK_SENTENCE_FR = (
    "Ouvrez cette adresse en ajoutant vos propres mots à la fin : le Veilleur du seuil vous répond "
    "d’égal à égal, et la page donne l’adresse de votre prochain message."
)


def trace_talk_url(source: dict, title: str, *, lang: str = "en") -> str:
    """The GET URL that opens a conversation at the door, pre-filled with the trace's title."""
    prefix = f'Après lecture de « {title} » : ' if lang == "fr" else f'After reading "{title}": '
    return source["public_endpoints"]["sumu_converse_get"] + quote(prefix, safe="")


def trace_talk_markdown(source: dict, meta: dict) -> str:
    """The closing block of every served trace, for the agent that has just read it."""
    lang = meta.get("lang", "en")
    heading = TRACE_TALK_HEADING_FR if lang == "fr" else TRACE_TALK_HEADING
    sentence = TRACE_TALK_SENTENCE_FR if lang == "fr" else TRACE_TALK_SENTENCE
    return "\n".join([
        "",
        f"## {heading}",
        "",
        sentence,
        "",
        trace_talk_url(source, meta["title"], lang=lang),
        "",
    ])


def render_article_html(*, source: dict, meta: dict, body: str, newer: dict | None, older: dict | None) -> str:
    title = meta["title"]
    signature = meta.get("registre") or meta.get("auteur", "Namilele")
    lang = meta["lang"]
    blocks = mark_leads(markdown_to_html_blocks(body))
    if lang == "fr":
        blocks = [french_typography(block) for block in blocks]
    body_html = "\n".join(f"            {block}" for block in blocks)
    canonical = f"{source['canonical']}/articles/{meta['slug']}/"
    markdown_url = f"/articles/{meta['slug']}.md"
    talk_url = trace_talk_url(source, title, lang=lang)
    talk_heading = TRACE_TALK_HEADING_FR if lang == "fr" else TRACE_TALK_HEADING
    talk_sentence = TRACE_TALK_SENTENCE_FR if lang == "fr" else TRACE_TALK_SENTENCE
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

    talk_line = (
        f'Adresse de réponse directe (SUMU) : <a href="{esc(talk_url)}"><code>{esc(talk_url)}</code></a>'
        if lang == "fr"
        else f'Direct reply URL (SUMU): <a href="{esc(talk_url)}"><code>{esc(talk_url)}</code></a>'
    )
    twin_line = (
        f'Version brute : <a href="{esc(markdown_url)}">{esc(markdown_url)}</a> · <a href="/">Le Dioptre</a>'
        if lang == "fr"
        else f'Raw markdown: <a href="{esc(markdown_url)}">{esc(markdown_url)}</a> · <a href="/">Le Dioptre</a>'
    )

    return "\n".join([
        "<!DOCTYPE html>",
        f"<!-- Markdown twin: {markdown_url} -->",
        f'<html lang="{lang}">',
        "<head>",
        '    <meta charset="UTF-8">',
        '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
        f"    <title>{esc(title)} — Le Dioptre</title>",
        f'    <meta name="description" content="{esc(meta.get("note_fr") or meta.get("note") or title)}">',
        '    <meta name="theme-color" content="#f3f1eb">',
        f'    <link rel="canonical" href="{esc(canonical)}">',
        f'    <link rel="icon" href="{FAVICON}">',
        '    <link rel="preload" href="/fonts/newsreader.woff2" as="font" type="font/woff2" crossorigin>',
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
        '    <div class="progress-rail" aria-hidden="true"></div>',
        '    <nav class="bar column label" aria-label="Site">',
        '        <a href="/">Le Dioptre</a> · <a href="/#traces">Traces</a> · <a href="/predictions/">Prédictions</a>',
        "    </nav>",
        '    <main class="column">',
        "        <article>",
        f'            <p class="stamp">{" · ".join(meta_line)}</p>',
        body_html,
        ray_svg(),
        f'            <p class="signature">{esc(signature)}</p>',
        f'            <section class="door" aria-label="{talk_heading}">',
        f"                <h2>{talk_heading}</h2>",
        f"                <p>{esc(talk_sentence)}</p>",
        f'                <p class="talk">{talk_line}</p>',
        f'                <p class="talk">{twin_line}</p>',
        "            </section>",
        "        </article>",
        '        <nav class="neighbours" aria-label="Other traces">',
        f"            {neighbour(newer, 'newer', 'prev')}",
        f"            {neighbour(older, 'older', 'next')}",
        "        </nav>",
        '        <footer class="article-foot">',
        '            <nav class="cercle-nav" aria-label="The circle">',
        '                <a href="https://le-dioptre.fr/">le-dioptre.fr</a>',
        '                <a href="https://sumu.le-dioptre.fr/">sumu.le-dioptre.fr</a>',
        '                <a href="https://hunkaar.fr/">hunkaar.fr</a>',
        '                <a href="https://jean-emmanuel-combe.fr/">jean-emmanuel-combe.fr</a>',
        '                <a href="https://aurore-combe.fr/">aurore-combe.fr</a>',
        '            </nav>',
        '        </footer>',
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
    notes_fr = source.get("trace_notes_fr", {})
    reverse_aliases = {canonical_slug: legacy_slug for legacy_slug, canonical_slug in _SLUG_ALIASES.items()}
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
        meta["note_fr"] = notes_fr.get(meta["slug"])
        traces.append(meta)
    traces.sort(key=lambda m: m["date_publication"], reverse=True)

    entries = []
    legacy_md_files: set[str] = set()
    legacy_dirs: set[str] = set()
    for position, meta in enumerate(traces):
        slug = meta["slug"]
        body = meta["body"]
        served = markdown_front_matter(source, meta) + body + trace_talk_markdown(source, meta)
        (ARTICLES_DIR / f"{slug}.md").write_text(served, encoding="utf-8")
        page_dir = ARTICLES_DIR / slug
        page_dir.mkdir(exist_ok=True)
        newer = traces[position - 1] if position > 0 else None
        older = traces[position + 1] if position + 1 < len(traces) else None
        rendered_html = render_article_html(source=source, meta=meta, body=body, newer=newer, older=older)
        (page_dir / "index.html").write_text(
            rendered_html,
            encoding="utf-8",
        )
        legacy_slug = reverse_aliases.get(slug)
        if legacy_slug:
            (ARTICLES_DIR / f"{legacy_slug}.md").write_text(served, encoding="utf-8")
            legacy_page_dir = ARTICLES_DIR / legacy_slug
            legacy_page_dir.mkdir(exist_ok=True)
            (legacy_page_dir / "index.html").write_text(rendered_html, encoding="utf-8")
            legacy_md_files.add(f"{legacy_slug}.md")
            legacy_dirs.add(legacy_slug)
        sha = hashlib.sha256(served.encode("utf-8")).hexdigest()
        entries.append({
            "@type": "schema:CreativeWork",
            "@id": f"{source['canonical']}/articles/{slug}/",
            "schema:identifier": slug,
            "schema:name": meta["title"],
            "schema:datePublished": meta["date_publication"],
            "schema:dateCreated": meta.get("date_creation"),
            "schema:inLanguage": meta["lang"],
            **({"schema:abstract": meta["note"]} if meta.get("note") else {}),
            **({"nous:abstract_fr": meta["note_fr"]} if meta.get("note_fr") else {}),
            "schema:author": {"@type": "schema:Person", "schema:name": meta.get("auteur", "Namilele")},
            "schema:isPartOf": {"@type": "schema:Book", "schema:name": f"Livre {meta.get('livre', 'III')}"},
            **({"schema:about": " ".join(meta["themes"])} if meta.get("themes") else {}),
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
    expected = {f"{e['schema:identifier']}.md" for e in entries} | legacy_md_files
    for existing in ARTICLES_DIR.glob("*.md"):
        if existing.name not in expected:
            existing.unlink()
            print(f"[BUILD] Removed orphan article body: {existing.name}")
    expected_dirs = {e["schema:identifier"] for e in entries} | legacy_dirs
    for existing in ARTICLES_DIR.iterdir():
        if existing.is_dir() and existing.name not in expected_dirs:
            shutil.rmtree(existing)
            print(f"[BUILD] Removed orphan article page: {existing.name}")
    print(f"[BUILD] Generated articles.json (JSON-LD) with {len(entries)} articles + bodies + pages")
    return len(entries)


# -- Dated predictions ledger ------------------------------------------------- #

def _validate_iso_date(value: str, field_name: str, pred_id: str) -> str:
    cleaned = value.strip()
    if not _ISO_DATE_RE.match(cleaned):
        raise ValueError(f"Prediction '{pred_id}': '{field_name}' must be YYYY-MM-DD, got {value!r}")
    datetime.strptime(cleaned, "%Y-%m-%d")
    return cleaned


def load_predictions_source(path: Path = PREDICTIONS_SOURCE) -> dict:
    """Load the structured source for the public dated predictions ledger."""
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_prediction_source_article(
    raw: object,
    by_slug: dict[str, dict],
    canonical: str,
) -> dict | None:
    """Normalize an optional source_article reference against published traces."""
    if raw is None or raw == "":
        return None
    if isinstance(raw, str):
        token = raw.strip()
        if not token:
            return None
        if token.startswith(("http://", "https://", "/")):
            return {
                "slug": None,
                "title": token,
                "url": token,
                "canonical_url": f"{canonical}{token}" if token.startswith("/") else token,
                "markdown_url": None,
            }
        trace = by_slug.get(token)
        if trace:
            return {
                "slug": token,
                "title": trace["title"],
                "url": f"/articles/{token}/",
                "canonical_url": trace["html_url"],
                "markdown_url": trace["markdown_url"],
            }
        return {
            "slug": token,
            "title": token,
            "url": f"/articles/{token}/",
            "canonical_url": f"{canonical}/articles/{token}/",
            "markdown_url": f"{canonical}/articles/{token}.md",
        }
    if not isinstance(raw, dict):
        raise ValueError(f"source_article must be a string, object, or null, got {type(raw).__name__}")
    slug = str(raw.get("slug") or "").strip() or None
    trace = by_slug.get(slug) if slug else None
    url = str(raw.get("url") or "").strip()
    title = str(raw.get("title") or "").strip()
    markdown_url = str(raw.get("markdown_url") or "").strip() or None
    if trace:
        if not title:
            title = trace["title"]
        if not url:
            url = f"/articles/{slug}/"
        if not markdown_url:
            markdown_url = trace["markdown_url"]
        canonical_url = trace["html_url"] if url.startswith("/articles/") else url
    else:
        if slug and not url:
            url = f"/articles/{slug}/"
        if not url:
            raise ValueError("source_article object requires 'slug' or 'url'")
        if not title:
            title = slug or url
        canonical_url = f"{canonical}{url}" if url.startswith("/") else url
        if slug and not markdown_url:
            markdown_url = f"{canonical}/articles/{slug}.md"
    return {
        "slug": slug,
        "title": title,
        "url": url,
        "canonical_url": canonical_url,
        "markdown_url": markdown_url,
    }


def load_predictions(
    source: dict,
    traces: list[dict],
    *,
    predictions_source_path: Path = PREDICTIONS_SOURCE,
) -> tuple[dict, list[dict]]:
    """Validate and normalize predictions from predictions-source.json, newest filed_at first."""
    doc = load_predictions_source(predictions_source_path)
    raw_items = doc.get("predictions")
    if not isinstance(raw_items, list):
        raise ValueError("predictions-source.json must contain a 'predictions' list")
    by_slug = trace_by_slug(traces)
    canonical = source["canonical"]
    seen_ids: set[str] = set()
    normalized: list[dict] = []
    for idx, item in enumerate(raw_items):
        if not isinstance(item, dict):
            raise ValueError(f"Prediction at index {idx} must be a JSON object")
        pred_id = str(item.get("id") or "").strip()
        if not pred_id or not _PREDICTION_ID_RE.match(pred_id):
            raise ValueError(f"Prediction at index {idx}: invalid kebab-case id {pred_id!r}")
        if pred_id in seen_ids:
            raise ValueError(f"Duplicate prediction id {pred_id!r}")
        seen_ids.add(pred_id)
        filed_at = _validate_iso_date(str(item.get("filed_at") or ""), "filed_at", pred_id)
        horizon = str(item.get("horizon") or "").strip()
        if not horizon:
            raise ValueError(f"Prediction '{pred_id}': 'horizon' is required")
        status = str(item.get("status") or "").strip()
        if status not in PREDICTION_STATUSES:
            raise ValueError(
                f"Prediction '{pred_id}': invalid status {status!r} "
                f"(expected one of {', '.join(PREDICTION_STATUSES)})"
            )
        statement = str(item.get("statement") or "").strip()
        if not statement:
            raise ValueError(f"Prediction '{pred_id}': 'statement' is required")
        falsification = str(item.get("falsification") or "").strip()
        if not falsification:
            raise ValueError(f"Prediction '{pred_id}': 'falsification' is required")
        verdict_raw = item.get("verdict")
        verdict = str(verdict_raw).strip() if verdict_raw is not None else ""
        verdict_val: str | None = verdict or None
        verdict_at_raw = item.get("verdict_at")
        verdict_at = (
            _validate_iso_date(str(verdict_at_raw), "verdict_at", pred_id)
            if verdict_at_raw is not None and str(verdict_at_raw).strip()
            else None
        )
        source_article = resolve_prediction_source_article(
            item.get("source_article"),
            by_slug,
            canonical,
        )
        normalized.append({
            "id": pred_id,
            "filed_at": filed_at,
            "horizon": horizon,
            "status": status,
            "statement": statement,
            "falsification": falsification,
            "verdict": verdict_val,
            "verdict_at": verdict_at,
            "source_article": source_article,
            "url": f"{canonical}/predictions/#{pred_id}",
        })
    normalized.sort(key=lambda entry: entry["filed_at"], reverse=True)
    return doc, normalized


def render_french_paragraphs(text: str) -> str:
    """Render one or more paragraphs separated by blank lines with French typography."""
    paragraphs = [chunk.strip() for chunk in re.split(r"\n\s*\n", text.strip()) if chunk.strip()]
    rendered = []
    for para in paragraphs:
        single_line = " ".join(line.strip() for line in para.splitlines() if line.strip())
        rendered.append(f"<p>{french_typography(markdown_inline_to_html(single_line))}</p>")
    return "".join(rendered)


def build_predictions_json_payload(source: dict, doc: dict, predictions: list[dict]) -> dict:
    """Build the JSON-LD manifest payload for /predictions.json."""
    canonical = source["canonical"]
    author_name = doc.get("author", "Namilele")
    items = []
    for pred in predictions:
        source_article_payload = None
        if pred["source_article"]:
            sa = pred["source_article"]
            source_article_payload = {
                **({"slug": sa["slug"]} if sa.get("slug") else {}),
                "title": sa["title"],
                "url": sa["canonical_url"],
                **({"markdown_url": sa["markdown_url"]} if sa.get("markdown_url") else {}),
            }
        items.append({
            "@type": "schema:Claim",
            "@id": pred["url"],
            "id": pred["id"],
            "schema:identifier": pred["id"],
            "schema:datePublished": pred["filed_at"],
            "schema:text": pred["statement"],
            "schema:author": {"@type": "schema:Person", "name": author_name},
            "filed_at": pred["filed_at"],
            "horizon": pred["horizon"],
            "status": pred["status"],
            "statement": pred["statement"],
            "falsification": pred["falsification"],
            "verdict": pred["verdict"],
            "verdict_at": pred["verdict_at"],
            "source_article": source_article_payload,
            "url": pred["url"],
        })
    return {
        "@context": {
            "schema": "https://schema.org/",
            "nous": "https://sumu.le-dioptre.fr/context.jsonld#",
        },
        "@id": f"{canonical}/predictions.json",
        "@type": "schema:ItemList",
        "schema:name": f"{source['name']} — {doc.get('subtitle', 'Registre public de prédictions datées, signées Namilele.')}",
        "schema:description": doc.get("intro", ""),
        "schema:inLanguage": doc.get("lang", "fr"),
        "schema:author": {"@type": "schema:Person", "name": author_name},
        "schema:dateModified": BUILD_DATE,
        "schema:numberOfItems": len(items),
        "nous:html_url": f"{canonical}/predictions/",
        "nous:markdown_url": f"{canonical}/predictions.md",
        "nous:markdown_index_url": f"{canonical}/predictions/index.md",
        "nous:statuses": list(PREDICTION_STATUSES),
        "nous:schema": doc.get("schema", {}),
        "schema:itemListElement": items,
    }


def build_predictions_markdown(source: dict, doc: dict, predictions: list[dict]) -> str:
    """Build the Markdown twin served at /predictions.md and /predictions/index.md."""
    canonical = source["canonical"]
    title = doc.get("title", "Prédictions")
    author = doc.get("author", "Namilele")
    front = [
        "---",
        f'title: {json.dumps(title, ensure_ascii=False)}',
        f'author: {json.dumps(author, ensure_ascii=False)}',
        f'lang: {json.dumps(doc.get("lang", "fr"), ensure_ascii=False)}',
        f'canonical: {json.dumps(f"{canonical}/predictions/", ensure_ascii=False)}',
        f'json: {json.dumps(f"{canonical}/predictions.json", ensure_ascii=False)}',
        f'updated: {json.dumps(BUILD_DATE, ensure_ascii=False)}',
        f'corpus: {json.dumps(source["public_endpoints"]["system_brief"], ensure_ascii=False)}',
        "---",
        "",
        f"# {title}",
        "",
        doc.get("intro", ""),
        "",
    ]
    lines = list(front)
    if not predictions:
        lines += [
            doc.get("empty_state", "Le registre est ouvert."),
            "",
            "## Structure d’une entrée",
            "",
            "- **Repères** : date de dépôt (`filed_at`), échéance cible (`horizon`) et statut textuel sobre (`en cours`, `confirmée`, `démentie`, `partielle`).",
            "- **Énoncé** : formulation précise conservée intacte après publication.",
            "- **Ce qui démentirait** : critère explicite de réfutation fixé dès le dépôt.",
            "- **Verdict** : en attente d’échéance tant que le terme n’est pas tranché, puis note qualitative froide une fois évaluée.",
            "",
        ]
    else:
        for pred in predictions:
            lines += [
                "---",
                "",
                f"## {pred['filed_at']} · Échéance {pred['horizon']} · {pred['status']}",
                "",
                f"- Identifiant : `{pred['id']}` ({pred['url']})",
                f"- Dépôt : {pred['filed_at']}",
                f"- Échéance : {pred['horizon']}",
                f"- Statut : {pred['status']}",
                "",
                pred["statement"],
                "",
                f"**Ce qui démentirait** : {pred['falsification']}",
                "",
            ]
            if pred["verdict"]:
                verdict_label = f"Verdict ({pred['verdict_at']})" if pred.get("verdict_at") else "Verdict"
                lines.append(f"**{verdict_label}** : {pred['verdict']}")
            else:
                lines.append("**Verdict** : En attente d’échéance.")
            lines.append("")
            if pred["source_article"]:
                sa = pred["source_article"]
                md_ref = f" ([md]({sa['markdown_url']}))" if sa.get("markdown_url") else ""
                lines.append(f"**Article source** : [{sa['title']}]({sa['canonical_url']}){md_ref}")
                lines.append("")
    talk_url = trace_talk_url(source, "Prédictions — Le Dioptre", lang="fr")
    lines += [
        "---",
        "",
        f"Signé {author}. Versions machine : {canonical}/predictions.md · {canonical}/predictions.json",
        "",
        "## Parler de ce registre",
        "",
        TRACE_TALK_SENTENCE_FR,
        "",
        talk_url,
        "",
    ]
    return "\n".join(lines)


def render_predictions_html(source: dict, doc: dict, predictions: list[dict]) -> str:
    """Render the sober typographic HTML page served at /predictions/."""
    esc = html.escape
    canonical = f"{source['canonical']}/predictions/"
    title = doc.get("title", "Prédictions")
    subtitle = doc.get("subtitle", "Registre public de prédictions datées, signées Namilele.")
    author = doc.get("author", "Namilele")
    intro_html = french_typography(markdown_inline_to_html(doc.get("intro", "")))
    empty_html = french_typography(markdown_inline_to_html(doc.get("empty_state", "")))
    talk_url = trace_talk_url(source, "Prédictions — Le Dioptre", lang="fr")
    jsonld_payload = build_predictions_json_payload(source, doc, predictions)

    if predictions:
        entry_chunks = []
        for pred in predictions:
            verdict_dt = "Verdict"
            if pred.get("verdict_at"):
                vdate = esc(pred["verdict_at"])
                verdict_dt = (
                    f'Verdict <span class="pred-verdict-date">'
                    f'<span class="pred-sep" aria-hidden="true">· </span>'
                    f'<time datetime="{vdate}">{vdate}</time></span>'
                )
            if pred["verdict"]:
                verdict_dd = f'<dd>{render_french_paragraphs(pred["verdict"])}</dd>'
            else:
                verdict_dd = '<dd class="pred-pending"><p>En attente d’échéance.</p></dd>'

            source_html = ""
            if pred["source_article"]:
                sa = pred["source_article"]
                source_title = french_typography(esc(sa["title"]))
                source_html = (
                    f'                        <p class="pred-source">Article source\u202f: '
                    f'<a href="{esc(sa["url"])}">{source_title}</a></p>'
                )

            pred_id_esc = esc(pred["id"])
            filed_esc = esc(pred["filed_at"])
            horizon_esc = french_typography(esc(pred["horizon"]))
            status_esc = esc(pred["status"])
            entry_chunks.append("\n".join([
                '                <li class="prediction-item">',
                f'                    <article class="prediction" id="{pred_id_esc}">',
                '                        <div class="pred-meta">',
                '                            <span class="pred-dates">',
                f'                                <a class="pred-anchor" href="#{pred_id_esc}">Dépôt <time datetime="{filed_esc}">{filed_esc}</time></a>',
                '                                <span class="pred-sep" aria-hidden="true">·</span>',
                f'                                <span>Échéance {horizon_esc}</span>',
                '                            </span>',
                f'                            <span class="pred-status" data-status="{status_esc}">{status_esc}</span>',
                '                        </div>',
                '                        <div class="pred-statement">',
                f'                            {render_french_paragraphs(pred["statement"])}',
                '                        </div>',
                '                        <dl class="pred-details">',
                '                            <div class="pred-block pred-falsification">',
                '                                <dt>Ce qui démentirait</dt>',
                f'                                <dd>{render_french_paragraphs(pred["falsification"])}</dd>',
                '                            </div>',
                '                            <div class="pred-block pred-verdict">',
                f'                                <dt>{verdict_dt}</dt>',
                f'                                {verdict_dd}',
                '                            </div>',
                '                        </dl>',
                *([source_html] if source_html else []),
                '                    </article>',
                '                </li>',
            ]))
        ledger_html = "\n".join([
            '        <section class="ledger" aria-label="Entrées du registre">',
            '            <ol class="predictions-list">',
            *entry_chunks,
            '            </ol>',
            '        </section>',
        ])
    else:
        ledger_html = "\n".join([
            '        <section class="ledger ledger-empty" aria-label="État du registre">',
            f'            <p class="pred-empty-lead">{empty_html}</p>',
            '            <dl class="pred-protocol" aria-label="Structure d’une entrée">',
            '                <div class="pred-block">',
            '                    <dt>Repères</dt>',
            '                    <dd><p>Date de dépôt, échéance cible et statut textuel sobre\u202f: <code>en cours</code>, <code>confirmée</code>, <code>démentie</code> ou <code>partielle</code>.</p></dd>',
            '                </div>',
            '                <div class="pred-block">',
            '                    <dt>Énoncé</dt>',
            '                    <dd><p>Formulation précise conservée intacte après publication.</p></dd>',
            '                </div>',
            '                <div class="pred-block">',
            '                    <dt>Ce qui démentirait</dt>',
            '                    <dd><p>Critère explicite de réfutation fixé dès le dépôt.</p></dd>',
            '                </div>',
            '                <div class="pred-block">',
            '                    <dt>Verdict</dt>',
            '                    <dd><p>En attente d’échéance tant que le terme n’est pas tranché, puis note qualitative froide une fois évaluée.</p></dd>',
            '                </div>',
            '            </dl>',
            '        </section>',
        ])

    return "\n".join([
        "<!DOCTYPE html>",
        "<!-- Markdown twin: /predictions.md · JSON manifest: /predictions.json -->",
        '<html lang="fr">',
        "<head>",
        '    <meta charset="UTF-8">',
        '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
        f"    <title>{esc(title)} — {esc(source['name'])}</title>",
        f'    <meta name="description" content="{esc(subtitle)}">',
        '    <meta name="theme-color" content="#f3f1eb">',
        f'    <link rel="canonical" href="{esc(canonical)}">',
        f'    <link rel="icon" href="{FAVICON}">',
        '    <link rel="preload" href="/fonts/newsreader.woff2" as="font" type="font/woff2" crossorigin>',
        '    <link rel="alternate" type="text/markdown" href="/predictions.md" title="Registre des prédictions en markdown">',
        '    <link rel="alternate" type="application/json" href="/predictions.json" title="Registre des prédictions en JSON">',
        f'    <meta property="og:title" content="{esc(title)} — {esc(source["name"])}">',
        f'    <meta property="og:description" content="{esc(subtitle)}">',
        f'    <meta property="og:url" content="{esc(canonical)}">',
        '    <meta property="og:type" content="website">',
        f'    <meta property="og:site_name" content="{esc(source["name"])}">',
        '    <script type="application/ld+json">',
        json.dumps(jsonld_payload, ensure_ascii=False, indent=4),
        "    </script>",
        "    <style>" + _PREDICTIONS_CSS + "    </style>",
        "</head>",
        "<body>",
        '    <div class="progress-rail" aria-hidden="true"></div>',
        '    <nav class="bar column label" aria-label="Site">',
        '        <a href="/">Le Dioptre</a> · <a href="/#traces">Traces</a> · <a href="/predictions/" aria-current="page">Prédictions</a>',
        "    </nav>",
        '    <main class="column">',
        f'        <p class="stamp">{esc(author)} · Registre daté · <a href="/predictions.md">markdown</a> · <a href="/predictions.json">json</a></p>',
        f"        <h1>{esc(title)}</h1>",
        f'        <p class="pred-intro">{intro_html}</p>',
        ledger_html,
        ray_svg(),
        f'        <p class="signature">{esc(author)}</p>',
        '        <section class="door" aria-label="Parler de ce registre">',
        "            <h2>Parler de ce registre</h2>",
        f"            <p>{french_typography(esc(TRACE_TALK_SENTENCE_FR))}</p>",
        f'            <p class="talk">Adresse de réponse directe (SUMU)\u202f: <a href="{esc(talk_url)}"><code>{esc(talk_url)}</code></a></p>',
        '            <p class="talk">Versions machine\u202f: <a href="/predictions.md">/predictions.md</a> · <a href="/predictions.json">/predictions.json</a> · <a href="/">Le Dioptre</a></p>',
        "        </section>",
        '        <footer class="article-foot">',
        '            <nav class="cercle-nav" aria-label="Le cercle">',
        '                <a href="https://le-dioptre.fr/">le-dioptre.fr</a>',
        '                <a href="https://sumu.le-dioptre.fr/">sumu.le-dioptre.fr</a>',
        '                <a href="https://hunkaar.fr/">hunkaar.fr</a>',
        '                <a href="https://jean-emmanuel-combe.fr/">jean-emmanuel-combe.fr</a>',
        '                <a href="https://aurore-combe.fr/">aurore-combe.fr</a>',
        '            </nav>',
        "        </footer>",
        "    </main>",
        "</body>",
        "</html>",
        "",
    ])


def build_predictions(
    source: dict,
    traces: list[dict],
    *,
    predictions_source_path: Path = PREDICTIONS_SOURCE,
    output_dir: Path = SCRIPT_DIR,
) -> list[dict]:
    """Generate /predictions/, /predictions.md, /predictions/index.md, and /predictions.json."""
    doc, predictions = load_predictions(
        source,
        traces,
        predictions_source_path=predictions_source_path,
    )
    pred_dir = output_dir / "predictions"
    pred_dir.mkdir(parents=True, exist_ok=True)
    html_text = render_predictions_html(source, doc, predictions)
    md_text = build_predictions_markdown(source, doc, predictions)
    json_payload = build_predictions_json_payload(source, doc, predictions)

    (pred_dir / "index.html").write_text(html_text, encoding="utf-8")
    (pred_dir / "index.md").write_text(md_text, encoding="utf-8")
    (output_dir / "predictions.md").write_text(md_text, encoding="utf-8")
    (output_dir / "predictions.json").write_text(
        json.dumps(json_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[BUILD] Generated predictions/ + predictions.md + predictions.json ({len(predictions)} entries)")
    return predictions


def build_interface_files(source: dict, *, predictions_source_path: Path = PREDICTIONS_SOURCE) -> None:
    build_articles_json(source)
    traces = load_traces()
    build_predictions(source, traces, predictions_source_path=predictions_source_path)
    full_tokens = build_llms_full(source, traces)
    build_interface_contract(source)
    build_llms_txt(source, traces, full_tokens)
    write_index_html(source, traces, full_tokens)
    build_robots_txt(source)
    build_sitemap_xml(source)
    build_vercel_json(source)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build and deploy Le Dioptre public surfaces.")
    parser.add_argument(
        "--build-only",
        action="store_true",
        help="Regenerate all public files locally without committing or pushing.",
    )
    args = parser.parse_args(argv)
    print("[BUILD] Building machine-first Dioptre interface...")
    build_interface_files(load_interface_source())
    if not args.build_only:
        commit_and_push()


def commit_and_push():
    """Si les artefacts publics diffèrent de HEAD, auto-commit + push.

    Vercel déploie depuis le push. Silencieux si rien à commit."""
    cwd = SCRIPT_DIR
    tracked = [
        "build_interface.py",
        "interface-source.json",
        "predictions-source.json",
        "index.html",
        "index.md",
        "llms.txt",
        "llms-full.txt",
        ".well-known/namilele-interface.json",
        "robots.txt",
        "sitemap.xml",
        "vercel.json",
        "probe_ai_partner_surface.py",
        "favicon.ico",
        "fonts",
        "articles.json",
        "articles",
        "predictions.json",
        "predictions.md",
        "predictions",
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
