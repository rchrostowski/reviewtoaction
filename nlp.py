import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_analyzer = SentimentIntensityAnalyzer()

def add_sentiment(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["sentiment_compound"] = out["review_text"].astype(str).apply(
        lambda t: _analyzer.polarity_scores(t)["compound"]
    )
    out["sentiment_label"] = pd.cut(
        out["sentiment_compound"],
        bins=[-1.01, -0.05, 0.05, 1.01],
        labels=["negative", "neutral", "positive"]
    )
    return out

def cluster_issues(df: pd.DataFrame, n_clusters: int) -> tuple[pd.DataFrame, dict]:
    texts = df["review_text"].astype(str).tolist()

    if len(texts) < 5:
        df2 = df.copy()
        df2["cluster"] = 0
        return df2, {0: ["mixed"]}

    # keep clusters sane
    n_clusters = max(2, min(n_clusters, max(2, len(texts)//3)))

    vect = TfidfVectorizer(
        stop_words="english",
        max_features=4000,
        ngram_range=(1, 2)
    )
    X = vect.fit_transform(texts)

    model = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
    clusters = model.fit_predict(X)

    df2 = df.copy()
    df2["cluster"] = clusters

    terms = np.array(vect.get_feature_names_out())
    cluster_keywords = {}

    for c in range(n_clusters):
        idx = np.where(clusters == c)[0]
        if len(idx) == 0:
            cluster_keywords[c] = ["(empty)"]
            continue

        mean_tfidf = X[idx].mean(axis=0)
        mean_tfidf = np.asarray(mean_tfidf).ravel()
        top = mean_tfidf.argsort()[::-1][:8]
        cluster_keywords[c] = terms[top].tolist()

    return df2, cluster_keywords


