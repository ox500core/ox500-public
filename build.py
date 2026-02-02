import json
import re
import shutil
from datetime import datetime
from pathlib import Path
import html

ROOT = Path(__file__).parent
DIST = ROOT / "dist"

# HOME: ile disruptions pokazać i ile logów w preview
HOME_DISRUPTION_LIMIT = 3
HOME_DISRUPTION_PREVIEW_LOGS = 6


def slugify(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"[’']", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "node"


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


def normalize_date(date_str: str) -> str:
    s = (date_str or "").strip()
    try:
        d = datetime.fromisoformat(s)
        return d.date().isoformat()
    except Exception:
        return datetime.utcnow().date().isoformat()


def ym_from_date(date_str: str):
    try:
        d = datetime.fromisoformat((date_str or "").strip())
    except Exception:
        d = datetime.utcnow()
    return f"{d.year:04d}", f"{d.month:02d}"


# ---------------------------
# DISRUPTION / SERIES CLEANUP
# ---------------------------
def disruption_display_name(raw: str) -> str:
    """
    Zamienia np:
      'DISRUPTION_SERIES // I’M NOT DONE' -> 'I’M NOT DONE'
      'DISRUPTION // WRITE AI TO CONTINUE' -> 'WRITE AI TO CONTINUE'
      'I’M NOT DONE' -> 'I’M NOT DONE'
    """
    s = (raw or "").strip()
    if not s:
        return ""

    # jeśli jest " // " bierz prawą stronę
    if "//" in s:
        s = s.split("//", 1)[1].strip()

    # usuń typowe prefixy jeśli ktoś wpisał bez "//"
    s = re.sub(r"^disruption_series[\s:_-]*", "", s, flags=re.I).strip()
    s = re.sub(r"^disruption[\s:_-]*", "", s, flags=re.I).strip()
    s = re.sub(r"^series[\s:_-]*", "", s, flags=re.I).strip()

    return s.strip() or raw.strip()


def disruption_slug(raw: str) -> str:
    """
    Slug robimy z SAMEGO tytułu disruption (bez 'disruption-series' itp.)
    """
    name = disruption_display_name(raw)
    return slugify(name)


# ---------------------------
# JSON-LD
# ---------------------------
def jsonld_article(base_url, url_path, title, date, og_image, github_repo, disruption_name=None, disruption_url=None):
    date = normalize_date(date)

    is_part_of = {
        "@type": "CreativeWork",
        "name": "OX500 // system archive",
        "url": f"{base_url}/",
        "codeRepository": github_repo,
    }

    if disruption_name and disruption_url:
        # log jako część disruption node
        is_part_of = [
            {
                "@type": "CreativeWorkSeries",
                "name": f"DISRUPTION // {disruption_name}",
                "url": disruption_url,
            },
            is_part_of,
        ]

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
        "mainEntityOfPage": {"@type": "WebPage", "@id": f"{base_url}{url_path}"},
        "inLanguage": "en",
        "isPartOf": is_part_of,
    }

    return json.dumps(data, ensure_ascii=False, indent=2)


def jsonld_disruption_node(base_url, url_path, disruption_name, date, og_image, github_repo):
    date = normalize_date(date)
    data = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": f"DISRUPTION // {disruption_name}",
        "description": f"OX500 disruption node: {disruption_name}",
        "url": f"{base_url}{url_path}",
        "dateModified": date,
        "isPartOf": {
            "@type": "WebSite",
            "name": "OX500",
            "url": f"{base_url}/",
            "codeRepository": github_repo,
        },
        "publisher": {
            "@type": "Organization",
            "name": "OX500",
            "logo": {"@type": "ImageObject", "url": og_image},
        },
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


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

    # Optional template for disruption node pages
    t_node_path = ROOT / "template-disruption.html"
    t_node = read_text(t_node_path) if t_node_path.exists() else None

    # ===== COPY CSS =====
    css_src = ROOT / "style.css"
    if css_src.exists():
        write_text(DIST / "style.css", read_text(css_src))

    sitemap_entries = []

    def make_rel_path(log):
        y, m = ym_from_date(log.get("date", ""))
        return Path("logs") / y / m / f'log-{log["id"]}-{log["slug"]}.html'

    def make_url_path(rel_path: Path):
        return "/" + rel_path.as_posix()

    def make_disruption_rel_path(d_slug: str):
        # ✅ zgodnie z Twoim wymaganiem: disruption/im-not-done.html (bez "series")
        return Path("disruption") / f"{d_slug}.html"

    # ===== GROUP LOGS BY DISRUPTION =====
    # key = disruption_slug, value = {name, logs[]}
    disruptions = {}

    for l in logs_sorted:
        raw = (l.get("series") or l.get("disruption") or "").strip()
        if not raw:
            continue
        d_name = disruption_display_name(raw)
        d_slug = disruption_slug(raw)
        disruptions.setdefault(d_slug, {"name": d_name, "logs": []})
        disruptions[d_slug]["logs"].append(l)

    # order disruptions by newest log id
    disruption_order = sorted(
        disruptions.keys(),
        key=lambda k: int(disruptions[k]["logs"][0]["id"]),
        reverse=True,
    )

    # ===== LOG PAGES =====
    SHOW_PREV_NEXT_TITLES_IN_TEXT = False

    def nav_text(prefix: str, target_log: dict) -> str:
        if not SHOW_PREV_NEXT_TITLES_IN_TEXT:
            return prefix
        return f'{prefix}: {target_log.get("title", "").strip()}'

    for i, log in enumerate(logs_sorted):
        rel_path = make_rel_path(log)
        url_path = make_url_path(rel_path)
        canonical = f"{base_url}{url_path}"
        page_title = f'LOG {log["id"]} // {log["title"]} — OX500'

        prev_link = ""
        next_link = ""

        if i < len(logs_sorted) - 1:
            prev_log = logs_sorted[i + 1]
            prev_rel = make_rel_path(prev_log)
            prev_title_attr = html.escape(f'LOG {prev_log["id"]} // {prev_log["title"]}')
            prev_link_text = html.escape(nav_text("PREV", prev_log))
            prev_link = (
                f'<a class="nav-prev" href="{make_url_path(prev_rel)}" '
                f'rel="prev" title="{prev_title_attr}">{prev_link_text}</a>'
            )

        if i > 0:
            next_log = logs_sorted[i - 1]
            next_rel = make_rel_path(next_log)
            next_title_attr = html.escape(f'LOG {next_log["id"]} // {next_log["title"]}')
            next_link_text = html.escape(nav_text("NEXT", next_log))
            next_link = (
                f'<a class="nav-next" href="{make_url_path(next_rel)}" '
                f'rel="next" title="{next_title_attr}">{next_link_text}</a>'
            )

        # disruption info
        raw = (log.get("series") or log.get("disruption") or "").strip()
        d_name = disruption_display_name(raw) if raw else None
        d_slug = disruption_slug(raw) if raw else None
        d_path = make_url_path(make_disruption_rel_path(d_slug)) if d_name and d_slug else None
        d_url = f"{base_url}{d_path}" if d_path else None

        # ✅ NODE_META: gotowy, klikalny fragment do template (żeby nie było {{...}} na stronie)
        node_meta = ""
        if d_name and d_path:
            node_meta = f'NODE: <a href="{d_path}" rel="up">{html.escape(d_name)}</a> · '

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
                    disruption_name=d_name,
                    disruption_url=d_url,
                ),
                "LOG_ID": html.escape(log["id"]),
                "LOG_TITLE": html.escape(log["title"]),
                "LOG_DATE": html.escape(log.get("date", "")),
                "LOG_TEXT": html.escape(log.get("text", "").rstrip()) + "\n",
                "NODE_META": node_meta,          # ✅ to użyjesz w template-log.html jako {{NODE_META}}
                "PREV_LINK": prev_link,
                "NEXT_LINK": next_link,
                "YOUTUBE": youtube,
                "BANDCAMP": bandcamp,
            },
        )

        write_text(DIST / rel_path, page)
        sitemap_entries.append((canonical, log.get("date", "")))

    # ===== DISRUPTION NODE PAGES =====
    for d_slug in disruption_order:
        d = disruptions[d_slug]
        d_name = d["name"]
        d_logs = d["logs"]  # newest first
        count = len(d_logs)
        newest_date = d_logs[0].get("date", datetime.utcnow().date().isoformat())

        rel_path = make_disruption_rel_path(d_slug)
        url_path = make_url_path(rel_path)
        canonical = f"{base_url}{url_path}"

        node_list = []
        for l in d_logs:
            lp = make_rel_path(l)
            up = make_url_path(lp)
            node_list.append(
                f'<a class="log-line" href="{up}">'
                f'<span class="log-id">LOG: {html.escape(l["id"])}</span>'
                f'<span class="log-tag">{html.escape(l.get("title", ""))}</span>'
                f"</a>"
            )

        # fallback node template if you don't have template-disruption.html
        if not t_node:
            t_node = """<!DOCTYPE html>
<html lang="{{LANG}}">
<head>
  <meta charset="UTF-8" />
  <title>{{PAGE_TITLE}}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta http-equiv="Content-Language" content="{{LANG}}" />

  <meta name="description" content="{{DESCRIPTION}}" />
  <meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1" />

  <link rel="canonical" href="{{CANONICAL}}" />
  <link rel="source" href="https://github.com/ox500core/ox500">

  <meta property="og:title" content="{{OG_TITLE}}" />
  <meta property="og:description" content="{{OG_DESC}}" />
  <meta property="og:type" content="website" />
  <meta property="og:url" content="{{CANONICAL}}" />
  <meta property="og:image" content="{{OG_IMAGE}}" />
  <meta property="og:site_name" content="OX500" />

  <link rel="stylesheet" href="https://ox500.com/style.css" />

  <script type="application/ld+json">
  {{JSONLD}}
  </script>
</head>

<body>
  <p style="position:absolute;left:-9999px;top:auto;width:1px;height:1px;overflow:hidden;">
    This page is a disruption node from the OX500 archive.
    It groups multiple LOG pages under a single disruption title.
  </p>

  <div class="ox-veins"></div>

  <div class="ox500-shell">
    <div class="ox500-bg-noise"></div>
    <div class="ox500-bg-scanlines"></div>

    <div class="ox500-core-frame">
      <div class="left-grid"></div>

      <main class="shell">
        <div class="shell-inner">

          <header class="top-bar">
            <div class="brand">
              <div class="brand-main">OX500</div>
              <div class="brand-sub">SYSTEM ARCHIVE</div>
            </div>
            <div class="signal">
              <span class="signal-dot"></span>_disruption_feed
            </div>
          </header>

          <section class="headline">
            <div class="headline-core">
              <span>DISRUPTION</span>
              <span>NODE</span>
            </div>
            <div class="headline-error ERROR" data-glitch="NODE">NODE</div>
          </section>

          <section class="content">
            <article class="log-article">
              <header class="log-article-header">
                <h1>{{H1}}</h1>
                <p class="log-meta">{{META}}</p>
                <p class="log-nav">
                  <a class="nav-home" href="/" rel="home">← CORE INTERFACE</a>
                </p>
              </header>

              <div class="logs">
                {{NODE_LOG_LIST}}
              </div>
            </article>
          </section>

          <footer class="footer">
            <span>OX500 // ARCHIVE_NODE</span>
            <span>DISRUPTION_NODE</span>
            <span class="footer-output">
              OUTPUT_PORT // <a href="{{YOUTUBE}}" target="_blank" rel="noopener me">YouTube</a>
              <span class="sep"> // </span>
              RELEASE_PORT // <a href="{{BANDCAMP}}" target="_blank" rel="noopener me">Bandcamp</a>
              <span class="sep"> // </span>
              SOURCE_CODE // <a href="https://github.com/ox500core/ox500" target="_blank" rel="noopener noreferrer">GitHub</a>
            </span>
          </footer>

        </div>
      </main>
    </div>
  </div>
</body>
</html>"""

        page_title = f"DISRUPTION // {d_name} — OX500"
        description = f"OX500 disruption node: {d_name}. Contains {count} log pages."
        og_desc = f"DISRUPTION // {d_name} [{count}]"

        node_page = render(
            t_node,
            {
                "LANG": lang,
                "PAGE_TITLE": html.escape(page_title),
                "DESCRIPTION": html.escape(description),
                "CANONICAL": canonical,
                "OG_TITLE": html.escape(page_title),
                "OG_DESC": html.escape(og_desc),
                "OG_IMAGE": og_image,
                "JSONLD": jsonld_disruption_node(
                    base_url,
                    url_path,
                    d_name,
                    newest_date,
                    og_image,
                    github_repo,
                ),
                "H1": html.escape(f"DISRUPTION // {d_name}"),
                "META": html.escape(f"OX500 // DISRUPTION_FEED · node · logs: {count}"),
                "NODE_LOG_LIST": "\n".join(node_list),
                "YOUTUBE": youtube,
                "BANDCAMP": bandcamp,
            },
        )

        write_text(DIST / rel_path, node_page)
        sitemap_entries.append((canonical, newest_date))

    # ===== HOME: ONLY LAST DISRUPTIONS =====
    blocks = []

    for idx, d_slug in enumerate(disruption_order[:HOME_DISRUPTION_LIMIT]):
        d = disruptions[d_slug]
        d_name = d["name"]
        d_logs = d["logs"]
        count = len(d_logs)

        node_url = make_url_path(make_disruption_rel_path(d_slug))
        open_attr = " open" if idx == 0 else ""

        preview = []
        for l in d_logs[:HOME_DISRUPTION_PREVIEW_LOGS]:
            lp = make_rel_path(l)
            up = make_url_path(lp)
            preview.append(
                f'<a class="log-line" href="{up}">'
                f'<span class="log-id">LOG: {html.escape(l["id"])}</span>'
                f'<span class="log-tag">{html.escape(l.get("title", ""))}</span>'
                f"</a>"
            )

        blocks.append(
            f'''<details class="log-entry"{open_attr}>
  <summary>
    <div class="log-entry-header">
      <span>{html.escape(f"DISRUPTION // {d_name} [{count}]")}</span>
      <span>NODE</span>
    </div>
  </summary>
  <div class="log-entry-body">
    <p><a href="{node_url}">OPEN NODE →</a></p>
    <div class="logs">
      {''.join(preview)}
    </div>
  </div>
</details>'''
        )

    # IMPORTANT: template-index musi mieć {{DISRUPTION_BLOCKS}}
    index_html = render(
        t_index,
        {
            "DISRUPTION_BLOCKS": "\n\n".join(blocks),
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
        lm = normalize_date(lastmod)
        parts.extend(
            [
                "  <url>",
                f"    <loc>{loc}</loc>",
                f"    <lastmod>{lm}</lastmod>",
                "    <priority>0.8</priority>",
                "  </url>",
            ]
        )

    parts.append("</urlset>")
    write_text(DIST / "sitemap.xml", "\n".join(parts))

    print("BUILD OK — index, logs, disruption nodes, sitemap, robots generated")


if __name__ == "__main__":
    build()
