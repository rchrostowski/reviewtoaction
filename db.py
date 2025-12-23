import sqlite3
from typing import Optional
import pandas as pd

DB_PATH = "app.db"

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner TEXT NOT NULL,
            review_text TEXT NOT NULL,
            rating REAL,
            date TEXT
        );
    """)
    conn.commit()
    conn.close()

def insert_reviews(owner: str, df: pd.DataFrame) -> int:
    conn = get_conn()
    cur = conn.cursor()
    rows = 0
    for _, r in df.iterrows():
        cur.execute(
            "INSERT INTO reviews (owner, review_text, rating, date) VALUES (?, ?, ?, ?)",
            (
                owner,
                str(r["review_text"]),
                float(r["rating"]) if "rating" in df.columns and pd.notna(r.get("rating")) else None,
                str(r["date"]) if "date" in df.columns and pd.notna(r.get("date")) else None,
            )
        )
        rows += 1
    conn.commit()
    conn.close()
    return rows

def fetch_reviews(owner: str) -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query(
        "SELECT id, review_text, rating, date FROM reviews WHERE owner = ? ORDER BY id DESC",
        conn,
        params=(owner,),
    )
    conn.close()
    return df

def delete_all_reviews(owner: str) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM reviews WHERE owner = ?", (owner,))
    conn.commit()
    conn.close()

