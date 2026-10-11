"""
Generate a stratified labeling sample for human validation (§6.3).
Stratified by: rating (1-5), app (employee/driver/competitor), language.
Outputs a CSV for the human to label.
"""
import csv
import os
import random
import sys

import psycopg2
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.db.schema import get_connection


def make_label_sample(target_size=150, output_path="outputs/label_sample.csv"):
    """
    Generate a stratified sample of reviews for human labeling.
    Stratification: by rating bucket (1-2, 3, 4-5) × app role × language group.
    """
    conn = get_connection()
    cur = conn.cursor()

    # Get all reviews with text
    cur.execute("""
        SELECT r.review_id, a.package_id, a.name, a.role, r.rating, r.text, r.lang,
               r.review_date, r.app_version, r.source_review_id
        FROM reviews r
        JOIN apps a ON r.app_id = a.app_id
        WHERE r.text IS NOT NULL AND r.text != ''
        ORDER BY r.review_id
    """)

    reviews = cur.fetchall()
    cur.close()
    conn.close()

    # Stratify
    buckets = {}
    for row in reviews:
        review_id, pkg, name, role, rating, text, lang = row[:7]
        review_date, app_version, src_id = row[7:]

        # Rating bucket
        if rating <= 2:
            rating_bucket = "1-2"
        elif rating == 3:
            rating_bucket = "3"
        else:
            rating_bucket = "4-5"

        # Language bucket
        if lang in ("en",):
            lang_bucket = "en"
        elif lang in ("hi",):
            lang_bucket = "hi"
        else:
            lang_bucket = "other"

        key = (role, rating_bucket, lang_bucket)
        if key not in buckets:
            buckets[key] = []
        buckets[key].append({
            "review_id": review_id,
            "package_id": pkg,
            "app_name": name,
            "role": role,
            "rating": rating,
            "text": text,
            "lang": lang,
            "review_date": str(review_date) if review_date else "",
            "app_version": app_version or "",
            "source_review_id": src_id,
        })

    # Allocate samples proportionally, with minimums
    total_available = sum(len(v) for v in buckets.values())
    sample = []

    print(f"Total reviews with text: {total_available}")
    print(f"Stratification buckets: {len(buckets)}")
    print(f"Target sample size: {target_size}")
    print()

    for key, bucket_reviews in sorted(buckets.items()):
        # Proportional allocation with minimum of 1 if bucket exists
        proportion = len(bucket_reviews) / total_available
        n = max(1, round(proportion * target_size))
        n = min(n, len(bucket_reviews))

        selected = random.sample(bucket_reviews, n)
        sample.extend(selected)

        print(f"  {str(key):40s}: {len(bucket_reviews):4d} available, {n:3d} sampled")

    # Shuffle
    random.shuffle(sample)

    # Write CSV
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fieldnames = [
        "review_id", "package_id", "app_name", "role", "rating", "text", "lang",
        "review_date", "app_version", "source_review_id",
        # Columns for human to fill:
        "human_primary_theme", "human_attribution", "human_notes",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in sample:
            row["human_primary_theme"] = ""
            row["human_attribution"] = ""
            row["human_notes"] = ""
            writer.writerow(row)

    print(f"\nSample written to {output_path} ({len(sample)} reviews)")
    print("Human should fill: human_primary_theme, human_attribution, human_notes")
    return output_path


if __name__ == "__main__":
    target = int(sys.argv[1]) if len(sys.argv) > 1 else 150
    make_label_sample(target_size=target)
