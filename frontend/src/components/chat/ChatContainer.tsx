import { useState, useRef, useEffect, useCallback } from "react";
import { ChatInput } from "./ChatInput";
import { MessageBubble } from "./MessageBubble";
import { streamMessage } from "../../api/client";
import type { ChatResponse } from "../../api/types";

interface Message {
  role: "user" | "assistant";
  content: string;
  response?: Partial<ChatResponse>;
  streaming?: boolean;
}

export function ChatContainer() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = useCallback(
    (content: string) => {
      if (isLoading) return;
      setError(null);

      // Append the user message and an initial empty assistant bubble
      // that we'll stream into.
      setMessages((prev) => [
        ...prev,
        { role: "user", content },
        { role: "assistant", content: "", streaming: true, response: {} },
      ]);
      setIsLoading(true);

      abortRef.current = streamMessage(
        content,
        {
          onMetadata: (meta) => {
            setSessionId(meta.session_id);
            setMessages((prev) => {
              const next = [...prev];
              const last = next[next.length - 1];
              if (last?.role === "assistant") {
                last.response = {
                  ...last.response,
                  session_id: meta.session_id,
                  metrics: meta.metrics,
                  evidence_snippets: meta.evidence_snippets,
                  data_coverage: meta.data_coverage ?? undefined,
                  assumptions: meta.assumptions,
                  limitations: meta.limitations,
                };
              }
              return next;
            });
          },
          onToken: (text) => {
            setMessages((prev) => {
              const next = [...prev];
              const last = next[next.length - 1];
              if (last?.role === "assistant") {
                last.content = (last.content || "") + text;
              }
              return next;
            });
          },
          onFollowups: (followups) => {
            setMessages((prev) => {
              const next = [...prev];
              const last = next[next.length - 1];
              if (last?.role === "assistant") {
                last.response = { ...last.response, followups };
              }
              return next;
            });
          },
          onDone: () => {
            setMessages((prev) => {
              const next = [...prev];
              const last = next[next.length - 1];
              if (last?.role === "assistant") last.streaming = false;
              return next;
            });
            setIsLoading(false);
            abortRef.current = null;
          },
          onError: (err) => {
            setError(err.message);
            setMessages((prev) => {
              const next = [...prev];
              const last = next[next.length - 1];
              if (last?.role === "assistant") {
                last.streaming = false;
                if (!last.content) {
                  last.content =
                    "Sorry, I encountered an error processing your request. Please try again.";
                }
              }
              return next;
            });
            setIsLoading(false);
            abortRef.current = null;
          },
        },
        { sessionId }
      );
    },
    [isLoading, sessionId]
  );

  const handleReset = () => {
    abortRef.current?.abort();
    setMessages([]);
    setSessionId(undefined);
    setError(null);
    setIsLoading(false);
  };

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-gray-900">
              BSA Voice of Customer
            </h1>
            <p className="text-sm text-gray-500">
              Analyse customer sentiment across UK building societies
            </p>
          </div>
          {messages.length > 0 && (
            <button
              onClick={handleReset}
              className="text-sm text-gray-500 hover:text-gray-700 px-3 py-1 rounded hover:bg-gray-100 transition-colors"
            >
              New conversation
            </button>
          )}
        </div>
      </header>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {messages.length === 0 ? (
          <WelcomeScreen onPick={handleSend} />
        ) : (
          <div className="space-y-4 max-w-4xl mx-auto">
            {messages.map((message, idx) => (
              <MessageBubble
                key={idx}
                message={message}
                onFollowupClick={handleSend}
              />
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {error && (
        <div className="bg-red-50 border-t border-red-200 px-6 py-3">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      <ChatInput onSend={handleSend} disabled={isLoading} />
    </div>
  );
}

function WelcomeScreen({ onPick }: { onPick: (text: string) => void }) {
  const suggestions: { text: string; icon: string }[] = [
    {
      text: "Compare Nationwide and Coventry sentiment across all sources",
      icon: "📊",
    },
    {
      text: "What are Reddit users saying about West Brom's mobile app?",
      icon: "📱",
    },
    {
      text: "How do Fairer Finance's editorial ratings compare to customer sentiment?",
      icon: "⭐",
    },
    {
      text: "Show me sentiment trends for Yorkshire Building Society",
      icon: "📈",
    },
  ];

  return (
    <div className="flex flex-col items-center justify-center h-full text-center max-w-2xl mx-auto">
      <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mb-6">
        <svg
          className="w-8 h-8 text-blue-600"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
          />
        </svg>
      </div>
      <h2 className="text-2xl font-semibold text-gray-900 mb-3">
        Ask about Building Society Sentiment
      </h2>
      <p className="text-gray-600 mb-8">
        Explore customer experiences across Trustpilot, Feefo, Smart Money
        People, app stores, Reddit, MoneySavingExpert, Google Reviews, Fairer
        Finance and Which?.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full">
        {suggestions.map((s) => (
          <SuggestionCard key={s.text} text={s.text} icon={s.icon} onClick={() => onPick(s.text)} />
        ))}
      </div>
    </div>
  );
}

function SuggestionCard({
  text,
  icon,
  onClick,
}: {
  text: string;
  icon: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="bg-white border border-gray-200 rounded-lg p-4 text-left hover:border-blue-300 hover:shadow-sm transition-all cursor-pointer"
    >
      <span className="text-2xl mb-2 block">{icon}</span>
      <p className="text-sm text-gray-700">{text}</p>
    </button>
  );
}
