# Methods note

## Data collection

Public Play Store reviews were collected through `google-play-scraper`, then stored as immutable raw JSON in Postgres and normalized into `reviews`. The collected dataset contains 2,326 text reviews across three MoveInSync apps and two competitor apps. The recommendation report analyzes the 1,003 collected MoveInSync employee-app reviews dated 2016-10-04 to 2026-10-09.

This is a collected public-review sample, not the full population of Play Store ratings or reviews. Ratings without text are absent, so text-review results must not be treated as the aggregate Play Store score.

## Taxonomy and classification

`docs/TAXONOMY.md` v1.0 was derived from an open-coded, stratified sample of 160 MoveInSync reviews. Gemini `gemini-2.5-flash` was configured for classification, but the project hit its active free-tier limit of 20 generation requests/day after 165 labels.

For the final package, `scripts/build_final_recommendation.py` uses an explicit, deterministic rule set under label prompt version `rule-v1`. The report clearly marks this as a fallback. It does not mix the fallback results with Gemini results: both label versions remain separately queryable.

No independently human-labeled evaluation set is available. Classifier accuracy, per-theme precision/recall, and Cohen's kappa are therefore **UNKNOWN** and are not represented as validated metrics.

## Metrics and recommendations

All counts, means, confidence intervals, theme shares, and modeled rating-points-lost values in `outputs/final_recommendations.md` and `outputs/report.pdf` are calculated by `scripts/build_final_recommendation.py` from Postgres. Every quoted review is fetched from the stored review table and shown with its review ID.

The rating-points-lost metric is the difference between the observed mean collected-review rating and the mean rating if the focal theme's reviews matched the mean of all other collected reviews. It is a counterfactual prioritization diagnostic, not a forecast of rating lift.

## Tools used

Python 3.12; Postgres/Supabase; `google-play-scraper`; `psycopg2`; `langdetect`; Google Gemini API; `reportlab`; and Git/GitHub-ready project files. Source and rate-limit references are recorded in `docs/SOURCES.md`.

## Reproduction

Set `DATABASE_URL` in `.env`, then run:

```powershell
python scripts/build_final_recommendation.py
```

This refreshes the fallback label version and generates `outputs/final_recommendations.md`, `outputs/final_recommendations.html`, `outputs/claims.json`, and `outputs/report.pdf`.
