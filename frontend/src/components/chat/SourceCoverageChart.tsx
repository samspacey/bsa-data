import type { DataCoverage, SourceCount } from "../../api/types";

interface SourceCoverageChartProps {
  coverage: DataCoverage;
}

// Colour palette: reviews in blue, mentions in amber so the two classes read
// differently in the chart even when mixed.
const REVIEW_SOURCES = new Set([
  "trustpilot",
  "app_store",
  "play_store",
  "smartmoneypeople",
  "feefo",
  "google",
]);

function isReviewSource(source_id: string): boolean {
  return REVIEW_SOURCES.has(source_id);
}

function barColour(source_id: string): string {
  if (isReviewSource(source_id)) return "bg-blue-500";
  return "bg-amber-500";
}

function labelColour(source_id: string): string {
  if (isReviewSource(source_id)) return "text-blue-700";
  return "text-amber-700";
}

export function SourceCoverageChart({ coverage }: SourceCoverageChartProps) {
  const sources: SourceCount[] = coverage.per_source_counts ?? [];
  if (sources.length === 0) return null;

  const max = Math.max(...sources.map((s) => s.count), 1);
  const total = sources.reduce((acc, s) => acc + s.count, 0);

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-3">
      <div className="flex items-baseline justify-between mb-2">
        <h4 className="text-xs font-medium text-gray-600 uppercase tracking-wide">
          Source Coverage
        </h4>
        <span className="text-xs text-gray-500">
          {total.toLocaleString()} items across {sources.length} source
          {sources.length === 1 ? "" : "s"}
        </span>
      </div>

      <div className="space-y-1.5">
        {sources.map((s) => {
          const pct = Math.max(4, Math.round((s.count / max) * 100));
          return (
            <div key={s.source_id} className="flex items-center gap-2 text-xs">
              <span
                className={`w-32 shrink-0 font-medium ${labelColour(s.source_id)}`}
                title={s.source_name}
              >
                {s.source_name}
              </span>
              <div className="flex-1 bg-gray-100 rounded-full overflow-hidden h-3">
                <div
                  className={`h-full rounded-full ${barColour(s.source_id)}`}
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="w-12 text-right text-gray-600 tabular-nums">
                {s.count.toLocaleString()}
              </span>
            </div>
          );
        })}
      </div>

      {coverage.includes_mentions && (
        <p className="text-[11px] text-gray-500 mt-2">
          <span className="inline-block w-2 h-2 rounded-full bg-amber-500 mr-1 align-middle" />
          Forum posts and editorial ratings are counted separately and do not
          contribute to average customer-rating metrics.
        </p>
      )}
    </div>
  );
}
