import { useState, useRef, useEffect } from "react";
import { ChatInput } from "./ChatInput";
import { MessageBubble } from "./MessageBubble";
import { sendMessage } from "../../api/client";
import type { ChatResponse } from "../../api/types";

interface Message {
  role: "user" | "assistant";
  content: string;
  response?: ChatResponse;
}

export function ChatContainer() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (content: string) => {
    // Add user message
    setMessages((prev) => [...prev, { role: "user", content }]);
    setIsLoading(true);
    setError(null);

    try {
      const response = await sendMessage(content, sessionId);
      setSessionId(response.session_id);

      // Add assistant message
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: response.answer,
          response,
        },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      // Add error message
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, I encountered an error processing your request. Please try again.",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setMessages([]);
    setSessionId(undefined);
    setError(null);
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
              Analyze customer sentiment across UK building societies
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
          <WelcomeScreen />
        ) : (
          <div className="space-y-4 max-w-4xl mx-auto">
            {messages.map((message, idx) => (
              <MessageBubble key={idx} message={message} />
            ))}
            {isLoading && <LoadingIndicator />}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Error banner */}
      {error && (
        <div className="bg-red-50 border-t border-red-200 px-6 py-3">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      {/* Input area */}
      <ChatInput onSend={handleSend} disabled={isLoading} />
    </div>
  );
}

function WelcomeScreen() {
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
        Get insights into customer experiences, compare societies, and explore
        trends across the UK building society sector.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full">
        <SuggestionCard
          text="How is Nationwide's customer sentiment compared to Coventry?"
          icon="📊"
        />
        <SuggestionCard
          text="What are the main complaints about mobile banking apps?"
          icon="📱"
        />
        <SuggestionCard
          text="Which building society has the best customer service ratings?"
          icon="⭐"
        />
        <SuggestionCard
          text="Show me sentiment trends for Yorkshire Building Society"
          icon="📈"
        />
      </div>
    </div>
  );
}

function SuggestionCard({ text, icon }: { text: string; icon: string }) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 text-left hover:border-blue-300 hover:shadow-sm transition-all cursor-pointer">
      <span className="text-2xl mb-2 block">{icon}</span>
      <p className="text-sm text-gray-700">{text}</p>
    </div>
  );
}

function LoadingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-md px-4 py-3 shadow-sm">
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
          <span className="text-sm">Analyzing customer sentiment...</span>
        </div>
      </div>
    </div>
  );
}
