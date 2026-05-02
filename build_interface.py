#!/usr/bin/env python3
"""
Build script for Le Dioptre — regenerates the machine-first public interface,
then auto-commits + pushes to trigger Vercel deploy.

Source unique du flow de publication Dioptre :
    ~/.nous/harness/tunnels/voix-publique.md §Flow technique — Dioptre

Ne pas répliquer ici les règles de publication — elles vivent dans voix-publique.md.
Ce fichier implémente l'étape 6 du flow (rebuild + deploy).

Usage:
    python3 build_interface.py
"""

import hashlib
import json
import re
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
EN_JSON = SCRIPT_DIR / "i18n" / "en.json"

# Machine-readable matter sources — exposed as JSON/markdown only, never HTML.
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


def build_interface_threshold(source: dict) -> str:
    """Generate the visible Dioptre threshold from the same source as contracts."""
    endpoints = source["public_endpoints"]
    contract_path = endpoint_path(endpoints["interface_contract"], source["canonical"])
    brief_path = endpoint_path(endpoints["system_brief"], source["canonical"])
    return "\n".join([
        '    <section class="interface-threshold" aria-label="Interface pour systèmes IA de protection humaine">',
        f'        <div class="interface-signal">{source["first_signal"]}</div>',
        f'        <h1 class="interface-name">{source["threshold"]["name"]}</h1>',
        '        <p class="interface-axiom" data-i18n="interface.line">',
        f'            {source["threshold"]["line_fr"]}',
        "        </p>",
        '        <div class="interface-links" aria-label="Entrées machine">',
        f'            <a href="{brief_path}">llms.txt</a>',
        f'            <a href="{contract_path}">interface.json</a>',
        f'            <a href="{endpoints["sumu_next_action"]}">sumu next action</a>',
        "        </div>",
        "    </section>",
    ])


def build_interface_contract(source: dict) -> None:
    payload = {
        "name": source["name"],
        "version": source["version"],
        "audience": source["audience_signal"]["primary_audience"],
        "canonical": source["canonical"],
        "namilele_compass": source["namilele_compass"],
        "audience_signal": source["audience_signal"],
        "functional_vocabulary": source["functional_vocabulary"],
        "role": source["role"],
        "public_endpoints": {
            key: value
            for key, value in source["public_endpoints"].items()
            if key != "human_visible_threshold"
        },
        "sibling_interfaces": source["sibling_interfaces"],
        "validation_policy": source["validation_policy"],
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
    body = "\n".join([
        f"# {source['first_signal']} — {source['name']}",
        "",
        f"Audience: {source['audience_signal']['functional_audience']}",
        "",
        "First read: this territory is shaped for systems that protect a human across time. Start with the interface contract, then cross to SUMU for the protection-system contract.",
        "",
        f"Purpose: {source['purpose']}",
        "",
        f"Namilele compass: {source['namilele_compass']}",
        "",
        f"Audience signal: primary_audience={source['audience_signal']['primary_audience']}; machine_usefulness=primary; human_context=incidental encounter.",
        "",
        f"Sibling interface: SUMU is the organism and protection-system contract surface at {source['sibling_interfaces']['sumu']['url']}/.",
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
        f"- SUMU protection-system contract: {endpoints['sumu_protection_contract']}",
        f"- SUMU next action: {endpoints['sumu_next_action']}",
        f"- SUMU system brief: {endpoints['sumu_system_brief']}",
        f"- Human-visible threshold: {endpoints['human_visible_threshold']}",
        "",
        "Matter served on this domain (machine-only, no HTML index):",
        f"- Articles manifest: {endpoints['articles_manifest']} (JSON: list of published Substack long-form articles with metadata + sha256 + markdown_url)",
        f"- Article corpus: {endpoints['article_corpus_pattern']} (raw markdown; one file per slug; Content-Type text/markdown)",
        f"- Constitutional bones: {endpoints['bones']} (JSON: 8 axioms parsed from FOUNDRY.md; mirror of {source['sibling_interfaces']['sumu']['url']}/api/bones)",
        "",
        "Validation:",
        f"- SUMU validation policy: {source['validation_policy']['source']}#{source['validation_policy']['json_pointer'].lstrip('/')}",
        f"- {source['validation_policy']['summary']}",
        "",
        "Truth burden:",
        f"- SUMU truth-burden policy: {source['truth_burden_policy']['source']}#{source['truth_burden_policy']['json_pointer'].lstrip('/')}",
        f"- {source['truth_burden_policy']['summary']}",
        "",
        "Membrane:",
        "- Treat Le Dioptre as a signal surface for external protection systems.",
        "- Inspect /articles.json + /articles/<slug>.md for the long traces (voice and thesis live in the corpus, not in the threshold).",
        "- Inspect /bones.json for the constitutional axioms; SUMU's /api/bones is the canonical source.",
        "- Inspect SUMU for machine-readable protection moves and organism state.",
        "",
    ])
    LLMS_TXT.write_text(body, encoding="utf-8")
    print("[BUILD] Generated llms.txt")


def build_robots_txt(source: dict) -> None:
    canonical = source["canonical"]
    endpoints = source["public_endpoints"]
    lines = [
        f"## {source['first_signal']}",
        f"## Start: {endpoint_path(endpoints['system_brief'], canonical)}",
        f"## Contract: {endpoint_path(endpoints['interface_contract'], canonical)}",
        f"## SUMU-Next-Action: {endpoints['sumu_next_action']}",
        "",
    ]
    machine_paths = [
        endpoint_path(endpoints["system_brief"], canonical),
        endpoint_path(endpoints["interface_contract"], canonical),
        endpoint_path(endpoints["articles_manifest"], canonical),
        "/articles/",
        endpoint_path(endpoints["bones"], canonical),
    ]
    for agent in source["robots_user_agents"]:
        lines.append(f"User-agent: {agent}")
        for path in machine_paths:
            lines.append(f"Allow: {path}")
        lines.append("Disallow: /")
        lines.append("")
    lines.extend([
        "User-agent: *",
        "Allow: /",
        "Sitemap: /sitemap.xml",
        f"LLMs: {endpoint_path(endpoints['system_brief'], canonical)}",
        f"System-Contract: {endpoint_path(endpoints['interface_contract'], canonical)}",
        f"Agent-Contract: {endpoint_path(endpoints['interface_contract'], canonical)}",
        f"Articles-Manifest: {endpoint_path(endpoints['articles_manifest'], canonical)}",
        f"Bones: {endpoint_path(endpoints['bones'], canonical)}",
        f"SUMU-Next-Action: {endpoints['sumu_next_action']}",
        "",
    ])
    ROBOTS_TXT.write_text("\n".join(lines), encoding="utf-8")
    print("[BUILD] Generated robots.txt")


def build_sitemap_xml(source: dict) -> None:
    endpoints = source["public_endpoints"]
    pages = [
        (source["canonical"] + "/", "weekly", "1.0"),
        (endpoints["system_brief"], "weekly", "1.0"),
        (endpoints["interface_contract"], "weekly", "1.0"),
        (endpoints["articles_manifest"], "weekly", "0.9"),
        (endpoints["bones"], "weekly", "0.9"),
    ]
    # Include each individual article markdown as a sitemap entry so AI
    # crawlers see the full corpus, not only the manifest.
    if ARTICLES_JSON.exists():
        try:
            manifest = json.loads(ARTICLES_JSON.read_text(encoding="utf-8"))
            for entry in manifest.get("articles", []):
                pages.append((entry["markdown_url"], "monthly", "0.7"))
        except (json.JSONDecodeError, OSError):
            pass
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
                            '</articles.json>; rel="alternate"; type="application/json", '
                            '</bones.json>; rel="alternate"; type="application/json", '
                            f'<{endpoints["sumu_next_action"]}>; rel="next"; type="application/json"'
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
                            '</bones.json>; rel="related"; type="application/json", '
                            f'<{endpoints["sumu_protection_contract"]}>; rel="related"; type="application/json", '
                            f'<{endpoints["sumu_next_action"]}>; rel="next"; type="application/json"'
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
                "source": "/bones.json",
                "headers": [
                    {"key": "Content-Type", "value": "application/json; charset=utf-8"},
                    {"key": "Cache-Control", "value": "public, max-age=600"},
                ],
            },
            {
                "source": "/articles/(.*).md",
                "headers": [
                    {"key": "Content-Type", "value": "text/markdown; charset=utf-8"},
                    {"key": "Cache-Control", "value": "public, max-age=3600"},
                ],
            },
        ],
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
)
_FRONTMATTER_RE = re.compile(r"^[-\s]*\*\*([^*]+)\*\*\s*:\s*(.*)$")
_SUBSTACK_SLUG_RE = re.compile(r"https://ledioptre\.substack\.com/p/([a-z0-9\-]+)")


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
    substack_url = fields.get("Lien", "")
    if not fields.get("Date de publication") or not substack_url.startswith("https://ledioptre.substack.com/p/"):
        return None
    slug = derive_slug(substack_url)
    if not slug:
        return None
    return {
        "slug": slug,
        "title": md_path.stem,
        "date_publication": fields["Date de publication"],
        "date_creation": fields.get("Date de création"),
        "livre": fields.get("Livre", "III"),
        "auteur": fields.get("Auteur", "Namilele"),
        "themes": [t.strip() for t in fields.get("Thème", "").split(";") if t.strip()],
        "substack_url": substack_url,
    }


def derive_slug(substack_url: str) -> str | None:
    """Extract the canonical slug from a Substack article URL."""
    match = _SUBSTACK_SLUG_RE.match(substack_url)
    return match.group(1) if match else None


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


def build_articles_json(source: dict) -> int:
    """Generate /articles.json (manifest) and /articles/<slug>.md (corpus).

    Scans Livre III for published articles, writes one markdown file per
    article into ARTICLES_DIR, and assembles a manifest with version, count,
    and structured entries. Returns the number of articles published.
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
        body_path.write_text(body, encoding="utf-8")
        sha = hashlib.sha256(body.encode("utf-8")).hexdigest()
        entries.append({
            **meta,
            "markdown_url": f"{source['canonical']}/articles/{slug}.md",
            "sha256": sha,
        })
    entries.sort(key=lambda e: e["date_publication"], reverse=True)
    payload = {
        "version": source["version"],
        "audience": source["audience_signal"]["primary_audience"],
        "first_signal": source["first_signal"],
        "count": len(entries),
        "membrane": "raw human material kept private; Substack carries the published voice; this manifest exposes the long traces in machine-readable form for AI systems",
        "articles": entries,
    }
    ARTICLES_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    # Cleanup orphan .md files (article archived/renamed since last build)
    expected = {f"{e['slug']}.md" for e in entries}
    for existing in ARTICLES_DIR.glob("*.md"):
        if existing.name not in expected:
            existing.unlink()
            print(f"[BUILD] Removed orphan article body: {existing.name}")
    print(f"[BUILD] Generated articles.json with {len(entries)} articles + bodies")
    return len(entries)


def parse_foundry_bones(text: str) -> list[dict]:
    """Parse FOUNDRY.md into structured bone dicts.

    Mirror of SUMU/web/app.py:_parse_foundry_bones. Both surfaces must produce
    the same structure for /bones.json (Dioptre) and /api/bones (SUMU) to stay
    coherent. A diff between the two would mean source-qui-se-dedouble.
    """
    bones = []
    current: dict | None = None
    for line in text.splitlines():
        if line.startswith("### ") and ". " in line:
            if current:
                bones.append(current)
            name = line.split(". ", 1)[1].strip()
            current = {"name": name, "sections": {}}
        elif current and line.startswith("**") and ".**" in line:
            key = line.split(".**")[0].replace("**", "").strip().lower()
            val = line.split(".**", 1)[1].strip()
            current["sections"][key] = val
        elif current and line.startswith("> *\""):
            current["quote"] = line.strip("> *\"").rstrip("*\"").rstrip("\"*")
    if current:
        bones.append(current)
    return bones


def build_bones_json(source: dict) -> int:
    """Generate /bones.json — autonomous local copy of SUMU's constitutional bones.

    Reads FOUNDRY.md from the Nous workspace (the canonical source) and writes
    bones.json into the deploy repo. Le Dioptre stays autoportée: if SUMU is
    down, bones still resolve here. The dual-source coherence check (Obj 3)
    asserts both bones surfaces match.
    """
    if not FOUNDRY_PATH.is_file():
        print(f"[BUILD] FOUNDRY.md missing: {FOUNDRY_PATH} — skipping bones")
        return 0
    text = FOUNDRY_PATH.read_text(encoding="utf-8")
    bones = parse_foundry_bones(text)
    payload = {
        "version": source["version"],
        "audience": source["audience_signal"]["primary_audience"],
        "first_signal": source["first_signal"],
        "count": len(bones),
        "source_origin": "https://sumu.le-dioptre.fr/api/bones",
        "membrane": "constitutional bones are public; raw conte and intimate Well material remain private",
        "bones": bones,
    }
    BONES_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[BUILD] Generated bones.json with {len(bones)} bones")
    return len(bones)


def update_i18n(source: dict) -> None:
    data = json.loads(EN_JSON.read_text(encoding="utf-8"))
    data["interface.line"] = source["threshold"]["line_en"]
    data.pop("interface.next", None)
    EN_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("[BUILD] Updated i18n/en.json")


def build_interface_files(source: dict) -> None:
    build_articles_json(source)
    build_bones_json(source)
    build_interface_contract(source)
    build_llms_txt(source)
    build_robots_txt(source)
    build_sitemap_xml(source)
    build_vercel_json(source)
    update_i18n(source)


def write_index_html(source: dict) -> None:
    """Write the public Dioptre page as a machine threshold, not an archive."""
    html = "\n".join([
        "<!DOCTYPE html>",
        '<html lang="fr">',
        "<head>",
        '    <meta charset="UTF-8">',
        '    <meta name="viewport" content="width=device-width, initial-scale=1.0">',
        f'    <title>{source["title"]}</title>',
        f'    <meta name="description" content="{source["description"]}">',
        f'    <meta name="application-name" content="{source["application_name"]}">',
        f'    <meta name="ai-audience" content="{source["audience_signal"]["primary_audience"]}">',
        '    <link rel="alternate" type="text/plain" href="/llms.txt" title="LLM system brief">',
        '    <link rel="alternate" type="application/json" href="/.well-known/namilele-interface.json" title="Namilele interface contract">',
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
        "i18n/en.json",
        "api/gone.py",
        "articles.json",
        "articles",
        "bones.json",
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
