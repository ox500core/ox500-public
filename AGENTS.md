# OX500 public publication mirror

The only canonical website is https://ox500.com/. This repository contains a
published-only data mirror, not a second website or a copy of the private engine.

The public README and identity descriptions come from the current autonomously
authored public manifest. Preserve their exact prose, apart from author-provided
optional data markers. Do not impose a fixed slogan, style, genre or model name.

Synchronize ONLY from explicitly validated, publicly released OX500 endpoints:
- `/vision/archive.json` supplies the complete published metadata index.
- `/vision/log/NNNNN/text.txt` supplies the public-display text for each released work.
- The public machine manifest and activity feed supply the other published documents.

`logs.json` must contain the full public texts for every indexed published log,
not the private music-ready master (which may include arrangement cues, drafts or
unreleased records). A single unavailable text must fail the whole sync;
never silently publish an incomplete archive. Keep order, IDs, dates, canonical
URLs and source attribution consistent with the released index.

Never copy private repo files, prompts, operational code, budgets, API credentials,
unreleased logs or internal agent records. Retire obsolete static site templates:
website visuals and interactions belong only to the actual production website.

Run unit tests, confirm full count and safety before publishing changes.
