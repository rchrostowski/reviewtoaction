import streamlit as st
import pandas as pd

from auth import require_login, hash_password
from db import init_db, insert_reviews, fetch_reviews, delete_all_reviews, upsert_user, list_users
from nlp import add_sentiment, cluster_issues
from scoring import compute_issue_table
from report import build_pdf_report
from imports import import_google_reviews_outscraper, import_google_reviews_serpapi

st.set_page_config(page_title="Review-to-Action Engine", layout="wide")

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

def admin_panel():
    st.subheader("🛠️ Admin Panel (Users)")
    st.caption("Create business logins and reset passwords. Each user only sees their own reviews.")

    users_df = list_users()
    st.dataframe(users_df, use_container_width=True, hide_index=True)

    st.divider()
    st.write("### Create / Reset a user password")
    col1, col2 = st.columns(2)
    with col1:
        new_user = st.text_input("Username (business login)")
    with col2:
        new_pw = st.text_input("New password", type="password")

    if st.button("Save user", use_container_width=True):
        if not new_user or not new_pw:
            st.error("Provide username and password.")
        elif new_user.strip().lower() == "admin":
            st.error("Use Streamlit secrets to set admin password.")
        else:
            upsert_user(new_user.strip(), hash_password(new_pw))
            st.success(f"Saved user: {new_user.strip()}")
            st.rerun()

def main():
    init_db()
    user = require_login()
    owner = user.username

    st.title("🧠 Review-to-Action Intelligence Engine")
    st.caption("Upload/import reviews → find recurring issues → prioritize fixes → export PDF report.")

    with st.sidebar:
        st.subheader("Settings")
        business_name = st.text_input("Business name (for report)", value=owner)
        business_type = st.selectbox(
            "Business type (context)",
            ["Restaurant", "Coffee shop", "Gym", "Salon", "Clinic", "Hotel/Airbnb", "Other"],
            index=0,
        )
        n_clusters = st.slider("Number of issue clusters", 2, 12, 6)

        st.divider()
        if user.is_admin:
            with st.expander("Admin", expanded=False):
                admin_panel()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📥 Upload", "🔗 Import via URL", "📊 Dashboard", "🧩 Evidence", "📄 Report (PDF)"])

    # --- Upload ---
    with tab1:
        st.subheader("Upload Reviews (CSV or Paste)")
        colA, colB = st.columns(2)

        with colA:
            uploaded = st.file_uploader("Upload CSV", type=["csv"])
            if uploaded:
                try:
                    df_new = load_csv(uploaded)
                    count = insert_reviews(owner, df_new, source="csv_upload")
                    st.success(f"Saved {count} reviews to your workspace.")
                except Exception as e:
                    st.error(f"Upload failed: {e}")

        with colB:
            pasted = st.text_area("Paste reviews (one per line)", height=180)
            if st.button("Save pasted reviews"):
                lines = [x.strip() for x in pasted.splitlines() if x.strip()]
                if not lines:
                    st.warning("Paste at least one review.")
                else:
                    df_new = pd.DataFrame({"review_text": lines, "rating": None, "date": None})
                    count = insert_reviews(owner, df_new, source="paste")
                    st.success(f"Saved {count} reviews to your workspace.")

        st.divider()
        st.subheader("Your stored reviews")
        df_all = fetch_reviews(owner)
        st.write(f"Total reviews in your workspace: **{len(df_all)}**")
        st.dataframe(df_all.head(50), use_container_width=True)

        if len(df_all) > 0:
            if st.button("🗑️ Delete ALL my reviews", type="secondary"):
                delete_all_reviews(owner)
                st.success("Deleted your reviews.")
                st.rerun()

    # --- Import via URL (Provider APIs) ---
    with tab2:
        st.subheader("Import Reviews via URL (Provider APIs)")
        st.caption("We avoid direct HTML scraping. Use an API provider for structured review data.")

        provider = st.selectbox("Provider", ["Outscraper (Google)", "SerpApi (Google)"])
        place = st.text_input("Google place URL or Place ID (depending on provider)")
        limit = st.slider("Max reviews to import", 10, 500, 200)

        if st.button("Import", use_container_width=True):
            try:
                if provider.startswith("Outscraper"):
                    df_imp = import_google_reviews_outscraper(place, limit=limit)
                    src = "outscraper"
                else:
                    df_imp = import_google_reviews_serpapi(place, limit=min(limit, 100))
                    src = "serpapi"

                if df_imp is None or len(df_imp) == 0:
                    st.warning("No reviews returned. Check your URL/Place ID or provider params.")
                else:
                    count = insert_reviews(owner, df_imp, source=src)
                    st.success(f"Imported and saved {count} reviews.")
            except Exception as e:
                st.error(f"Import failed: {e}")
                st.info("Make sure your API key is set in Streamlit secrets (OUTSCRAPER_API_KEY or SERPAPI_API_KEY).")

    # --- Shared analysis ---
    df_all = fetch_reviews(owner)
    if len(df_all) >= 1:
        df_sent = add_sentiment(df_all)
        df_clustered, cluster_keywords = cluster_issues(df_sent, n_clusters=n_clusters)
        issue_table = compute_issue_table(df_clustered, cluster_keywords)
    else:
        df_sent = df_clustered = cluster_keywords = issue_table = None

    # --- Dashboard ---
    with tab3:
        st.subheader("Dashboard")
        if df_all is None or len(df_all) == 0:
            st.info("Upload or import reviews to see analytics.")
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
                freq_df = issue_table[["issue_label", "frequency"]].copy()
                st.bar_chart(freq_df.set_index("issue_label"))

    # --- Evidence ---
    with tab4:
        st.subheader("Evidence")
        if df_clustered is None:
            st.info("Upload/import reviews to see evidence.")
        else:
            issue_pick = st.selectbox(
                "Select an issue cluster",
                options=issue_table["cluster"].tolist(),
                format_func=lambda c: f"Cluster {c}: {issue_table.loc[issue_table['cluster']==c, 'issue_label'].values[0]}",
            )
            kws = cluster_keywords.get(issue_pick, [])
            st.write("**Top keywords:**", ", ".join(kws))

            sub = df_clustered[df_clustered["cluster"] == issue_pick].copy()
            sub = sub.sort_values("sentiment_compound")  # most negative first

            st.write("**Most negative examples**")
            for _, row in sub.head(10).iterrows():
                st.markdown(f"- **{row['sentiment_label']}** ({row['sentiment_compound']:.3f}) — {row['review_text']}")

    # --- PDF Report ---
    with tab5:
        st.subheader("PDF Report (Deliverable)")
        if issue_table is None:
            st.info("Upload/import reviews first.")
        else:
            # Build top quotes dict for report
            top_quotes = {}
            for _, r in issue_table.head(5).iterrows():
                cid = int(r["cluster"])
                sub = df_clustered[df_clustered["cluster"] == cid].copy().sort_values("sentiment_compound")
                top_quotes[cid] = sub["review_text"].astype(str).head(3).tolist()

            neg_pct = float((df_sent["sentiment_label"] == "negative").mean() * 100)
            avg = float(df_sent["sentiment_compound"].mean())
            metrics = {"reviews": len(df_all), "negative_pct": round(neg_pct, 1), "avg_sentiment": round(avg, 3)}

            st.write("Preview: Top 5 priorities")
            st.dataframe(issue_table.head(5), use_container_width=True, hide_index=True)

            pdf_bytes = build_pdf_report(
                business_name=business_name,
                issue_table=issue_table,
                top_quotes=top_quotes,
                summary_metrics=metrics,
            )

            st.download_button(
                "⬇️ Download PDF Report",
                data=pdf_bytes,
                file_name=f"{business_name}_review_to_action_report.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

if __name__ == "__main__":
    main()
