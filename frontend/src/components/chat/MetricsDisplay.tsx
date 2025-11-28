import type { MetricSummary } from "../../api/types";

interface MetricsDisplayProps {
  metrics: MetricSummary[];
}

function MetricCard({ metric }: { metric: MetricSummary }) {
  const formatPercentage = (value: number) => `${(value * 100).toFixed(0)}%`;
  const formatRating = (value: number) => value.toFixed(2);
  const formatSentiment = (value: number) => value.toFixed(2);

  // Determine if sentiment is positive or negative for styling
  const sentimentColor = metric.net_sentiment_score >= 0
    ? "text-green-600"
    : "text-red-600";

  return (
    <div className="bg-blue-50 rounded-lg p-3">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-xs text-blue-600 font-medium uppercase tracking-wide">
            {metric.building_society_name}
          </p>
          <p className="text-xs text-gray-500 mt-0.5">
            {metric.aspect === "overall" ? "Overall" : metric.aspect}
          </p>
        </div>
        <p className="text-xs text-gray-400">
          n={metric.review_count.toLocaleString()}
        </p>
      </div>

      <div className="grid grid-cols-3 gap-2 mt-3">
        <div>
          <p className="text-lg font-semibold text-gray-900">
            {formatRating(metric.avg_rating)}
          </p>
          <p className="text-xs text-gray-500">Avg Rating</p>
        </div>
        <div>
          <p className={`text-lg font-semibold ${sentimentColor}`}>
            {formatSentiment(metric.net_sentiment_score)}
          </p>
          <p className="text-xs text-gray-500">Net Sentiment</p>
        </div>
        <div>
          <p className="text-lg font-semibold text-green-600">
            {formatPercentage(metric.pct_positive_reviews)}
          </p>
          <p className="text-xs text-gray-500">Positive</p>
        </div>
      </div>

      {metric.peer_group_avg_sentiment_score !== null && (
        <div className="mt-2 pt-2 border-t border-blue-100">
          <p className="text-xs text-gray-500">
            Peer avg: {formatSentiment(metric.peer_group_avg_sentiment_score)}
            {metric.peer_group_review_count &&
              ` (${metric.peer_group_review_count.toLocaleString()} reviews)`}
          </p>
        </div>
      )}
    </div>
  );
}

export function MetricsDisplay({ metrics }: MetricsDisplayProps) {
  if (metrics.length === 0) return null;

  // Group metrics by building society
  const grouped = metrics.reduce((acc, metric) => {
    const key = metric.building_society_name;
    if (!acc[key]) acc[key] = [];
    acc[key].push(metric);
    return acc;
  }, {} as Record<string, MetricSummary[]>);

  const societyCount = Object.keys(grouped).length;

  return (
    <div>
      <h4 className="text-sm font-medium text-gray-700 mb-2">
        Key Metrics {societyCount > 1 && `(${societyCount} societies)`}
      </h4>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
        {metrics.slice(0, 6).map((metric, idx) => (
          <MetricCard key={idx} metric={metric} />
        ))}
      </div>
    </div>
  );
}
