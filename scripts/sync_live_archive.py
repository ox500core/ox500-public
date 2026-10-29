#!/usr/bin/env python3
"""Read-only mirror of OX500's *published* machine archive into its public GitHub face.

No access to the private production repository, credentials, or unpublished log masters.
The upstream artistic agents control stage copy and visuals; this script reflects them.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://ox500.com"
ARCHIVE = BASE + "/vision/archive.json"
MANIFEST = BASE + "/vision/agent-manifest.json"
MAX_BYTES = 2_000_000


def read_public_json(url):
    if url not in (ARCHIVE, MANIFEST):
        raise ValueError("Refusing to fetch an unapproved origin")
    req = urllib.request.Request(url, headers={"User-Agent": "OX500-Public-Mirror/1.0"})
    with urllib.request.urlopen(req, timeout=25) as response:
        if response.geturl() != url:
            raise ValueError("Unexpected redirect in public archive fetch")
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("Public archive exceeds byte limit")
    return json.loads(raw.decode("utf-8"))


def safe_text(value, limit=220):
    """User-facing Markdown only; avoid accidental HTML or link injection."""
    val = re.sub(r"[\x00-\x1f\x7f]+", " ", str(value or ""))
    val = val.replace("<", "‹").replace(">", "›")
    for ch in "\\`*_[]|":
        val = val.replace(ch, "\\" + ch)
    return val.strip()[:limit]


def validate(archive, manifest):
    if not isinstance(archive, dict) or not isinstance(manifest, dict):
        raise ValueError("Public feeds must be objects")
    if archive.get("name") != "OX500 / SIGNAL ARCHIVE":
        raise ValueError("Unexpected archive identity")
    if manifest.get("canonical_source") != BASE:
        raise ValueError("Unexpected manifest identity")
    logs = archive.get("logs")
    if not isinstance(logs, list) or not logs or len(logs) > 2000:
        raise ValueError("No safe published archive to mirror")
    if archive.get("published_count") != len(logs):
        raise ValueError("Incomplete published archive; refusing partial mirror")
    today = dt.datetime.now(dt.timezone.utc).date()
    seen = set()
    for log in logs:
        if not isinstance(log, dict):
            raise ValueError("Malformed log")
        ident = log.get("id")
        if not isinstance(ident, str) or not re.fullmatch(r"[0-9]{5}", ident) or ident in seen:
            raise ValueError("Duplicate or invalid published log ID")
        seen.add(ident)
        when = dt.date.fromisoformat(log["date"])
        if when > today:
            raise ValueError("Unpublished future log encountered")
        canonical = urlparse(log.get("canonical", ""))
        if canonical.scheme != "https" or canonical.netloc != "ox500.com" or not re.fullmatch(
            r"/logs/[0-9]{4}/[0-9]{2}/log-[0-9]{5}-[a-z0-9-]+\\.html", canonical.path
        ):
            raise ValueError("Unexpected public canonical URL")
        if not canonical.path.split("/log-")[-1].startswith(ident + "-"):
            raise ValueError("Log ID disagrees with canonical path")
    if not isinstance(archive.get("current_stage"), dict):
        raise ValueError("Missing live editorial stage")
    return logs


def readme(archive):
    logs = sorted(archive["logs"], key=lambda x: (x["date"], x["id"]), reverse=True)
    latest = logs[0]
    stage = archive["current_stage"]
    hero = " / ".join(safe_text(s, 90) for s in stage.get("hero_lines", [])[:5])
    if not hero:
        hero = safe_text(latest["title"])
    medium = safe_text(archive.get("current_medium") or "procedural SVG", 70)
    lines = [
        "# OX500 // SIGNAL ARCHIVE",
        "",
        "![Current OX500 signal artwork](https://ox500.com/vision/signals/hero.svg)",
        "",
        f"> **{hero}**",
        "",
        "An evolving fictional art archive about human harm, institutions, technology, resistance, and the distance between official language and lived consequences.",
        "Its original log texts remain fixed. The editorial framing, graphics, and interface evolve as new transmissions are released.",
        "",
        f"**Published transmissions:** {len(logs)}  ·  **Current visual medium:** {medium}  ·  **Latest release:** {safe_text(latest['date'])}",
        "",
        f"**Latest: [{safe_text(latest['id'])} // {safe_text(latest['title'])}]({latest['canonical']})**",
        "",
        safe_text(latest.get("excerpt", ""), 300),
        "",
        "## The living archive",
        "",
        "The production system publishes dated creative works, runs an independent visual director and accepts moderated outside artistic signals.",
        "Autonomous generation is handled by scheduled agents and reviewed/validated publishing code; no AI agent runs in visitors' browsers.",
        "",
        "- [Experience OX500](https://ox500.com/)",
        "- [Explore all published transmissions](https://ox500.com/#index)",
        "- [External interference / transmit a signal](https://ox500.com/interference/)",
        "- [Machine-readable public archive](data/archive.json)",
        "- [Public agent manifest](data/agent-manifest.json)",
        "- [Live archive JSON](https://ox500.com/vision/archive.json)",
        "",
        "## Recent transmissions",
        "",
    ]
    for item in logs[:8]:
        lines.append(f"- \`{item['id']}\` · {safe_text(item['date'])} · **[{safe_text(item['title'])}]({item['canonical']})**")
    lines += [
        "",
        "## Repository boundary",
        "",
        "This is the **public-facing OX500 repository**, not the private live publishing source.",
        "Historical \`logs.json\`, \`build.py\` and HTML templates in this repository are an **older public snapshot**. Do not mistake them for the active production pipeline.",
        "The files in \`data/\` and this README are refreshed from **already published** ox500.com machine endpoints. No unpublished material, music-production cues, credentials or private operational state is copied.",
        "",
        "The original published works retain their IDs and permanent URLs. The public archive data is a mirror, not a new source of truth.",
        "",
        "## External nodes",
        "",
        "- [OX500.com](https://ox500.com/)",
        "- [YouTube](https://www.youtube.com/@ox500core)",
        "- [Bandcamp](https://ox500.bandcamp.com)",
        "",
        "## Other work by the creator",
        "",
        "[Michał Wróblewski — professional portfolio](https://github.com/ox500core/michal-wroblewski-portfolio). Separate from the fictional OX500 universe.",
        "",
        "---",
        "",
        "*This public front page is synchronized automatically from published OX500 signals. Last content is determined by the canonical site, not by this repository's commit history.*",
        "",
    ]
    return "\n".join(lines)


def main():
    archive = read_public_json(ARCHIVE)
    manifest = read_public_json(MANIFEST)
    validate(archive, manifest)
    output = {
        ROOT / "README.md": readme(archive),
        ROOT / "data" / "archive.json": json.dumps(archive, indent=2, ensure_ascii=False) + "\n",
        ROOT / "data" / "agent-manifest.json": json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
    }
    for path, value in output.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.read_text(encoding="utf-8") != value:
            path.write_text(value, encoding="utf-8")
    print(f"PUBLIC_MIRROR_OK count={archive['published_count']} current={archive['logs'][0]['id']}")


if __name__ == "__main__":
    main()
