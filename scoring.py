import pandas as pd

# Simple action templates by keyword cues
ACTION_RULES = [
    (["wait", "line", "slow", "minutes"], "Reduce wait times: add staff at peak hours, simplify workflow, prep high-demand items."),
    (["rude", "attitude", "unfriendly"], "Improve service: quick staff coaching, greeting script, and manager follow-up on complaints."),
    (["dirty", "clean", "bathroom", "mess"], "Improve cleanliness: add cleaning checklist and assign ownership per shift."),
    (["price", "expensive", "cost"], "Address pricing: highlight value, add bundles, or adjust portion/quality messaging."),
    (["cold", "hot", "temperature"], "Fix temperature/quality: check holding times, packaging, and handoff process."),
    (["schedule", "appointment", "booking"], "Fix scheduling: tighten booking rules, add buffer time, and confirm appointments."),
]

def issue_name_from_keywords(keywords: list[str]) -> str:
    # Make a readable short label
    if not keywords:
        return "General"
    return ", ".join(keywords[:3])

def recommended_action(keywords: list[str]) -> str:
    kws = " ".join(keywords).lower()
    for triggers, action in ACTION_RULES:
        if any(t in kws for t in triggers):
            return action
    return "Review top quotes and implement a simple SOP change; measure results weekly."

def compute_issue_table(df: pd.DataFrame, cluster_keywords: dict) -> pd.DataFrame:
    """
    df must have: cluster, sentiment_compound, sentiment_label
    """
    total = len(df)
    rows = []
    for cluster_id, sub in df.groupby("cluster"):
        freq = len(sub)
        freq_pct = freq / total if total else 0.0

        # Severity: focus on negative sentiment
        # Convert compound (-1..1) to severity (0..1), higher means worse
        avg_comp = float(sub["sentiment_compound"].mean())
        severity = max(0.0, (-avg_comp + 1) / 2)  # negative => higher severity

        # Ease: heuristic (for MVP). Later can be user-input.
        # Assume most operational fixes are medium-easy; nudge up if keywords hint operational.
        kws = cluster_keywords.get(cluster_id, [])
        ease = 0.65
        if any(k in " ".join(kws).lower() for k in ["clean", "bathroom", "staff", "wait", "line", "schedule"]):
            ease = 0.75

        priority = (freq_pct * 100) * (severity * 100) * (ease * 100) / 10000  # keep scale sane

        rows.append({
            "cluster": int(cluster_id),
            "issue_label": issue_name_from_keywords(kws),
            "frequency": freq,
            "frequency_pct": round(freq_pct * 100, 1),
            "avg_sentiment": round(avg_comp, 3),
            "severity_score_0_1": round(severity, 3),
            "ease_to_fix_0_1": round(ease, 3),
            "priority_score": round(priority, 2),
            "recommended_action": recommended_action(kws),
        })

    out = pd.DataFrame(rows).sort_values("priority_score", ascending=False).reset_index(drop=True)
    return out

