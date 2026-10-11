# DECISIONS LOG

Each decision records the alternatives considered, why the chosen option was picked, and any tradeoffs.

## D01: Programming Language — Python 3.10+
- **Alternatives:** Node.js/TypeScript, Go
- **Why Python:** Best ecosystem for the deliverables — pandas/polars for analysis, google-generativeai SDK for Gemini, matplotlib/plotly for charts, weasyprint/reportlab for PDF, streamlit for dashboard. `google-play-scraper` library is Python-native.
- **Tradeoff:** Slightly slower runtime than Go/Node, irrelevant at this data scale.
- **Status:** approved (GATE 0)

## D02: Dashboard Framework — TBD
- **Candidates:** Streamlit (fast to build, free Community Cloud hosting), Dash (more control, needs separate hosting), Next.js + Vercel (most polished, more build effort)
- **Decision:** TBD — will decide at GATE 2 after confirming data shape.

## D03: Review Data Source — `google-play-scraper` Python library
- **Alternatives considered:**
  - SerpApi: Managed API, cleaner ToS, but 250 searches/mo limit is too tight for 5 apps with weekly refreshes.
  - Hybrid (SerpApi + scraper): Unnecessary complexity.
- **Why `google-play-scraper`:** Free, unlimited, returns more fields (app_version, thumbs_up, dev reply text + date), critical for version-regression and reply-rate analysis. Human approved at GATE 1.
- **Tradeoff:** Direct scraping carries IP-ban risk and potential Google ToS issues. Mitigated by rate-limiting requests and caching.
- **Status:** approved (GATE 1)

## D04: Database — Postgres on Supabase
- **Per master prompt §2.** Human created Supabase account and provided `DATABASE_URL`.
- **Status:** approved (GATE 1)

## D05: Apps in Scope
- Employee: `com.moveinsync.ets`
- Driver Partner Lite: `com.moveinsync.driver.lite`
- Driver Onboarding: `com.moveinsync.driver.dco`
- Competitor: Routematic `com.routematic.employee`
- Competitor: Safetrax `com.mtap.safetrax`
- **Status:** approved (GATE 1)

## D06: Gemini Model — `gemini-2.5-flash`
- **Alternatives:** newer Flash and Flash-Lite models listed by the configured Gemini project.
- **Why this model:** It is available to the configured project and is the model already used for the 165 existing labels; retaining it avoids mixing classifiers inside taxonomy v1.
- **Runtime limit:** the API reported 20 free-tier generation requests per day for this project/model on 2026-10-11. Requests per day reset at midnight Pacific time (S11).
- **Batching strategy:** 15 reviews per request, maximum 20 requests per quota window (up to 300 reviews/day, with caching).
- **Tradeoff:** full-data labeling requires multiple quota windows. Switching models would require a documented choice and a clean re-label to avoid a mixed model population.
- **Status:** approved by runtime verification (P4)
