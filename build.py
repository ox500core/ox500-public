import json
import re
import shutil
from datetime import datetime
from pathlib import Path
import html

ROOT = Path(__file__).parent
DIST = ROOT / "dist"

# ile logów pokazujemy na głównej jako <details>
INDEX_DETAILS_LIMIT = 10  # 1 open + 9 closed
# ile linków pokazujemy w ARCHIVE liście (same linki)
INDEX_LINKS_LIMIT = 20


def slugify(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"[’']", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "log"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def render(template: str, mapping: dict) -> str:
    out = template
    for k, v in mapping.items():
        out = out.replace("{{" + k + "}}", v)
    return out


def jsonld_article(base_url, url_path, title, date, og_image):
    # url_path = "/logs/2025/12/log-0001-..."
    data = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "author": {"@type": "Organization", "name": "OX500"},
        "publisher": {
            "@type": "Organization",
            "name": "OX500",
            "logo": {"@type": "ImageObject", "url": og_image},
        },
        "datePublished": date,
        "dateModified": date,
        "mainEntityOfPage": {"@type": "WebPage", "@id": f"{base_url}{url_path}"},
        "inLanguage": "en",
        "isPartOf": {
            "@type": "CreativeWork",
            "name": "OX500 // system archive",
            "url": f"{base_url}/",
        },
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def ym_from_date(date_str: str):
    """
    date_str: "2025-12-07" -> ("2025","12")
    fallback: UTC today
    """
    try:
        d = datetime.fromisoformat((date_str or "").strip())
    except Exception:
        d = datetime.utcnow()
    return f"{d.year:04d}", f"{d.month:02d}"


def build():
    # HARD CLEAN dist (żeby nie oglądać starych plików)
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True, exist_ok=True)

    cfg = json.loads(read_text(ROOT / "logs.json"))
    site = cfg["site"]
    logs = cfg["logs"]

    base_url = site["base_url"].rstrip("/")
    og_image = site["og_image"]
    youtube = site["youtube"]
    bandcamp = site.get("bandcamp", "")

    lang = site.get("default_lang", "en")

    # Normalize slugs
    for l in logs:
        if not l.get("slug"):
            l["slug"] = slugify(l.get("title", ""))
        else:
            l["slug"] = slugify(l["slug"])

    # Sort by id numeric: newest first (01614 -> 01599)
    logs_sorted = sorted(logs, key=lambda x: int(x["id"]), reverse=True)

    # Templates
    t_log = read_text(ROOT / "template-log.html")
    t_index = read_text(ROOT / "template-index.html")

    # Copy CSS
    css_src = ROOT / "style.css"
    if css_src.exists():
        write_text(DIST / "style.css", read_text(css_src))

    sitemap_entries = []

    def make_rel_path(log):
        """
        Zwraca ścieżkę RELATYWNĄ wewnątrz dist, np:
        logs/2025/12/log-01612-im-not-done.html
        """
        y, m = ym_from_date(log.get("date", ""))
        filename = f'log-{log["id"]}-{log["slug"]}.html'
        return Path("logs") / y / m / filename

    def make_url_path(rel_path: Path):
        # zwraca "/logs/2025/12/log-..."
        return "/" + rel_path.as_posix()

    # ===== Build log pages =====
    for i, log in enumerate(logs_sorted):
        rel_path = make_rel_path(log)
        url_path = make_url_path(rel_path)  # "/logs/2025/12/..."
        canonical = f"{base_url}{url_path}"
        page_title = f'LOG {log["id"]} // {log["title"]} — OX500'

        # NAV:
        # logs_sorted jest DESC (0 = newest)
        # CHCEMY: PREV = starszy (i+1), NEXT = nowszy (i-1)
        prev_link = '<span class="nav-prev" style="opacity:.6">PREV</span>'
        next_link = '<span class="nav-next" style="opacity:.6">NEXT</span>'

        # PREV -> starszy (niższy numer): i+1
        if i < len(logs_sorted) - 1:
            prev_rel = make_rel_path(logs_sorted[i + 1])
            prev_link = f'<a class="nav-prev" href="{make_url_path(prev_rel)}" rel="prev">PREV</a>'

        # NEXT -> nowszy (wyższy numer): i-1
        if i > 0:
            next_rel = make_rel_path(logs_sorted[i - 1])
            next_link = f'<a class="nav-next" href="{make_url_path(next_rel)}" rel="next">NEXT</a>'


        log_text = html.escape(log.get("text", "").rstrip()) + "\n"
        desc = f'LOG {log["id"]} // {log["title"]} — OX500 disruption lyrics log.'
        og_desc = log.get("excerpt", "OX500 // system archive — disruption lyrics log.").strip()

        page = render(
            t_log,
            {
                "LANG": lang,
                "PAGE_TITLE": html.escape(page_title),
                "DESCRIPTION": html.escape(desc),
                "CANONICAL": canonical,
                "OG_TITLE": html.escape(page_title),
                "OG_DESC": html.escape(og_desc),
                "OG_IMAGE": og_image,
                "JSONLD": jsonld_article(
                    base_url,
                    url_path,
                    f'LOG {log["id"]} // {log["title"]}',
                    log.get("date", datetime.utcnow().date().isoformat()),
                    og_image,
                ),
                "LOG_ID": html.escape(log["id"]),
                "LOG_TITLE": html.escape(log["title"]),
                "LOG_DATE": html.escape(log.get("date", "")),
                "LOG_TEXT": log_text,
                "PREV_LINK": prev_link,
                "NEXT_LINK": next_link,
                "YOUTUBE": youtube,
                "BANDCAMP": bandcamp,

            },
        )

        write_text(DIST / rel_path, page)
        sitemap_entries.append((canonical, log.get("date", "")))

    # ===== INDEX: ARCHIVE LINKS (limit) =====
    log_list_html = []
    for log in logs_sorted[:INDEX_LINKS_LIMIT]:
        rel_path = make_rel_path(log)
        url_path = make_url_path(rel_path)
        line = (
            f'<a class="log-line" href="{url_path}">'
            f'<span class="log-id">LOG: {html.escape(log["id"])}</span>'
            f'<span class="log-tag">{html.escape(log.get("tag", "DISRUPTION"))}</span>'
            f"</a>"
        )
        log_list_html.append(line)

    # ===== INDEX: DETAILS BLOCK (1 open + 9 closed) =====
    details_html = []
    featured = logs_sorted[:INDEX_DETAILS_LIMIT]

    for idx, log in enumerate(featured):
        rel_path = make_rel_path(log)
        url_path = make_url_path(rel_path)
        open_attr = " open" if idx == 0 else ""
        title = html.escape(log.get("title", ""))
        log_id = html.escape(log.get("id", ""))
        tag = html.escape(log.get("tag", "DISRUPTION"))
        text_raw = log.get("text", "").rstrip()

        # NAJWAŻNIEJSZE: zachowanie nowych linii w HTML
        # Najprościej: wstawiamy to w <pre> (już po escape)
        body = html.escape(text_raw)

        details_html.append(
            f'''<details class="log-entry"{open_attr}>
  <summary>
    <div class="log-entry-header">
      <span>LOG: {log_id} // {title}</span>
      <span>OX500 // {tag}</span>
    </div>
  </summary>
  <div class="log-entry-body">
    <p><a href="{url_path}">OPEN LOG PAGE →</a></p>
    <pre class="log-pre">{body}</pre>
  </div>
</details>'''
        )

    index_html = render(
        t_index,
        {
            "LOG_LIST": "\n".join(log_list_html),
            "DETAILS_BLOCK": "\n\n".join(details_html),
        },
    )
    write_text(DIST / "index.html", index_html)

    # robots.txt
    robots = f"User-agent: *\nAllow: /\n\nSitemap: {base_url}/sitemap.xml\n"
    write_text(DIST / "robots.txt", robots)

    # sitemap.xml
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    parts.append("  <url>")
    parts.append(f"    <loc>{base_url}/</loc>")
    parts.append(f"    <lastmod>{datetime.utcnow().date().isoformat()}</lastmod>")
    parts.append("    <priority>1.0</priority>")
    parts.append("  </url>")

    for loc, lastmod in sitemap_entries:
        lm = lastmod if lastmod else datetime.utcnow().date().isoformat()
        parts.append("  <url>")
        parts.append(f"    <loc>{loc}</loc>")
        parts.append(f"    <lastmod>{lm}</lastmod>")
        parts.append("    <priority>0.8</priority>")
        parts.append("  </url>")

    parts.append("</urlset>")
    write_text(DIST / "sitemap.xml", "\n".join(parts))

    print("Built to /dist: index.html + log pages + sitemap.xml + robots.txt + style.css")


if __name__ == "__main__":
    build()
