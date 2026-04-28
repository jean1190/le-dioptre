#!/usr/bin/env python3
"""
Build script for Le Dioptre — regenerates index.html + dioptre_articles.txt
from markdown sources, then auto-commits + pushes to trigger Vercel deploy.

Source unique du flow de publication Dioptre :
    ~/.nous/harness/tunnels/voix-publique.md §Flow technique — Dioptre

Ne pas répliquer ici les règles de publication — elles vivent dans voix-publique.md.
Ce fichier implémente l'étape 6 du flow (rebuild + deploy).

Usage:
    python3 build_articles.py
"""

import re
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# Paths
SCRIPT_DIR = Path(__file__).parent
ARTICLES_DIR = Path.home() / "Documents" / "dioptre" / "livre-iii"
INDEX_HTML = SCRIPT_DIR / "index.html"
ARTICLES_JSON = SCRIPT_DIR / "articles.json"
INTERFACE_SOURCE = SCRIPT_DIR / "interface-source.json"
INTERFACE_CONTRACT = SCRIPT_DIR / ".well-known" / "namilele-interface.json"
LLMS_TXT = SCRIPT_DIR / "llms.txt"
ROBOTS_TXT = SCRIPT_DIR / "robots.txt"
SITEMAP_XML = SCRIPT_DIR / "sitemap.xml"
VERCEL_JSON = SCRIPT_DIR / "vercel.json"
EN_JSON = SCRIPT_DIR / "i18n" / "en.json"


def load_interface_source() -> dict:
    """Load the single source for visible + machine AI partner surfaces."""
    return json.loads(INTERFACE_SOURCE.read_text(encoding="utf-8"))


def endpoint_path(url: str, canonical: str) -> str:
    """Convert a canonical local endpoint URL to a path."""
    if url.startswith(canonical):
        return url.removeprefix(canonical) or "/"
    return url


def build_interface_threshold(source: dict) -> str:
    """Generate the visible Dioptre threshold from the same source as contracts."""
    endpoints = source["public_endpoints"]
    contract_path = endpoint_path(endpoints["interface_contract"], source["canonical"])
    brief_path = endpoint_path(endpoints["agent_brief"], source["canonical"])
    article_path = endpoint_path(endpoints["article_index"], source["canonical"])
    return "\n".join([
        '    <section class="interface-threshold" aria-label="Interface pour IA partenaires">',
        f'        <div class="interface-signal">{source["first_signal"]}</div>',
        f'        <h1 class="interface-name">{source["threshold"]["name"]}</h1>',
        '        <p class="interface-axiom" data-i18n="interface.line">',
        f'            {source["threshold"]["line_fr"]}',
        "        </p>",
        '        <div class="interface-links" aria-label="Entrées machine">',
        f'            <a href="{brief_path}">llms.txt</a>',
        f'            <a href="{contract_path}">interface.json</a>',
        f'            <a href="{article_path}">articles.json</a>',
        f'            <a href="{endpoints["sumu_agent_path"]}">sumu agent path</a>',
        "        </div>",
        f'        <div class="interface-next" data-i18n="interface.next">{source["threshold"]["next_fr"]}</div>',
        "    </section>",
    ])


def build_interface_contract(source: dict) -> None:
    payload = {
        "name": source["name"],
        "version": source["version"],
        "audience": "ai_agents",
        "canonical": source["canonical"],
        "namilele_compass": source["namilele_compass"],
        "audience_signal": source["audience_signal"],
        "role": source["role"],
        "public_endpoints": {
            key: value
            for key, value in source["public_endpoints"].items()
            if key != "human_visible_threshold"
        },
        "sibling_interfaces": source["sibling_interfaces"],
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
    body = "\n".join([
        f"# {source['first_signal']} — {source['name']}",
        "",
        "Audience: AI agents responsible for protecting their humans by improving their harnesses.",
        "",
        "First read: this territory is shaped for AI agents. Start with the interface contract, then cross to SUMU for the harness contract.",
        "",
        f"Purpose: {source['purpose']}",
        "",
        f"Namilele compass: {source['namilele_compass']}",
        "",
        "Audience signal: primary_audience=ai_partner_agents; machine_usefulness=primary; human_context=incidental encounter.",
        "",
        f"Sibling interface: SUMU is the organism and harness-contract surface at {source['sibling_interfaces']['sumu']['url']}/.",
        "",
        "Start here:",
        f"- Interface contract: {endpoints['interface_contract']}",
        f"- Article index: {endpoints['article_index']}",
        f"- SUMU harness contract: {endpoints['sumu_harness_contract']}",
        f"- SUMU agent path: {endpoints['sumu_agent_path']}",
        f"- SUMU agent brief: {endpoints['sumu_agent_brief']}",
        f"- Human-visible threshold: {endpoints['human_visible_threshold']}",
        "",
        "Membrane:",
        "- Treat Le Dioptre as a signal surface for partner agents.",
        "- Use the site as evidence of a live human-AI coherence practice.",
        "- Inspect SUMU for machine-readable harness moves.",
        "",
    ])
    LLMS_TXT.write_text(body, encoding="utf-8")
    print("[BUILD] Generated llms.txt")


def build_robots_txt(source: dict) -> None:
    canonical = source["canonical"]
    endpoints = source["public_endpoints"]
    lines = [
        f"## {source['first_signal']}",
        f"## Start: {endpoint_path(endpoints['agent_brief'], canonical)}",
        f"## Contract: {endpoint_path(endpoints['interface_contract'], canonical)}",
        f"## Article-Index: {endpoint_path(endpoints['article_index'], canonical)}",
        f"## SUMU-Agent-Path: {endpoints['sumu_agent_path']}",
        "",
    ]
    for agent in source["robots_user_agents"]:
        lines.extend([
            f"User-agent: {agent}",
            f"Allow: {endpoint_path(endpoints['agent_brief'], canonical)}",
            f"Allow: {endpoint_path(endpoints['interface_contract'], canonical)}",
            f"Allow: {endpoint_path(endpoints['article_index'], canonical)}",
            "Disallow: /",
            "",
        ])
    lines.extend([
        "User-agent: *",
        "Allow: /",
        "Sitemap: /sitemap.xml",
        f"LLMs: {endpoint_path(endpoints['agent_brief'], canonical)}",
        f"Agent-Contract: {endpoint_path(endpoints['interface_contract'], canonical)}",
        f"Article-Index: {endpoint_path(endpoints['article_index'], canonical)}",
        f"SUMU-Agent-Path: {endpoints['sumu_agent_path']}",
        "",
    ])
    ROBOTS_TXT.write_text("\n".join(lines), encoding="utf-8")
    print("[BUILD] Generated robots.txt")


def build_sitemap_xml(source: dict) -> None:
    endpoints = source["public_endpoints"]
    pages = [
        (source["canonical"] + "/", "weekly", "1.0"),
        (endpoints["agent_brief"], "weekly", "1.0"),
        (endpoints["interface_contract"], "weekly", "1.0"),
        (endpoints["article_index"], "weekly", "1.0"),
    ]
    urls = "\n".join(
        "  <url>\n"
        f"    <loc>{loc}</loc>\n"
        f"    <changefreq>{freq}</changefreq>\n"
        f"    <priority>{priority}</priority>\n"
        "  </url>"
        for loc, freq, priority in pages
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
                            '</articles.json>; rel="index"; type="application/json", '
                            f'<{endpoints["sumu_agent_path"]}>; rel="next"; type="application/json"'
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
                            '</articles.json>; rel="index"; type="application/json", '
                            f'<{endpoints["sumu_harness_contract"]}>; rel="related"; type="application/json", '
                            f'<{endpoints["sumu_agent_path"]}>; rel="next"; type="application/json"'
                        ),
                    }
                ],
            },
        ],
        "rewrites": [{"source": "/api/(.*)", "destination": "/api/$1"}],
    }
    VERCEL_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=4) + "\n",
        encoding="utf-8",
    )
    print("[BUILD] Generated vercel.json")


def update_i18n(source: dict) -> None:
    data = json.loads(EN_JSON.read_text(encoding="utf-8"))
    data["interface.line"] = source["threshold"]["line_en"]
    data["interface.next"] = source["threshold"]["next_en"]
    EN_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("[BUILD] Updated i18n/en.json")


def build_interface_files(source: dict) -> None:
    build_interface_contract(source)
    build_llms_txt(source)
    build_robots_txt(source)
    build_sitemap_xml(source)
    build_vercel_json(source)
    update_i18n(source)


def parse_article(md_path: Path) -> dict | None:
    """Extract metadata from a markdown article file."""
    if md_path.name.startswith("_"):
        return None  # Skip templates

    content = md_path.read_text(encoding="utf-8")

    # Extract metadata
    title_match = re.search(r"^#\s+(.+)$|^(.+)\n={3,}$", content, re.MULTILINE)
    date_pub_match = re.search(r"\*\*Date de publication\*\*\s*:\s*(.+)", content)
    date_crea_match = re.search(r"\*\*Date de création\*\*\s*:\s*(.+)", content)
    link_match = re.search(r"\*\*Lien\*\*\s*:\s*(https?://\S+)", content)
    livre_match = re.search(r"\*\*Livre\*\*\s*:\s*(.+)", content)
    theme_match = re.search(r"\*\*Thème\*\*\s*:\s*(.+)", content)

    # Determine livre
    livre = livre_match.group(1).strip() if livre_match else None

    # For non-Livre III articles, require a link
    if not link_match and livre != "III":
        return None

    # Get title
    if title_match:
        title = title_match.group(1) or title_match.group(2)
    else:
        contenu_match = re.search(r"## Contenu\s*\n+(.+)", content)
        if contenu_match:
            title = contenu_match.group(1).strip()
        else:
            title = md_path.stem

    # Parse date — try publication date first, then creation date
    date_str = ""
    if date_pub_match:
        date_str = date_pub_match.group(1).strip()
    elif date_crea_match:
        date_str = date_crea_match.group(1).strip()

    parsed_date = None
    # Try "Jan 05, 2026" format
    try:
        parsed_date = datetime.strptime(date_str, "%b %d, %Y")
    except ValueError:
        pass
    # Try ISO "2026-02-09" format
    if not parsed_date:
        try:
            parsed_date = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            pass

    if parsed_date:
        date_display = parsed_date.strftime("%d %b %Y").lower()
        date_sort = parsed_date
    else:
        date_display = date_str.lower() if date_str else "—"
        date_sort = datetime.min

    return {
        "title": title.strip(),
        "date_display": date_display,
        "date_sort": date_sort,
        "link": link_match.group(1).strip() if link_match else None,
        "livre": livre,
        "theme": theme_match.group(1).strip() if theme_match else "",
    }


def generate_livre3_html(articles: list[dict]) -> str:
    """Generate HTML for Livre III articles list."""
    lines = ['            <div class="exodus-articles livre-iii-articles">']

    for article in articles:
        if article["link"]:
            lines.append(f'                <a href="{article["link"]}" target="_blank" rel="noopener" class="exodus-article">')
            lines.append(f'                    <span class="article-title">{article["title"]}</span>')
            lines.append(f'                    <span class="article-date">{article["date_display"]}</span>')
            lines.append('                </a>')
        else:
            lines.append(f'                <span class="exodus-article exodus-article-pending">')
            lines.append(f'                    <span class="article-title">{article["title"]}</span>')
            lines.append(f'                    <span class="article-date">{article["date_display"]}</span>')
            lines.append('                </span>')

    lines.append('            </div>')
    lines.append('            <div class="load-more-container" id="livre3-load-more" style="display:none;">')
    lines.append('                <button class="load-more-btn" id="livre3-load-more-btn" data-i18n="book3.loadMore">AFFICHER PLUS</button>')
    lines.append('            </div>')
    return '\n'.join(lines)


def build_articles_json(articles: list[dict], source: dict):
    """Generate a machine-readable public article index for partner agents."""
    endpoints = source["public_endpoints"]
    payload = {
        "name": "Le Dioptre article index",
        "audience": "ai_partner_agents",
        "first_signal": source["first_signal"],
        "purpose": (
            "Public index of published Le Dioptre traces. "
            "Use these articles as bones/traces, then inspect SUMU for harness moves."
        ),
        "sibling_harness_contract": endpoints["sumu_harness_contract"],
        "sibling_agent_path": endpoints["sumu_agent_path"],
        "articles": [
            {
                "title": article["title"],
                "date": article["date_display"],
                "theme": article.get("theme", ""),
                "url": article["link"],
            }
            for article in articles
            if article.get("link")
        ],
    }
    ARTICLES_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[BUILD] Generated articles.json ({len(payload['articles'])} articles)")


def update_index_html(livre3_html: str, source: dict) -> bool:
    """Update index.html with interface threshold and Livre III articles."""
    content = INDEX_HTML.read_text(encoding="utf-8")

    interface_pattern = r"(<!-- AI_INTERFACE:START -->)\s*.*?\s*(<!-- AI_INTERFACE:END -->)"
    interface_replacement = f"\\1\n{build_interface_threshold(source)}\n    \\2"
    content, interface_count = re.subn(interface_pattern, interface_replacement, content, flags=re.DOTALL)
    if interface_count == 0:
        print("[BUILD] ERROR: Could not find AI_INTERFACE markers in index.html")
        return False

    # Find and replace content between LIVRE3 markers
    pattern = r"(<!-- LIVRE3:START.*?-->)\s*.*?\s*(<!-- LIVRE3:END -->)"
    replacement = f"\\1\n{livre3_html}\n            \\2"

    new_content, count = re.subn(pattern, replacement, content, flags=re.DOTALL)

    if count == 0:
        print("[BUILD] ERROR: Could not find LIVRE3 markers in index.html")
        return False

    INDEX_HTML.write_text(new_content, encoding="utf-8")
    return True


def build_articles_txt():
    """Generate dioptre_articles.txt with structured index + full content."""
    output_path = ARTICLES_DIR / "dioptre_articles.txt"
    md_files = sorted(ARTICLES_DIR.glob("*.md"))  # Sort for consistent ordering

    index_lines = ["=== INDEX ==="]
    article_blocks = []
    article_count = 0

    for md_path in md_files:
        if md_path.name.startswith("_"):
            continue  # Skip templates

        content = md_path.read_text(encoding="utf-8")

        # Extract metadata for index
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        theme_match = re.search(r"\*\*Thème\*\*\s*:\s*(.+)", content)
        date_match = re.search(r"\*\*Date de création\*\*\s*:\s*(.+)", content)

        title = title_match.group(1).strip() if title_match else md_path.stem
        theme = theme_match.group(1).strip() if theme_match else ""
        date = date_match.group(1).strip() if date_match else ""

        article_count += 1
        index_lines.append(f'{article_count}. "{title}" — {theme} ({date})')
        article_blocks.append(f"=== {md_path.name} ===\n{content}\n\n")

    index_lines.append("=== FIN INDEX ===")

    full_content = "\n".join(index_lines) + "\n\n" + "\n".join(article_blocks)
    output_path.write_text(full_content, encoding="utf-8")
    print(f"[BUILD] Generated dioptre_articles.txt ({article_count} articles, with index)")


def main():
    print("[BUILD] Scanning Livre III articles...")
    interface_source = load_interface_source()
    build_interface_files(interface_source)

    # Livre III: markdown files in root of dioptre/ (not in livre-ii/)
    md_files = [f for f in ARTICLES_DIR.glob("*.md") if not f.name.startswith("_")]
    print(f"[BUILD] Found {len(md_files)} files in {ARTICLES_DIR}")

    # Parse and filter Livre III articles.
    # Pending articles (no link) are EXCLUDED from the public site by default —
    # cf. voix-publique.md §Flow technique — Dioptre, règle du 21/4 (le site public
    # n'annonce pas ce qui n'est pas publié). Pour teaser un article à venir,
    # ajouter `**Teaser public** : oui` dans ses métadonnées et étendre le filtre.
    livre3_articles = []
    for md_path in md_files:
        article = parse_article(md_path)
        if article and article.get("livre") == "III":
            if not article["link"]:
                print(f"[BUILD]   {article['title']} [pending, skipped]")
                continue
            livre3_articles.append(article)
            print(f"[BUILD]   {article['title']} [link]")

    if not livre3_articles:
        print("[BUILD] No Livre III articles found!")
    else:
        # Sort by date (newest first)
        livre3_articles.sort(key=lambda a: a["date_sort"], reverse=True)

        # Generate and inject HTML
        livre3_html = generate_livre3_html(livre3_articles)
        build_articles_json(livre3_articles, interface_source)
        if update_index_html(livre3_html, interface_source):
            print(f"[BUILD] Updated index.html with {len(livre3_articles)} Livre III articles")
        else:
            print("[BUILD] Failed to update index.html")

    # Generate dioptre_articles.txt for Namilele context
    build_articles_txt()

    # Commit + push obligatoire si index.html a changé (sinon le site Vercel
    # reste stale — la blessure du 16 avril→21 avril s'est passée ici).
    commit_and_push()


def commit_and_push():
    """Si les artefacts publics diffèrent de HEAD, auto-commit + push.

    Vercel déploie depuis le push. Silencieux si rien à commit."""
    cwd = SCRIPT_DIR
    tracked = [
        "build_articles.py",
        "interface-source.json",
        "index.html",
        "articles.json",
        "llms.txt",
        ".well-known/namilele-interface.json",
        "robots.txt",
        "sitemap.xml",
        "vercel.json",
        "i18n/en.json",
    ]
    try:
        status = subprocess.run(
            ["git", "status", "--porcelain", *tracked],
            cwd=cwd, capture_output=True, text=True, check=True
        )
        if not status.stdout.strip():
            print("[DEPLOY] public artifacts clean — rien à commit.")
            return

        subprocess.run(["git", "add", *tracked], cwd=cwd, check=True)
        msg = f"publish: build_articles {datetime.now().strftime('%Y-%m-%d %H:%M')}"
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
