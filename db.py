import sqlite3
import pandas as pd

DB_PATH = "app.db"

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # Users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            pw_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Reviews table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner TEXT NOT NULL,
            source TEXT,
            review_text TEXT NOT NULL,
            rating REAL,
            date TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.commit()
    conn.close()

# -------- Users --------

def upsert_user(username: str, pw_hash: str) -> None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (username, pw_hash) VALUES (?, ?)
        ON CONFLICT(username) DO UPDATE SET pw_hash = excluded.pw_hash;
    """, (username, pw_hash))
    conn.commit()
    conn.close()

def get_user_hash(username: str) -> str | None:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT pw_hash FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

def list_users() -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query("SELECT username, created_at FROM users ORDER BY created_at DESC", conn)
    conn.close()
    return df

# -------- Reviews --------

def insert_reviews(owner: str, df: pd.DataFrame, source: str = "upload") -> int:
    conn = get_conn()
    cur = conn.cursor()
    rows = 0
    for _, r in df.iterrows():
        cur.execute(
            "INSERT INTO reviews (owner, source, review_text, rating, date) VALUES (?, ?, ?, ?, ?)",
            (
                owner,
                source,
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
        "SELECT id, source, review_text, rating, date, created_at FROM reviews WHERE owner = ? ORDER BY id DESC",
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
