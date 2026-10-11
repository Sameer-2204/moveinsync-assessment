"""
Analysis module: compute all metrics from labeled reviews.
Produces the data for the report and dashboard.

Metrics computed (per master prompt §6.4):
- Theme frequency (absolute + %)
- Theme × rating cross-tab
- Theme trend over time (quarterly)
- Attribution split
- Version regression analysis
- Competitor benchmarking
- Reply rate analysis
- Severity distribution
"""
import json
import os
import sys
from datetime import datetime

import psycopg2
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.db.schema import get_connection


def run_analysis(conn):
    """Run all analysis queries and return results dict."""
    results = {}

    # 1. Theme frequency by app
    print("1. Theme frequency by app...")
    df = pd.read_sql("""
        SELECT a.name as app, a.role, l.primary_theme, COUNT(*) as count
        FROM labels l
        JOIN reviews r ON l.review_id = r.review_id
        JOIN apps a ON r.app_id = a.app_id
        WHERE l.status IN ('auto', 'human')
        GROUP BY a.name, a.role, l.primary_theme
        ORDER BY a.name, count DESC
    """, conn)
    results["theme_frequency"] = df.to_dict(orient="records")

    # 2. Theme frequency for MIS employee app only (negative reviews)
    print("2. MIS Employee negative theme breakdown...")
    df = pd.read_sql("""
        SELECT l.primary_theme, COUNT(*) as count,
               ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 1) as pct
        FROM labels l
        JOIN reviews r ON l.review_id = r.review_id
        JOIN apps a ON r.app_id = a.app_id
        WHERE a.package_id = 'com.moveinsync.ets'
          AND r.rating <= 2
          AND l.status IN ('auto', 'human')
        GROUP BY l.primary_theme
        ORDER BY count DESC
    """, conn)
    results["mis_negative_themes"] = df.to_dict(orient="records")

    # 3. Theme × rating cross-tab (MIS employee)
    print("3. Theme × rating cross-tab...")
    df = pd.read_sql("""
        SELECT l.primary_theme, r.rating, COUNT(*) as count
        FROM labels l
        JOIN reviews r ON l.review_id = r.review_id
        JOIN apps a ON r.app_id = a.app_id
        WHERE a.package_id = 'com.moveinsync.ets'
          AND l.status IN ('auto', 'human')
        GROUP BY l.primary_theme, r.rating
        ORDER BY l.primary_theme, r.rating
    """, conn)
    results["theme_rating_crosstab"] = df.to_dict(orient="records")

    # 4. Theme trend over time (quarterly)
    print("4. Theme trends over time...")
    df = pd.read_sql("""
        SELECT
            DATE_TRUNC('quarter', r.review_date) as quarter,
            l.primary_theme,
            COUNT(*) as count
        FROM labels l
        JOIN reviews r ON l.review_id = r.review_id
        JOIN apps a ON r.app_id = a.app_id
        WHERE a.package_id = 'com.moveinsync.ets'
          AND r.review_date IS NOT NULL
          AND l.status IN ('auto', 'human')
        GROUP BY quarter, l.primary_theme
        ORDER BY quarter, count DESC
    """, conn)
    results["theme_trends"] = df.to_dict(orient="records")

    # 5. Attribution split
    print("5. Attribution split...")
    df = pd.read_sql("""
        SELECT l.attribution, COUNT(*) as count,
               ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 1) as pct
        FROM labels l
        JOIN reviews r ON l.review_id = r.review_id
        JOIN apps a ON r.app_id = a.app_id
        WHERE a.package_id = 'com.moveinsync.ets'
          AND r.rating <= 3
          AND l.status IN ('auto', 'human')
        GROUP BY l.attribution
        ORDER BY count DESC
    """, conn)
    results["attribution_split"] = df.to_dict(orient="records")

    # 6. Version regression analysis
    print("6. Version regression analysis...")
    df = pd.read_sql("""
        SELECT r.app_version, l.primary_theme,
               COUNT(*) as count,
               ROUND(AVG(r.rating)::numeric, 2) as avg_rating
        FROM labels l
        JOIN reviews r ON l.review_id = r.review_id
        JOIN apps a ON r.app_id = a.app_id
        WHERE a.package_id = 'com.moveinsync.ets'
          AND r.app_version IS NOT NULL
          AND l.status IN ('auto', 'human')
        GROUP BY r.app_version, l.primary_theme
        HAVING COUNT(*) >= 3
        ORDER BY r.app_version, count DESC
    """, conn)
    results["version_themes"] = df.to_dict(orient="records")

    # 7. Competitor comparison
    print("7. Competitor comparison...")
    df = pd.read_sql("""
        SELECT a.name, a.role, l.primary_theme, COUNT(*) as count,
               ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(PARTITION BY a.name), 1) as pct
        FROM labels l
        JOIN reviews r ON l.review_id = r.review_id
        JOIN apps a ON r.app_id = a.app_id
        WHERE l.status IN ('auto', 'human')
          AND r.rating <= 2
        GROUP BY a.name, a.role, l.primary_theme
        ORDER BY a.name, count DESC
    """, conn)
    results["competitor_negative_themes"] = df.to_dict(orient="records")

    # 8. Reply rate analysis
    print("8. Reply rate analysis...")
    df = pd.read_sql("""
        SELECT a.name,
               COUNT(*) as total,
               COUNT(r.dev_reply) as replied,
               ROUND(100.0 * COUNT(r.dev_reply) / COUNT(*), 1) as reply_rate_pct,
               ROUND(AVG(r.rating) FILTER (WHERE r.dev_reply IS NOT NULL)::numeric, 2) as avg_rating_replied,
               ROUND(AVG(r.rating) FILTER (WHERE r.dev_reply IS NULL)::numeric, 2) as avg_rating_unreplied
        FROM reviews r
        JOIN apps a ON r.app_id = a.app_id
        GROUP BY a.name
        ORDER BY reply_rate_pct DESC
    """, conn)
    results["reply_rate"] = df.to_dict(orient="records")

    # 9. Severity distribution (MIS negative)
    print("9. Severity distribution...")
    df = pd.read_sql("""
        SELECT l.severity, l.primary_theme, COUNT(*) as count
        FROM labels l
        JOIN reviews r ON l.review_id = r.review_id
        JOIN apps a ON r.app_id = a.app_id
        WHERE a.package_id = 'com.moveinsync.ets'
          AND r.rating <= 3
          AND l.status IN ('auto', 'human')
        GROUP BY l.severity, l.primary_theme
        ORDER BY l.severity DESC, count DESC
    """, conn)
    results["severity_themes"] = df.to_dict(orient="records")

    # 10. Top verbatim quotes per theme (for report)
    print("10. Top quotes per theme...")
    df = pd.read_sql("""
        SELECT DISTINCT ON (l.primary_theme)
            l.primary_theme, r.text, r.rating, l.evidence_span, r.review_id
        FROM labels l
        JOIN reviews r ON l.review_id = r.review_id
        JOIN apps a ON r.app_id = a.app_id
        WHERE a.package_id = 'com.moveinsync.ets'
          AND r.rating <= 2
          AND LENGTH(r.text) > 50
          AND l.status IN ('auto', 'human')
        ORDER BY l.primary_theme, r.thumbs_up DESC, LENGTH(r.text) DESC
    """, conn)
    results["top_quotes"] = df.to_dict(orient="records")

    # 11. Overall stats
    print("11. Overall stats...")
    cur = conn.cursor()
    cur.execute("""
        SELECT
            COUNT(DISTINCT r.review_id) as total_labeled,
            COUNT(DISTINCT CASE WHEN r.rating <= 2 THEN r.review_id END) as negative_labeled,
            COUNT(DISTINCT l.primary_theme) as unique_themes
        FROM labels l
        JOIN reviews r ON l.review_id = r.review_id
        JOIN apps a ON r.app_id = a.app_id
        WHERE a.package_id = 'com.moveinsync.ets'
          AND l.status IN ('auto', 'human')
    """)
    row = cur.fetchone()
    results["overall_stats"] = {
        "total_labeled": row[0],
        "negative_labeled": row[1],
        "unique_themes": row[2],
    }
    cur.close()

    return results


def save_analysis(results, output_path="outputs/analysis_results.json"):
    """Save analysis results to JSON."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Convert any non-serializable types
    def default_handler(obj):
        if isinstance(obj, (pd.Timestamp, datetime)):
            return obj.isoformat()
        if hasattr(obj, 'item'):
            return obj.item()
        return str(obj)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=default_handler, ensure_ascii=False)

    print(f"\nAnalysis saved to {output_path}")


def print_summary(results):
    """Print a human-readable summary."""
    print("\n" + "=" * 60)
    print("ANALYSIS SUMMARY")
    print("=" * 60)

    stats = results.get("overall_stats", {})
    print(f"\nTotal MIS Employee reviews labeled: {stats.get('total_labeled', 0)}")
    print(f"Negative reviews (1-2 star) labeled: {stats.get('negative_labeled', 0)}")

    print("\n--- MIS EMPLOYEE: NEGATIVE THEME BREAKDOWN ---")
    for item in results.get("mis_negative_themes", []):
        print(f"  {item['primary_theme']:30s}: {item['count']:4d} ({item['pct']}%)")

    print("\n--- ATTRIBUTION SPLIT (negative reviews) ---")
    for item in results.get("attribution_split", []):
        print(f"  {item['attribution']:20s}: {item['count']:4d} ({item['pct']}%)")

    print("\n--- REPLY RATE ---")
    for item in results.get("reply_rate", []):
        print(f"  {item['name']:45s}: {item['reply_rate_pct']}% replied "
              f"(avg rating replied={item.get('avg_rating_replied', 'N/A')}, "
              f"unreplied={item.get('avg_rating_unreplied', 'N/A')})")

    print("\n--- TOP QUOTES ---")
    for item in results.get("top_quotes", []):
        print(f"\n  [{item['primary_theme']}] (rating {item['rating']}):")
        text = item['text'][:200] + "..." if len(item['text']) > 200 else item['text']
        print(f"    \"{text}\"")


if __name__ == "__main__":
    conn = get_connection()
    try:
        results = run_analysis(conn)
        save_analysis(results)
        print_summary(results)
    finally:
        conn.close()
