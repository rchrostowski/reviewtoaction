import uuid
import streamlit as st
import pandas as pd

from db import init_db, insert_reviews, fetch_reviews, delete_all_reviews
from nlp import add_sentiment, cluster_issues
from scoring import compute_issue_table
from report import build_pdf_report
from providers import serpapi_search_place, serpapi_fetch_reviews

st.set_page_config(page_title="Review-to-Action Engine", layout="wide")

def ensure_workspace():
    if "workspace_id" not in st.session_state:
        st.session_state["workspace_id"] = str(uuid.uuid4())
    return st.session_state["workspace_id"]

def load_csv(file) -> pd.DataFrame:
    df = pd.read_csv(file)
    cols = {c.lower().strip(): c for c in df.columns}

    if "review_text" not in cols:
        for alt in ["text", "review", "comment", "content"]:
            if alt in cols:
                df = df.rename(columns={cols[alt]: "review_text"})
                break

    if "review_text" not in df.columns:
        raise ValueError("CSV must contain 'review_text' (or text/review/comment/content).")

    if "rating" not in df.columns:
        df["rating"] = None
    if "date" not in df.columns:
        df["date"] = None

    df = df[["review_text", "rating", "date"]].copy()
    df["review_text"] = df["review_text"].astype(str)
    return df

def main():
    init_db()
    ws = ensure_workspace()

    st.title("🧠 Review-to-Action Engine")
    st.caption("Search any place → import reviews → find issues → prioritize actions → download PDF.")

    with st.sidebar:
        st.subheader("Analysis settings")
        n_clusters = st.slider("Number of issue clusters", 2, 12, 6)
        st.divider()
        st.subheader("Workspace")
        st.write("This session workspace ID:")
        st.code(ws)
        if st.button("🧹 Clear my workspace reviews"):
            delete_all_reviews(ws)
            st.success("Cleared workspace reviews.")

    tab1, tab2, tab3, tab4 = st.tabs(["🔎 Search & Import", "📥 Upload / Paste", "📊 Dashboard", "📄 PDF Report"])

    # --- Search & Import ---
    with tab1:
        st.subheader("Search a place and import reviews")
        st.write("Requires `SERPAPI_API_KEY` in Streamlit secrets. If missing, use Upload/Paste tab.")

        q = st.text_input("Search (e.g., 'Blue Bottle Coffee Boston' or 'Joe's Pizza NYC')")
        location = st.text_input("Optional location hint (e.g., 'Boston, MA')", value="")

        colA, colB = st.columns([1, 1])
        with colA:
            if st.button("Search places", use_container_width=True):
                try:
                    places = serpapi_search_place(q, location=location or None)
                    if not places:
                        st.warning("No places found. Try a more specific query.")
                    else:
                        st.session_state["place_candidates"] = places
                        st.success(f"Found {len(places)} candidates.")
                except Exception as e:
                    st.error(str(e))

        places = st.session_state.get("place_candidates", [])
        if places:
            st.write("Select the correct place:")
            labels = []
            for p in places:
                labels.append(f"{p['title']} — {p.get('address','')} (rating: {p.get('rating')}, reviews: {p.get('reviews')})")
            idx = st.selectbox("Candidates", options=list(range(len(places))), format_func=lambda i: labels[i])

            limit = st.slider("Max reviews to import", 10, 500, 200)
            if st.button("Import reviews for selected place", use_container_width=True):
                chosen = places[idx]
                pid = chosen.get("place_id") or chosen.get("data_id")
                if not pid:
                    st.error("No place_id/data_id found for this place. Try another candidate.")
                else:
                    try:
                        df_imp = serpapi_fetch_reviews(pid, limit=limit)
                        if df_imp is None or df_imp.empty:
                            st.warning("No reviews returned. Some places may block or have limited review access.")
                        else:
                            count = insert_reviews(ws, df_imp, source="serpapi")
                            st.success(f"Imported {count} reviews into your workspace.")
                            st.session_state["current_place_name"] = chosen["title"]
                    except Exception as e:
                        st.error(str(e))

    # --- Upload / Paste ---
    with tab2:
        st.subheader("Upload CSV or paste reviews (fallback)")
        col1, col2 = st.columns(2)

        with col1:
            up = st.file_uploader("Upload CSV", type=["csv"])
            if up:
                try:
                    df_new = load_csv(up)
                    n = insert_reviews(ws, df_new, source="csv")
                    st.success(f"Saved {n} reviews.")
                except Exception as e:
                    st.error(f"Upload failed: {e}")

        with col2:
            pasted = st.text_area("Paste reviews (one per line)", height=180)
            if st.button("Save pasted reviews"):
                lines = [x.strip() for x in pasted.splitlines() if x.strip()]
                if not lines:
                    st.warning("Paste at least one review.")
                else:
                    df_new = pd.DataFrame({"review_text": lines, "rating": None, "date": None})
                    n = insert_reviews(ws, df_new, source="paste")
                    st.success(f"Saved {n} reviews.")

        st.divider()
        df_all = fetch_reviews(ws)
        st.write(f"Reviews in workspace: **{len(df_all)}**")
        st.dataframe(df_all.head(50), use_container_width=True)

    # --- Analysis shared ---
    df_all = fetch_reviews(ws)
    if len(df_all) > 0:
        df_sent = add_sentiment(df_all)
        df_clustered, cluster_keywords = cluster_issues(df_sent, n_clusters=n_clusters)
        issue_table = compute_issue_table(df_clustered, cluster_keywords)
    else:
        df_sent = df_clustered = cluster_keywords = issue_table = None

    # --- Dashboard ---
    with tab3:
        st.subheader("Dashboard")
        if df_sent is None:
            st.info("Import or upload reviews first.")
        else:
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Reviews", len(df_all))
            with c2:
                neg_pct = float((df_sent["sentiment_label"] == "negative").mean() * 100)
                st.metric("Negative %", f"{neg_pct:.1f}%")
            with c3:
                avg = float(df_sent["sentiment_compound"].mean())
                st.metric("Avg sentiment", f"{avg:.3f}")

            st.divider()
            left, right = st.columns([1, 1])
            with left:
                st.write("**Top Issues (by priority)**")
                st.dataframe(issue_table, use_container_width=True, hide_index=True)
            with right:
                st.write("**Issue frequency**")
                st.bar_chart(issue_table[["issue_label", "frequency"]].set_index("issue_label"))

            st.divider()
            st.write("**Cluster keywords**")
            for _, r in issue_table.head(8).iterrows():
                cid = int(r["cluster"])
                st.write(f"- **{r['issue_label']}** → {', '.join(cluster_keywords.get(cid, []))}")

    # --- PDF report ---
    with tab4:
        st.subheader("PDF Report")
        if issue_table is None:
            st.info("Import or upload reviews first.")
        else:
            place_name = st.session_state.get("current_place_name", "Selected Place / Business")

            # quotes for top issues
            top_quotes = {}
            for _, r in issue_table.head(5).iterrows():
                cid = int(r["cluster"])
                sub = df_clustered[df_clustered["cluster"] == cid].copy().sort_values("sentiment_compound")
                top_quotes[cid] = sub["review_text"].astype(str).head(3).tolist()

            neg_pct = float((df_sent["sentiment_label"] == "negative").mean() * 100)
            avg = float(df_sent["sentiment_compound"].mean())
            metrics = {"reviews": len(df_all), "negative_pct": round(neg_pct, 1), "avg_sentiment": round(avg, 3)}

            st.write("Preview (Top 5 priorities):")
            st.dataframe(issue_table.head(5), use_container_width=True, hide_index=True)

            pdf_bytes = build_pdf_report(place_name, issue_table, top_quotes, metrics)
            st.download_button(
                "⬇️ Download PDF",
                data=pdf_bytes,
                file_name=f"{place_name}_review_to_action_report.pdf".replace(" ", "_"),
                mime="application/pdf",
                use_container_width=True,
            )

if __name__ == "__main__":
    main()

