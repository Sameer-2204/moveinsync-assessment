"""Populate the label sample with assistant-generated provisional labels.

These are explicitly not human validation labels.  The output remains useful for
review and triage, but evaluation metrics must not use it as ground truth.
"""
import csv
import os
import sys
import re


INPUT_PATH = "outputs/label_sample.csv"


def load_rows(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


RULES = (
    ("app_crash_install", "app", r"\b(crash|crashes|blank screen|install|installed from play|reinstall|open the app|not open)\b"),
    ("login_otp", "app", r"\b(otp|log ?in|sign ?in|verify|verification|register|registration)\b"),
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


def classify(rows):
    """Apply transparent rules; unclear text stays unclear rather than guessed."""
    results = {}
    for row in rows:
        text = row["text"]
        lowered = text.lower()
        theme, attribution, evidence = "other_unclear", "unclear", ""
        for candidate_theme, candidate_attribution, pattern in RULES:
            match = re.search(pattern, lowered, flags=re.IGNORECASE)
            if match:
                theme, attribution = candidate_theme, candidate_attribution
                evidence = text[match.start():match.end()]
                break
        if theme == "other_unclear" and int(row["rating"]) >= 4 and len(text.strip()) >= 3:
            theme, attribution, evidence = "positive_general", "unclear", text.strip()
        if theme == "routing_stops" and re.search(r"\b(company|organisation|organization|office|shift|policy)\b", lowered):
            attribution = "customer_policy"
        results[row["review_id"]] = {
            "primary_theme": theme,
            "attribution": attribution,
            "evidence_span": evidence,
        }
    return results


def write_rows(path, rows, labels):
    fieldnames = list(rows[0].keys())
    for row in rows:
        label = labels[row["review_id"]]
        row["human_primary_theme"] = label["primary_theme"]
        row["human_attribution"] = label["attribution"]
        row["human_notes"] = (
            "ASSISTANT-GENERATED PROVISIONAL LABEL (rule-based; not human ground truth); "
            f"evidence: {label['evidence_span'] or 'none'}"
        )

    temp_path = path + ".tmp"
    with open(temp_path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temp_path, path)


def main():
    rows = load_rows(INPUT_PATH)
    if not rows:
        raise RuntimeError(f"No rows found in {INPUT_PATH}")
    labels = classify(rows)
    write_rows(INPUT_PATH, rows, labels)
    print(f"Wrote {len(rows)} provisional labels to {INPUT_PATH}")


if __name__ == "__main__":
    main()
