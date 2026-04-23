import { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import type { ChatResponse, ReviewSnippet } from "../../api/types";
import { EvidenceCard } from "./EvidenceCard";
import { MetricsDisplay } from "./MetricsDisplay";
import { DataCoverageDisplay } from "./DataCoverageDisplay";
import { SourceCoverageChart } from "./SourceCoverageChart";
import { FollowUpChips } from "./FollowUpChips";
import { CitationMarker } from "./CitationMarker";

interface Message {
  role: "user" | "assistant";
  content: string;
  response?: Partial<ChatResponse>;
  streaming?: boolean;
}

interface MessageBubbleProps {
  message: Message;
  onFollowupClick?: (question: string) => void;
}

const CITATION_PATTERN = /\[\[s_(\d+)\]\]/g;

interface ContentPart {
  type: "text" | "citation";
  value: string;
  index?: number;
}

/**
 * Split markdown text at [[s_N]] citation markers so we can interleave
 * ReactMarkdown blocks with clickable CitationMarker components.
 */
function splitWithCitations(text: string): ContentPart[] {
  const parts: ContentPart[] = [];
  let lastIndex = 0;
  for (const match of text.matchAll(CITATION_PATTERN)) {
    const start = match.index ?? 0;
    if (start > lastIndex) {
      parts.push({ type: "text", value: text.slice(lastIndex, start) });
    }
    parts.push({ type: "citation", value: match[0], index: parseInt(match[1], 10) });
    lastIndex = start + match[0].length;
  }
  if (lastIndex < text.length) {
    parts.push({ type: "text", value: text.slice(lastIndex) });
  }
  return parts;
}

export function MessageBubble({ message, onFollowupClick }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const [highlightIdx, setHighlightIdx] = useState<number | null>(null);

  const snippets: ReviewSnippet[] = message.response?.evidence_snippets ?? [];
  const followups: string[] = message.response?.followups ?? [];

  const parts = useMemo(
    () => (isUser ? [] : splitWithCitations(message.content || "")),
    [message.content, isUser]
  );

  const handleHighlight = (idx: number) => {
    setHighlightIdx(idx);
    window.setTimeout(() => setHighlightIdx(null), 1600);
  };

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] ${
          isUser
            ? "bg-blue-600 text-white rounded-2xl rounded-br-md px-4 py-3"
            : "bg-white border border-gray-200 rounded-2xl rounded-bl-md px-4 py-3 shadow-sm"
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.content}</p>
        ) : (
          <div className="prose prose-sm prose-gray max-w-none">
            {parts.length === 0 && message.streaming ? (
              <StreamingPlaceholder />
            ) : (
              parts.map((part, i) =>
                part.type === "citation" ? (
                  <CitationMarker
                    key={`c-${i}`}
                    index={part.index!}
                    snippet={snippets[part.index!]}
                    onHighlight={handleHighlight}
                  />
                ) : (
                  <ReactMarkdown key={`t-${i}`}>{part.value}</ReactMarkdown>
                )
              )
            )}
            {message.streaming && parts.length > 0 && <StreamingCursor />}
          </div>
        )}

        {!isUser && message.response && (
          <div className="mt-4 space-y-4">
            {(message.response.metrics?.length ?? 0) > 0 && (
              <MetricsDisplay metrics={message.response.metrics!} />
            )}

            {snippets.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-2">
                  Supporting Evidence
                </h4>
                <div className="space-y-2">
                  {snippets.slice(0, 5).map((snippet, idx) => (
                    <EvidenceCard
                      key={idx}
                      snippet={snippet}
                      index={idx}
                      highlighted={highlightIdx === idx}
                    />
                  ))}
                </div>
              </div>
            )}

            {message.response.data_coverage && (
              <>
                <SourceCoverageChart coverage={message.response.data_coverage} />
                <DataCoverageDisplay coverage={message.response.data_coverage} />
              </>
            )}

            {((message.response.assumptions?.length ?? 0) > 0 ||
              (message.response.limitations?.length ?? 0) > 0) && (
              <div className="text-xs text-gray-500 border-t border-gray-100 pt-3 mt-3">
                {(message.response.assumptions?.length ?? 0) > 0 && (
                  <div className="mb-2">
                    <span className="font-medium">Assumptions: </span>
                    {message.response.assumptions!.join("; ")}
                  </div>
                )}
                {(message.response.limitations?.length ?? 0) > 0 && (
                  <div>
                    <span className="font-medium">Limitations: </span>
                    {message.response.limitations!.join("; ")}
                  </div>
                )}
              </div>
            )}

            {followups.length > 0 && onFollowupClick && (
              <FollowUpChips followups={followups} onPick={onFollowupClick} />
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function StreamingCursor() {
  return (
    <span
      className="inline-block w-[3px] h-4 align-middle bg-blue-500 ml-0.5 animate-pulse"
      aria-hidden="true"
    />
  );
}

function StreamingPlaceholder() {
  return (
    <div className="flex items-center gap-2 text-gray-500">
      <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
        <circle
          className="opacity-25"
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="4"
          fill="none"
        />
        <path
          className="opacity-75"
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        />
      </svg>
      <span className="text-sm">Searching across sources…</span>
    </div>
  );
}
