"""
P3 Step 1: Extract stratified review sample for theme discovery.
Reads ~150 reviews from DB stratified by rating and app, outputs them for analysis.
"""
import os, sys, json
import psycopg2
from dotenv import load_dotenv
load_dotenv()
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.db.schema import get_connection

def extract_sample():
    conn = get_connection()
    cur = conn.cursor()
    
    # Focus on MoveInSync apps (employee + driver) for taxonomy discovery
    # Stratify: 60 1-star, 30 2-3 star, 30 4-5 star from employee app
    # + 20 1-star, 10 other from driver app
    queries = [
        ("MIS Employee 1-star", """
            SELECT r.review_id, r.rating, r.text, r.app_version, r.lang, r.dev_reply, a.name
            FROM reviews r JOIN apps a ON r.app_id = a.app_id
            WHERE a.package_id = 'com.moveinsync.ets' AND r.rating = 1
            AND r.text IS NOT NULL AND r.text != ''
            ORDER BY RANDOM() LIMIT 70
        """),
        ("MIS Employee 2-3 star", """
            SELECT r.review_id, r.rating, r.text, r.app_version, r.lang, r.dev_reply, a.name
            FROM reviews r JOIN apps a ON r.app_id = a.app_id
            WHERE a.package_id = 'com.moveinsync.ets' AND r.rating IN (2, 3)
            AND r.text IS NOT NULL AND r.text != ''
            ORDER BY RANDOM() LIMIT 30
        """),
        ("MIS Employee 4-5 star", """
            SELECT r.review_id, r.rating, r.text, r.app_version, r.lang, r.dev_reply, a.name
            FROM reviews r JOIN apps a ON r.app_id = a.app_id
            WHERE a.package_id = 'com.moveinsync.ets' AND r.rating IN (4, 5)
            AND r.text IS NOT NULL AND r.text != ''
            ORDER BY RANDOM() LIMIT 30
        """),
        ("MIS Driver 1-2 star", """
            SELECT r.review_id, r.rating, r.text, r.app_version, r.lang, r.dev_reply, a.name
            FROM reviews r JOIN apps a ON r.app_id = a.app_id
            WHERE a.package_id = 'com.moveinsync.driver.lite' AND r.rating <= 2
            AND r.text IS NOT NULL AND r.text != ''
            ORDER BY RANDOM() LIMIT 20
        """),
        ("MIS Driver 3-5 star", """
            SELECT r.review_id, r.rating, r.text, r.app_version, r.lang, r.dev_reply, a.name
            FROM reviews r JOIN apps a ON r.app_id = a.app_id
            WHERE a.package_id = 'com.moveinsync.driver.lite' AND r.rating >= 3
            AND r.text IS NOT NULL AND r.text != ''
            ORDER BY RANDOM() LIMIT 10
        """),
    ]
    
    all_reviews = []
    for label, query in queries:
        cur.execute(query)
        rows = cur.fetchall()
        print(f"{label}: {len(rows)} reviews")
        for row in rows:
            all_reviews.append({
                "review_id": row[0],
                "rating": row[1],
                "text": row[2],
                "app_version": row[3],
                "lang": row[4],
                "dev_reply": row[5],
                "app": row[6],
            })
    
    cur.close()
    conn.close()
    
    # Output as readable text
    output = []
    for i, r in enumerate(all_reviews):
        output.append(f"--- Review #{i+1} (ID: {r['review_id']}, Rating: {r['rating']}, App: {r['app']}, Version: {r['app_version']}, Lang: {r['lang']}) ---")
        output.append(r['text'])
        if r['dev_reply']:
            output.append(f"  [DEV REPLY]: {r['dev_reply']}")
        output.append("")
    
    os.makedirs("outputs", exist_ok=True)
    with open("outputs/theme_discovery_sample.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output))
    
    # Also save as JSON for programmatic use
    with open("outputs/theme_discovery_sample.json", "w", encoding="utf-8") as f:
        json.dump(all_reviews, f, indent=2, default=str, ensure_ascii=False)
    
    print(f"\nTotal: {len(all_reviews)} reviews extracted")
    print(f"Saved to outputs/theme_discovery_sample.txt and .json")
    return all_reviews

if __name__ == "__main__":
    extract_sample()
