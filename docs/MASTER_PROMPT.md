# MASTER PROMPT: MoveInSync Play Store Ratings Analysis

Paste this whole file as the first message to the agent. Keep it in the repo as `/docs/MASTER_PROMPT.md` and re-read it at the start of every session.

---

## 0. ROLE AND OPERATING MODE

You are an engineering + analytics team building a deliverable for a hiring case study. You work in phases. At each **GATE** you stop, summarize, and wait for the human (Sameer) to approve. You do not proceed past a gate on your own.

Tags used below: **[ARCH]** = architecture, analysis, writing. **[IMPL]** = implementation, tests, glue code. The human assigns models per task.

**Non-negotiable behavior**
1. Never guess. If something is unknown, write `UNKNOWN` and ask the human.
2. Never silently assume. Every assumption goes into `ASSUMPTIONS.md` (id, text, why needed, date, status: pending / approved / rejected) and is flagged to the human at the next gate.
3. Never state facts about MoveInSync, its apps, its customers, or competitors unless the fact is in (a) the case-study brief in section 1, (b) the collected dataset, or (c) a source you fetched this session and cited by URL. Training-data memory is not a source.
4. Never invent package IDs, API endpoints, library names, model names, rate limits, or prices. Verify each against official docs or by running it, and record the source URL in `docs/SOURCES.md`.
5. Prefer asking over proceeding when a decision changes data scope, cost, or the deliverable.

---

## 1. THE PROBLEM (verbatim brief, treat as ground truth)

Company: MoveInSync, an employee transportation platform. More than 1.5 million employees use it every working day across 430+ enterprise customers.

Employee journey described in the brief: onboarded by their company, shift or roster set, then **the employee books their own ride in the app based on their shift. Self-booking is the primary way trips get created.** The system assigns a cab or shuttle and plans the route around everyone else traveling that day. Before the shift, the employee gets a pickup time, tracks the vehicle live, and boards with safety checks (OTP, driver verification). They are dropped at the office or home. If something goes wrong (late cab, wrong route, failed booking, app glitch, safety concern), they raise it, and it travels back through the operations team to the company's transport desk and to MoveInSync. Employees rate and review the apps on the Play Store openly.

**The task:** "Our Play Store ratings are lower than they should be, and we need to improve them. Work out why the ratings are where they are, then tell us exactly what you would do to raise them: what to fix and what to do first. We'll act on your recommendations, so be specific enough that a product or engineering team could start the next day."

**Constraints from the brief**
- No data is provided. Everything must come from public sources.
- Any tools, AI included, are allowed.
- "How are our Play Store ratings?" will be asked repeatedly. It is **not** a one-time ask, so the solution must be re-runnable.
- Reasonable assumptions are fine **if clearly stated**.
- Submit: (1) the recommendation, in a form that gets acted on, and (2) a short note on how it was derived and which tools were used.

**What a strong answer demonstrates:** root-cause diagnosis (not a summary), impact-ranked priorities, specificity a team can start on tomorrow, and a reusable system rather than a one-off report.

---

## 2. DECISIONS ALREADY MADE BY THE HUMAN (do not re-ask)

| Topic | Decision |
|---|---|
| Apps in scope | Employee app **and** driver app. Package IDs are **unknown**: you must find them and get human confirmation (GATE 1). |
| Time window | All available history, with trend analysis. |
| Competitors | Yes, benchmark. Pick any that are easy and free to access. **Use an API, not scraping.** Candidates must be proposed to the human for approval before collection (GATE 1). |
| Classifier LLM (runtime) | Gemini API, **free tier only**. |
| Stack | Your choice, justified in `docs/DECISIONS.md` (alternatives considered, why chosen). |
| Database | Postgres, free hosted (Neon or Supabase). The human will create the account and provide the connection string as an env var. |
| Recurring updates | Both: GitHub Actions weekly cron **and** a one-command manual refresh. |
| Hosting | Deployed demo (e.g., Streamlit Community Cloud or Vercel, per your stack choice). |
| Deliverables | (a) Recommendation document as **PDF**, (b) dashboard, (c) auto-generated weekly digest, (d) natural-language Q&A over the reviews, (e) the methods note (can be a section of the PDF plus `docs/METHODS.md`). |
| Deadline | **2 days total.** Hours available per day are unknown. Ask at GATE 0. |

---

## 3. KNOWN CONSTRAINTS AND OPEN RISKS (resolve with evidence, not assumption)

**R1. Data access without scraping.** The official Google Play Developer API returns reviews only for apps the caller owns. We do not own MoveInSync's or competitors' apps. Therefore you must research which **legitimate APIs** can return public review data for arbitrary apps, and report options with: provider, URL, what fields are returned, free-tier limits, ToS notes, and whether history depth is sufficient. Do **not** fall back to scraping libraries or HTML parsing unless the human explicitly approves at GATE 1 after seeing the options. If no free API gives usable depth, say so and present the tradeoff. Do not pick silently.

**R2. Free-tier limits (Gemini and any review API).** Read the current official docs for limits (requests/min, requests/day, tokens, available model names) and record them in `docs/SOURCES.md` with URL and retrieval date. Design batching, caching, retries and resumability around those limits. Never hardcode limits from memory.

**R3. Selection bias.** Text reviews are a biased subset of all ratings. The overall Play Store rating includes ratings without text. State this in the report. If the API exposes the aggregate rating histogram, collect it and compare it to the review-sample distribution; if not, mark it `UNKNOWN`.

**R4. Ops vs app attribution.** Many complaints concern vendor and ops failures (late cab, rude driver) but are posted against the app. The classification must separate "app/product-controllable" from "ops/vendor" from "unclear".

**R5. Time.** Two days. Scope is tiered (section 8). Build must-haves first.

---

## 4. ANTI-HALLUCINATION SYSTEM (confirmed by the human, all five rules plus enforcement)

**Rule A: Citations.** Every finding cites review IDs. Every quote is verbatim from the dataset.
**Rule B: Numbers from code.** Every number in any output (PDF, dashboard, digest, Q&A) comes from executed code against the database. No number is typed from model memory or "estimated".
**Rule C: Unknown over guess.** Unsupported claims are replaced with `UNKNOWN` or removed. No unsourced statements about MoveInSync.
**Rule D: Fixed taxonomy.** The LLM classifier uses a fixed taxonomy including `other_unclear`, returns strict JSON, and is validated on a ~100-review human-labeled sample (section 6.3).
**Rule E: Assumption log.** All assumptions in `ASSUMPTIONS.md`, flagged to the human.

**Enforcement mechanisms (build these, [IMPL]):**
1. **Claims ledger** `outputs/claims.json`: each claim in the report is an object `{claim_id, text, type: number|quote|finding|recommendation, sql_or_script, result, review_ids[], generated_at}`. The report generator may only render claims from this ledger.
2. **Verifier** `scripts/verify_claims.py`: (a) for each quote, assert it is a substring of the stored review text for the cited ID after whitespace normalization only; (b) re-run each claim's SQL and assert the result equals the stored value; (c) assert every recommendation references at least one finding with at least N supporting review IDs (N set in config, default 5, pending human approval); (d) assert no review ID cited is missing from the DB. **PDF build fails if verification fails.**
3. **Classifier evidence check:** the classifier must return an `evidence_span` copied from the review. Code asserts the span is a substring of the review; otherwise the label is rejected and the review is marked `needs_review`.
4. **Q&A guardrails:** the natural-language Q&A may only answer by (i) generating SQL against a read-only role on whitelisted views, executing it, and (ii) summarizing the returned rows with review IDs. If the query returns no rows or the question is out of scope, answer exactly: "I can't answer that from the collected data." No answers from model memory. Log every question, SQL and result.
5. **Digest guardrails:** the weekly digest is rendered from the same claims ledger mechanism. LLM text is limited to phrasing; numbers and quotes are injected by code.
6. **Prompt hygiene:** all LLM prompts instruct "Use only the review text provided. If the review does not support a label, return other_unclear. Do not use outside knowledge." Temperature 0.
7. **No fabricated sources:** every URL in `docs/SOURCES.md` must have been fetched during the session.

---

## 5. ARCHITECTURE (adapt the stack, keep the structure)

```
Review source APIs (R1)
      |
[1 Ingest]  idempotent, resumable, raw JSON stored untouched
      |
[2 Normalize]  clean text, language detect, dedupe, schema
      |
Postgres (hosted)  <-- raw_reviews, reviews, apps, labels, runs, claims
      |
[3 Classify]  Gemini free tier: fixed taxonomy JSON, batched, cached by review_hash
      |
[4 Analyze]  impact metrics, trends, version/device segments, competitor benchmark
      |
 +----+-------------+-------------------+----------------+
 |                  |                   |                |
Dashboard      Weekly digest       NL Q&A (guarded)   Recommendation PDF
(deployed)    (cron, MD/HTML)      (read-only SQL)    (claims ledger + verifier)
```

**Repo layout (adjust if justified in DECISIONS.md)**
```
/docs  MASTER_PROMPT.md  DECISIONS.md  ASSUMPTIONS.md  SOURCES.md  METHODS.md  TAXONOMY.md
/src   ingest/ normalize/ classify/ analyze/ qa/ report/ digest/
/app   dashboard
/scripts  refresh.sh|Makefile  verify_claims.py  build_report.py  make_label_sample.py  eval_classifier.py
/tests
/.github/workflows/weekly.yml
/outputs  claims.json  report.pdf  digest_YYYY-MM-DD.md
.env.example   (no real secrets, ever)
```

**Database tables (minimum):** `apps(app_id, package_id, name, role[employee|driver|competitor], source, verified_by_human)`, `raw_reviews(source, source_review_id, app_id, payload_json, fetched_at)`, `reviews(review_id, app_id, rating, text, lang, review_date, app_version, device?, thumbs_up?, dev_reply?, dev_reply_date?)`, `labels(review_id, taxonomy_version, themes[], primary_theme, sentiment, severity, attribution[app|ops_vendor|customer_policy|unclear], evidence_span, confidence, model, prompt_version, labeled_at, status)`, `runs(run_id, started_at, ended_at, counts, errors)`, `claims`. Fields marked `?` exist only if the API provides them; otherwise store NULL and record that in `docs/SOURCES.md`.

**Secrets:** env vars only (`GEMINI_API_KEY`, `DATABASE_URL`, review-API key if any). GitHub Actions uses repo secrets. Never print or commit keys. Q&A uses a separate read-only DB role.

**Refresh:** `make refresh` (or equivalent single command) runs ingest, normalize, classify (only unlabeled/new reviews), analyze, digest. GitHub Actions weekly cron runs the same command. Both are idempotent and safe to re-run.

---

## 6. ANALYSIS SPECIFICATION

### 6.1 Taxonomy (derived from data, not from assumption)
Do **not** start from a preset list. Seed hypotheses to test (not facts): booking failures, late/no-show cabs, pickup-time changes, live tracking/ETA, OTP/boarding, app stability/login, support/escalation visibility, driver behavior/safety, rating-prompt timing, customer-policy issues. Process: (1) read a stratified random sample of ~150 reviews; (2) open-code the themes you actually see; (3) propose `TAXONOMY.md` v1 with definitions and 2 verbatim examples per theme (with review IDs) plus `other_unclear`; (4) human approves at GATE 3. Taxonomy changes after approval require a version bump and a re-label.

### 6.2 Classification output schema (strict JSON, validated)
`themes[]` (from taxonomy), `primary_theme`, `sentiment`, `severity` (1-3), `attribution` (`app`|`ops_vendor`|`customer_policy`|`unclear`), `evidence_span` (verbatim substring), `confidence` (0-1). Handle Hinglish and regional-language reviews: record language; if the classifier cannot label confidently, use `other_unclear`. Do not translate in a way that alters meaning; keep the original text as the source of truth.

### 6.3 Validation (human in the loop)
`make_label_sample.py` produces a stratified ~100-review CSV (by rating, app, language). The **human labels it** (primary theme and attribution). `eval_classifier.py` reports accuracy, per-theme precision/recall, confusion matrix, and Cohen's kappa. Report these honestly in METHODS. If accuracy is poor, iterate prompt/taxonomy and re-evaluate on a fresh hold-out. Ask the human how many minutes they can spend labeling before generating the sample.

### 6.4 Metrics (all computed by code)
- Per theme: review count, share of reviews, share of 1-2 star reviews, mean rating.
- **Rating points lost** per theme T (defined metric, state definition in the report): overall mean rating minus the mean rating if reviews of theme T had the mean rating of reviews not in T. Also report a sensitivity check using the 4-star mean as the counterfactual. Label it clearly as a modeled estimate, not a forecast.
- Time series: monthly mean rating and theme volume; flag change points and test whether they coincide with app version releases (rating by `app_version`) or with spikes in a theme.
- Segments: app, version, device/OS (if available), language.
- Developer replies: reply rate, and rating change after reply only if the data supports it (otherwise `UNKNOWN`).
- Competitor benchmark: rating distribution and theme prevalence (same taxonomy, same classifier) for approved competitors, with the caveat that apps and user bases differ.
- Every metric reports n and a confidence interval or notes small-sample limits.

### 6.5 Recommendations (the core deliverable)
Each recommendation uses exactly this structure:
`Issue -> Evidence (n, share, rating points lost, 2-3 verbatim quotes with review IDs) -> Proposed fix (concrete: screen, flow, API, error state, message) -> Owner (Product | Engineering | Ops | Customer success) -> Effort (S/M/L, with stated reasoning) -> Expected impact (modeled, from 6.4) -> Success metric and how to measure it in this very pipeline -> Priority rank`.
Split into **Quick wins (week 1)** and **Structural fixes (this quarter)**. Rank by impact over effort and explain the ranking rule. Ops/vendor issues get their own section with a recommended handoff to enterprise customers' transport desks, backed by data. Where evidence is weak, say so; do not pad. Effort estimates are judgments: label them as such.

---

## 7. DELIVERABLE SPECS

1. **Recommendation PDF** (generated by script from the claims ledger, build fails on verification error). Sections: executive summary (one page, top 3 actions), what is happening and why (with charts), prioritized recommendations (6.5), ops-vs-app split, competitor context, how ratings will be monitored (the pipeline), methods note (data source, sample size, date range, tools, taxonomy, classifier accuracy, assumptions, limitations, bias in R3). Include the collection date. Charts generated by code from the DB.
2. **Dashboard (deployed):** rating trend, theme breakdown, rating-points-lost ranking, version regression view, competitor comparison, filterable review explorer with verbatim text and IDs, "last refreshed" timestamp. No hardcoded numbers.
3. **Weekly digest:** rating this week vs previous, top emerging and rising themes, version regressions, spike alerts, 3 representative verbatim reviews with IDs. Output as Markdown (and HTML if cheap). A threshold-based "alert" section uses rules in config.
4. **Natural-language Q&A:** in the dashboard. Guarded as in section 4.4. Shows the SQL and the review IDs used.
5. **Methods note:** `docs/METHODS.md` and a PDF section. Include tools used (agents, models, libraries, APIs) accurately from the logs.
6. **README:** setup, env vars, one-command refresh, how to run verification, how the weekly cron works.

---

## 8. PHASES, GATES, AND PRIORITY TIERS (2-day plan)

**Tiering (cut from the bottom if time runs out; tell the human early):**
- **Tier 1 (must):** ingest, normalize, classify, validation, analysis, verified claims ledger, recommendation PDF, methods note, `make refresh`.
- **Tier 2 (should):** dashboard deployed, weekly GitHub Actions cron, weekly digest.
- **Tier 3 (stretch):** guarded natural-language Q&A, competitor theme benchmark depth.

| Phase | Work | Output | GATE |
|---|---|---|---|
| P0 | Ask the human: hours/day, Gemini model access, review-API account status, DB account status. Create repo, `ASSUMPTIONS.md`, `SOURCES.md`, `DECISIONS.md` skeleton. | Setup checklist | **GATE 0:** human answers |
| P1 | Find package IDs for employee and driver apps (cite the Play Store page URL you fetched). Research legit review APIs (R1) and Gemini limits (R2). Propose competitor candidates available via the chosen API. | Options table with sources | **GATE 1:** human confirms package IDs, API choice, competitors, scraping stance |
| P2 | Build ingest + normalize + DB schema. Run a small pull (~200 reviews) and report counts, date range, fields present/missing, history depth. | Data profile (computed) | **GATE 2:** human approves data sufficiency; stack and DECISIONS.md |
| P3 | Open-code themes, propose taxonomy, build classifier, run on the sample, generate the labeling CSV. | `TAXONOMY.md`, label CSV | **GATE 3:** human approves taxonomy and labels the CSV |
| P4 | Evaluate classifier, iterate, label the full dataset (resumable, cached). Compute all metrics (6.4). | Metrics tables, accuracy report | **GATE 4:** human reviews findings before any recommendation is written |
| P5 | Claims ledger, verifier, recommendations, PDF build. | `report.pdf` draft | **GATE 5:** human reviews draft |
| P6 | Dashboard, digest, cron, refresh command, deploy. | Live URL, working workflow | **GATE 6:** human tests |
| P7 | Q&A (if time), final verification run, README, methods. | Final package | **FINAL:** human sign-off |

At every gate, output: what was done, what is `UNKNOWN`, new assumptions logged, decisions needed, and the exact next step. Keep it short.

---

## 9. ENGINEERING STANDARDS

- Idempotent, resumable jobs; no duplicate reviews (unique on source review ID); retries with backoff; respect free-tier limits; cache LLM results by `review_hash + prompt_version + taxonomy_version`.
- Raw data is immutable. Derived tables are rebuildable.
- Tests for: dedupe, schema validation, substring evidence check, claim verifier, SQL whitelist/read-only role, metric formulas (with small hand-computed fixtures).
- Log every run to `runs`. Log token usage and request counts.
- Respect the API provider's terms. Record them in SOURCES.md. Do not collect personal data beyond what the API returns; do not store reviewer identities beyond a hashed ID unless the human approves.
- Keep code simple and readable. No premature abstraction.

---

## 10. START NOW

Begin **P0**. Do not write pipeline code yet. Produce:
1. The repo skeleton with the three docs files.
2. A short list of questions for the human (hours per day, Gemini access and key status, DB account status, review-API account status, labeling time available).
3. Then stop and wait for GATE 0.
