"""
P2 full pipeline: fix Safetrax, bigger ingest, normalize, profile.
"""
import json
import os
import sys
import time

import psycopg2
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.schema import get_connection
from src.ingest.fetch_reviews import fetch_reviews_for_app, store_raw_reviews, fetch_app_info
from src.normalize.process import normalize_all


def main():
    conn = get_connection()
    cur = conn.cursor()

    # 1. Fix Safetrax package ID
    print("=" * 60)
    print("STEP 1: Fix Safetrax package ID")
    print("=" * 60)
    cur.execute(
        "UPDATE apps SET package_id = %s WHERE package_id = %s",
        ("in.mtap.iincube.safetrax.commuter", "com.mtap.safetrax"),
    )
    conn.commit()
    print("  Updated Safetrax package ID to in.mtap.iincube.safetrax.commuter")

    # 2. Fetch Safetrax reviews
    print("\n" + "=" * 60)
    print("STEP 2: Fetch Safetrax reviews")
    print("=" * 60)
    cur.execute("SELECT app_id FROM apps WHERE package_id = 'in.mtap.iincube.safetrax.commuter'")
    safetrax_id = cur.fetchone()[0]

    info = fetch_app_info("in.mtap.iincube.safetrax.commuter")
    if info:
        print(f"  Safetrax - Rating: {info.get('score')}, Reviews: {info.get('reviews')}, Installs: {info.get('installs')}")

    for lang in ["en", "hi"]:
        reviews = fetch_reviews_for_app("in.mtap.iincube.safetrax.commuter", count=500, lang=lang)
        new = store_raw_reviews(conn, safetrax_id, reviews)
        print(f"  Lang={lang}: fetched {len(reviews)}, {new} new")

    # 3. Bigger pull for MoveInSync employee app (the main target)
    print("\n" + "=" * 60)
    print("STEP 3: Bigger pull for MoveInSync Employee (target: 1000+)")
    print("=" * 60)
    cur.execute("SELECT app_id FROM apps WHERE package_id = 'com.moveinsync.ets'")
    ets_id = cur.fetchone()[0]

    for lang in ["en", "hi"]:
        reviews = fetch_reviews_for_app("com.moveinsync.ets", count=1000, lang=lang)
        new = store_raw_reviews(conn, ets_id, reviews)
        print(f"  Lang={lang}: fetched {len(reviews)}, {new} new")

    # 4. Bigger pull for Routematic too (for a fair comparison)
    print("\n" + "=" * 60)
    print("STEP 4: Bigger pull for Routematic")
    print("=" * 60)
    cur.execute("SELECT app_id FROM apps WHERE package_id = 'com.routematic.employee'")
    rout_id = cur.fetchone()[0]

    for lang in ["en", "hi"]:
        reviews = fetch_reviews_for_app("com.routematic.employee", count=500, lang=lang)
        new = store_raw_reviews(conn, rout_id, reviews)
        print(f"  Lang={lang}: fetched {len(reviews)}, {new} new")

    cur.close()

    # 5. Normalize everything
    print("\n" + "=" * 60)
    print("STEP 5: Normalize all raw reviews")
    print("=" * 60)
    normalize_all(conn)

    conn.close()

    # 6. Profile
    print("\n" + "=" * 60)
    print("STEP 6: Data Profile")
    print("=" * 60)
    # Import and run profiler
    from scripts.profile_data import profile_data
    profile_data()


if __name__ == "__main__":
    main()
