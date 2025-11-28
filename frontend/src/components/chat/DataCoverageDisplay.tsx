import type { DataCoverage } from "../../api/types";

interface DataCoverageDisplayProps {
  coverage: DataCoverage;
}

export function DataCoverageDisplay({ coverage }: DataCoverageDisplayProps) {
  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("en-GB", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  };

  const societiesCount = coverage.per_society_review_counts.length;
  const sourcesCount = coverage.sources.length;

  return (
    <div className="bg-gray-50 rounded-lg p-3">
      <h4 className="text-xs font-medium text-gray-600 uppercase tracking-wide mb-2">
        Data Coverage
      </h4>

      <div className="grid grid-cols-3 gap-3 text-center">
        <div>
          <p className="text-lg font-semibold text-gray-900">
            {coverage.total_reviews_considered.toLocaleString()}
          </p>
          <p className="text-xs text-gray-500">Reviews</p>
        </div>

        <div>
          <p className="text-lg font-semibold text-gray-900">
            {societiesCount}
          </p>
          <p className="text-xs text-gray-500">Societies</p>
        </div>

        <div>
          <p className="text-lg font-semibold text-gray-900">
            {sourcesCount}
          </p>
          <p className="text-xs text-gray-500">Sources</p>
        </div>
      </div>

      {/* Sources list */}
      {coverage.sources.length > 0 && (
        <div className="mt-3 pt-2 border-t border-gray-200">
          <p className="text-xs text-gray-500">
            Sources: {coverage.sources.join(", ")}
          </p>
        </div>
      )}

      {/* Snapshot date */}
      <p className="text-xs text-gray-400 mt-2 text-center">
        Data as of {formatDate(coverage.snapshot_end_date)}
      </p>
    </div>
  );
}
