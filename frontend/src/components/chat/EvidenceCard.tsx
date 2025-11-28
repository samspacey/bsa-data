import type { ReviewSnippet, SentimentLabel } from "../../api/types";

interface EvidenceCardProps {
  snippet: ReviewSnippet;
}

function StarRating({ rating }: { rating: number }) {
  return (
    <div className="flex gap-0.5">
      {[1, 2, 3, 4, 5].map((star) => (
        <svg
          key={star}
          className={`w-3 h-3 ${
            star <= rating ? "text-yellow-400" : "text-gray-300"
          }`}
          fill="currentColor"
          viewBox="0 0 20 20"
        >
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
        </svg>
      ))}
    </div>
  );
}

function SentimentBadge({ sentiment }: { sentiment: SentimentLabel }) {
  const config: Record<SentimentLabel, { bg: string; text: string; label: string }> = {
    very_positive: { bg: "bg-green-100", text: "text-green-800", label: "Very Positive" },
    positive: { bg: "bg-green-50", text: "text-green-700", label: "Positive" },
    neutral: { bg: "bg-gray-100", text: "text-gray-700", label: "Neutral" },
    negative: { bg: "bg-red-50", text: "text-red-700", label: "Negative" },
    very_negative: { bg: "bg-red-100", text: "text-red-800", label: "Very Negative" },
  };

  const { bg, text, label } = config[sentiment] || config.neutral;

  return (
    <span className={`text-xs px-2 py-0.5 rounded-full ${bg} ${text}`}>
      {label}
    </span>
  );
}

export function EvidenceCard({ snippet }: EvidenceCardProps) {
  return (
    <div className="bg-gray-50 rounded-lg p-3 text-sm">
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="font-medium text-gray-700">
            {snippet.building_society_name}
          </span>
          <StarRating rating={snippet.rating} />
        </div>
        <div className="flex items-center gap-2">
          <SentimentBadge sentiment={snippet.sentiment_label} />
          <span className="text-xs text-gray-500">{snippet.source}</span>
        </div>
      </div>

      {/* Snippet text */}
      <p className="text-gray-600 leading-relaxed">
        {snippet.snippet_text}
      </p>

      {/* Topics */}
      {snippet.topics.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {snippet.topics.map((topic, idx) => (
            <span
              key={idx}
              className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded"
            >
              {topic}
            </span>
          ))}
        </div>
      )}

      {/* Date */}
      <div className="text-xs text-gray-400 mt-2">
        {new Date(snippet.review_date).toLocaleDateString("en-GB", {
          day: "numeric",
          month: "short",
          year: "numeric",
        })}
      </div>
    </div>
  );
}
