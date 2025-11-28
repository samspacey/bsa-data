import type { ChatRequest, ChatResponse } from "./types";

// Re-export types for convenience
export type { ChatResponse };

const API_BASE = "/api";

export async function sendMessage(
  message: string,
  sessionId?: string
): Promise<ChatResponse> {
  const request: ChatRequest = {
    message,
    session_id: sessionId,
  };

  const response = await fetch(`${API_BASE}/chat/`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}

export async function resetSession(sessionId?: string): Promise<void> {
  const url = sessionId
    ? `${API_BASE}/chat/reset?session_id=${sessionId}`
    : `${API_BASE}/chat/reset`;

  await fetch(url, { method: "POST" });
}

export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/health`);
    return response.ok;
  } catch {
    return false;
  }
}
