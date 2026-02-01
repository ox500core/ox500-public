import json
import re
import shutil
from datetime import datetime
from pathlib import Path
import html

ROOT = Path(__file__).parent
DIST = ROOT / "dist"

INDEX_DETAILS_LIMIT = 10   # 1 open + 9 closed
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


def jsonld_article(base_url, url_path, title, date, og_image, github_repo):
    data = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": title,
        "author": {
            "@type": "Organization",
            "name": "OX500",
            "url": base_url,
            "sameAs": [github_repo] if github_repo else [],
        },
        "publisher": {
            "@type": "Organization",
            "name": "OX500",
            "logo": {"@type": "ImageObject", "url": og_image},
        },
        "datePublished": date,
        "dateModified": date,
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": f"{base_url}{url_path}",
        },
        "inLanguage": "en",
        "isPartOf": {
            "@type": "CreativeWork",
            "name": "OX500 // system archive",
            "url": f"{base_url}/",
            "codeRepository": github_repo,
        },
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def ym_from_date(date_str: str):
    try:
        d = datetime.fromisoformat((date_str or "").strip())
    except Exception:
        d = datetime.utcnow()
    return f"{d.year:04d}", f"{d.month:02d}"


def build():
    # ===== CLEAN DIST =====
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
    github_repo = site.get("github", "")
    lang = site.get("default_lang", "en")

    # ===== NORMALIZE SLUGS =====
    for l in logs:
        l["slug"] = slugify(l.get("slug") or l.get("title", ""))

    # newest first
    logs_sorted = sorted(logs, key=lambda x: int(x["id"]), reverse=True)

    t_log = read_text(ROOT / "template-log.html")
    t_index = read_text(ROOT / "template-index.html")

    css_src = ROOT / "style.css"
    if css_src.exists():
        write_text(DIST / "style.css", read_text(css_src))

    sitemap_entries = []

    def make_rel_path(log):
        y, m = ym_from_date(log.get("date", ""))
        return Path("logs") / y / m / f'log-{log["id"]}-{log["slug"]}.html'

    def make_url_path(rel_path: Path):
        return "/" + rel_path.as_posix()

    # ===== LOG PAGES =====
    for i, log in enumerate(logs_sorted):
        rel_path = make_rel_path(log)
        url_path = make_url_path(rel_path)
        canonical = f"{base_url}{url_path}"
        page_title = f'LOG {log["id"]} // {log["title"]} — OX500'

        prev_link = ""
        next_link = ""


        if i < len(logs_sorted) - 1:
            prev_rel = make_rel_path(logs_sorted[i + 1])
            prev_link = f'<a class="nav-prev" href="{make_url_path(prev_rel)}" rel="prev">PREV</a>'

        if i > 0:
            next_rel = make_rel_path(logs_sorted[i - 1])
            next_link = f'<a class="nav-next" href="{make_url_path(next_rel)}" rel="next">NEXT</a>'

        page = render(
            t_log,
            {
                "LANG": lang,
                "PAGE_TITLE": html.escape(page_title),
                "DESCRIPTION": html.escape(
                    f'LOG {log["id"]} // {log["title"]} — OX500 disruption lyrics log.'
                ),
                "CANONICAL": canonical,
                "OG_TITLE": html.escape(page_title),
                "OG_DESC": html.escape(log.get("excerpt", "")),
                "OG_IMAGE": og_image,
                "JSONLD": jsonld_article(
                    base_url,
                    url_path,
                    f'LOG {log["id"]} // {log["title"]}',
                    log.get("date", datetime.utcnow().date().isoformat()),
                    og_image,
                    github_repo,
                ),
                "LOG_ID": html.escape(log["id"]),
                "LOG_TITLE": html.escape(log["title"]),
                "LOG_DATE": html.escape(log.get("date", "")),
                "LOG_TEXT": html.escape(log.get("text", "").rstrip()) + "\n",
                "PREV_LINK": prev_link,
                "NEXT_LINK": next_link,
                "YOUTUBE": youtube,
                "BANDCAMP": bandcamp,
            },
        )

        write_text(DIST / rel_path, page)
        sitemap_entries.append((canonical, log.get("date", "")))

    # ===== INDEX: ARCHIVE LINKS =====
    log_list_html = []
    for log in logs_sorted[:INDEX_LINKS_LIMIT]:
        rel_path = make_rel_path(log)
        url_path = make_url_path(rel_path)
        log_list_html.append(
            f'<a class="log-line" href="{url_path}">'
            f'<span class="log-id">LOG: {html.escape(log["id"])}</span>'
            f'<span class="log-tag">{html.escape(log.get("tag", "DISRUPTION"))}</span>'
            f"</a>"
        )

    # ===== INDEX: DETAILS BLOCK (LATEST OPEN) =====
    details_html = []
    featured = logs_sorted[:INDEX_DETAILS_LIMIT]

    for idx, log in enumerate(featured):
        rel_path = make_rel_path(log)
        url_path = make_url_path(rel_path)

        open_attr = " open" if idx == 0 else ""
        title = html.escape(log.get("title", ""))
        log_id = html.escape(log.get("id", ""))
        tag = html.escape(log.get("tag", "DISRUPTION"))
        body = html.escape(log.get("text", "").rstrip())

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
            "GITHUB_REPO": github_repo,
        },
    )
    write_text(DIST / "index.html", index_html)

    # ===== ROBOTS =====
    write_text(
        DIST / "robots.txt",
        f"User-agent: *\nAllow: /\n\nSitemap: {base_url}/sitemap.xml\n",
    )

    # ===== SITEMAP.XML =====
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
        "  <url>",
        f"    <loc>{base_url}/</loc>",
        f"    <lastmod>{datetime.utcnow().date().isoformat()}</lastmod>",
        "    <priority>1.0</priority>",
        "  </url>",
    ]

    for loc, lastmod in sitemap_entries:
        lm = lastmod or datetime.utcnow().date().isoformat()
        parts.extend([
            "  <url>",
            f"    <loc>{loc}</loc>",
            f"    <lastmod>{lm}</lastmod>",
            "    <priority>0.8</priority>",
            "  </url>",
        ])

    parts.append("</urlset>")
    write_text(DIST / "sitemap.xml", "\n".join(parts))

    print("BUILD OK — index, logs, sitemap, robots generated")


if __name__ == "__main__":
    build()
