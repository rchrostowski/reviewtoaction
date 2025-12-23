# Review-to-Action Intelligence Engine (Streamlit)

Multi-tenant Streamlit app that converts customer reviews into prioritized operational actions.

## Features
- Login (username/password)
- Each business only sees their own uploaded reviews (row-level isolation)
- Upload reviews via CSV
- Issue clustering (TF-IDF + KMeans)
- Sentiment scoring (VADER)
- Priority scoring & recommended actions
- Downloadable issue table CSV

## Quickstart

1) Create a virtual env (optional)
```bash
python -m venv .venv
source .venv/bin/activate  # mac/linux
# .venv\Scripts\activate   # windows

