import type {
  ChatRequest,
  ChatResponse,
  ChatStreamMetadata,
  FeaturedReview,
  PersonaSpec,
  StreamHandlers,
} from "./types";

export type { ChatResponse };

/**
 * API base URL.
 *
 * - In local dev: empty string → requests go to `/api/...` which Vite's dev
 *   server proxies to `http://localhost:8000` (see `vite.config.ts`).
 * - In production: set `VITE_API_BASE` at build time to the deployed
 *   backend's origin (e.g. `https://bsa-api.up.railway.app`). The
 *   pathnames below stay the same; only the origin changes.
 */
const API_BASE = (import.meta.env.VITE_API_BASE || "").replace(/\/$/, "");

function apiUrl(path: string): string {
  // Local dev: "" + "/api/chat/stream"
  // Prod     : "https://bsa-api.example.com" + "/chat/stream" (no /api prefix in prod)
  if (API_BASE) return `${API_BASE}${path}`;
  return `/api${path}`;
}

export interface ChatOptions {
  sessionId?: string;
  societyId?: string;
  persona?: PersonaSpec;
}

export async function sendMessage(
  message: string,
  options: ChatOptions = {}
): Promise<ChatResponse> {
  const request: ChatRequest = {
    message,
    session_id: options.sessionId,
    society_id: options.societyId,
    persona: options.persona,
  };

  const response = await fetch(apiUrl("/chat/"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }
  return response.json();
}

/**
 * Stream a chat response via Server-Sent Events.
 * Emits: metadata → many token events → followups → done.
 * Returns an AbortController so callers can cancel in flight.
 */
export function streamMessage(
  message: string,
  handlers: StreamHandlers,
  options: ChatOptions = {}
): AbortController {
  const controller = new AbortController();

  (async () => {
    try {
      const response = await fetch(apiUrl("/chat/stream"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message,
          session_id: options.sessionId,
          society_id: options.societyId,
          persona: options.persona,
        }),
        signal: controller.signal,
      });

      if (!response.ok || !response.body) {
        throw new Error(`API error: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        let sep = buffer.indexOf("\n\n");
        while (sep !== -1) {
          const rawFrame = buffer.slice(0, sep);
          buffer = buffer.slice(sep + 2);
          parseFrame(rawFrame, handlers);
          sep = buffer.indexOf("\n\n");
        }
      }

      if (buffer.trim()) parseFrame(buffer, handlers);
      handlers.onDone();
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      handlers.onError(err instanceof Error ? err : new Error(String(err)));
    }
  })();

  return controller;
}

function parseFrame(frame: string, handlers: StreamHandlers) {
  let event = "message";
  const dataLines: string[] = [];
  for (const line of frame.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
  }
  if (!dataLines.length) return;

  const data = dataLines.join("\n");
  try {
    switch (event) {
      case "metadata": {
        const payload = JSON.parse(data) as ChatStreamMetadata;
        handlers.onMetadata(payload);
        break;
      }
      case "token": {
        const payload = JSON.parse(data) as { text: string };
        if (payload.text) handlers.onToken(payload.text);
        break;
      }
      case "followups": {
        const payload = JSON.parse(data) as { followups: string[] };
        handlers.onFollowups(payload.followups || []);
        break;
      }
      case "done":
        handlers.onDone();
        break;
    }
  } catch (err) {
    console.warn("SSE parse error", err, data);
  }
}

export async function fetchFeaturedReviews(limit = 10): Promise<FeaturedReview[]> {
  const response = await fetch(apiUrl(`/reviews/featured?limit=${limit}`));
  if (!response.ok) throw new Error(`API error: ${response.status}`);
  return response.json();
}

export async function fetchSocietyReviews(societyId: string, limit = 300) {
  const response = await fetch(apiUrl(`/reviews/by-society/${societyId}?limit=${limit}`));
  if (!response.ok) throw new Error(`API error: ${response.status}`);
  return response.json() as Promise<import("./types").SocietyReview[]>;
}

/**
 * Direct URL for the PDF download. Browser navigates here (or follows a
 * link with `download` attr) to trigger a file download, rather than a
 * window.print() flow.
 */
export function reportPdfUrl(societyId: string, region: string, sessionId?: string): string {
  const params = new URLSearchParams({ society_id: societyId });
  if (region) params.set("region", region);
  if (sessionId) params.set("session_id", sessionId);
  return apiUrl(`/report/pdf?${params.toString()}`);
}

export interface EmailReportResult {
  email_sent: boolean;
  error: string | null;
  pdf_base64: string | null;
  filename: string;
}

export async function emailReport(
  societyId: string,
  toEmail: string,
  region: string,
  sessionId?: string
): Promise<EmailReportResult> {
  const response = await fetch(apiUrl("/report/email"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      society_id: societyId,
      to_email: toEmail,
      region,
      session_id: sessionId,
    }),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`API error: ${response.status} ${text}`);
  }
  return response.json();
}

export async function resetSession(sessionId?: string): Promise<void> {
  const url = sessionId ? apiUrl(`/chat/reset?session_id=${sessionId}`) : apiUrl("/chat/reset");
  await fetch(url, { method: "POST" });
}

export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(apiUrl("/health"));
    return response.ok;
  } catch {
    return false;
  }
}
