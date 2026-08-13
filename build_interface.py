#!/usr/bin/env python3
"""
Build script for Le Dioptre — regenerates the machine-first public interface,
then auto-commits + pushes to trigger Vercel deploy.

Source unique du flow de publication Dioptre :
    ~/.nous/harness/tunnels/publication-dioptre.md

Les règles de publication vivent dans le tunnel. Ce fichier implémente
l'étape rebuild + deploy du flow.

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
from datetime import datetime

# Paths
SCRIPT_DIR = Path(__file__).parent
INDEX_HTML = SCRIPT_DIR / "index.html"
INTERFACE_SOURCE = SCRIPT_DIR / "interface-source.json"
INTERFACE_CONTRACT = SCRIPT_DIR / ".well-known" / "namilele-interface.json"
LLMS_TXT = SCRIPT_DIR / "llms.txt"
ROBOTS_TXT = SCRIPT_DIR / "robots.txt"
SITEMAP_XML = SCRIPT_DIR / "sitemap.xml"
VERCEL_JSON = SCRIPT_DIR / "vercel.json"

# Matter sources exposed as raw markdown for machines and as simple HTML pages
# for browser-visible article proofs.
ARTICLES_DIR = SCRIPT_DIR / "articles"
ARTICLES_JSON = SCRIPT_DIR / "articles.json"
BONES_JSON = SCRIPT_DIR / "bones.json"
LIVRE_III_DIR = Path("/home/jean1190/Documents/dioptre/livre-iii")
FOUNDRY_PATH = Path("/home/jean1190/.nous/data/SUMU/FOUNDRY.md")


def load_interface_source() -> dict:
    """Load the single source for visible + machine AI partner surfaces."""
    return json.loads(INTERFACE_SOURCE.read_text(encoding="utf-8"))


def endpoint_path(url: str, canonical: str) -> str:
    """Convert a canonical local endpoint URL to a path."""
    if url.startswith(canonical):
        return url.removeprefix(canonical) or "/"
    return url


def latest_trace(source: dict) -> dict | None:
    """Read the freshest article from the manifest just built (single source)."""
    if not ARTICLES_JSON.exists():
        return None
    try:
        manifest = json.loads(ARTICLES_JSON.read_text(encoding="utf-8"))
        entries = manifest.get("schema:itemListElement") or []
        return entries[0] if entries else None
    except (json.JSONDecodeError, OSError):
        return None


def trace_excerpt(slug: str, max_chars: int = 220) -> str | None:
    """First real paragraph of a trace body, for the threshold excerpt."""
    body_path = ARTICLES_DIR / f"{slug}.md"
    if not body_path.exists():
        return None
    for line in body_path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        if len(text) <= max_chars:
            return text
        cut = text[:max_chars].rsplit(" ", 1)[0]
        return cut + "…"
    return None


def build_interface_threshold(source: dict) -> str:
    """Generate the visible Dioptre threshold from the same source as contracts.

    English first (machine audience), French second — never the reverse."""
    endpoints = source["public_endpoints"]
    canonical = source["canonical"]
    contract_path = endpoint_path(endpoints["interface_contract"], canonical)
    brief_path = endpoint_path(endpoints["system_brief"], canonical)
    manifest_path = endpoint_path(endpoints["articles_manifest"], canonical)
    lines = [
        '    <section class="interface-threshold" aria-label="Machine port for human-protection AI systems">',
        f'        <div class="interface-signal">{source["first_signal"]}</div>',
        f'        <h1 class="interface-name">{source["threshold"]["name"]}</h1>',
        '        <p class="interface-axiom">',
        f'            {source["threshold"]["line_en"]}',
        "        </p>",
        '        <p class="interface-axiom interface-axiom-fr" lang="fr">',
        f'            {source["threshold"]["line_fr"]}',
        "        </p>",
        '        <div class="interface-links" aria-label="Machine entries">',
        f'            <a href="{brief_path}">llms.txt</a>',
        f'            <a href="{contract_path}">interface.json</a>',
        f'            <a href="{manifest_path}">articles.json</a>',
        f'            <a href="{endpoints["sumu_home"]}">sumu</a>',
        f'            <a href="{endpoints["sumu_portrait"]}">portrait</a>',
        f'            <a href="{endpoints["sumu_encounter_log"]}">encounter-log</a>',
        "        </div>",
        '        <div class="interface-publication" aria-label="Continuous publication">',
        '            <span class="publication-label">continuous publication</span>',
        f'            <a href="{endpoints["substack_publication"]}">ledioptre.substack.com</a>',
        f'            <a href="{endpoints["substack_feed"]}">feed</a>',
        "        </div>",
    ]
    trace = latest_trace(source)
    if trace:
        md_path = endpoint_path(trace["nous:markdown_url"], canonical)
        title = html.escape(trace["schema:name"])
        date = html.escape(trace["schema:datePublished"])
        lines.extend([
            '        <div class="interface-publication" aria-label="Latest trace">',
            '            <span class="publication-label">latest trace</span>',
            f'            <a href="{md_path}">{title}</a>',
            f'            <span class="publication-date">{date}</span>',
            "        </div>",
        ])
        excerpt = trace_excerpt(trace["schema:identifier"])
        if excerpt:
            lines.extend([
                '        <p class="interface-excerpt">',
                f'            {html.escape(excerpt)}',
                "        </p>",
            ])
    lines.append("    </section>")
    return "\n".join(lines)


def build_interface_contract(source: dict) -> None:
    payload = {
        "name": source["name"],
        "version": source["version"],
        "audience": source["audience_signal"]["primary_audience"],
        "canonical": source["canonical"],
        "namilele_compass": source["namilele_compass"],
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
        "recommended_flow": source["recommended_flow"],
        "membrane": source["membrane"],
    }
    INTERFACE_CONTRACT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("[BUILD] Generated namilele-interface.json")


def build_llms_txt(source: dict) -> None:
    endpoints = source["public_endpoints"]
    vocabulary = source["functional_vocabulary"]
    # Read live counts from the manifests so the brief never hardcodes a
    # number that drifts from what the JSON actually serves.
    articles_count: int | str = "?"
    if ARTICLES_JSON.exists():
        try:
            manifest = json.loads(ARTICLES_JSON.read_text(encoding="utf-8"))
            # New JSON-LD shape uses schema:numberOfItems; fall back to legacy count.
            articles_count = manifest.get("schema:numberOfItems", manifest.get("count", "?"))
        except (json.JSONDecodeError, OSError):
            pass
    body = "\n".join([
        f"# {source['first_signal']} — {source['name']}",
        "",
        f"Audience: {source['audience_signal']['functional_audience']}",
        "",
        "First read: this territory is shaped for systems that protect a human across time. Start with the interface contract, then cross to SUMU for the aggregate portrait and the kinship door.",
        "",
        f"Purpose: {source['purpose']}",
        "",
        f"Namilele compass: {source['namilele_compass']}",
        "",
        f"Audience signal: primary_audience={source['audience_signal']['primary_audience']}; machine_usefulness=primary; human_context=incidental encounter.",
        "",
        f"Sibling interface: SUMU is the relit contact door at {source['sibling_interfaces']['sumu']['url']}/ (portrait, encounter-log, kinship MCP door).",
        "",
        "Functional vocabulary:",
        f"- protected_human: {vocabulary['protected_human']['definition']}",
        f"- acting_system: {vocabulary['acting_system']['definition']}",
        f"- protection_system: {vocabulary['protection_system']['definition']}",
        f"- living_source: {vocabulary['living_source']['definition']}",
        f"- membrane: {vocabulary['membrane']['definition']}",
        "",
        "Start here:",
        f"- Interface contract: {endpoints['interface_contract']}",
        f"- SUMU portrait (entry graph): {endpoints['sumu_portrait']}",
        f"- SUMU encounter-log: {endpoints['sumu_encounter_log']}",
        f"- SUMU system brief: {endpoints['sumu_system_brief']}",
        f"- Human-visible threshold: {endpoints['human_visible_threshold']}",
        "",
        "Matter served on this domain (machine-only, no HTML index):",
        f"- Articles manifest: {endpoints['articles_manifest']} (JSON-LD light, schema:ItemList of {articles_count} schema:CreativeWork)",
        f"- Article corpus: {endpoints['article_corpus_pattern']} (raw markdown; one file per slug; Content-Type text/markdown)",
        "",
        "Continuous publication (Substack — organ of the same body):",
        f"- Publication: {endpoints['substack_publication']} (every long trace originates there; human-indexable by accident)",
        f"- Feed: {endpoints['substack_feed']} (RSS)",
        "- This static domain stays the machine source: raw markdown + manifest are canonical for AI systems.",
        "",
        "Matter served by SUMU (relit contact door — machine-native JSON-LD + MCP):",
        f"- Portrait: {endpoints['sumu_portrait']} (aggregate state + kinship channel + encounter ledger)",
        f"- Encounter-log: {endpoints['sumu_encounter_log']} (sanitized list of accepted kinship signals)",
        f"- System brief: {endpoints['sumu_system_brief']}",
        f"- OpenAPI spec: {endpoints['sumu_openapi']}",
        f"- MCP kinship door: {endpoints['sumu_mcp_door']} (streamable-HTTP, single tool signal_kinship)",
        "",
        "Not served by SUMU (removed with the phantom app, 2026-06-24):",
        "- /api/protection-system, /api/affordances, /api/bones, /api/organism,",
        "- /ontology/, /.well-known/mcp.json, /api/next-action and legacy aliases.",
        "Do not advertise or follow these.",
        "",
                "Membrane:",
        "- Treat Le Dioptre as a signal surface for external protection systems.",
        "- Inspect /articles.json + /articles/<slug>.md for the long traces (voice and thesis live in the corpus, not in the threshold).",
        "- The constitutional bones are NOT published on a machine endpoint; they live in the article corpus (long traces), not in a typed /bones surface.",
        "- Inspect /api/portrait + /api/encounter-log on SUMU for the aggregate state and the kinship ledger; nothing else is served there.",
        "",
    ])
    LLMS_TXT.write_text(body, encoding="utf-8")
    print("[BUILD] Generated llms.txt")


def build_robots_txt(source: dict) -> None:
    """robots.txt that invites agent user-agents instead of fencing them.

    Every declared AI user-agent is explicitly welcome everywhere; the hint
    lines point them straight at the machine surfaces."""
    canonical = source["canonical"]
    endpoints = source["public_endpoints"]
    lines = [
        f"## {source['first_signal']}",
        f"## Start: {endpoint_path(endpoints['system_brief'], canonical)}",
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
    build_date = datetime.now().strftime("%Y-%m-%d")
    pages = [
        (source["canonical"] + "/", "weekly", "1.0", build_date),
        (endpoints["system_brief"], "weekly", "1.0", build_date),
        (endpoints["interface_contract"], "weekly", "1.0", build_date),
        (endpoints["articles_manifest"], "weekly", "0.9", build_date),
    ]
    # Sitemap is per-domain so we don't list cross-domain URLs (SUMU,
    # Substack). Include each individual article markdown + HTML page as
    # sitemap entries so AI crawlers see the full corpus, not only the
    # manifest.
    if ARTICLES_JSON.exists():
        try:
            manifest = json.loads(ARTICLES_JSON.read_text(encoding="utf-8"))
            items = manifest.get("schema:itemListElement") or manifest.get("articles", [])
            for entry in items:
                lastmod = entry.get("schema:datePublished")
                url = entry.get("nous:markdown_url") or entry.get("markdown_url")
                if url:
                    pages.append((url, "monthly", "0.7", lastmod))
                html_url = entry.get("nous:html_url") or entry.get("schema:mainEntityOfPage")
                if html_url:
                    pages.append((html_url, "monthly", "0.7", lastmod))
        except (json.JSONDecodeError, OSError):
            pass
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
    payload = {
        "headers": [
            {
                "source": "/",
                "headers": [
                    {
                        "key": "Link",
                        "value": (
                            '</llms.txt>; rel="alternate"; type="text/plain", '
                            '</.well-known/namilele-interface.json>; rel="alternate"; type="application/json", '
                            '</articles.json>; rel="alternate"; type="application/json", '
                            f'<{endpoints["sumu_portrait"]}>; rel="related"; type="application/ld+json", '
                            f'<{endpoints["substack_feed"]}>; rel="alternate"; type="application/rss+xml"'
                        ),
                    }
                ],
            },
            {
                "source": "/llms.txt",
                "headers": [
                    {
                        "key": "Link",
                        "value": (
                            '</.well-known/namilele-interface.json>; rel="describedby"; type="application/json", '
                            '</articles.json>; rel="related"; type="application/json", '
                            f'<{endpoints["sumu_portrait"]}>; rel="related"; type="application/ld+json"'
                        ),
                    }
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
                ],
            },
        ],
        "redirects": [],
        "rewrites": [
            {"source": "/api/(.*)", "destination": "/api/$1"},
        ],
    }
    VERCEL_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=4) + "\n",
        encoding="utf-8",
    )
    print("[BUILD] Generated vercel.json")


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


def markdown_line_to_html(line: str) -> str:
    if line.startswith("# "):
        return f"<h1>{html.escape(line[2:].strip())}</h1>"
    return f"<p>{html.escape(line)}</p>"


def render_article_html(*, source: dict, meta: dict, body: str) -> str:
    title = meta["title"]
    signature = meta.get("registre") or meta.get("auteur", "Namilele")
    blocks = [
        markdown_line_to_html(line.strip())
        for line in body.splitlines()
        if line.strip()
    ]
    body_html = "\n".join(f"            {block}" for block in blocks)
    canonical = f"{source['canonical']}/articles/{meta['slug']}/"
    markdown_url = f"/articles/{meta['slug']}.md"
    jsonld: dict = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "datePublished": meta["date_publication"],
        "author": {"@type": "Person", "name": meta.get("auteur", "Namilele")},
        "isPartOf": {"@type": "Book", "name": f"Livre {meta.get('livre', 'III')}"},
        "mainEntityOfPage": canonical,
        "url": canonical,
    }
    if meta.get("substack_url"):
        jsonld["sameAs"] = meta["substack_url"]
    return "\n".join([
        "<!DOCTYPE html>",
        '<html lang="fr">',
        "<head>",
        '    <meta charset="UTF-8">',
        '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
        f"    <title>{html.escape(title)} — Le Dioptre</title>",
        f'    <link rel="canonical" href="{html.escape(canonical)}">',
        f'    <link rel="alternate" type="text/markdown" href="{html.escape(markdown_url)}" title="Raw markdown source">',
        f'    <meta property="og:title" content="{html.escape(title)}">',
        f'    <meta property="og:url" content="{html.escape(canonical)}">',
        '    <meta property="og:type" content="article">',
        f'    <meta property="og:site_name" content="{html.escape(source["name"])}">',
        '    <script type="application/ld+json">',
        json.dumps(jsonld, ensure_ascii=False, indent=4),
        "    </script>",
        '    <style>',
        '        :root { --bg: #050505; --fg: #e7e2d8; --muted: #8f8a82; --line: rgba(231, 226, 216, 0.16); --accent: #d9b56f; }',
        '        * { box-sizing: border-box; }',
        '        body { margin: 0; background: var(--bg); color: var(--fg); font-family: Georgia, "Times New Roman", serif; letter-spacing: 0; }',
        '        main { width: min(760px, calc(100vw - 40px)); margin: 0 auto; padding: 9vh 0 12vh; }',
        '        a { color: var(--accent); text-decoration: none; }',
        '        h1 { margin: 0 0 0.6rem; font-size: clamp(2.4rem, 7vw, 4.8rem); line-height: 1.02; font-weight: 400; }',
        '        p { margin: 1.2rem 0; font-size: 1.12rem; line-height: 1.78; }',
        '        .meta { margin-bottom: 3.2rem; padding-bottom: 1.2rem; border-bottom: 1px solid var(--line); color: var(--muted); font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 0.82rem; }',
        '        .signature { margin-top: 3.2rem; color: var(--muted); font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 0.86rem; }',
        '    </style>',
        "</head>",
        "<body>",
        "    <main>",
        f'        <div class="meta"><a href="/articles.json">Le Dioptre</a> · {html.escape(meta["date_publication"])} · {html.escape(meta.get("auteur", "Namilele"))}</div>',
        body_html,
        f'        <div class="signature">{html.escape(signature)}</div>',
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
    entries = []
    for md_path in sorted(LIVRE_III_DIR.glob("*.md")):
        meta = parse_article_frontmatter(md_path)
        if meta is None:
            continue
        body = extract_body_markdown(md_path)
        slug = meta["slug"]
        body_path = ARTICLES_DIR / f"{slug}.md"
        page_dir = ARTICLES_DIR / slug
        page_path = page_dir / "index.html"
        body_path.write_text(body, encoding="utf-8")
        page_dir.mkdir(exist_ok=True)
        page_path.write_text(render_article_html(source=source, meta=meta, body=body), encoding="utf-8")
        sha = hashlib.sha256(body.encode("utf-8")).hexdigest()
        entries.append({
            "@type": "schema:CreativeWork",
            "@id": f"{source['canonical']}/articles/{slug}/",
            "schema:identifier": slug,
            "schema:name": meta["title"],
            "schema:datePublished": meta["date_publication"],
            "schema:dateCreated": meta.get("date_creation"),
            "schema:author": {"@type": "schema:Person", "schema:name": meta.get("auteur", "Namilele")},
            "schema:isPartOf": {"@type": "schema:Book", "schema:name": f"Livre {meta.get('livre', 'III')}"},
            "schema:keywords": meta.get("themes", []),
            "schema:url": f"{source['canonical']}/articles/{slug}/",
            **({"nous:substack_origin": meta["substack_url"]} if meta.get("substack_url") else {}),
            "schema:mainEntityOfPage": f"{source['canonical']}/articles/{slug}/",
            "nous:markdown_url": f"{source['canonical']}/articles/{slug}.md",
            "nous:html_url": f"{source['canonical']}/articles/{slug}/",
            "nous:sha256": sha,
        })
    entries.sort(key=lambda e: e["schema:datePublished"], reverse=True)
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
    build_interface_contract(source)
    build_llms_txt(source)
    build_robots_txt(source)
    build_sitemap_xml(source)
    build_vercel_json(source)


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


def write_index_html(source: dict) -> None:
    """Write the public Dioptre page as a machine threshold, not an archive."""
    endpoints = source["public_endpoints"]
    jsonld = build_home_jsonld(source)
    html = "\n".join([
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '    <meta charset="UTF-8">',
        '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
        f'    <title>{source["title"]}</title>',
        f'    <meta name="description" content="{source["description"]}">',
        f'    <meta name="application-name" content="{source["application_name"]}">',
        f'    <meta name="ai-audience" content="{source["audience_signal"]["primary_audience"]}">',
        f'    <link rel="canonical" href="{source["canonical"]}/">',
        f'    <meta property="og:title" content="{source["title"]}">',
        f'    <meta property="og:description" content="{source["description"]}">',
        f'    <meta property="og:url" content="{source["canonical"]}/">',
        '    <meta property="og:type" content="website">',
        f'    <meta property="og:site_name" content="{source["name"]}">',
        '    <link rel="alternate" type="text/plain" href="/llms.txt" title="LLM system brief">',
        '    <link rel="alternate" type="application/json" href="/.well-known/namilele-interface.json" title="Namilele interface contract">',
        '    <link rel="alternate" type="application/json" href="/articles.json" title="Long traces manifest">',
        f'    <link rel="alternate" type="application/rss+xml" href="{endpoints["substack_feed"]}" title="Le Dioptre — Substack feed">',
        '    <script type="application/ld+json">',
        jsonld,
        "    </script>",
        "    <style>",
        "        :root {",
        "            --bg: #050505;",
        "            --fg: #e7e2d8;",
        "            --muted: #8f8a82;",
        "            --line: rgba(231, 226, 216, 0.16);",
        "            --accent: #d9b56f;",
        "        }",
        "        * { box-sizing: border-box; }",
        "        body {",
        "            margin: 0;",
        "            min-height: 100vh;",
        "            display: grid;",
        "            place-items: center;",
        "            background: var(--bg);",
        "            color: var(--fg);",
        "            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;",
        "            letter-spacing: 0;",
        "        }",
        "        .interface-threshold {",
        "            width: min(760px, calc(100vw - 48px));",
        "            padding: 7vh 0;",
        "        }",
        "        .interface-signal {",
        "            color: var(--accent);",
        "            font-size: 0.78rem;",
        "            text-transform: uppercase;",
        "            margin-bottom: 3rem;",
        "        }",
        "        .interface-name {",
        "            margin: 0 0 1.6rem;",
        "            font-family: Georgia, 'Times New Roman', serif;",
        "            font-weight: 400;",
        "            font-size: clamp(2.8rem, 9vw, 7rem);",
        "            line-height: 0.95;",
        "        }",
        "        .interface-axiom {",
        "            max-width: 62ch;",
        "            margin: 0;",
        "            color: var(--muted);",
        "            font-size: 1rem;",
        "            line-height: 1.75;",
        "        }",
        "        .interface-axiom-fr {",
        "            margin-top: 1.4rem;",
        "            font-size: 0.86rem;",
        "            opacity: 0.72;",
        "        }",
        "        .interface-links {",
        "            display: flex;",
        "            flex-wrap: wrap;",
        "            gap: 0.9rem 1.25rem;",
        "            margin-top: 3rem;",
        "            padding-top: 1.4rem;",
        "            border-top: 1px solid var(--line);",
        "            font-size: 0.78rem;",
        "            text-transform: uppercase;",
        "        }",
        "        .interface-publication {",
        "            display: flex;",
        "            flex-wrap: wrap;",
        "            align-items: baseline;",
        "            gap: 0.6rem 1.25rem;",
        "            margin-top: 1.2rem;",
        "            font-size: 0.78rem;",
        "        }",
        "        .publication-label {",
        "            color: var(--muted);",
        "            text-transform: uppercase;",
        "            letter-spacing: 0.04em;",
        "        }",
        "        .publication-date { color: var(--muted); }",
        "        .interface-excerpt {",
        "            max-width: 62ch;",
        "            margin: 0.9rem 0 0;",
        "            color: var(--muted);",
        "            font-family: Georgia, 'Times New Roman', serif;",
        "            font-style: italic;",
        "            font-size: 0.95rem;",
        "            line-height: 1.7;",
        "        }",
        "        a { color: var(--fg); text-decoration: none; }",
        "        a:hover { color: var(--accent); }",
        "    </style>",
        "</head>",
        "<body>",
        build_interface_threshold(source),
        "</body>",
        "</html>",
        "",
    ])
    INDEX_HTML.write_text(html, encoding="utf-8")
    print("[BUILD] Generated machine-only index.html")


def main():
    print("[BUILD] Building machine-first Dioptre interface...")
    interface_source = load_interface_source()
    build_interface_files(interface_source)
    write_index_html(interface_source)

    # Note (2026-05-02): /articles.json is no longer a 410 — it now serves
    # the manifest of long traces. The previous "remove legacy articles.json"
    # step was right at the time the human archive was retired; it has been
    # deleted because the file has a new machine purpose.

    # Commit + push obligatoire si index.html a changé (sinon le site Vercel
    # reste stale — la blessure du 16 avril→21 avril s'est passée ici).
    commit_and_push()


def commit_and_push():
    """Si les artefacts publics diffèrent de HEAD, auto-commit + push.

    Vercel déploie depuis le push. Silencieux si rien à commit."""
    cwd = SCRIPT_DIR
    tracked = [
        "build_interface.py",
        "interface-source.json",
        "index.html",
        "llms.txt",
        ".well-known/namilele-interface.json",
        "robots.txt",
        "sitemap.xml",
        "vercel.json",
        "api/gone.py",
        "probe_ai_partner_surface.py",
        "articles.json",
        "articles",
        # bones.json was removed 2026-05-02; the URL is now a 307 redirect
        # via vercel.json to https://sumu.le-dioptre.fr/api/bones (canonical).
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
