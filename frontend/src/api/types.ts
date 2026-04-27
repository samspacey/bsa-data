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
  source_url?: string | null;
}

export interface PerSocietyReviewCount {
  building_society_id: string;
  building_society_name: string;
  review_count: number;
}

export interface SourceCount {
  source_id: string;
  source_name: string;
  count: number;
}

export interface DataCoverage {
  snapshot_end_date: string;
  sources: string[];
  total_reviews_considered: number;
  per_society_review_counts: PerSocietyReviewCount[];
  per_source_counts: SourceCount[];
  includes_mentions: boolean;
  mentions_considered: number;
}

export interface ChatResponse {
  session_id: string;
  answer: string;
  metrics: MetricSummary[];
  evidence_snippets: ReviewSnippet[];
  data_coverage: DataCoverage | null;
  assumptions: string[];
  limitations: string[];
  followups: string[];
}

export interface ChatStreamMetadata {
  session_id: string;
  metrics: MetricSummary[];
  evidence_snippets: ReviewSnippet[];
  data_coverage: DataCoverage | null;
  assumptions: string[];
  limitations: string[];
}

/**
 * Callbacks for consuming a streamed chat response.
 *
 * Event order: metadata → many tokens → followups → done.
 * Any unhandled error is delivered to onError.
 */
export interface StreamHandlers {
  onMetadata: (meta: ChatStreamMetadata) => void;
  onToken: (text: string) => void;
  onFollowups: (followups: string[]) => void;
  onDone: () => void;
  onError: (err: Error) => void;
}

export interface PersonaSpec {
  id: string;
  name: string;
  first_name: string;
  age: string;
  detail: string;
  concerns: string[];
}

export interface ChatRequest {
  message: string;
  session_id?: string;
  society_id?: string;
  persona?: PersonaSpec;
}

export interface FeaturedReview {
  id: number;
  quote: string;
  rating: number;
  review_date: string;
  society_id: string;
  society_name: string;
  source_id: string;
}

export interface SocietyReview {
  id: number;
  snippet_id: string;
  body: string;
  rating: number;
  review_date: string;
  society_id: string;
  society_name: string;
  source: string;
  source_id: string;
  sentiment_label: SentimentLabel;
  source_url?: string | null;
}

export interface BenchmarkScore {
  factor: string;
  score: number;
  avg: number;
  rank: number;
  reviews: number;
  status: "above" | "near" | "below";
}

export interface BenchmarkScoresResponse {
  society_id: string;
  society_name: string;
  scores: BenchmarkScore[];
  of_total: number;
}

// Re-export ChatResponse for components that import from client.ts
export type { ChatResponse as ChatResponseType };
