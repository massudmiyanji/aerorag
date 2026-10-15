# AeroRAG

Retrieval-augmented question answering over public aerospace maintenance documents,
served through FastAPI and run locally with Docker.

## Quick start

```bash
uv sync          # install dependencies
make up          # start Qdrant (dashboard: http://localhost:6333/dashboard)
make corpus      # download the documents into data/raw
make check       # lint, type check and test
```

## Data

Real Pratt & Whitney engine manuals are proprietary, so the corpus uses public
US-government documents instead:

| Source | Documents |
| --- | --- |
| FAA Aviation Maintenance Technician Handbooks (2023) | Powerplant (FAA-H-8083-32B), General (FAA-H-8083-30B), Airframe (FAA-H-8083-31B) |
| Federal Register | Final-rule Airworthiness Directives for Pratt & Whitney engines (newest 60 by default) |

`make corpus` writes the PDFs to `data/raw/` and a `data/manifest.csv` recording each
file's source URL and SHA-256 hash. Re-running it skips files already on disk. `data/`
is git-ignored; the source list lives in `src/aerorag/ingestion/sources.py`.
