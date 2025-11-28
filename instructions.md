## 0. Restated problem and key assumptions

You need a self-contained demo application for the BSA Annual Conference (Birmingham, 7–8 May 2025) that lets delegates from UK building societies sit down at a laptop and ask natural-language questions about what customers are saying about their society, and how that compares to peers, based entirely on a pre-prepared snapshot of public data. ([bsa.org.uk][1])

The core idea: a “Voice of the Customer on tap” assistant for UK building societies, powered by LLMs and RAG, but with all data collection, enrichment and indexing done offline beforehand. At the event, the app is essentially a fast, query-time orchestrator over a frozen dataset plus live calls to an LLM / embeddings API.

Assumptions and nuances:

* Scope is UK building societies (all BSA members and trading names) based on the BSA’s list of societies and associates. ([bsa.org.uk][2])
* Primary data: public customer reviews (Trustpilot building society category, app store reviews for mobile apps, possibly Google Maps branch reviews), not private customer data. ([Trustpilot][3])
* All data is collected and processed before the conference. At the conference, no scraping or outbound calls except to the LLM / embeddings provider.
* The app is exploratory and qualitative: it should provide directional, evidence-based insight rather than full statistically robust benchmarking.
* You have relatively high freedom to pre-process offline (including LLM-heavy enrichment), but runtime should be snappy and robust on a single laptop with a decent network connection.
* You want something impressive to senior FS leaders: it must feel like a serious, insight-led tool, not a toy chatbot.

I will go through the requested sections in order.

---

## 1) Overall concept and requirements

### 1.1 Refined problem statement

Design a single-laptop demo application that:

* Lets a user type free-text questions about one or more UK building societies, timeframes and focus areas.
* Interprets intent into structured filters: who (which societies), when (time period), what (topic/area), and how (question type: sentiment, comparison, trends, drivers, examples).
* Answers with:

  * A concise insight summary.
  * Simple, interpretable metrics (e.g. average rating, % negative, volume of reviews).
  * Selected anonymised excerpts from underlying reviews as “evidence”.
* Is honest about:

  * Data coverage and sources.
  * Time window of the snapshot.
  * Limitations (e.g. uneven coverage, public-review biases).
* Is robust in a noisy, high-traffic demo setting:

  * Handles mis-typed society names, nicknames and aliases.
  * Handles incomplete / follow-up questions.
  * Degrades gracefully when data is sparse or a question is impossible.

### 1.2 Additional use cases / interaction patterns

All still within your constraints:

* “What distinguishes us” style questions

  * “What do customers say we are particularly good at compared with other societies of our size?”
  * Answer: key differentiators by topic, backed by relative sentiment scores and quotes.

* “What changed” questions

  * “How has sentiment about our digital banking changed since Covid?”
  * Requires precomputed pre/post segments (e.g. pre-March 2020 vs post-March 2020) and basic trend indicators.

* “Drill-down” flows

  * User: “How are we doing overall versus Nationwide and Skipton?”
  * Follow-up: “What are the main drivers of negative sentiment for us in that comparison?”
  * The system reuses the already inferred entity/timeframe context, only narrowing to negative drivers.

* “What if we zoom out” sector questions

  * “What are the top three pain points for customers across the mutual sector overall?”
  * Helps BSA staff reflect on sector-wide themes.

* “Explain it to my board” mode (implicit)

  * Recognise when the question is high-level and strategic (“If you had to brief our board on customer sentiment, what would you say?”) and respond with an executive-style summary first, then evidence.

* “Outlier detection” type questions

  * “Which building societies look like outliers for customer satisfaction on branches?”
  * Needs precomputed z-scores or relative rankings, with caveats on sample size.

### 1.3 Additional design constraints and risks

Some that are easy to miss:

* Platform terms of use and legality of scraping:

  * Trustpilot, app stores and Google often restrict automated scraping and use of data. You may need to use approved APIs, rate limits, or manual exports rather than unfettered scraping. ([Trustpilot][3])
* GDPR and data protection:

  * Even though reviews are public, you must treat them as personal data under UK GDPR if individuals are identifiable. ICO guidance on analytics stresses careful assessment of lawful basis, data minimisation and anonymisation. ([ICO][4])
* Review manipulation and bias:

  * Trustpilot and others deal with fake and manipulated reviews; CMA guidance already treats fake reviews as illegal, and recent reporting highlights exploitation of review platforms to appear legitimate. ([GOV.UK][5])
  * This must be acknowledged in limitations.
* Reputational risk at an industry conference:

  * You could surface very negative sentiment about specific societies (e.g. large ones with low ratings). If poorly framed, that might create embarrassment at your stand.
* Latency and network dependency:

  * Conference Wi‑Fi is often unreliable. Outsourcing all reasoning to a remote LLM is fine, but you should design for graceful degradation when latency spikes or the API is temporarily unavailable.
* Safety and content risk:

  * Public reviews sometimes contain abusive or defamatory content. The system needs to filter or paraphrase such content so you are not amplifying harmful statements at a conference stand.
* UX constraints in a noisy environment:

  * People will have limited time and attention. Answers must be scannable in 20–30 seconds.

---

## 2) Data and modelling design

### 2.1 Data sources and MVP scope

Starting point: the BSA list of UK building societies and trading names (e.g. Nationwide, Coventry, Leeds, Skipton, Yorkshire, Principality, Nottingham, Newcastle, West Bromwich, etc.). ([bsa.org.uk][2])

Proposed MVP scope:

* Building societies:

  * Target 10–15 societies:

    * The largest 8–10 by assets. ([advratings.com][6])
    * Plus 3–5 regionals with strong Trustpilot presence. ([Trustpilot][3])
  * This keeps data volume manageable but still interesting for delegates.
* Time window:

  * e.g. Reviews from 1 January 2020 to a chosen cut-off (say 31 March 2025).
  * This allows “since Covid” comparisons and “last year / last 12 months” without being too big.
* Data sources:

  * Trustpilot:

    * Building Society category, plus direct profiles for selected societies. ([Trustpilot][3])
  * App store reviews:

    * Apple App Store and Google Play for each society’s main mobile banking app(s).
  * Optional for stretch:

    * Google Maps reviews for key branches.
    * Selected public news or survey summaries for context (but used in a different index to avoid mixing with reviews).

If constraints bite, you could start with:

* 5–8 major societies.
* Trustpilot + one app store only.
* 2–3 years of data.

### 2.2 Core data model (tables)

You can implement this in SQLite or DuckDB (Parquet-backed), plus a separate vector index.

**1. building_society**

* id (string)
* canonical_name
* bsa_name (as on BSA site) ([bsa.org.uk][2])
* legal_entity_name
* trading_names (JSON or separate table)
* size_bucket (e.g. “mega”, “large”, “regional”)
* website_domain
* notes (optional)

**2. building_society_alias**

* id
* building_society_id
* alias_text (e.g. “Nationwide”, “Nationwide BS”, “YBS”, “Coventry Building Soc”)
* alias_type (short_name, trading_name, acronym, misspelling, legacy_brand)
* confidence_score

**3. data_source**

* id
* name (“Trustpilot”, “Apple App Store”, “Google Play”, “Google Maps”)
* source_type (review_platform, app_store, maps)
* url_pattern
* terms_version_note

**4. public_review**

* id (internal)
* source_id
* source_review_id (as string)
* building_society_id
* review_date (date)
* rating_raw (e.g. 1–5)
* rating_normalised (float 0–1 or 1–5)
* title_text
* body_text_raw
* body_text_clean (PII redacted, normalised)
* reviewer_language
* channel (branch, online, mobile_app, call_centre, other, unknown)
* product (mortgage, savings, current_account, ISA, other, unknown)
* location_text (optional if available)
* is_flagged_for_exclusion (e.g. suspected spam or PII-heavy)

**5. sentiment_aspect**

One row per review x aspect.

* id
* review_id
* overall_sentiment_label (very_negative, negative, neutral, positive, very_positive)
* overall_sentiment_score (e.g. −1 to +1)
* aspect (e.g. digital_banking, branches, mortgages, savings, customer_service, onboarding, fees)
* aspect_sentiment_label
* aspect_sentiment_score
* emotion (e.g. angry, frustrated, relieved, delighted)
* model_version

**6. topic_tag**

* id
* review_id
* topic_key (e.g. “login_issues”, “slow_mortgage_processing”, “staff_friendly”, “rate_changes”)
* topic_group (e.g. “digital”, “mortgages”, “service”)
* relevance_score (0–1)
* model_version

**7. summary_metric**

Aggregated metrics at a chosen grain, e.g. monthly per society per aspect.

* id
* building_society_id
* time_bucket_start (date)
* time_bucket_end (date)
* aspect (“overall” or specific)
* product (optional dimension)
* channel (optional dimension)
* review_count
* avg_rating
* avg_sentiment_score
* pct_negative_reviews
* pct_positive_reviews
* net_sentiment_score (e.g. positive minus negative share)
* peer_group_avg_sentiment_score
* peer_group_review_count
* metric_version

**8. embedding_document**

Documents for the vector index.

* embedding_id
* doc_type (review, synthetic_summary, topic_cluster_description)
* source_review_id (nullable if synthetic)
* building_society_id
* review_date
* aspects (JSON list)
* topics (JSON list)
* sentiment_label
* text_for_embedding (shortised, redacted)
* embedding_vector (stored in vector DB, but an id can be stored here)

The physical storage of embeddings will depend on chosen vector DB; you can either keep metadata in SQLite and vector data in a separate store, or use one database that supports vectors directly (e.g. pgvector, LanceDB, Qdrant).

### 2.3 Offline processing pipeline

You can implement this as a series of Python steps (e.g. Prefect, Airflow, or just scripts). At a high level:

**Step 1: Canonical entity list and aliases**

* Pull the current list of UK building societies and trading names from the BSA site. ([bsa.org.uk][2])
* Manually add common short forms and acronyms:

  * “Nationwide”, “Nationwide BS”, “YBS”, “Skipton”, “Coventry BS”, etc.
* Optionally use:

  * A small LLM prompt to generate plausible aliases from canonical names and websites.
* Store in building_society and building_society_alias tables.

**Step 2: Data collection**

* For each building society and data source:

  * Use source-specific collection code:

    * Trustpilot:

      * Use allowed mechanisms (API/CSV export or careful scraping compliant with robots.txt and terms).
      * Pull all reviews in the chosen date range. ([Trustpilot][3])
    * App stores:

      * Use App Store/Google Play APIs or scraping libraries to get review text, rating, date, app version.
    * Optional: Google Maps for key branches.
* Persist raw JSON or CSV in a “raw” bucket (e.g. local folder / Parquet files).
* Include metadata such as retrieval_date and source_version.

**Step 3: Cleaning and normalisation**

* Standardise fields:

  * Convert dates to UTC date.
  * Map star ratings to a common 1–5 scale.
* Filter:

  * Discard reviews outside the date range.
  * Optionally discard non-English reviews if they are rare.
* PII handling:

  * Regex removal for emails, phone numbers, account numbers, postcodes.
  * Optional LLM-based redaction of names and other identifiers.
* Channel and product inference:

  * Use heuristics and an LLM classifier to tag whether a review is about:

    * Branch vs call centre vs website vs mobile app.
    * Mortgages vs savings vs current accounts vs general service.
* Save as public_review records.

**Step 4: Sentiment and topic extraction**

Offline, using an LLM or a cheaper sentiment model:

* For each review (or for a high-quality subset if cost is a concern):

  * Call LLM with a structured prompt to output:

    * Overall sentiment label and score.
    * Aspect-specific sentiments for a fixed taxonomy.
    * Key topics (up to 3–5 per review) from a controlled vocabulary plus free-text.
    * Emotion (optional).
* Store results in sentiment_aspect and topic_tag tables.

You can also cluster topics offline to derive a stable taxonomy for the demo (e.g. run BERTopic or similar on the review texts, then manually label clusters).

**Step 5: Metric computation**

Using SQLite, DuckDB or pandas:

* Choose grain:

  * Monthly buckets from Jan 2020 to cut-off date.
* For each society x time_bucket x aspect (and optionally product/channel):

  * Compute:

    * review_count
    * avg_rating
    * avg_sentiment_score
    * pct_negative, pct_positive
  * Compute peer averages:

    * For example: for a given society and aspect, compare to:

      * All other societies.
      * A size-based peer group.
* Persist these to summary_metric.

Also precompute:

* “Since Covid”:

  * Pre-Covid period: up to Feb 2020.
  * Post-Covid period: from Mar 2020 onwards.
* “Last year” and “last 12 months”:

  * Based on the snapshot cut-off.

**Step 6: Embeddings and vector index**

* Decide on embedding granularity:

  * Each review as one document is often enough.
  * Optionally create synthetic “topic summaries” per society per aspect (e.g. 150–200 words generated once offline) to help RAG.
* For each embedding document:

  * Create text_for_embedding:

    * Shortened to e.g. 256–512 tokens.
    * Redacted and cleaned.
  * Call embeddings API (e.g. text-embedding-3-large) offline.
  * Store vectors and metadata in your vector DB (e.g. LanceDB, Chroma, Qdrant, pgvector).
* Store the vector index directory ready for copying to the demo laptop.

**Step 7: Snapshot and packaging**

* Freeze all structured data (SQLite/Parquet/CSV) plus the vector index and configuration (taxonomy, prompts).
* Record:

  * Data sources used.
  * Date window.
  * Number of reviews per society.
* This metadata will be used in disclaimers and in responses.

### 2.4 Name resolution and aliases

Robust name handling is critical.

Approach:

* Offline:

  * Build a canonical alias dictionary from:

    * BSA list of building societies and trading names. ([bsa.org.uk][2])
    * Manual additions (common shorthand like “Nationwide”, “YBS”).
  * Optionally add approximate string matches (fuzzy matching on edit distance).
* At query-time:

  1. Use the parse_query tool (LLM) to extract free-text mentions of institutions from the user query.
  2. For each extracted string:

     * Normalise (lowercase, strip punctuation, remove “BS” / “Building Society” suffix).
     * Look up in alias table first.
     * If not found, apply fuzzy matching against canonical names and aliases, returning candidates with scores.
  3. If ambiguous:

     * If one candidate’s score is clearly higher, pick it but record that the mapping is low-confidence.
     * If ambiguity remains, the bot can:

       * Either ask a clarifying question.
       * Or state that it assumed a specific mapping and show that assumption in the answer (“Interpreting ‘YBS’ as Yorkshire Building Society”).

Also handle “sector” references:

* Phrases like “the sector”, “building societies overall” should map to a pseudo-entity representing “all societies in scope”.

---

## 3) LLM interaction and backend workflow

### 3.1 Turn-level interaction flow

For each user message:

1. **Context assembly**

   * Retrieve conversation state for the session:

     * Previously inferred primary societies, comparison set, timeframe, aspects.
     * Last answer’s entities and metrics.

2. **Query parsing via tool / function**

   Use an LLM function `parse_query` to transform the user message plus recent context into structured intent.

   Inputs to LLM:

   * System instruction:

     * Explain role: “You extract structured intent from questions about UK building societies’ public customer sentiment and reviews.”
     * Provide allowable values for aspects, question types, timeframe interpretations etc.
     * Always use British English spellings in any textual fields.
   * User message (current turn).
   * Limited conversation summary (last 2–3 turns).
   * Canonical list of building society names and known aliases (if within token budget).

   Output: JSON (validated by the function schema).

3. **Intent consolidation**

   Backend merges parsed intent with previous state:

   * If `is_follow_up` is true:

     * Reuse primary_societies and timeframe from state, unless explicitly overridden.
     * Update aspects or question_type where new information is present.
   * If new primary societies are specified, override previous ones.

4. **Data retrieval (metrics and RAG)**

   Based on the resolved intent:

   * Metrics query:

     * Translate timeframe into a concrete range or into precomputed segments:

       * e.g. “last year” → previous calendar year; “recently” → last 6 months; “since Covid” → Mar 2020 to snapshot cut-off.
     * Query summary_metric for:

       * Each primary and comparison society.
       * Each requested aspect.
     * Perform additional calculations as needed:

       * Differences between society and peer average.
       * Trend labels (improving, stable, deteriorating) based on slopes.

   * RAG query:

     * Build a search filter:

       * building_society_id in set.
       * review_date in timeframe.
       * aspects or topics matching focus_areas (if specified).
       * sentiment filters if question is about negative / positive / complaints.
     * Build a query string:

       * Combine society names + aspect words + question type hints.
     * Call the vector DB:

       * Top N = 20–50 reviews.
       * Apply diversity: limit per society and per time bucket.
     * Post-process for display:

       * Redact residual PII.
       * Shorten to 1–2 sentences per review.

5. **Answer generation**

   Use a second LLM call for answer generation.

   Inputs:

   * System message:

     * You are an assistant summarising public customer sentiment about UK building societies.
     * Use only the metrics and review snippets provided.
     * Do not invent numbers or rankings that are not in the metrics.
     * Always mention data coverage (approximate review counts, timeframe, sources).
     * Use British English.
     * Avoid naming individual reviewers or including PII; refer to “one reviewer said …”.
   * Tool-style content:

     * A single JSON object containing:

       * Parsed intent (from parse_query).
       * Metrics (structured).
       * Evidence snippets (structured).
       * Data coverage summary (counts, sources).
   * User message (for context).

   Required behaviour of the LLM:

   * Produce:

     * A short headline answer (2–3 sentences).
     * A small number of bullet points with key stats and themes.
     * An “Evidence from reviews” section with 3–6 anonymised snippets.
     * Where relevant, explicit caveats (e.g. small sample size).

6. **Response delivery**

   * Return answer text plus:

     * Structured data for the UI:

       * metrics used.
       * snippets.
       * assumptions (e.g. “Interpreted ‘YBS’ as Yorkshire Building Society”).

### 3.2 JSON schema: parse_query tool

Example (OpenAI function-style):

```json
{
  "name": "parse_query",
  "description": "Parse a user question about UK building societies' public reviews into structured intent.",
  "parameters": {
    "type": "object",
    "properties": {
      "is_follow_up": {
        "type": "boolean",
        "description": "True if the user is clearly referring to the previous answer."
      },
      "primary_building_societies": {
        "type": "array",
        "description": "Building societies that are the primary focus of the question, as mentioned by the user.",
        "items": { "type": "string" }
      },
      "comparison_building_societies": {
        "type": "array",
        "description": "Building societies used as comparators (e.g. 'versus Nationwide').",
        "items": { "type": "string" }
      },
      "timeframe": {
        "type": "object",
        "description": "The time period implied by the question.",
        "properties": {
          "original_expression": { "type": "string" },
          "timeframe_type": {
            "type": "string",
            "enum": ["all_available", "last_12_months", "last_24_months", "calendar_year", "since_covid", "custom_absolute", "recent_generic"]
          },
          "calendar_year": {
            "type": "integer",
            "description": "Used if timeframe_type = 'calendar_year'."
          },
          "start_date": {
            "type": "string",
            "description": "ISO date 'YYYY-MM-DD' if explicitly mentioned or inferred for custom windows."
          },
          "end_date": {
            "type": "string",
            "description": "ISO date 'YYYY-MM-DD'."
          }
        },
        "required": ["original_expression", "timeframe_type"]
      },
      "focus_areas": {
        "type": "array",
        "description": "High-level aspects or topics the user cares about.",
        "items": {
          "type": "string",
          "enum": [
            "overall",
            "mortgages",
            "savings",
            "current_accounts",
            "branches",
            "digital_banking",
            "mobile_app",
            "online_banking",
            "customer_service",
            "complaints_handling",
            "fees_and_rates",
            "onboarding"
          ]
        }
      },
      "question_type": {
        "type": "string",
        "description": "The main analytical question the user is asking.",
        "enum": [
          "overall_sentiment",
          "comparison",
          "trend_over_time",
          "drivers_of_sentiment",
          "volume_and_mix",
          "examples_only",
          "other"
        ]
      },
      "sentiment_focus": {
        "type": "string",
        "description": "If the user emphasises positive, negative or both.",
        "enum": ["all", "mostly_negative", "mostly_positive"]
      },
      "detail_level": {
        "type": "string",
        "description": "Desired level of detail.",
        "enum": ["brief", "standard", "board_level_summary"]
      },
      "constraints": {
        "type": "object",
        "description": "Any explicit constraints.",
        "properties": {
          "max_societies": { "type": "integer" },
          "min_review_count": { "type": "integer" }
        }
      }
    },
    "required": [
      "is_follow_up",
      "primary_building_societies",
      "comparison_building_societies",
      "timeframe",
      "focus_areas",
      "question_type",
      "sentiment_focus",
      "detail_level"
    ]
  }
}
```

Backend then maps `primary_building_societies` and `comparison_building_societies` through the alias resolution logic.

### 3.3 JSON schema: metrics and evidence to answer-generation prompt

Example structure passed into the answer LLM:

```json
{
  "intent": {
    "primary_building_societies": ["Nationwide Building Society"],
    "comparison_building_societies": ["Yorkshire Building Society"],
    "timeframe": {
      "label": "last_12_months",
      "start_date": "2024-04-01",
      "end_date": "2025-03-31"
    },
    "focus_areas": ["digital_banking", "branches"],
    "question_type": "comparison"
  },
  "data_coverage": {
    "snapshot_end_date": "2025-03-31",
    "sources": ["Trustpilot", "Apple App Store", "Google Play"],
    "total_reviews_considered": 18234,
    "per_society_review_counts": [
      { "building_society_id": "nationwide", "review_count": 7756 },
      { "building_society_id": "yorkshire", "review_count": 9380 }
    ]
  },
  "metrics": [
    {
      "building_society_id": "nationwide",
      "building_society_name": "Nationwide Building Society",
      "aspect": "digital_banking",
      "timeframe_start": "2024-04-01",
      "timeframe_end": "2025-03-31",
      "review_count": 3200,
      "avg_rating": 3.4,
      "avg_sentiment_score": -0.15,
      "pct_negative_reviews": 0.42,
      "pct_positive_reviews": 0.36,
      "peer_group_avg_sentiment_score": -0.05
    },
    {
      "building_society_id": "yorkshire",
      "building_society_name": "Yorkshire Building Society",
      "aspect": "digital_banking",
      "timeframe_start": "2024-04-01",
      "timeframe_end": "2025-03-31",
      "review_count": 2100,
      "avg_rating": 4.2,
      "avg_sentiment_score": 0.35,
      "pct_negative_reviews": 0.18,
      "pct_positive_reviews": 0.63,
      "peer_group_avg_sentiment_score": -0.05
    }
  ],
  "evidence_snippets": [
    {
      "snippet_id": "rev_12345",
      "building_society_id": "nationwide",
      "building_society_name": "Nationwide Building Society",
      "source": "Trustpilot",
      "review_date": "2024-11-03",
      "rating": 2,
      "sentiment_label": "negative",
      "aspects": ["digital_banking", "mobile_app"],
      "topics": ["login_problems"],
      "snippet_text": "One reviewer said they were locked out of the app for days and could not reach support, calling the experience 'incredibly stressful'."
    },
    {
      "snippet_id": "rev_67890",
      "building_society_id": "yorkshire",
      "building_society_name": "Yorkshire Building Society",
      "source": "Trustpilot",
      "review_date": "2024-10-15",
      "rating": 5,
      "sentiment_label": "positive",
      "aspects": ["digital_banking"],
      "topics": ["ease_of_use", "speed"],
      "snippet_text": "Another reviewer praised how easy it was to set up online access and said the app 'just works' for checking balances and moving money."
    }
  ],
  "limitations": {
    "notes": [
      "Digital banking reviews may over-represent customers who had problems.",
      "Sample size for some societies and aspects is below 100 reviews."
    ]
  }
}
```

The answer-generation system prompt can then instruct the LLM exactly how to use this object.

### 3.4 Handling follow-ups and context

* Session state per conversation:

  * Store latest resolved intent, plus last metrics and society IDs.
* The `parse_query` tool:

  * Detects follow-ups via content and pronouns (“What about just for mortgages?”, “And how do we compare with X?”).
  * Returns `is_follow_up: true` and only new fields.
* Backend logic:

  * If `is_follow_up`:

    * Fill missing fields from session state.
    * For example, if user says “What about just for mortgages?”:

      * Keep the same primary societies and timeframe.
      * Replace focus_areas with ["mortgages"].
* Conversations should feel cumulative:

  * “How are we doing overall?” → “What about branches?” → “And how does that compare to Coventry?”
  * You do not need to re-ask for the society name.

---

## 4) Application architecture

### 4.1 High-level architecture for a single laptop

**Runtime at conference**

* Frontend:

  * Single-page web app (React or simple Vanilla JS) running in a browser in kiosk/full-screen mode.
* Backend:

  * Python + FastAPI server running locally.
  * Provides:

    * POST /chat for chat turns.
    * POST /reset_session for starting fresh conversations.
    * GET /health for quick checks.
* Data stores (local):

  * SQLite or DuckDB:

    * building_society, aliases, public_review (if you want to show IDs), summary_metric, and metadata tables.
  * Vector DB:

    * Local instance of Chroma, LanceDB, Qdrant, or pgvector (embedded Postgres).
    * Stored on disk in a folder you ship with the application.
* External dependencies:

  * LLM / embedding APIs (OpenAI or Azure OpenAI).
  * Optional: you could precompute all embeddings offline so no embedding API is needed at runtime, only chat completions.

**Offline / pre-event**

* Data ingestion and enrichment:

  * Python scripts or notebooks for:

    * Scraping / API calls.
    * Cleaning and normalisation.
    * LLM calls for sentiment and topics.
    * Metric computation.
    * Embedding creation and vector index building.
* Build artefacts:

  * SQLite / DuckDB file with structured data.
  * Vector index folder.
  * A config file containing:

    * Data coverage summary.
    * Aspect taxonomy.
    * Cut-off dates and mapping rules for “recently”, “since Covid”, etc.

### 4.2 Backend responsibilities

Backend (FastAPI) responsibilities:

* Session management:

  * Generate session IDs.
  * Maintain in-memory or lightweight stored state per session (intent, last societies, last timeframe).
* Orchestration:

  * For each chat turn:

    * Call LLM with parse_query tool.
    * Run SQL queries against summary_metric.
    * Run vector DB queries for evidence.
    * Call LLM for answer generation.
* Safety and guardrails:

  * Pre-filter review texts for PII or abusive language when building snippets.
  * Enforce maximum tokens in prompts.
* Logging:

  * Log anonymised sessions (session ID, query text, resolved intent, metrics used), but:

    * Do not log raw review snippets again (they already exist in the DB).
* Administration:

  * Endpoint or local script to reset everything (wipe in-memory sessions).

### 4.3 Data storage choices

* SQL layer:

  * SQLite:

    * Simple, file-based, perfect for a laptop demo.
    * Can handle tens or hundreds of thousands of reviews easily.
  * DuckDB:

    * Nice if you prefer columnar and analytical queries; but SQLite is sufficient here.

* Vector DB:

  * LanceDB or Chroma:

    * Both can run embedded.
    * Good Python support.
    * For a few hundred thousand vectors, either is fine.
  * pgvector:

    * Requires a Postgres instance; might be heavier than necessary for a conference laptop.

Given a one-off demo, SQLite + LanceDB is a good combination.

### 4.4 Front-end options

* Minimal custom SPA:

  * React or Vue, or even plain JS:

    * One central chat pane.
    * Input box.
    * “Reset conversation” button.
  * Advantages:

    * Full control over look and feel.
    * Easy to add subtle hints (placeholder text, rotating suggestions).

* Quick options (if you want to accelerate):

  * Gradio or Streamlit:

    * Ultra-fast prototyping.
    * But looks more like a data-science demo than a polished conference product.

Given the audience, I would favour a simple custom SPA with:

* Large, readable typography.
* Clear BSA / Woodhurst branding.
* Dark or muted background to work well on stand screens.

### 4.5 Logging, monitoring, and controls

For a demo:

* On-device logging:

  * Log to a file:

    * Timestamp.
    * Session ID.
    * Raw user query.
    * Parsed intent JSON.
    * Error traces if any.
  * Do not log LLM outputs beyond what is necessary.

* Monitoring:

  * Simple terminal output:

    * HTTP access logs.
    * Occasional metrics (e.g. number of sessions).

* Controls:

  * “Reset conversation” button in the UI:

    * Calls /reset_session.
  * “Demo mode” toggle (keyboard shortcut or hidden button):

    * Shows extra debug info (like metrics and raw parsed intent) for you, not for attendees.
  * Safety handling for adversarial questions:

    * System prompt instructs LLM to respond with a neutral “out of scope” answer if:

      * The question is not about building societies.
      * The user asks for personal financial advice.
      * The question is abusive or discriminatory.

---

## 5) UX and explanation

### 5.1 How answers should be presented

Structure every answer consistently so it is easy to scan.

Suggested structure:

1. **Headline**

   * One or two sentences summarising the key point:

     * “Over the last 12 months, public reviews suggest that customers are generally positive about your branch experience, but more mixed about digital banking.”

2. **Key metrics**

   * Bullet list with numbers:

     * Avg rating (e.g. 4.2 / 5).
     * Share of negative vs positive reviews.
     * Comparison versus peers (“about 0.3 points higher than the peer average for branches”).

3. **Key themes and drivers**

   * 3–5 bullets that summarise topics:

     * “Strong praise for friendly and knowledgeable branch staff.”
     * “Complaints about slow mortgage application processing times.”

4. **Comparison (if applicable)**

   * Small table-style textual summary:

     * “Compared with Society X, digital banking sentiment is lower, but branch sentiment is slightly higher.”

5. **Evidence snippets**

   * Show 3–6 short review excerpts, each in a small card:

     * Society name, source (Trustpilot / App Store), date.
     * Rating (stars).
     * Short snippet:

       * “One reviewer said the app was ‘easy to use and reliable’, especially for checking balances.”
     * Avoid names or specific identifiers.

6. **Data coverage and caveats**

   * A short paragraph:

     * “Based on approximately 5,200 public reviews from Trustpilot and app stores between Jan 2023 and Mar 2025. Public reviews are self-selected and may over-represent customers with strong opinions.”

### 5.2 Disclaimers and data coverage

Always visible on screen (footer):

* “This demonstration summarises anonymised public reviews (e.g. Trustpilot and app stores) for selected UK building societies over a fixed time period. It does not include internal customer data and is not official BSA analysis or financial advice.”

For each answer, dynamically:

* Show:

  * Snapshot end date.
  * Sources used.
  * Approximate number of reviews for the societies in scope.
* If sample sizes are low (e.g. < 100 for an aspect/society combination):

  * “Results for this segment are based on a limited number of reviews and should be treated as indicative only.”

### 5.3 Subtle guidance to encourage interesting questions

Without dropdowns or explicit filters, you can still guide behaviour.

Ideas:

* Rotating placeholder text in the input box:

  * “Ask: ‘What are customers saying about our digital banking recently?’”
  * “Ask: ‘How do we compare to Nationwide on mortgages since Covid?’”
  * “Ask: ‘What are our top three pain points in public reviews?’”

* On idle screen:

  * Show a short “scripted” example chat transcript as greyed-out bubbles, which disappears when the user starts typing.

* Small static text above the chat:

  * “Try asking about mortgages, savings, digital banking, branches or customer service.”

### 5.4 Avoiding hallucination and overclaiming

UX can reinforce guardrails:

* Wording:

  * Prefer formulations like “In these public reviews, many customers say …” rather than “Customers think …”.
* Evidence:

  * Always include snippets so users see why the answer was given.
* Explicit mention:

  * When the model has to generalise from patchy data (e.g. few reviews for a smaller society), instruct it to say:

    * “There are relatively few public reviews in this area, so it is difficult to draw firm conclusions.”

---

## 6) Risks, constraints and mitigations

### 6.1 Misinterpretation of sentiment or topics

Risks:

* LLM sentiment classification errors.
* Topic labelling may be inconsistent across time or societies.

Mitigations:

* Data preprocessing:

  * Use a consistent, fixed taxonomy for aspects and topics.
  * Run a calibration step:

    * Sample 100–200 reviews across societies.
    * Manually label sentiment and topics.
    * Compare with model output and tune prompts / thresholds.
* Prompting:

  * In the sentiment extraction prompt:

    * Explicitly define examples for each sentiment label.
    * Ask model to respect star rating as a strong but not absolute prior.
* Output formatting:

  * Avoid very granular or over-precise claims (e.g. “customer satisfaction has increased by exactly 12%” unless based on actual metrics).
  * Focus on direction and relative strength, not too many decimal places.

### 6.2 Hallucination or fabrication about societies

Risks:

* Answer-generation LLM invents facts not present in metrics or snippets (e.g. quoting wrong interest rates or mocking up product names).

Mitigations:

* Data and prompts:

  * Do not pass full product terms, rate tables or similar into the prompt.
  * In system prompt:

    * “Do not mention specific interest rates, product terms, or internal performance metrics. Focus only on themes present in reviews.”
  * Emphasise:

    * “If information is not present in the metrics or evidence, respond that it is not available from this dataset.”
* RAG design:

  * Only supply review snippets and aggregated metrics, not arbitrary web search results.
* Guardrails:

  * Post-process the LLM output:

    * Simple regex-based checks for digits that look like APRs or account numbers.
    * If suspicious, either redact or regenerate with stricter instructions.

### 6.3 Misleading comparisons due to uneven coverage

Risks:

* One society might have 17,000 reviews, another 50; direct comparison of percentages could be misleading. ([Trustpilot][3])

Mitigations:

* Data preprocessing:

  * Compute and store review_counts at the same level as sentiment metrics.
* Prompting:

  * Provide sample sizes alongside sentiment metrics in the metrics JSON.
  * Instruct the answer LLM:

    * “Always mention sample size and be cautious when one or more sample sizes are small.”
* Output formatting:

  * Use language like:

    * “Based on a small number of reviews, customers appear …”
    * “Compared with a much larger volume of reviews for Society X, Society Y has only limited public feedback, so comparisons are indicative.”

### 6.4 Legal and reputational considerations

Risks:

* Repeating defamatory content from reviews.
* Breaching platform terms.
* Creating the impression that BSA endorses specific societies’ performance.

Mitigations:

* Data selection:

  * Filter out reviews with explicit allegations of criminality or serious misconduct.
  * Paraphrase extreme statements rather than quoting verbatim.
* Prompting and tools:

  * In evidence snippet generation:

    * Ask LLM to summarise the gist of a review in neutral terms rather than copying long text.
* Output formatting:

  * Always frame statements as:

    * “In these public reviews…” rather than as objective facts.
  * Include a clear disclaimer that:

    * The demo is independent and illustrative.
    * It uses public reviews which may not be representative.
* Governance:

  * Have BSA / key member societies review a sample of outputs beforehand.
  * Prepare “safe examples” that you know look reasonable.

### 6.5 Data source constraints and fake reviews

Risks:

* Violating terms of sites like Trustpilot or app stores.
* Including manipulated reviews.

Mitigations:

* Data source approach:

  * Use only volume and content at reasonable scale; do not attempt full industrial scraping.
  * Where possible, respect any export or API mechanisms provided.
* Bias and manipulation:

  * Acknowledge explicitly:

    * “Online reviews can be influenced by campaigns or fake reviews; we rely on the review platforms’ own fraud detection.”
  * Optionally:

    * Filter out reviews with extremely generic text and repeated phrases, but this is hard to do robustly.
* Compliance:

  * Consider CMA guidance on online reviews and endorsements, and ICO guidance on analytics. ([ICO][4])

---

## 7) Delivery plan

Assuming a conference date in early May 2025 and that you start relatively soon, you can work through several phases.

### 7.1 Phase 0: Decisions and design (1–2 weeks)

Key tasks:

* Decide:

  * LLM provider (OpenAI vs Azure OpenAI).
  * Vector store (e.g. LanceDB vs Chroma).
  * SQL engine (SQLite vs DuckDB).
* Lock in:

  * MVP scope of societies and data sources.
  * Time window (e.g. 2020–2025).
  * Aspect and topic taxonomy.
* Produce:

  * This conceptual design refined into a technical design doc.
  * Initial prompt drafts for:

    * Sentiment/topic extraction.
    * parse_query.
    * answer_generation.

Early decisions that matter:

* Vector DB choice (affects implementation).
* LLM provider (affects function calling, token limits and cost).
* Scope of societies and data sources (affects ingestion workload).

### 7.2 Phase 1: Data ingestion and modelling MVP (2–3 weeks)

Goal: get a working dataset and simple analytic queries before any UI.

Tasks:

* Build the canonical building_society and alias tables.
* Implement ingestion for:

  * Trustpilot for 3–5 target societies as a pilot.
  * One app store (e.g. Google Play) for those societies’ apps.
* Implement cleaning and PII redaction.
* Implement simple sentiment classification:

  * Could start with a non-LLM model (e.g. a standard transformer classifier) for speed, then upgrade.
* Compute:

  * Basic summary metrics per society per month:

    * review_count.
    * avg_rating.
    * share of 1–2 star vs 4–5 star reviews.
* Store everything in SQLite.

Outcome:

* Even before RAG and fancy LLM interaction, you can answer:

  * “What is our average public rating over the last year vs peer average?”

### 7.3 Phase 2: LLM tooling and backend orchestration (2–3 weeks)

Goal: end-to-end pipeline from user question to structured intent, metrics retrieval, and LLM answer in a backend-only environment (no polished UI yet).

Tasks:

* Implement parse_query function:

  * Write and test function-calling prompts using a few dozen example queries.
  * Unit tests for tricky cases (aliases, follow-ups, ambiguous timeframes).
* Implement vector index:

  * Build embeddings for the pilot dataset.
  * Set up LanceDB/Chroma with metadata filters.
* Implement answer_generation prompt:

  * Template the metrics and snippets JSON passed to the LLM.
  * Test for hallucination and formatting adherence.
* Build FastAPI endpoints:

  * /chat that orchestrates the above.
  * Add in-memory session state.

Outcome:

* You can run the system from a terminal:

  * Type a question and get a structured, evidence-backed answer.

### 7.4 Phase 3: Front-end and UX (2–3 weeks)

Goal: a minimal but polished chat UI suitable for a conference.

Tasks:

* Build the SPA:

  * Chat bubble layout.
  * Input box.
  * “Reset” button.
  * Section showing evidence snippets and data coverage under each answer.
* Integrate with backend /chat endpoint.
* Implement idle-state example conversation / hints.
* Run usability tests with a small group (internal and possibly BSA contacts).

Outcome:

* The demo is visually presentable and usable.

### 7.5 Phase 4: Scale-up of data and hardening (2–4 weeks)

Goal: prepare the final dataset and stabilise the system for the conference.

Tasks:

* Scale data ingestion to full MVP scope:

  * 10–15 societies.
  * All selected sources.
* Run full sentiment/topic extraction and embeddings offline.
* Rebuild metrics and vector index.
* Optimise:

  * Pre-cache some per-society high-level summaries (e.g. for “How are we doing overall?”).
  * Monitor latency of LLM calls; tune prompts for efficiency.
* Add guardrails:

  * Safety language in prompts.
  * Defamation filters.
  * Checks for suspicious outputs (e.g. product rates).
* Rehearsals:

  * Dry-run at internal event or BSA visit to test robustness.

Outcome:

* Production-ready demo snapshot and application image for the conference laptop.

### 7.6 Smallest viable MVP that still feels impressive

If time compresses, an impressive MVP could include:

* 5 major building societies.
* Trustpilot only.
* Time window: last 3–4 years.
* Features:

  * Free-text questions with smart interpretation of society names and timeframes.
  * Overall sentiment and comparison answers with:

    * Avg rating.
    * % negative / positive.
  * 3–4 evidence snippets per answer.
* You can add aspects (mortgages vs savings vs digital vs branches) as the main stretch feature.

### 7.7 Stretch features if time allows

If you have time and appetite:

* Trend visualisation:

  * Small inline sparkline or textual description:

    * “Sentiment has improved slightly over the last 12 months.”
* Benchmarking views:

  * When user asks:

    * “Which societies have the highest public sentiment on digital banking?”
  * Return a ranked, caveated list.
* More sophisticated topic modelling:

  * Use BERTopic or LDA to cluster topics and display:

    * “Top three negative topics for mortgages for your society vs peers.”
* Geo segmentation (if data supports it):

  * “What are customers in the North of England saying about us?” based on location tags.

---

## 8) Targeted questions for refinement

Once you have considered the above, the following decisions will sharpen the design:

1. How many societies must be covered in the conference build for it to be politically acceptable:

   * All BSA members, or “major societies plus a representative sample of smaller ones”?

2. Do you have preferences or constraints on data sources:

   * For example, is relying heavily on Trustpilot acceptable, or should you deliberately diversify?

3. What is your tolerance for LLM and embeddings spend in the offline pipeline:

   * This affects how much enrichment you can do per review and which models you choose.

4. Do you want the demo to handle questions about banks as well as building societies:

   * Or is it strictly a “building societies only” experience?

5. What level of quantitative rigour is expected:

   * Are approximate, directional metrics sufficient, or do you want explicitly defined statistical methods (e.g. confidence intervals, weighted averages)?

With those clarified, we can tighten the taxonomy, prompts, and data scope into an implementable blueprint.

[1]: https://www.bsa.org.uk/events/upcoming-events/building-societies-annual-conference-2025?utm_source=chatgpt.com "Building Societies Annual Conference 2025 - bsa.org.uk"
[2]: https://www.bsa.org.uk/information/consumer-factsheets/general-information/list-of-uk-building-societies-and-associates?utm_source=chatgpt.com "List of UK members and associates"
[3]: https://uk.trustpilot.com/categories/building_society?utm_source=chatgpt.com "Best companies in Building Society on Trustpilot"
[4]: https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/artificial-intelligence/toolkit-for-organisations-considering-using-data-analytics/toolkit-for-organisations-considering-using-data-analytics-uk-gdpr/?utm_source=chatgpt.com "Toolkit for organisations considering using data analytics - UK GDPR"
[5]: https://www.gov.uk/government/publications/reviews-and-social-media-endorsements-guidance-for-businesses-and-brands?utm_source=chatgpt.com "Reviews and social media endorsements: guidance for businesses and ..."
[6]: https://www.advratings.com/uk/building-societies?utm_source=chatgpt.com "List of Building Societies in the UK (2025) - Top 10 Building Societies"
