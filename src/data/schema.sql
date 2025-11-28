-- BSA Voice of Customer Database Schema
-- Reference schema (actual tables created via SQLAlchemy ORM)

-- Building society canonical information
CREATE TABLE IF NOT EXISTS building_society (
    id TEXT PRIMARY KEY,
    canonical_name TEXT NOT NULL,
    bsa_name TEXT NOT NULL,
    legal_entity_name TEXT,
    size_bucket TEXT NOT NULL CHECK (size_bucket IN ('mega', 'large', 'regional')),
    website_domain TEXT NOT NULL,
    trustpilot_url TEXT,
    app_store_id TEXT,
    play_store_id TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Aliases and alternative names
CREATE TABLE IF NOT EXISTS building_society_alias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    building_society_id TEXT NOT NULL REFERENCES building_society(id),
    alias_text TEXT NOT NULL,
    alias_type TEXT NOT NULL CHECK (alias_type IN ('canonical', 'short_name', 'trading_name', 'acronym', 'misspelling', 'legacy_brand')),
    confidence_score REAL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Data source platforms
CREATE TABLE IF NOT EXISTS data_source (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    source_type TEXT NOT NULL CHECK (source_type IN ('review_platform', 'app_store', 'maps')),
    url_pattern TEXT,
    terms_version_note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Public customer reviews
CREATE TABLE IF NOT EXISTS public_review (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL REFERENCES data_source(id),
    source_review_id TEXT NOT NULL,
    building_society_id TEXT NOT NULL REFERENCES building_society(id),

    -- Review content
    review_date DATE NOT NULL,
    rating_raw INTEGER NOT NULL CHECK (rating_raw BETWEEN 1 AND 5),
    rating_normalised REAL NOT NULL,
    title_text TEXT,
    body_text_raw TEXT NOT NULL,
    body_text_clean TEXT,

    -- Metadata
    reviewer_language TEXT,
    channel TEXT CHECK (channel IN ('branch', 'online', 'mobile_app', 'call_centre', 'other', 'unknown')),
    product TEXT CHECK (product IN ('mortgage', 'savings', 'current_account', 'ISA', 'other', 'unknown')),
    location_text TEXT,
    app_version TEXT,

    -- Flags
    is_flagged_for_exclusion INTEGER DEFAULT 0,
    exclusion_reason TEXT,

    -- Timestamps
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cleaned_at TIMESTAMP,
    enriched_at TIMESTAMP,

    -- Unique constraint to prevent duplicates
    UNIQUE (source_id, source_review_id)
);

-- Sentiment analysis results
CREATE TABLE IF NOT EXISTS sentiment_aspect (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id INTEGER NOT NULL REFERENCES public_review(id),

    -- Overall sentiment
    overall_sentiment_label TEXT NOT NULL CHECK (overall_sentiment_label IN ('very_negative', 'negative', 'neutral', 'positive', 'very_positive')),
    overall_sentiment_score REAL NOT NULL CHECK (overall_sentiment_score BETWEEN -1 AND 1),

    -- Aspect-level
    aspect TEXT NOT NULL,
    aspect_sentiment_label TEXT CHECK (aspect_sentiment_label IN ('very_negative', 'negative', 'neutral', 'positive', 'very_positive')),
    aspect_sentiment_score REAL CHECK (aspect_sentiment_score BETWEEN -1 AND 1),

    -- Emotion
    emotion TEXT CHECK (emotion IN ('angry', 'frustrated', 'relieved', 'delighted', 'neutral')),

    -- Model info
    model_version TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Topics extracted from reviews
CREATE TABLE IF NOT EXISTS topic_tag (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id INTEGER NOT NULL REFERENCES public_review(id),

    -- Topic details
    topic_key TEXT NOT NULL,
    topic_group TEXT NOT NULL,
    topic_label TEXT,

    -- Confidence
    relevance_score REAL DEFAULT 1.0 CHECK (relevance_score BETWEEN 0 AND 1),

    -- Model info
    model_version TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Aggregated metrics
CREATE TABLE IF NOT EXISTS summary_metric (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    building_society_id TEXT NOT NULL REFERENCES building_society(id),

    -- Dimensions
    time_bucket_start DATE NOT NULL,
    time_bucket_end DATE NOT NULL,
    aspect TEXT NOT NULL,
    product TEXT,
    channel TEXT,

    -- Metrics
    review_count INTEGER NOT NULL,
    avg_rating REAL NOT NULL,
    avg_sentiment_score REAL NOT NULL,
    pct_negative_reviews REAL NOT NULL CHECK (pct_negative_reviews BETWEEN 0 AND 1),
    pct_positive_reviews REAL NOT NULL CHECK (pct_positive_reviews BETWEEN 0 AND 1),
    net_sentiment_score REAL NOT NULL,

    -- Peer comparison
    peer_group_avg_sentiment_score REAL,
    peer_group_review_count INTEGER,

    -- Version
    metric_version TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Unique constraint
    UNIQUE (building_society_id, time_bucket_start, time_bucket_end, aspect, product, channel)
);

-- Embedding documents (vector stored in LanceDB)
CREATE TABLE IF NOT EXISTS embedding_document (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_type TEXT NOT NULL CHECK (doc_type IN ('review', 'synthetic_summary', 'topic_cluster_description')),
    source_review_id INTEGER REFERENCES public_review(id),
    building_society_id TEXT NOT NULL REFERENCES building_society(id),

    -- Context
    review_date DATE,
    aspects TEXT, -- JSON array
    topics TEXT, -- JSON array
    sentiment_label TEXT,

    -- Text content
    text_for_embedding TEXT NOT NULL,

    -- Vector DB reference
    vector_id TEXT,

    -- Version
    embedding_model TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_review_society ON public_review(building_society_id);
CREATE INDEX IF NOT EXISTS idx_review_date ON public_review(review_date);
CREATE INDEX IF NOT EXISTS idx_review_source ON public_review(source_id);
CREATE INDEX IF NOT EXISTS idx_sentiment_review ON sentiment_aspect(review_id);
CREATE INDEX IF NOT EXISTS idx_topic_review ON topic_tag(review_id);
CREATE INDEX IF NOT EXISTS idx_metric_society ON summary_metric(building_society_id);
CREATE INDEX IF NOT EXISTS idx_metric_time ON summary_metric(time_bucket_start, time_bucket_end);
CREATE INDEX IF NOT EXISTS idx_alias_society ON building_society_alias(building_society_id);
CREATE INDEX IF NOT EXISTS idx_alias_text ON building_society_alias(alias_text COLLATE NOCASE);
