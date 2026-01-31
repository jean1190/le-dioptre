#!/usr/bin/env python3
"""
Build script for Le Dioptre - Generates article links from markdown files.
Reads from /docs/nous/dioptre/*.md and updates index.html.

Usage:
    python build_articles.py

Or from sanctuaire root:
    python sanctuaires-publiques/le-dioptre-deploy/build_articles.py
"""

import re
from pathlib import Path
from datetime import datetime

# Paths
SCRIPT_DIR = Path(__file__).parent
SANCTUAIRE_ROOT = SCRIPT_DIR.parent.parent
ARTICLES_DIR = SANCTUAIRE_ROOT / "docs" / "nous" / "dioptre"
INDEX_HTML = SCRIPT_DIR / "index.html"


def parse_article(md_path: Path) -> dict | None:
    """Extract metadata from a markdown article file."""
    if md_path.name.startswith("_"):
        return None  # Skip templates

    content = md_path.read_text(encoding="utf-8")

    # Extract metadata
    title_match = re.search(r"^#\s+(.+)$|^(.+)\n={3,}$", content, re.MULTILINE)
    date_match = re.search(r"\*\*Date de publication\*\*\s*:\s*(.+)", content)
    link_match = re.search(r"\*\*Lien\*\*\s*:\s*(https?://\S+)", content)

    if not link_match:
        return None  # No link = not a published article

    # Get title from filename if not found in content
    if title_match:
        title = title_match.group(1) or title_match.group(2)
    else:
        # Use first non-empty line after ## Contenu
        contenu_match = re.search(r"## Contenu\s*\n+(.+)", content)
        if contenu_match:
            title = contenu_match.group(1).strip()
        else:
            title = md_path.stem

    # Parse date
    date_str = date_match.group(1).strip() if date_match else ""
    try:
        # Try parsing "Jan 05, 2026" format
        parsed_date = datetime.strptime(date_str, "%b %d, %Y")
        date_display = parsed_date.strftime("%d %b %Y").lower()
        date_sort = parsed_date
    except ValueError:
        date_display = date_str.lower() if date_str else "—"
        date_sort = datetime.min

    return {
        "title": title.strip(),
        "date_display": date_display,
        "date_sort": date_sort,
        "link": link_match.group(1).strip()
    }


def generate_articles_html(articles: list[dict]) -> str:
    """Generate HTML for the articles list."""
    lines = ['                <div class="exodus-articles">']

    for article in articles:
        lines.append(f'                    <a href="{article["link"]}" target="_blank" rel="noopener" class="exodus-article">')
        lines.append(f'                        <span class="article-title">{article["title"]}</span>')
        lines.append(f'                        <span class="article-date">{article["date_display"]}</span>')
        lines.append('                    </a>')

    lines.append('                </div>')
    return '\n'.join(lines)


def update_index_html(articles_html: str) -> bool:
    """Update index.html with new articles list."""
    content = INDEX_HTML.read_text(encoding="utf-8")

    # Find and replace content between markers
    pattern = r"(<!-- ARTICLES:START.*?-->)\s*.*?\s*(<!-- ARTICLES:END -->)"
    replacement = f"\\1\n{articles_html}\n                \\2"

    new_content, count = re.subn(pattern, replacement, content, flags=re.DOTALL)

    if count == 0:
        print("[BUILD] ERROR: Could not find ARTICLES markers in index.html")
        return False

    INDEX_HTML.write_text(new_content, encoding="utf-8")
    return True


def build_articles_txt():
    """Generate dioptre_articles.txt with full content of all articles (for Namilele context)."""
    output_path = SANCTUAIRE_ROOT / "dioptre_articles.txt"
    md_files = sorted(ARTICLES_DIR.glob("*.md"))  # Sort for consistent ordering
    
    lines = []
    article_count = 0
    
    for md_path in md_files:
        if md_path.name.startswith("_"):
            continue  # Skip templates
        
        content = md_path.read_text(encoding="utf-8")
        lines.append(f"=== {md_path.name} ===")
        lines.append(content)
        lines.append("\n\n")
        article_count += 1
    
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[BUILD] ✓ Generated dioptre_articles.txt ({article_count} articles)")


def main():
    print("[BUILD] Scanning articles...")

    # Find all markdown files
    md_files = list(ARTICLES_DIR.glob("*.md"))
    print(f"[BUILD] Found {len(md_files)} files in {ARTICLES_DIR}")

    # Parse articles
    articles = []
    for md_path in md_files:
        article = parse_article(md_path)
        if article:
            articles.append(article)
            print(f"[BUILD] ✓ {article['title']}")

    if not articles:
        print("[BUILD] No articles found!")
        return

    # Sort by date (newest first)
    articles.sort(key=lambda a: a["date_sort"], reverse=True)

    # Generate HTML
    articles_html = generate_articles_html(articles)

    # Update index.html
    if update_index_html(articles_html):
        print(f"[BUILD] ✓ Updated index.html with {len(articles)} articles")
    else:
        print("[BUILD] ✗ Failed to update index.html")

    # Generate dioptre_articles.txt for Namilele context
    build_articles_txt()


if __name__ == "__main__":
    main()
