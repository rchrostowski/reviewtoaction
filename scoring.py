import pandas as pd

ACTION_RULES = [
    (["wait", "line", "slow", "minutes"], "Reduce wait times: add staff at peak hours, simplify workflow, prep high-demand items."),
    (["rude", "attitude", "unfriendly"], "Improve service: quick staff coaching, greeting script, and manager follow-up on complaints."),
    (["dirty", "clean", "bathroom", "mess"], "Improve cleanliness: add cleaning checklist and assign ownership per shift."),
    (["price", "expensive", "cost"], "Address pricing: highlight value, add bundles, or adjust portion/quality messaging."),
    (["cold", "hot", "temperature"], "Fix temperature/quality: check holding times, packaging, and handoff process."),
    (["schedule", "appointment", "booking"], "Fix scheduling: tighten booking rules, add buffer time, and confirm appointments."),
    (["noise", "loud", "music"], "Improve ambience: adjust music volume, add quiet zones, and manage peak-time crowding."),
    (["parking", "traffic"], "Reduce parking friction: signage, partner lots, peak-time guidance, and clear directions."),
]

def issue_label_from_keywords(keywords: list[str]) -> str:
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
    total = len(df)
    rows = []

    for cluster_id, sub in df.groupby("cluster"):
        freq = len(sub)
        freq_pct = freq / total if total else 0.0

        # sentiment compound in [-1, 1]
        avg_comp = float(sub["sentiment_compound"].mean())
        # severity 0..1 (more negative => higher severity)
        severity = max(0.0, (-avg_comp + 1) / 2)

        kws = cluster_keywords.get(int(cluster_id), [])
        # heuristic ease score
        ease = 0.65
        if any(k in " ".join(kws).lower() for k in ["clean", "bathroom", "staff", "wait", "line", "schedule"]):
            ease = 0.75

        # priority (scaled)
        priority = (freq_pct * 100) * (severity * 100) * (ease * 100) / 10000

        rows.append({
            "cluster": int(cluster_id),
            "issue_label": issue_label_from_keywords(kws),
            "frequency": freq,
            "frequency_pct": round(freq_pct * 100, 1),
            "avg_sentiment": round(avg_comp, 3),
            "severity_score_0_1": round(severity, 3),
            "ease_to_fix_0_1": round(ease, 3),
            "priority_score": round(priority, 2),
            "recommended_action": recommended_action(kws),
        })

    return pd.DataFrame(rows).sort_values("priority_score", ascending=False).reset_index(drop=True)



