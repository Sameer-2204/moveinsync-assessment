"""
Ingest reviews from Google Play using google-play-scraper.

Idempotent: uses UPSERT on (source, source_review_id, app_id) to avoid duplicates.
Resumable: tracks each run in the runs table.
Raw JSON stored untouched in raw_reviews.
"""
import json
import time
import traceback
from datetime import datetime, timezone

import psycopg2
from google_play_scraper import Sort, reviews as gps_reviews, app as gps_app

from src.db.schema import get_connection


def fetch_reviews_for_app(package_id, count=200, lang="en", country="in", sort=Sort.NEWEST):
    """
    Fetch reviews using google-play-scraper.
    Returns (reviews_list, continuation_token).
    Each review is a dict with keys: reviewId, userName, content, score,
    thumbsUpCount, reviewCreatedVersion, at, replyContent, repliedAt, appVersion, etc.
    """
    all_reviews = []
    token = None
    batch_size = min(count, 200)  # google-play-scraper max per batch
    fetched = 0

    while fetched < count:
        try:
            result, token = gps_reviews(
                package_id,
                lang=lang,
                country=country,
                sort=sort,
                count=batch_size,
                continuation_token=token,
            )
            if not result:
                break
            all_reviews.extend(result)
            fetched += len(result)
            print(f"  Fetched {fetched} reviews for {package_id}...")
            time.sleep(1)  # rate limiting
            if token is None:
                break
        except Exception as e:
            print(f"  Error fetching reviews for {package_id}: {e}")
            break

    return all_reviews


def fetch_app_info(package_id, lang="en", country="in"):
    """Fetch app metadata (name, rating, installs, etc.)."""
    try:
        info = gps_app(package_id, lang=lang, country=country)
        return info
    except Exception as e:
        print(f"  Error fetching app info for {package_id}: {e}")
        return None


def store_raw_reviews(conn, app_id, reviews_list, source="google_play_scraper"):
    """
    Store raw reviews in raw_reviews table. Idempotent via UPSERT.
    Returns count of new reviews inserted.
    """
    inserted = 0
    with conn.cursor() as cur:
        for review in reviews_list:
            review_id = review.get("reviewId", "")
            if not review_id:
                continue

            # Serialize the review to JSON, handling datetime objects
            payload = json.loads(json.dumps(review, default=str))

            try:
                cur.execute(
                    """INSERT INTO raw_reviews (source, source_review_id, app_id, payload_json)
                       VALUES (%s, %s, %s, %s)
                       ON CONFLICT (source, source_review_id, app_id) DO NOTHING
                       RETURNING id""",
                    (source, review_id, app_id, json.dumps(payload)),
                )
                if cur.fetchone():
                    inserted += 1
            except Exception as e:
                conn.rollback()
                print(f"  Error storing review {review_id}: {e}")
                continue

    conn.commit()
    return inserted


def ingest_all(conn, count_per_app=200, languages=None):
    """
    Main ingest function. Fetches reviews for all apps in the DB.
    Returns a summary dict.
    """
    if languages is None:
        languages = ["en", "hi"]

    # Log the run
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO runs (phase) VALUES ('ingest') RETURNING run_id"
        )
        run_id = cur.fetchone()[0]
    conn.commit()

    summary = {"run_id": run_id, "apps": {}, "total_fetched": 0, "total_new": 0, "errors": []}

    # Get all apps
    with conn.cursor() as cur:
        cur.execute("SELECT app_id, package_id, name FROM apps ORDER BY app_id")
        apps = cur.fetchall()

    for app_id, package_id, name in apps:
        print(f"\n--- Ingesting: {name} ({package_id}) ---")
        app_summary = {"fetched": 0, "new": 0, "languages": {}}

        # Also fetch app info
        app_info = fetch_app_info(package_id)
        if app_info:
            print(f"  Rating: {app_info.get('score', 'N/A')}, "
                  f"Reviews: {app_info.get('reviews', 'N/A')}, "
                  f"Installs: {app_info.get('installs', 'N/A')}")
            app_summary["app_info"] = {
                "score": app_info.get("score"),
                "reviews_count": app_info.get("reviews"),
                "installs": app_info.get("installs"),
                "ratings": app_info.get("ratings"),  # histogram if available
            }

        for lang in languages:
            print(f"  Language: {lang}")
            reviews = fetch_reviews_for_app(
                package_id, count=count_per_app, lang=lang, country="in"
            )
            new_count = store_raw_reviews(conn, app_id, reviews)
            app_summary["fetched"] += len(reviews)
            app_summary["new"] += new_count
            app_summary["languages"][lang] = {"fetched": len(reviews), "new": new_count}

        summary["apps"][package_id] = app_summary
        summary["total_fetched"] += app_summary["fetched"]
        summary["total_new"] += app_summary["new"]
        print(f"  Total: {app_summary['fetched']} fetched, {app_summary['new']} new")

    # Update run record
    with conn.cursor() as cur:
        cur.execute(
            """UPDATE runs SET ended_at = NOW(), counts = %s, errors = %s
               WHERE run_id = %s""",
            (json.dumps(summary), json.dumps(summary["errors"]), run_id),
        )
    conn.commit()

    return summary


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    conn = get_connection()
    try:
        summary = ingest_all(conn, count_per_app=200)
        print("\n=== INGEST SUMMARY ===")
        print(json.dumps(summary, indent=2, default=str))
    finally:
        conn.close()
