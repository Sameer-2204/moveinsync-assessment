"""
Normalize raw reviews into the reviews table.

- Extracts fields from raw JSON
- Detects language
- Computes review_hash for caching
- Deduplicates via UPSERT on (app_id, source_review_id)
"""
import hashlib
import json
import re
from datetime import datetime, timezone

import psycopg2
from langdetect import detect, LangDetectException

from src.db.schema import get_connection


def compute_review_hash(text, rating):
    """Hash for caching: if text+rating are the same, classification can be reused."""
    content = f"{text or ''}|{rating}"
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def detect_language(text):
    """Detect language of review text. Returns ISO 639-1 code or 'unknown'."""
    if not text or len(text.strip()) < 10:
        return "unknown"
    try:
        return detect(text)
    except LangDetectException:
        return "unknown"


def clean_text(text):
    """Basic text cleaning: normalize whitespace, strip, keep original language."""
    if not text:
        return None
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text if text else None


def normalize_raw_reviews(conn, batch_size=500):
    """
    Process unprocessed raw_reviews into the reviews table.
    Only processes raw_reviews that don't already have a corresponding review.
    Returns count of newly normalized reviews.
    """
    with conn.cursor() as cur:
        # Find raw reviews not yet normalized
        cur.execute("""
            SELECT rr.id, rr.source_review_id, rr.app_id, rr.payload_json
            FROM raw_reviews rr
            LEFT JOIN reviews r ON r.app_id = rr.app_id AND r.source_review_id = rr.source_review_id
            WHERE r.review_id IS NULL
            ORDER BY rr.id
            LIMIT %s
        """, (batch_size,))
        rows = cur.fetchall()

    if not rows:
        print("No new raw reviews to normalize.")
        return 0

    print(f"Normalizing {len(rows)} raw reviews...")
    normalized = 0

    with conn.cursor() as cur:
        for raw_id, source_review_id, app_id, payload in rows:
            try:
                # payload is already a dict from JSONB
                if isinstance(payload, str):
                    payload = json.loads(payload)

                text = clean_text(payload.get("content", ""))
                rating = payload.get("score")
                if rating is None:
                    continue

                review_date = payload.get("at")
                # google-play-scraper returns datetime as string
                if isinstance(review_date, str):
                    try:
                        review_date = datetime.fromisoformat(review_date.replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        review_date = None

                app_version = payload.get("reviewCreatedVersion") or payload.get("appVersion")
                thumbs_up = payload.get("thumbsUpCount", 0) or 0
                dev_reply = clean_text(payload.get("replyContent", ""))

                dev_reply_date = payload.get("repliedAt")
                if isinstance(dev_reply_date, str):
                    try:
                        dev_reply_date = datetime.fromisoformat(dev_reply_date.replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        dev_reply_date = None

                lang = detect_language(text)
                review_hash = compute_review_hash(text, rating)

                cur.execute(
                    """INSERT INTO reviews
                       (app_id, source_review_id, rating, text, lang, review_date,
                        app_version, thumbs_up, dev_reply, dev_reply_date, review_hash)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (app_id, source_review_id) DO NOTHING
                       RETURNING review_id""",
                    (app_id, source_review_id, rating, text, lang, review_date,
                     app_version, thumbs_up, dev_reply, dev_reply_date, review_hash),
                )
                if cur.fetchone():
                    normalized += 1
            except Exception as e:
                print(f"  Error normalizing review {source_review_id}: {e}")
                conn.rollback()
                continue

    conn.commit()
    print(f"Normalized {normalized} reviews.")
    return normalized


def normalize_all(conn):
    """Normalize all pending raw reviews in batches."""
    # Log the run
    with conn.cursor() as cur:
        cur.execute("INSERT INTO runs (phase) VALUES ('normalize') RETURNING run_id")
        run_id = cur.fetchone()[0]
    conn.commit()

    total = 0
    while True:
        count = normalize_raw_reviews(conn, batch_size=1000)
        total += count
        if count == 0:
            break

    # Update run
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE runs SET ended_at = NOW(), counts = %s WHERE run_id = %s",
            (json.dumps({"normalized": total}), run_id),
        )
    conn.commit()
    print(f"Total normalized: {total}")
    return total


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    conn = get_connection()
    try:
        normalize_all(conn)
    finally:
        conn.close()
