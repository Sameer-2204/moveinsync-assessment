"""
Data profiling script for GATE 2.
Reports: review counts per app, date range, field completeness, rating distribution.
All numbers computed from the database, not from memory.
"""
import json
import os
import sys

import psycopg2
from dotenv import load_dotenv

load_dotenv()


def get_connection():
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL not set")
    return psycopg2.connect(database_url)


def profile_data():
    conn = get_connection()
    cur = conn.cursor()

    print("=" * 70)
    print("DATA PROFILE — GATE 2")
    print("=" * 70)

    # 1. Raw review counts
    print("\n--- RAW REVIEWS ---")
    cur.execute("""
        SELECT a.package_id, a.name, a.role, COUNT(rr.id) as count
        FROM apps a
        LEFT JOIN raw_reviews rr ON a.app_id = rr.app_id
        GROUP BY a.app_id, a.package_id, a.name, a.role
        ORDER BY a.app_id
    """)
    for row in cur.fetchall():
        print(f"  {row[1]:45s} ({row[2]:10s}): {row[3]:5d} raw reviews")

    # 2. Normalized review counts
    print("\n--- NORMALIZED REVIEWS ---")
    cur.execute("""
        SELECT a.package_id, a.name, a.role, COUNT(r.review_id) as count
        FROM apps a
        LEFT JOIN reviews r ON a.app_id = r.app_id
        GROUP BY a.app_id, a.package_id, a.name, a.role
        ORDER BY a.app_id
    """)
    for row in cur.fetchall():
        print(f"  {row[1]:45s} ({row[2]:10s}): {row[3]:5d} normalized reviews")

    # 3. Date range per app
    print("\n--- DATE RANGE ---")
    cur.execute("""
        SELECT a.name,
               MIN(r.review_date) as earliest,
               MAX(r.review_date) as latest,
               COUNT(r.review_id) as count
        FROM apps a
        JOIN reviews r ON a.app_id = r.app_id
        GROUP BY a.name
        ORDER BY a.name
    """)
    for row in cur.fetchall():
        earliest = row[1].strftime("%Y-%m-%d") if row[1] else "N/A"
        latest = row[2].strftime("%Y-%m-%d") if row[2] else "N/A"
        print(f"  {row[0]:45s}: {earliest} to {latest} ({row[3]} reviews)")

    # 4. Rating distribution per app
    print("\n--- RATING DISTRIBUTION ---")
    cur.execute("""
        SELECT a.name, r.rating, COUNT(*) as count
        FROM apps a
        JOIN reviews r ON a.app_id = r.app_id
        GROUP BY a.name, r.rating
        ORDER BY a.name, r.rating
    """)
    current_app = None
    for row in cur.fetchall():
        if row[0] != current_app:
            current_app = row[0]
            print(f"\n  {current_app}:")
        stars = "*" * row[1] + "." * (5 - row[1])
        print(f"    {stars} ({row[1]}): {row[2]:5d}")

    # 5. Mean rating per app
    print("\n--- MEAN RATING ---")
    cur.execute("""
        SELECT a.name, a.role,
               ROUND(AVG(r.rating)::numeric, 2) as mean_rating,
               COUNT(r.review_id) as n
        FROM apps a
        JOIN reviews r ON a.app_id = r.app_id
        GROUP BY a.name, a.role
        ORDER BY a.role, mean_rating
    """)
    for row in cur.fetchall():
        print(f"  {row[0]:45s} ({row[1]:10s}): {row[2]:5.2f} (n={row[3]})")

    # 6. Field completeness
    print("\n--- FIELD COMPLETENESS ---")
    cur.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(text) as has_text,
            COUNT(NULLIF(text, '')) as has_nonempty_text,
            COUNT(app_version) as has_version,
            COUNT(dev_reply) as has_reply,
            COUNT(dev_reply_date) as has_reply_date,
            COUNT(lang) as has_lang,
            COUNT(review_date) as has_date,
            COUNT(CASE WHEN thumbs_up > 0 THEN 1 END) as has_thumbs
        FROM reviews
    """)
    row = cur.fetchone()
    total = row[0]
    if total > 0:
        print(f"  Total reviews:     {total}")
        print(f"  Has text:          {row[1]:5d} ({100*row[1]/total:.1f}%)")
        print(f"  Has non-empty text:{row[2]:5d} ({100*row[2]/total:.1f}%)")
        print(f"  Has app_version:   {row[3]:5d} ({100*row[3]/total:.1f}%)")
        print(f"  Has dev_reply:     {row[4]:5d} ({100*row[4]/total:.1f}%)")
        print(f"  Has reply_date:    {row[5]:5d} ({100*row[5]/total:.1f}%)")
        print(f"  Has lang detected: {row[6]:5d} ({100*row[6]/total:.1f}%)")
        print(f"  Has review_date:   {row[7]:5d} ({100*row[7]/total:.1f}%)")
        print(f"  Has thumbs_up > 0: {row[8]:5d} ({100*row[8]/total:.1f}%)")

    # 7. Language distribution
    print("\n--- LANGUAGE DISTRIBUTION ---")
    cur.execute("""
        SELECT lang, COUNT(*) as count
        FROM reviews
        GROUP BY lang
        ORDER BY count DESC
        LIMIT 15
    """)
    for row in cur.fetchall():
        print(f"  {row[0]:10s}: {row[1]:5d}")

    # 8. Reviews with text (useful for classification)
    print("\n--- CLASSIFIABLE REVIEWS (with text) ---")
    cur.execute("""
        SELECT a.name, a.role, COUNT(*) as count
        FROM reviews r
        JOIN apps a ON r.app_id = a.app_id
        WHERE r.text IS NOT NULL AND r.text != ''
        GROUP BY a.name, a.role
        ORDER BY a.role, a.name
    """)
    for row in cur.fetchall():
        print(f"  {row[0]:45s} ({row[1]:10s}): {row[2]:5d}")

    # 9. Top app versions (for MoveInSync employee app)
    print("\n--- TOP APP VERSIONS (MoveInSync Employee) ---")
    cur.execute("""
        SELECT r.app_version, COUNT(*) as count,
               ROUND(AVG(r.rating)::numeric, 2) as avg_rating
        FROM reviews r
        JOIN apps a ON r.app_id = a.app_id
        WHERE a.package_id = 'com.moveinsync.ets'
          AND r.app_version IS NOT NULL
        GROUP BY r.app_version
        ORDER BY count DESC
        LIMIT 10
    """)
    for row in cur.fetchall():
        print(f"  v{row[0]:15s}: {row[1]:4d} reviews, avg rating {row[2]}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    profile_data()
