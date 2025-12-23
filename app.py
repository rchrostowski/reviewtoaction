import streamlit as st
import pandas as pd

from auth import require_login
from db import init_db, insert_reviews, fetch_reviews, delete_all_reviews
from nlp import add_sentiment, cluster_issues
from scoring import compute_issue_table

st.set_page_config(page_title="Review-to-Action Engine", layout="wide")

def load_csv(file) -> pd.DataFrame:
    df = pd.read_csv(file)
    # Normalize expected columns
    cols = {c.lower().strip(): c for c in df.columns}
    if "review_text" not in cols:
        # Try common alternatives
        for alt in ["text", "review", "comment", "content"]:
            if alt in cols:
                df = df.rename(columns={cols[alt]: "review_text"})
                break

    if "review_text" not in df.columns:
        raise ValueError("CSV must contain a 'review_text' column (or text/review/comment/content).")

    # Optional columns
    if "rating" not in df.columns:
        df["rating"] = None
    if "date" not in df.columns:
        df["date"] = None

    df = df[["review_text", "rating", "date"]].copy()
    df["review_text"] = df["review_text"].astype(str)
    return df

def main():
    init_db()
    user = require_login()
    owner = user.username

    st.title("🧠 Review-to-Action Intelligence Engine")
    st.caption("Upload reviews → find recurring issues → prioritize fixes → export actions.")

    with st.sidebar:
        st.subheader("Settings")
        business_type = st.selectbox(
            "Business type (context)",
            ["Restaurant", "Coffee shop", "Gym", "Salon", "Clinic", "Hotel/Airbnb", "Other"],
            index=0,
        )
        n_clusters = st.slider("Number of issue clusters", 2, 12, 6)

    tab1, tab2, tab3, tab4 = st.tabs(["📥 Upload", "📊 Dashboard", "🧩 Evidence", "📌 Actions"])

    with tab1:
        st.subheader("Upload Reviews")
        st.write("Upload a CSV or paste reviews. Only **you** can see your data after login.")

        colA, colB = st.columns(2)

        with colA:
            uploaded = st.file_uploader("Upload CSV", type=["csv"])
            if uploaded:
                try:
                    df_new = load_csv(uploaded)
                    count = insert_reviews(owner, df_new)
                    st.success(f"Saved {count} reviews to your workspace.")
                except Exception as e:
                    st.error(f"Upload failed: {e}")

        with colB:
            pasted = st.text_area("Or paste reviews (one per line)", height=180)
            if st.button("Save pasted reviews"):
                lines = [x.strip() for x in pasted.splitlines() if x.strip()]
                if not lines:
                    st.warning("Paste at least one review.")
                else:
                    df_new = pd.DataFrame({"review_text": lines, "rating": None, "date": None})
                    count = insert_reviews(owner, df_new)
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

    # Prepare analysis (shared)
    df_all = fetch_reviews(owner)
    if len(df_all) >= 1:
        df_sent = add_sentiment(df_all)
        df_clustered, cluster_keywords = cluster_issues(df_sent, n_clusters=n_clusters)
        issue_table = compute_issue_table(df_clustered, cluster_keywords)
    else:
        df_sent = None
        df_clustered = None
        cluster_keywords = None
        issue_table = None

    with tab2:
        st.subheader("Dashboard")
        if df_all is None or len(df_all) == 0:
            st.info("Upload at least 1 review to see analytics.")
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

    with tab3:
        st.subheader("Evidence")
        if df_clustered is None:
            st.info("Upload reviews to see evidence.")
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
            for _, row in sub.head(8).iterrows():
                st.markdown(f"- ({row.get('rating', '')}) **{row['sentiment_label']}** ({row['sentiment_compound']:.3f}) — {row['review_text']}")

    with tab4:
        st.subheader("Action Plan")
        if issue_table is None:
            st.info("Upload reviews to get an action plan.")
        else:
            st.write("**Top 3 actions to do this week**")
            top3 = issue_table.head(3).copy()
            for i, r in top3.iterrows():
                st.markdown(f"### {i+1}) {r['issue_label']}")
                st.write(f"- **Why:** {r['frequency']} reviews ({r['frequency_pct']}%) and avg sentiment {r['avg_sentiment']}")
                st.write(f"- **Do:** {r['recommended_action']}")
                st.write(f"- **Priority score:** {r['priority_score']}")

            st.divider()
            st.write("Download your issue table")
            csv_bytes = issue_table.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Download Issues CSV",
                data=csv_bytes,
                file_name=f"{owner}_issues.csv",
                mime="text/csv",
                use_container_width=True,
            )

if __name__ == "__main__":
    main()

