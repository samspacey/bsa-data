// API Response Types matching backend schemas

export interface MetricSummary {
  building_society_id: string;
  building_society_name: string;
  time_bucket_start: string;
  time_bucket_end: string;
  aspect: string;
  review_count: number;
  avg_rating: number;
  avg_sentiment_score: number;
  pct_negative_reviews: number;
  pct_positive_reviews: number;
  net_sentiment_score: number;
  peer_group_avg_sentiment_score: number | null;
  peer_group_review_count: number | null;
}

export type SentimentLabel =
  | "very_negative"
  | "negative"
  | "neutral"
  | "positive"
  | "very_positive";

export interface ReviewSnippet {
  snippet_id: string;
  building_society_id: string;
  building_society_name: string;
  source: string;
  review_date: string;
  rating: number;
  sentiment_label: SentimentLabel;
  aspects: string[];
  topics: string[];
  snippet_text: string;
}

export interface PerSocietyReviewCount {
  building_society_id: string;
  building_society_name: string;
  review_count: number;
}

export interface DataCoverage {
  snapshot_end_date: string;
  sources: string[];
  total_reviews_considered: number;
  per_society_review_counts: PerSocietyReviewCount[];
}

export interface ChatResponse {
  session_id: string;
  answer: string;
  metrics: MetricSummary[];
  evidence_snippets: ReviewSnippet[];
  data_coverage: DataCoverage | null;
  assumptions: string[];
  limitations: string[];
}

export interface ChatRequest {
  message: string;
  session_id?: string;
}

// Re-export ChatResponse for components that import from client.ts
export type { ChatResponse as ChatResponseType };
