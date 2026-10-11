# MoveInSync Play Store Ratings Analysis

An evidence-linked, reproducible analysis of collected public Play Store reviews for MoveInSync employee and driver apps.

**Status:** Final report package generated. Full Gemini classification is quota-limited; the published report uses a documented rule-based fallback and must be read with its stated limitations.

## Deliverables

- `outputs/report.pdf` — recommendation PDF
- `outputs/final_recommendations.md` and `.html` — editable/shareable report formats
- `outputs/claims.json` — report claims, computed results, and supporting review IDs
- `docs/METHODS.md` — methods, limitations, and reproduction steps

## Reproduce the report

Copy `.env.example` to `.env`, set `DATABASE_URL`, install dependencies, then run:

```powershell
pip install -r requirements.txt
python scripts/build_final_recommendation.py
```

This generates the report and claims ledger from the collected Postgres dataset. The source code preserves Gemini labels separately from the deterministic `rule-v1` fallback labels used by the final report.

## Environment variables

| Variable | Description |
|---|---|
| `DATABASE_URL` | Postgres connection string |
| `GEMINI_API_KEY` | Gemini API key, required only for Gemini classification |

## Limitations

The report analyzes 1,003 collected MoveInSync employee-app text reviews, not every Play Store rating or review. Gemini quota exhaustion prevented complete LLM classification and independent human validation; the report instead uses a transparent `rule-v1` taxonomy fallback. Review `docs/METHODS.md` before using priorities for investment decisions.
