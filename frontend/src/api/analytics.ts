/**
 * Analytics helper - fire-and-forget POST /api/events.
 *
 * Session id lives in localStorage so events across screens (Screensaver ->
 * Society -> Persona -> Chat -> Benchmark) are correlated under one key.
 */

import type { PersonaSpec } from "./types";

const API_BASE = (import.meta.env.VITE_API_BASE || "").replace(/\/$/, "");
const SESSION_KEY = "bsa_kiosk_session_id";

function apiUrl(path: string): string {
  if (API_BASE) return `${API_BASE}${path}`;
  return `/api${path}`;
}

function randomSessionId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `sess_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
}

export function getSessionId(): string {
  try {
    const existing = localStorage.getItem(SESSION_KEY);
    if (existing) return existing;
    const fresh = randomSessionId();
    localStorage.setItem(SESSION_KEY, fresh);
    return fresh;
  } catch {
    // Private browsing or localStorage blocked - use a process-level fallback.
    return randomSessionId();
  }
}

export function resetSessionId(): string {
  const fresh = randomSessionId();
  try {
    localStorage.setItem(SESSION_KEY, fresh);
  } catch {
    /* ignore */
  }
  return fresh;
}

export interface TrackOptions {
  societyId?: string;
  persona?: PersonaSpec | { id: string } | null;
  props?: Record<string, unknown>;
}

/**
 * Record a user-facing event. Never throws - analytics must not break the UI.
 */
export function trackEvent(type: string, opts: TrackOptions = {}): void {
  try {
    const body = JSON.stringify({
      event_type: type,
      session_id: getSessionId(),
      building_society_id: opts.societyId,
      persona_id: opts.persona?.id,
      props: opts.props,
    });

    // Prefer sendBeacon so events still land during page unload (e.g. close tab).
    if (typeof navigator !== "undefined" && "sendBeacon" in navigator) {
      const blob = new Blob([body], { type: "application/json" });
      const ok = navigator.sendBeacon(apiUrl("/events/"), blob);
      if (ok) return;
    }

    fetch(apiUrl("/events/"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      keepalive: true,
    }).catch(() => {
      /* swallow - best-effort */
    });
  } catch (err) {
    console.warn("trackEvent failed", err);
  }
}
