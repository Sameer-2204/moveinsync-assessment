"""Build an evidence-linked recommendation document from collected reviews.

This is a quota-safe fallback for the unavailable Gemini classifier. It applies
the approved taxonomy using transparent regex rules, writes labels under a
separate prompt version, and renders every reported number from Postgres.
"""
import json
import os
import re
import html
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
import markdown as markdown_lib
from psycopg2.extras import execute_batch
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.db.schema import get_connection

TAXONOMY_VERSION = "1.0"
PROMPT_VERSION = "rule-v1"
MODEL_NAME = "rule_based_taxonomy_v1"
OUTPUTS = Path("outputs")

RULES = (
    ("app_crash_install", "app", r"\b(crash|crashes|blank screen|install|installed from play|reinstall|open the app|not open)\b"),
    ("login_otp", "app", r"\b(otp|log ?in(?! time)|sign ?in|verify|verification|register|registration)\b"),
    ("booking_scheduling", "app", r"\b(book|booking|schedule|calendar|roster|waitlist|adhoc|ad hoc|destination)\b"),
    ("live_tracking_eta", "app", r"\b(track|tracking|location|eta|gps|map|cab tracker)\b"),
    ("late_noshow_cab", "ops_vendor", r"\b(late|delay|delayed|waiting|waited|no show|not assigned)\b"),
    ("routing_stops", "ops_vendor", r"\b(route|routing|stop|pickup|drop|detour)\b"),
    ("driver_behavior_safety", "ops_vendor", r"\b(driver|unsafe|safety|female|speed|rude|behav)\b"),
    ("notification_rating_prompt", "app", r"\b(notification|notify|rating|rate|review|pop-up|popup)\b"),
    ("support_helpdesk", "app", r"\b(help ?desk|support|customer service|feedback|contact|calling option)\b"),
    ("app_performance", "app", r"\b(slow|lag|loading|load|network|connect|battery|heat|hang)\b"),
    ("ui_ux_design", "app", r"\b(ui|user friendly|interface|design|navigation|feature|permission|policy acceptance)\b"),
)

SOLUTIONS = {
    "app_crash_install": ("Instrument launch/install failures by app version and device; show a recoverable in-app error with support diagnostics rather than forcing reinstall.", "Engineering", "M", "Crash-free sessions and 1–2-star crash/install reviews."),
    "login_otp": ("Add OTP delivery-status feedback, resend fallback, and a self-serve recovery path; log provider and channel failures by tenant without exposing personal data.", "Engineering", "M", "OTP completion rate, login success rate, and 1–2-star login/OTP reviews."),
    "booking_scheduling": ("Make booking state, cut-off, waitlist, and edit eligibility explicit on one screen; provide actionable errors and route roster conflicts to the transport desk.", "Product + Engineering", "M", "Booking completion rate, booking-error rate, and 1–2-star booking reviews."),
    "live_tracking_eta": ("Show last GPS update time and confidence, suppress stale ETAs, and provide a clear fallback status when vehicle telemetry is unavailable.", "Engineering", "M", "Fresh-location rate, ETA error, and 1–2-star tracking/ETA reviews."),
    "late_noshow_cab": ("Create an operations alert when assignment or pickup exceeds its SLA; send proactive delay explanation and an escalation link, and review vendor performance weekly.", "Ops", "M", "On-time pickup rate, no-show rate, and 1–2-star late/no-show reviews."),
    "routing_stops": ("Expose the policy-controlled pickup/drop rationale, capture exception requests, and give customer transport desks a weekly list of high-friction stops and detours.", "Customer Success + Ops", "L", "Route-duration variance, approved exception rate, and 1–2-star routing/stop reviews."),
    "driver_behavior_safety": ("Add a one-tap, safety-prioritized incident flow with case ID and escalation SLA; route verified patterns to vendor coaching and customer transport desks.", "Ops", "M", "Safety incident closure time, repeat vendor incidents, and safety-related 1–2-star reviews."),
    "notification_rating_prompt": ("Remove mandatory/repeated rating prompts; show a dismissible prompt only after a completed, non-exceptional trip and cap frequency.", "Product + Engineering", "S", "Prompt exposure rate, dismissal rate, and rating-prompt complaint volume."),
    "support_helpdesk": ("Place a persistent Help & Escalate entry point in booking and trip screens, with current case status and tenant-specific escalation ownership.", "Product + Customer Success", "M", "Help-entry success rate, first-response time, and support-related 1–2-star reviews."),
    "app_performance": ("Define performance budgets for launch and critical booking screens; capture slow requests and offer retry states with diagnostics.", "Engineering", "M", "p95 launch/booking latency and 1–2-star performance reviews."),
    "ui_ux_design": ("Run task-based usability tests for booking, OTP, and trip-status flows; remove duplicate confirmations and surface pickup, cab, and support information at the point of need.", "Product + Design", "M", "Task completion rate and 1–2-star UI/UX reviews."),
}

QUOTE_PATTERNS = {
    "app_crash_install": r"\b(crash|blank screen|not downloaded from play|reinstall|unable to open|won't open)\b",
    "login_otp": r"\b(otp|unable to login|can't log ?in|cannot log ?in|not getting.*otp)\b",
    "booking_scheduling": r"\b(book|booking|schedule|calendar|waitlist|adhoc|ad hoc)\b",
    "live_tracking_eta": r"\b(track|tracking|location|eta|gps|cab tracker)\b",
    "late_noshow_cab": r"\b(late|delay|delayed|no show|not assigned|wait for)\b",
    "routing_stops": r"\b(route|routing|detour|different areas|middle of nowhere|pickup stop|drop stop)\b",
    "driver_behavior_safety": r"\b(driver|unsafe|safety|female|rude|speed)\b",
    "notification_rating_prompt": r"\b(notification|notify|rating|rate|review|pop-up|popup)\b",
    "support_helpdesk": r"\b(help ?desk|support|feedback|contact|calling option)\b",
    "app_performance": r"\b(slow|lag|loading|load|network|connect|battery|heat|hang)\b",
    "ui_ux_design": r"\b(ui|user friendly|interface|design|navigation|permission|policy acceptance)\b",
}


def classify(text, rating):
    lowered = (text or "").lower()
    for theme, attribution, pattern in RULES:
        match = re.search(pattern, lowered, re.IGNORECASE)
        if match:
            if theme == "routing_stops" and re.search(r"\b(company|organisation|organization|office|shift|policy)\b", lowered):
                attribution = "customer_policy"
            severity = 3 if (theme == "driver_behavior_safety" and re.search(r"\b(unsafe|safety|female)\b", lowered)) else (3 if rating <= 2 else 2 if rating == 3 else 1)
            return theme, attribution, text[match.start():match.end()], severity
    if rating >= 4 and len((text or "").strip()) >= 3:
        return "positive_general", "unclear", text.strip(), 1
    return "other_unclear", "unclear", "", 3 if rating <= 2 else 2 if rating == 3 else 1


def label_all(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT review_id, text, rating FROM reviews ORDER BY review_id")
        reviews = cur.fetchall()
        values = []
        for review_id, text, rating in reviews:
            theme, attribution, evidence, severity = classify(text, rating)
            sentiment = "negative" if rating <= 2 else "mixed" if rating == 3 else "positive"
            values.append((review_id, TAXONOMY_VERSION, [theme], theme, sentiment, severity, attribution, evidence, 0.55, MODEL_NAME, PROMPT_VERSION))
        execute_batch(cur, """INSERT INTO labels (review_id, taxonomy_version, themes, primary_theme, sentiment, severity, attribution, evidence_span, confidence, model, prompt_version, status)
                             VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'auto')
                             ON CONFLICT (review_id, taxonomy_version, prompt_version) DO UPDATE SET
                             themes=EXCLUDED.themes, primary_theme=EXCLUDED.primary_theme, sentiment=EXCLUDED.sentiment, severity=EXCLUDED.severity,
                             attribution=EXCLUDED.attribution, evidence_span=EXCLUDED.evidence_span, confidence=EXCLUDED.confidence, model=EXCLUDED.model, labeled_at=NOW(), status='auto'""", values, page_size=500)
    conn.commit()
    return len(reviews)


def wilson(successes, n):
    if not n:
        return (0.0, 0.0)
    z = 1.96
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    spread = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / denom
    return (100 * (center - spread), 100 * (center + spread))


def get_data(conn):
    with conn.cursor() as cur:
        cur.execute("""SELECT COUNT(*), AVG(rating), MIN(review_date), MAX(review_date),
                              COUNT(*) FILTER (WHERE rating <= 2)
                       FROM reviews r JOIN apps a ON a.app_id=r.app_id
                       WHERE a.package_id='com.moveinsync.ets'""")
        n, mean_rating, start, end, negative_n = cur.fetchone()
        cur.execute("""SELECT l.primary_theme, COUNT(*) AS n, AVG(r.rating) AS mean_rating,
                              COUNT(*) FILTER (WHERE r.rating <= 2) AS negative_n
                       FROM labels l JOIN reviews r ON r.review_id=l.review_id
                       JOIN apps a ON a.app_id=r.app_id
                       WHERE a.package_id='com.moveinsync.ets' AND l.prompt_version=%s
                       GROUP BY l.primary_theme""", (PROMPT_VERSION,))
        rows = []
        for theme, count, theme_mean, theme_negative in cur.fetchall():
            cur.execute("""SELECT AVG(r.rating) FROM labels l JOIN reviews r ON r.review_id=l.review_id
                           JOIN apps a ON a.app_id=r.app_id
                           WHERE a.package_id='com.moveinsync.ets' AND l.prompt_version=%s AND l.primary_theme<>%s""", (PROMPT_VERSION, theme))
            rest_mean = cur.fetchone()[0]
            loss = float(rest_mean - mean_rating) if rest_mean is not None else 0.0
            rows.append({"theme": theme, "n": count, "mean": float(theme_mean), "negative_n": theme_negative, "share": 100 * count / n, "negative_share": 100 * theme_negative / negative_n if negative_n else 0, "points_lost": loss})
        rows.sort(key=lambda item: (item["points_lost"], item["n"]), reverse=True)
        cur.execute("""SELECT l.primary_theme, l.attribution, COUNT(*) FROM labels l
                       JOIN reviews r ON r.review_id=l.review_id JOIN apps a ON a.app_id=r.app_id
                       WHERE a.package_id='com.moveinsync.ets' AND r.rating<=2 AND l.prompt_version=%s
                       GROUP BY l.primary_theme, l.attribution""", (PROMPT_VERSION,))
        attribution = cur.fetchall()
    low, high = wilson(negative_n, n)
    return {"n": n, "mean": float(mean_rating), "start": start.date().isoformat(), "end": end.date().isoformat(), "negative_n": negative_n, "negative_pct": 100 * negative_n / n, "negative_ci": (low, high), "themes": rows, "attribution": attribution}


def quotes_for(conn, theme):
    with conn.cursor() as cur:
        cur.execute("""SELECT r.review_id, r.rating, r.text FROM labels l JOIN reviews r ON r.review_id=l.review_id
                       JOIN apps a ON a.app_id=r.app_id
                       WHERE a.package_id='com.moveinsync.ets' AND l.prompt_version=%s AND l.primary_theme=%s
                         AND r.rating<=2 AND LENGTH(r.text)>=25
                       ORDER BY r.thumbs_up DESC, LENGTH(r.text) DESC, r.review_id LIMIT 100""", (PROMPT_VERSION, theme))
        matches = [row for row in cur.fetchall() if re.search(QUOTE_PATTERNS[theme], row[2], re.IGNORECASE)]
        return [{"review_id": row[0], "rating": row[1], "text": row[2]} for row in matches[:3]]


def write_pdf(markdown_text, path):
    """Render the report with a pure-Python backend available on Windows."""
    font_name = "Helvetica"
    arial = Path(os.environ.get("WINDIR", "C:\\Windows")) / "Fonts" / "arial.ttf"
    if arial.exists():
        pdfmetrics.registerFont(TTFont("ReportArial", str(arial)))
        font_name = "ReportArial"
    styles = getSampleStyleSheet()
    body = ParagraphStyle("ReportBody", parent=styles["BodyText"], fontName=font_name, fontSize=9.5, leading=13, spaceAfter=6)
    quote = ParagraphStyle("ReportQuote", parent=body, leftIndent=10, borderColor=colors.HexColor("#6b9ec7"), borderWidth=2, borderPadding=6, backColor=colors.HexColor("#f4f8fb"), fontName=font_name)
    heading1 = ParagraphStyle("ReportH1", parent=styles["Heading1"], fontName=font_name, textColor=colors.HexColor("#17324d"), fontSize=20, leading=24, spaceAfter=12)
    heading2 = ParagraphStyle("ReportH2", parent=styles["Heading2"], fontName=font_name, textColor=colors.HexColor("#17324d"), fontSize=15, leading=19, spaceBefore=12, spaceAfter=8)
    heading3 = ParagraphStyle("ReportH3", parent=styles["Heading3"], fontName=font_name, textColor=colors.HexColor("#254e70"), fontSize=12, leading=15, spaceBefore=10, spaceAfter=6)
    story = []
    for line in markdown_text.splitlines():
        if not line.strip():
            story.append(Spacer(1, 3))
            continue
        if line.startswith("# "):
            style, content = heading1, line[2:]
        elif line.startswith("## "):
            style, content = heading2, line[3:]
        elif line.startswith("### "):
            style, content = heading3, line[4:]
        elif line.startswith("> "):
            style, content = quote, line[2:]
        elif line.startswith("- "):
            style, content = body, "• " + line[2:]
        else:
            style, content = body, line
        safe = html.escape(content)
        safe = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", safe)
        safe = re.sub(r"`(.+?)`", r"<font name='Courier'>\1</font>", safe)
        story.append(Paragraph(safe, style))
    SimpleDocTemplate(str(path), pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=15 * mm, bottomMargin=15 * mm, title="MoveInSync Play Store Ratings Recommendations").build(story)


def build_documents(conn, data, labeled_count):
    OUTPUTS.mkdir(exist_ok=True)
    selectable = [item for item in data["themes"] if item["theme"] in SOLUTIONS and item["n"] >= 5 and item["negative_n"] >= 5]
    recommendations = selectable[:6]
    claims = [{"claim_id": "C001", "text": "Collected employee-app review profile", "type": "number", "sql_or_script": "scripts/build_final_recommendation.py:get_data", "result": {k: data[k] for k in ("n", "mean", "start", "end", "negative_n", "negative_pct", "negative_ci")}, "review_ids": [], "generated_at": datetime.now(timezone.utc).isoformat()}]
    lines = [
        "# MoveInSync Play Store Ratings: Evidence-Linked Recommendations",
        "",
        f"Generated: {datetime.now(timezone.utc).date().isoformat()}  ",
        "Status: final project package with a documented rule-based classification fallback. See limitations before using priorities for investment decisions.",
        "",
        "## Decision-ready recommendation",
        "",
        f"The collected MoveInSync employee-app text-review dataset contains **{data['n']} reviews** from **{data['start']} to {data['end']}**. Its mean rating is **{data['mean']:.2f}/5**; **{data['negative_n']} ({data['negative_pct']:.1f}%, 95% CI {data['negative_ci'][0]:.1f}%–{data['negative_ci'][1]:.1f}%)** are 1–2-star reviews. These are collected text reviews, not the complete Play Store rating population.",
        "",
        "Prioritize the recommendations below by the modeled rating-points-lost estimate: the difference between the observed mean review rating and the mean if the focal theme's reviews instead matched all other collected reviews. It is a diagnostic counterfactual, not a forecast.",
        "",
        "## Prioritized actions",
    ]
    for index, item in enumerate(recommendations, 1):
        theme = item["theme"]
        solution, owner, effort, success = SOLUTIONS[theme]
        quotes = quotes_for(conn, theme)
        ids = [quote["review_id"] for quote in quotes]
        claim_id = f"R{index:03d}"
        claims.append({"claim_id": claim_id, "text": f"{theme}: {item['n']} reviews; modeled rating points lost {item['points_lost']:.3f}", "type": "recommendation", "sql_or_script": "scripts/build_final_recommendation.py:get_data+quotes_for", "result": item, "review_ids": ids, "generated_at": datetime.now(timezone.utc).isoformat()})
        lines.extend([
            f"### {index}. `{theme}`",
            "",
            f"**Evidence.** n={item['n']} ({item['share']:.1f}% of collected employee reviews); {item['negative_n']} 1–2-star reviews ({item['negative_share']:.1f}% of collected 1–2-star reviews); mean rating {item['mean']:.2f}; modeled rating points lost {item['points_lost']:.3f}.",
            "",
            "**Proof from verbatim reviews.**",
            *[f"> “{quote['text']}” — review ID {quote['review_id']} ({quote['rating']}★)" for quote in quotes],
            "",
            f"**Fix.** {solution}",
            "",
            f"**Owner / effort.** {owner}; {effort} (judgment: S = isolated UX/prompt change, M = instrumented product or operational workflow, L = cross-tenant policy/process change).",
            "",
            f"**Success measure.** {success}",
            "",
        ])
    lines.extend([
        "## Ownership split",
        "",
        "The labels explicitly separate product-controllable, operations/vendor, customer-policy and unclear issues. Route ops/vendor themes to vendor management and the relevant enterprise transport desk; do not treat them as app defects solely because the review is posted on the app page.",
        "",
        "## Methods and limitations",
        "",
        f"- Source: public Google Play reviews collected with `google-play-scraper`; raw payloads are retained in Postgres. The collected sample is {data['n']} employee-app reviews, not every Play Store rating or review.",
        f"- Taxonomy: approved v{TAXONOMY_VERSION}, derived from a 160-review stratified open-coding sample.",
        f"- Classification: {labeled_count} reviews were assigned using a transparent regex fallback under `{PROMPT_VERSION}` because the configured Gemini free-tier quota was exhausted. The fallback labels are not an LLM evaluation, and independent classifier accuracy/Cohen's kappa are UNKNOWN.",
        "- Selection bias: reviews with text are not representative of ratings without text. Conclusions are about the collected review sample.",
        "- All numbers and quotes in this document are rendered by `scripts/build_final_recommendation.py`; quoted review IDs identify the underlying stored reviews.",
    ])
    markdown_text = "\n".join(lines) + "\n"
    (OUTPUTS / "final_recommendations.md").write_text(markdown_text, encoding="utf-8")
    (OUTPUTS / "claims.json").write_text(json.dumps(claims, indent=2, ensure_ascii=False), encoding="utf-8")
    html_body = "<html><head><meta charset='utf-8'><style>@page{size:A4;margin:18mm}body{font-family:Arial,sans-serif;line-height:1.45;color:#17212b}h1{font-size:24px;color:#17324d}h2{font-size:19px;color:#17324d;margin-top:26px}h3{font-size:15px;color:#254e70;margin-top:22px}blockquote{border-left:4px solid #6b9ec7;padding:8px 12px;margin:10px 0;background:#f4f8fb;font-style:italic}code{background:#edf1f4;padding:2px 4px}strong{color:#17324d}</style></head><body>" + markdown_lib.markdown(markdown_text, extensions=["extra"]) + "</body></html>"
    (OUTPUTS / "final_recommendations.html").write_text(html_body, encoding="utf-8")
    write_pdf(markdown_text, OUTPUTS / "report.pdf")
    return recommendations


def main():
    load_dotenv()
    conn = get_connection()
    try:
        labeled_count = label_all(conn)
        data = get_data(conn)
        recommendations = build_documents(conn, data, labeled_count)
        print(f"Wrote recommendation document, claims ledger, and HTML. Recommendations: {len(recommendations)}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
