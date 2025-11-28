import type { ChatResponse } from "../../api/types";
import { EvidenceCard } from "./EvidenceCard";
import { MetricsDisplay } from "./MetricsDisplay";
import { DataCoverageDisplay } from "./DataCoverageDisplay";

interface Message {
  role: "user" | "assistant";
  content: string;
  response?: ChatResponse;
}

interface MessageBubbleProps {
  message: Message;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] ${
          isUser
            ? "bg-blue-600 text-white rounded-2xl rounded-br-md px-4 py-3"
            : "bg-white border border-gray-200 rounded-2xl rounded-bl-md px-4 py-3 shadow-sm"
        }`}
      >
        {/* Main message text */}
        <p className={`whitespace-pre-wrap ${isUser ? "" : "text-gray-800"}`}>
          {message.content}
        </p>

        {/* Assistant response extras */}
        {!isUser && message.response && (
          <div className="mt-4 space-y-4">
            {/* Metrics summary */}
            {message.response.metrics.length > 0 && (
              <MetricsDisplay metrics={message.response.metrics} />
            )}

            {/* Evidence snippets */}
            {message.response.evidence_snippets.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-gray-700 mb-2">
                  Supporting Evidence
                </h4>
                <div className="space-y-2">
                  {message.response.evidence_snippets.slice(0, 5).map((snippet, idx) => (
                    <EvidenceCard key={idx} snippet={snippet} />
                  ))}
                </div>
              </div>
            )}

            {/* Data coverage */}
            {message.response.data_coverage && (
              <DataCoverageDisplay coverage={message.response.data_coverage} />
            )}

            {/* Assumptions and limitations */}
            {(message.response.assumptions.length > 0 ||
              message.response.limitations.length > 0) && (
              <div className="text-xs text-gray-500 border-t border-gray-100 pt-3 mt-3">
                {message.response.assumptions.length > 0 && (
                  <div className="mb-2">
                    <span className="font-medium">Assumptions: </span>
                    {message.response.assumptions.join("; ")}
                  </div>
                )}
                {message.response.limitations.length > 0 && (
                  <div>
                    <span className="font-medium">Limitations: </span>
                    {message.response.limitations.join("; ")}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
