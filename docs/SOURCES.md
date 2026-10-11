# SOURCES

Every URL cited in this project must have been fetched during the session and is recorded here with retrieval date.

| ID | Source | URL | What Was Retrieved | Date Fetched |
|----|--------|-----|--------------------|-------------|
| S01 | Google Play Store | https://play.google.com/store/apps/details?id=com.moveinsync.ets | Employee app page — confirmed package ID `com.moveinsync.ets` exists and loads | 2026-10-10 |
| S02 | Google Play Store | https://play.google.com/store/apps/details?id=com.moveinsync.driver.dco | Driver Onboarding app page — confirmed package ID exists | 2026-10-10 |
| S03 | Google Play Store | https://play.google.com/store/apps/details?id=com.moveinsync.driverapp | 404 — this package ID does not exist | 2026-10-10 |
| S04 | SerpApi docs | https://serpapi.com/google-play-product-api | API documentation: Google Play Product API endpoint, parameters, response fields | 2026-10-10 |
| S05 | Google AI for Developers | https://ai.google.dev/gemini-api/docs/rate-limits | Gemini API rate limits page — confirms limits are per-project, check at aistudio.google.com/rate-limit | 2026-10-10 |
| S06 | Web search (Softonic) | (search result, no direct URL fetch) | `com.moveinsync.driver.lite` identified as the Partner Lite app package ID | 2026-10-10 |
| S07 | Web search (Uptodown, Softonic) | (search result) | `com.routematic.employee` identified as Routematic employee app package | 2026-10-10 |
| S08 | Web search | (search result) | `com.mtap.safetrax` identified as Safetrax Commuter app package | 2026-10-10 |
| S09 | SerpApi pricing | (search result) | Free tier: 250 searches/month, recurring, no CC. Pagination counts as separate searches. | 2026-10-10 |
| S10 | google-play-scraper (PyPI) | (search result referencing pypi.org) | Open-source Python library; reviews with rating, text, date, app_version, thumbs_up, reply fields | 2026-10-10 |
| S11 | Google AI for Developers — Gemini API rate limits | https://ai.google.dev/gemini-api/docs/rate-limits | Rate limits vary by model and project; are measured by RPM, TPM and RPD; RPD resets at midnight Pacific time. The runtime API response for this project reported a 20-RPD `gemini-2.5-flash` limit. | 2026-10-11 |

**Note on S06-S08:** Package IDs for Partner Lite, Routematic, and Safetrax were found via web search results referencing APKPure, Softonic, and Uptodown — third-party APK sites that list Play Store package IDs. These need verification by fetching the actual Play Store page, which will be done at the start of P2 ingest.
