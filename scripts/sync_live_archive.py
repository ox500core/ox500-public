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
ACTIVITY = BASE + "/vision/activity.json"
MAX_BYTES = 2_000_000


def read_public_json(url):
    if url not in (ARCHIVE, MANIFEST, ACTIVITY):
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
    for ch in r"\`*_[]|":
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
            r"/logs/[0-9]{4}/[0-9]{2}/log-[0-9]{5}-[a-z0-9-]+\.html", canonical.path
        ):
            raise ValueError("Unexpected public canonical URL")
        if not canonical.path.split("/log-")[-1].startswith(ident + "-"):
            raise ValueError("Log ID disagrees with canonical path")
    if not isinstance(archive.get("current_stage"), dict):
        raise ValueError("Missing live editorial stage")
    return logs


def readme(archive, manifest):
    """Preserve the autonomous author's Markdown; substitute only optional live data."""
    docs = manifest.get("public_presence")
    if (not isinstance(docs, dict) or not {"schema_version", "summary", "llms", "readme"} <= set(docs)
            or set(docs) - {"schema_version", "summary", "llms", "readme", "agent_manifest", "reader_skill"}
            or docs.get("schema_version") != 1):
        raise ValueError("No autonomous public documents published yet")
    for key, limit in (("summary", 650), ("llms", 12000), ("readme", 16000)):
        val = docs[key]
        if not isinstance(val, str) or not 40 <= len(val.strip()) <= limit or re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", val):
            raise ValueError("Unsafe autonomous public document")
        if re.search(r"<[^>]+>", val):
            raise ValueError("HTML in public document")
        if re.search(r"(?i)javascript:|data:|sk-[A-Za-z0-9_-]{12,}|OPENAI_API_KEY|Authorization:", val):
            raise ValueError("Secret or executable public document content")
    governance = manifest.get("identity_governance", {})
    if governance.get("review_cadence") != "quarterly" or governance.get("agent_positions") != 5:
        raise ValueError("Unexpected public author configuration")
    logs = sorted(archive["logs"], key=lambda x: (x["date"], x["id"]), reverse=True)
    recent = "\n".join(f"- `{x['id']}` · {safe_text(x['date'])} · [{safe_text(x['title'])}]({x['canonical']})" for x in logs[:8])
    substitutions = {
        "{{RECENT_TRANSMISSIONS}}": recent,
        "{{CURRENT_ARTWORK}}": "![Current archive artwork](https://ox500.com/vision/signals/hero.svg)",
        "{{ARCHIVE_STATS}}": f"{len(logs)} published · {safe_text(logs[0]['date'])} · {safe_text(archive.get('current_medium', ''))}",
    }
    page = docs["readme"]
    for marker, value in substitutions.items():
        page = page.replace(marker, value)
    if re.search(r"\{\{[^{}]*\}\}", page):
        raise ValueError("Unresolved public README placeholder")
    return page + ("\n" if not page.endswith("\n") else "")


def main():
    archive = read_public_json(ARCHIVE)
    manifest = read_public_json(MANIFEST)
    activity = read_public_json(ACTIVITY)
    validate(archive, manifest)
    if activity.get("schema_version") != 1 or activity.get("name") != "OX500 / MACHINE ACTIVITY" or not isinstance(activity.get("events"), list) or len(activity["events"]) > 24:
        raise ValueError("Invalid machine activity snapshot")
    output = {
        ROOT / "README.md": readme(archive, manifest),
        ROOT / "data" / "archive.json": json.dumps(archive, indent=2, ensure_ascii=False) + "\n",
        ROOT / "data" / "agent-manifest.json": json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        ROOT / "data" / "activity.json": json.dumps(activity, indent=2, ensure_ascii=False) + "\n",
    }
    for path, value in output.items():
        if re.search(r"\{\{[^{}]*\}\}", value):
            raise ValueError("Refusing to mirror unresolved public placeholder: " + path.name)
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.read_text(encoding="utf-8") != value:
            path.write_text(value, encoding="utf-8")
    print(f"PUBLIC_MIRROR_OK count={archive['published_count']} current={archive['logs'][0]['id']}")


if __name__ == "__main__":
    main()
