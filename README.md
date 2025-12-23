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
Install deps

bash
Copy code
pip install -r requirements.txt
Run

bash
Copy code
streamlit run app.py
CSV Format
Use columns:

review_text (required)

rating (optional, 1-5)

date (optional, YYYY-MM-DD)

See sample_data/sample_reviews.csv

Add Users
Edit USERS in auth.py (demo mode). For production:

Move USERS to Streamlit secrets

Use hashed passwords

Use an admin UI to create users

Deploy
Streamlit Community Cloud: push to GitHub, deploy app.py

Remember: SQLite works for small use; for scale use Postgres

yaml
Copy code

---

## `sample_data/sample_reviews.csv`

```csv
review_text,rating,date
"Love the coffee but the line is always long during lunch.",4,2025-11-02
"Staff was rude and the place felt dirty.",1,2025-11-10
"Prices are too high for what you get.",2,2025-11-15
"Great vibe and friendly service!",5,2025-11-18
"Waited 25 minutes for my order. Unacceptable.",1,2025-11-20
"The bathroom was messy and smelled bad.",1,2025-11-21
"Food was cold when it arrived.",2,2025-11-25
"Love the pastries. Coffee could be hotter.",4,2025-11-28
