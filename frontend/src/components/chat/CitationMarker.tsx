import { useState } from "react";
import type { ReviewSnippet } from "../../api/types";

interface CitationMarkerProps {
  index: number;
  snippet?: ReviewSnippet;
  onHighlight?: (index: number) => void;
}

/**
 * Inline citation `[N]` that scrolls to the matching evidence card when
 * clicked. Shows the source + society on hover as a lightweight tooltip.
 */
export function CitationMarker({
  index,
  snippet,
  onHighlight,
}: CitationMarkerProps) {
  const [hovering, setHovering] = useState(false);

  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault();
    onHighlight?.(index);
    const el = document.getElementById(`snippet-${index}`);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  };

  return (
    <span
      className="relative inline-block"
      onMouseEnter={() => setHovering(true)}
      onMouseLeave={() => setHovering(false)}
    >
      <a
        href={`#snippet-${index}`}
        onClick={handleClick}
        className="inline-flex items-center justify-center align-super text-[10px] font-medium text-blue-600 bg-blue-50 border border-blue-200 rounded-full px-1.5 min-w-[18px] h-[18px] leading-none mx-0.5 hover:bg-blue-100 transition-colors no-underline"
      >
        {index}
      </a>
      {hovering && snippet && (
        <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 whitespace-nowrap z-10 px-2 py-1 text-xs bg-gray-900 text-white rounded shadow-lg">
          {snippet.source} · {snippet.building_society_name}
        </span>
      )}
    </span>
  );
}
