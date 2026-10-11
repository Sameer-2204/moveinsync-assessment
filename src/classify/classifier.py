"""
Gemini-based review classifier.

Uses the taxonomy from TAXONOMY.md to classify reviews into themes.
Batches multiple reviews per API call to stay within RPD limits.
Caches results by review_hash + prompt_version + taxonomy_version.
"""
import json
import hashlib
import os
import sys
import time
import re
from datetime import datetime, timezone

import psycopg2
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.db.schema import get_connection

# Configuration
TAXONOMY_VERSION = "1.0"
PROMPT_VERSION = "1.0"
MODEL_NAME = "gemini-2.5-flash"
BATCH_SIZE = 15  # reviews per API call
RPM_LIMIT = 30   # stay well under 60
RPD_LIMIT = 95   # stay under 100, leave headroom
TEMPERATURE = 0.0
REQUEST_TIMEOUT_SECONDS = 45

THEMES_LIST = [
    "app_crash_install",
    "login_otp",
    "booking_scheduling",
    "live_tracking_eta",
    "late_noshow_cab",
    "routing_stops",
    "driver_behavior_safety",
    "ui_ux_design",
    "notification_rating_prompt",
    "app_performance",
    "support_helpdesk",
    "positive_general",
    "other_unclear",
]

SYSTEM_PROMPT = """You are a review classifier for a corporate employee transportation app (MoveInSync).
You classify Play Store reviews into predefined themes.

RULES:
1. Use ONLY the review text provided. Do not use outside knowledge.
2. If the review does not clearly support a theme, return "other_unclear".
3. For each review, return ALL applicable themes, a primary theme, sentiment, severity, attribution, and an evidence_span.
4. The evidence_span MUST be a verbatim substring copied directly from the review text. Do not paraphrase.
5. Attribution must be one of: "app" (product/engineering can fix), "ops_vendor" (cab vendor/driver issue), "customer_policy" (enterprise policy issue), "unclear".
6. Severity: 1=minor annoyance, 2=significant friction, 3=blocking/safety issue.
7. Respond ONLY with valid JSON array. No markdown, no explanation.

THEMES:
- app_crash_install: App crashes, won't open, "not installed from Play Store" errors, blank screens, forced reinstalls
- login_otp: Can't log in, OTP not received, verification failures
- booking_scheduling: Can't book/schedule rides, booking failures, can't edit bookings, calendar issues
- live_tracking_eta: GPS/tracking inaccurate, location frozen, ETA unreliable, map issues
- late_noshow_cab: Cab late, driver no-show, long wait times, cab not assigned on time
- routing_stops: Bad routes, inconvenient stops, long detours, unsafe pickup/drop locations
- driver_behavior_safety: Rude/untrained drivers, safety concerns, no-show without calling
- ui_ux_design: Poor UI, confusing navigation, too many clicks, info not visible, forced permissions
- notification_rating_prompt: Excessive notifications, repeated rating prompts, forced ratings
- app_performance: App slow/laggy, high battery use, phone overheating, network errors with good connection
- support_helpdesk: Can't reach support, no escalation visibility, unresponsive helpdesk
- positive_general: Positive feedback, praise, good experience
- other_unclear: Too short, vague, unrecognizable language, doesn't fit other themes"""


def build_classification_prompt(reviews_batch):
    """Build the prompt for a batch of reviews."""
    reviews_text = []
    for i, (review_id, text, rating) in enumerate(reviews_batch):
        reviews_text.append(f'Review {i+1} (ID: {review_id}, Rating: {rating}/5):\n"""{text}"""')

    prompt = f"""{SYSTEM_PROMPT}

Classify these {len(reviews_batch)} reviews. Return a JSON array with one object per review in order.

Each object must have these exact fields:
- "review_id": integer (the ID from above)
- "themes": array of strings (from the theme list)
- "primary_theme": string (the dominant theme)
- "sentiment": "positive" | "negative" | "mixed" | "neutral"
- "severity": 1 | 2 | 3
- "attribution": "app" | "ops_vendor" | "customer_policy" | "unclear"
- "evidence_span": string (verbatim substring from the review)
- "confidence": float 0-1

Reviews to classify:

{chr(10).join(reviews_text)}

Return ONLY the JSON array:"""

    return prompt


def parse_response(response_text, expected_ids):
    """Parse the Gemini response, extracting JSON array."""
    # Try to find JSON array in the response
    text = response_text.strip()

    # Remove markdown code fences if present
    if text.startswith("```"):
        text = re.sub(r'^```(?:json)?\s*\n?', '', text)
        text = re.sub(r'\n?```\s*$', '', text)

    try:
        results = json.loads(text)
        if isinstance(results, list):
            return results
    except json.JSONDecodeError:
        pass

    # Try to extract JSON array from mixed text
    match = re.search(r'\[[\s\S]*\]', text)
    if match:
        try:
            results = json.loads(match.group())
            if isinstance(results, list):
                return results
        except json.JSONDecodeError:
            pass

    return None


def validate_label(label, review_text):
    """
    Validate a single label against the review text.
    Returns (is_valid, reason).
    """
    # Check required fields
    required = ["review_id", "themes", "primary_theme", "sentiment", "severity",
                "attribution", "evidence_span", "confidence"]
    for field in required:
        if field not in label:
            return False, f"Missing field: {field}"

    # Validate primary_theme is in our taxonomy
    if label["primary_theme"] not in THEMES_LIST:
        return False, f"Invalid theme: {label['primary_theme']}"

    # Validate themes are all in taxonomy
    for theme in label.get("themes", []):
        if theme not in THEMES_LIST:
            return False, f"Invalid theme in array: {theme}"

    # Validate attribution
    if label["attribution"] not in ("app", "ops_vendor", "customer_policy", "unclear"):
        return False, f"Invalid attribution: {label['attribution']}"

    # Validate evidence_span is a substring of the review (case-insensitive, whitespace-normalized)
    evidence = label.get("evidence_span", "")
    if evidence and review_text:
        norm_evidence = re.sub(r'\s+', ' ', evidence.lower().strip())
        norm_text = re.sub(r'\s+', ' ', review_text.lower().strip())
        if norm_evidence not in norm_text:
            return False, f"Evidence span not found in review text"

    return True, "OK"


def store_labels(conn, labels_list, reviews_map):
    """Store validated labels in the database."""
    stored = 0
    rejected = 0

    with conn.cursor() as cur:
        for label in labels_list:
            review_id = label.get("review_id")
            if review_id not in reviews_map:
                continue

            review_text = reviews_map[review_id]
            is_valid, reason = validate_label(label, review_text)

            status = "auto" if is_valid else "needs_review"

            try:
                cur.execute(
                    """INSERT INTO labels
                       (review_id, taxonomy_version, themes, primary_theme, sentiment,
                        severity, attribution, evidence_span, confidence, model,
                        prompt_version, status)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (review_id, taxonomy_version, prompt_version)
                       DO UPDATE SET
                           themes = EXCLUDED.themes,
                           primary_theme = EXCLUDED.primary_theme,
                           sentiment = EXCLUDED.sentiment,
                           severity = EXCLUDED.severity,
                           attribution = EXCLUDED.attribution,
                           evidence_span = EXCLUDED.evidence_span,
                           confidence = EXCLUDED.confidence,
                           model = EXCLUDED.model,
                           status = EXCLUDED.status,
                           labeled_at = NOW()
                       RETURNING label_id""",
                    (review_id, TAXONOMY_VERSION, label.get("themes", []),
                     label["primary_theme"], label.get("sentiment"),
                     label.get("severity"), label["attribution"],
                     label.get("evidence_span", ""), label.get("confidence", 0.5),
                     MODEL_NAME, PROMPT_VERSION, status),
                )
                if is_valid:
                    stored += 1
                else:
                    rejected += 1
                    print(f"    Warning: review {review_id} -> {status}: {reason}")
            except Exception as e:
                print(f"    Error storing label for review {review_id}: {e}")
                conn.rollback()
                continue

    conn.commit()
    return stored, rejected


def classify_reviews(conn, limit=None, app_filter=None):
    """
    Main classification function.
    Classifies unlabeled reviews in batches using Gemini.
    """
    # Configure Gemini
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")
    genai.configure(api_key=api_key)

    model = genai.GenerativeModel(MODEL_NAME)

    # Find unlabeled reviews
    query = """
        SELECT r.review_id, r.text, r.rating
        FROM reviews r
        LEFT JOIN labels l ON r.review_id = l.review_id
            AND l.taxonomy_version = %s AND l.prompt_version = %s
        WHERE l.label_id IS NULL
        AND r.text IS NOT NULL AND r.text != ''
    """
    params = [TAXONOMY_VERSION, PROMPT_VERSION]

    if app_filter:
        query += " AND r.app_id IN (SELECT app_id FROM apps WHERE package_id = %s)"
        params.append(app_filter)

    query += " ORDER BY r.review_id"
    if limit:
        query += f" LIMIT {limit}"

    with conn.cursor() as cur:
        cur.execute(query, params)
        unlabeled = cur.fetchall()

    if not unlabeled:
        print("No unlabeled reviews found.")
        return {"total": 0, "classified": 0, "errors": 0}

    print(f"Found {len(unlabeled)} unlabeled reviews")
    print(f"Batch size: {BATCH_SIZE}, estimated API calls: {len(unlabeled) // BATCH_SIZE + 1}")
    print(f"RPD limit: {RPD_LIMIT}")

    # Log the run
    with conn.cursor() as cur:
        cur.execute("INSERT INTO runs (phase) VALUES ('classify') RETURNING run_id")
        run_id = cur.fetchone()[0]
    conn.commit()

    total_stored = 0
    total_rejected = 0
    total_errors = 0
    api_calls = 0
    start_time = time.time()
    quota_exhausted = False
    quota_error = None

    # Process in batches
    for i in range(0, len(unlabeled), BATCH_SIZE):
        if api_calls >= RPD_LIMIT:
            print(f"\n  RPD limit reached ({RPD_LIMIT} calls). Stopping. Run again tomorrow.")
            break

        batch = unlabeled[i:i + BATCH_SIZE]
        reviews_map = {r[0]: r[1] for r in batch}  # review_id -> text
        batch_data = [(r[0], r[1], r[2]) for r in batch]  # (id, text, rating)

        prompt = build_classification_prompt(batch_data)

        try:
            response = model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    temperature=TEMPERATURE,
                    max_output_tokens=4096,
                ),
                request_options={"timeout": REQUEST_TIMEOUT_SECONDS},
            )
            api_calls += 1

            results = parse_response(response.text, [r[0] for r in batch])
            if results:
                stored, rejected = store_labels(conn, results, reviews_map)
                total_stored += stored
                total_rejected += rejected
                print(f"  Batch {i // BATCH_SIZE + 1}: {stored} classified, {rejected} needs_review (call #{api_calls})")
            else:
                total_errors += len(batch)
                print(f"  Batch {i // BATCH_SIZE + 1}: PARSE ERROR (call #{api_calls})")

        except Exception as e:
            total_errors += len(batch)
            print(f"  Batch {i // BATCH_SIZE + 1}: API ERROR: {e} (call #{api_calls})")

            # Do not spin or consume further requests after a daily-quota error.
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                quota_exhausted = True
                quota_error = str(e)
                print("    Quota exhausted. Stopping; run again after the provider reset.")
                break

        # Rate limiting: stay under RPM
        elapsed = time.time() - start_time
        expected_time = api_calls * (60 / RPM_LIMIT)
        if elapsed < expected_time:
            sleep_time = expected_time - elapsed
            time.sleep(sleep_time)

    # Update run
    summary = {
        "total_reviews": len(unlabeled),
        "classified": total_stored,
        "needs_review": total_rejected,
        "errors": total_errors,
        "api_calls": api_calls,
        "duration_seconds": round(time.time() - start_time),
        "quota_exhausted": quota_exhausted,
        "quota_error": quota_error,
    }
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE runs SET ended_at = NOW(), counts = %s WHERE run_id = %s",
            (json.dumps(summary), run_id),
        )
    conn.commit()

    print(f"\n=== CLASSIFICATION SUMMARY ===")
    print(f"  Classified: {total_stored}")
    print(f"  Needs review: {total_rejected}")
    print(f"  Errors: {total_errors}")
    print(f"  API calls: {api_calls}")
    print(f"  Remaining RPD: {RPD_LIMIT - api_calls}")

    return summary


if __name__ == "__main__":
    conn = get_connection()
    try:
        # Optional: pass --app=com.moveinsync.ets to filter
        app_filter = None
        limit = None
        for arg in sys.argv[1:]:
            if arg.startswith("--app="):
                app_filter = arg.split("=")[1]
            elif arg.startswith("--limit="):
                limit = int(arg.split("=")[1])

        classify_reviews(conn, limit=limit, app_filter=app_filter)
    finally:
        conn.close()
