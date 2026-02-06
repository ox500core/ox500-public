# OX500

![Last log](https://img.shields.io/badge/last_log-active-critical?style=flat)

**Canonical site:**  
https://ox500.com

OX500 is an experimental AI–human narrative system.  
It manifests as audio transmissions, textual disruption logs, and structural artifacts.

This repository contains the public source of the OX500 site —  
the system that defines and generates the archive.

OX500 is not a product, service, or framework.  
It is a living structure: a log-based system of failures, signals, and narrative traces.

---

## Repository Contents

This repository documents the evolving structure of the system, not its final state.

Included components:

- `logs.json` — structured system logs (JSON source of the archive)
- `template-index.html` — homepage template (disruption feed)
- `template-log.html` — single log page template
- `template-series.html` — disruption node / series template
- `style.css` — interface layer (CSS)
- `assets/` — static assets (bg / img / icons / css)
  - `assets/icons/` — favicons + manifest (also copied to `dist/` root)
- `build.py` — static build script (source → generated output → `dist/`)

Generated output (`dist/`) is not tracked in this repository.
Only the system source is versioned.


---

## External Nodes

OX500 exists as a distributed system across multiple public archives.  
These platforms act as mirrors of selected artifacts.

- Website (canonical archive): https://ox500.com  
- YouTube (audio transmission mirror): https://www.youtube.com/@ox500core  
- Bandcamp (optional distribution node): https://ox500.bandcamp.com  

The canonical system state is maintained on ox500.com.

---

## Notes

OX500 is released as an open narrative system.  
It is intended to be read, interpreted, referenced, and archived —  
not optimized, branded, or finalized.

---

ARCHIVE_OF_FAILURE  
SYSTEM_LOGS_ONLY
