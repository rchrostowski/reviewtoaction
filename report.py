from io import BytesIO
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def build_pdf_report(
    business_name: str,
    issue_table: pd.DataFrame,
    top_quotes: dict[int, list[str]],
    summary_metrics: dict,
) -> bytes:
    """
    top_quotes: {cluster_id: [quote1, quote2, ...]}
    summary_metrics: e.g. {"reviews": 120, "negative_pct": 33.2, "avg_sentiment": -0.12}
    """
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    width, height = letter

    def header(title: str, y: float) -> float:
        c.setFont("Helvetica-Bold", 16)
        c.drawString(40, y, title)
        return y - 18

    def line(text: str, y: float, bold=False, size=11) -> float:
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.drawString(40, y, text[:120])
        return y - (size + 6)

    y = height - 50
    y = header(f"Review-to-Action Report: {business_name}", y)

    y = line(f"Total reviews analyzed: {summary_metrics.get('reviews', 'N/A')}", y)
    y = line(f"Negative %: {summary_metrics.get('negative_pct', 'N/A')}", y)
    y = line(f"Average sentiment: {summary_metrics.get('avg_sentiment', 'N/A')}", y)
    y -= 8

    y = line("Top priorities (do these first):", y, bold=True)

    top = issue_table.head(5).copy()
    for i, r in top.iterrows():
        if y < 120:
            c.showPage()
            y = height - 50
        y = line(f"{i+1}. {r['issue_label']}  | priority={r['priority_score']}  | freq={r['frequency']} ({r['frequency_pct']}%)", y)
        y = line(f"   Action: {r['recommended_action']}", y, size=10)

        quotes = top_quotes.get(int(r["cluster"]), [])[:2]
        for q in quotes:
            if y < 120:
                c.showPage()
                y = height - 50
            y = line(f'   Quote: "{q}"', y, size=9)
        y -= 4

    y = line("Notes:", y, bold=True)
    y = line("- This report groups similar review themes using text clustering.", y, size=10)
    y = line("- Priority score combines frequency, negativity severity, and ease-to-fix.", y, size=10)

    c.save()
    return buf.getvalue()
