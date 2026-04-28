import { useEffect, useMemo, useRef, useState } from "react";
import { ProductMark } from "../components/brand/WoodhurstMark";
import { SocietyLogo } from "../components/brand/SocietyLogo";
import { Monogram } from "../components/brand/Monogram";
import { Icon } from "../components/brand/Icons";
import type { Society } from "../data/societies";
import type { Archetype } from "../data/archetypes";
import { suggestedPrompts } from "../data/reviews";
import { fetchSocietyReviews, streamMessage } from "../api/client";
import type { ReviewSnippet, SocietyReview } from "../api/types";

interface Props {
  society: Society;
  persona: Archetype;
  onBack: () => void;
  onOpenBenchmark: () => void;
}

interface LiveMessage {
  role: "user" | "assistant";
  text: string;
  /**
   * Snapshot of the evidence snippets that were retrieved alongside this
   * assistant message. Citation markers `[[s_N]]` in `text` index into this
   * array - NOT the global `snippets` state, which can change per turn.
   */
  snippets?: ReviewSnippet[];
  streaming?: boolean;
}

const CITATION_PATTERN = /\[\[s_(\d+)\]\]/g;

interface TextPart {
  kind: "text";
  value: string;
}
interface CitePart {
  kind: "cite";
  index: number;
}
type MessagePart = TextPart | CitePart;

function parseMessage(text: string): MessagePart[] {
  const parts: MessagePart[] = [];
  let lastIndex = 0;
  for (const match of text.matchAll(CITATION_PATTERN)) {
    const start = match.index ?? 0;
    if (start > lastIndex) {
      parts.push({ kind: "text", value: text.slice(lastIndex, start) });
    }
    parts.push({ kind: "cite", index: parseInt(match[1], 10) });
    lastIndex = start + match[0].length;
  }
  if (lastIndex < text.length) {
    parts.push({ kind: "text", value: text.slice(lastIndex) });
  }
  return parts;
}

function sentimentOf(snippet: ReviewSnippet | SocietyReview): "positive" | "negative" | "neutral" {
  if (snippet.sentiment_label === "very_positive" || snippet.sentiment_label === "positive") return "positive";
  if (snippet.sentiment_label === "very_negative" || snippet.sentiment_label === "negative") return "negative";
  return "neutral";
}

function shortSourceName(sourceIdOrName: string): string {
  const map: Record<string, string> = {
    trustpilot: "Trustpilot",
    app_store: "App Store",
    play_store: "Play Store",
    smartmoneypeople: "Smart Money People",
    feefo: "Feefo",
    reddit: "Reddit",
    mse: "MSE",
    google: "Google",
    fairer_finance: "Fairer Finance",
    which: "Which?",
  };
  return map[sourceIdOrName.toLowerCase()] || sourceIdOrName;
}

function formatReviewDate(dateStr: string): string {
  try {
    return new Date(dateStr).toLocaleDateString("en-GB", { month: "short", year: "numeric" });
  } catch {
    return dateStr;
  }
}

function openingLine(persona: Archetype, society: Society): string {
  const societyShort = society.short;
  switch (persona.id) {
    case "loyalist":
      return `Oh, hello. Thirty-odd years I've been with ${societyShort}. Do sit down - what did you want to talk about?`;
    case "digital":
      return `Hey. Yeah, I signed up with ${societyShort} about a year ago. Happy to give you the honest read.`;
    case "family":
      return `Hi - got ten minutes. We've got the mortgage and the kids' savings with ${societyShort}, so fire away.`;
    case "business":
      return `Good to meet you. I've banked with ${societyShort} - personal and business - for a good while. What did you want to know?`;
    default:
      return `Hello. I'm a member of ${societyShort}. Happy to answer what I can.`;
  }
}


export function ChatInterface({ society, persona, onBack, onOpenBenchmark }: Props) {
  const suggested: string[] = suggestedPrompts[persona.id] || suggestedPrompts.loyalist;

  const [messages, setMessages] = useState<LiveMessage[]>(() => [
    { role: "assistant", text: openingLine(persona, society) },
  ]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [highlighted, setHighlighted] = useState<number | null>(null);
  const [sessionId, setSessionId] = useState<string | undefined>();
  // Total reviews available for this society (populated from the backend's
  // data_coverage on the first streamed metadata event). Separate from the
  // 10 snippets returned per turn - surfaced in the header so the user
  // sees the full corpus size, not the retrieval cap.
  const [totalReviewsForSociety, setTotalReviewsForSociety] = useState<number | null>(null);
  const [reportNudgeDismissed, setReportNudgeDismissed] = useState(false);
  // Full corpus of reviews for the current society. Fetched once on mount.
  // The panel always shows everything; the "Referenced" subset floats to the
  // top and stays saturated while the rest is desaturated.
  const [societyReviews, setSocietyReviews] = useState<SocietyReview[]>([]);

  // Keyed by review.id so scroll-on-cite works regardless of panel section.
  const reviewRefs = useRef<Record<number, HTMLDivElement | null>>({});
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Load all society reviews once on mount.
  useEffect(() => {
    let cancelled = false;
    fetchSocietyReviews(society.id, 300)
      .then(reviews => {
        if (cancelled) return;
        setSocietyReviews(reviews);
      })
      .catch(err => console.warn("society reviews fetch failed", err));
    return () => {
      cancelled = true;
    };
  }, [society.id]);

  // Snippets shown in the right-hand evidence panel - always the latest
  // assistant message's snippets (so it aligns with the most recent answer).
  const activeSnippets: ReviewSnippet[] = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      const m = messages[i];
      if (m.role === "assistant" && m.snippets && m.snippets.length > 0) {
        return m.snippets;
      }
    }
    return [];
  }, [messages]);

  // Latest assistant message's accumulated text - what the model actually said,
  // including [[s_N]] citation markers. Empty string during streaming until
  // tokens land.
  const latestAssistantText = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i--) {
      const m = messages[i];
      if (m.role === "assistant") return m.text || "";
    }
    return "";
  }, [messages]);

  // Parse [[s_N]] markers in the latest answer and keep only the UNIQUE
  // snippet indices that were actually cited. That way the "Referenced"
  // section mirrors the pills in the chat bubble - not every snippet the
  // model received.
  const citedSnippetIndices = useMemo(() => {
    const seen = new Set<number>();
    const ordered: number[] = [];
    for (const m of latestAssistantText.matchAll(/\[\[s_(\d+)\]\]/g)) {
      const n = parseInt(m[1], 10);
      if (Number.isNaN(n) || n < 0 || n >= activeSnippets.length) continue;
      if (seen.has(n)) continue;
      seen.add(n);
      ordered.push(n);
    }
    return ordered;
  }, [latestAssistantText, activeSnippets.length]);

  // Split the full society corpus into Referenced + Other. Referenced = the
  // snippets the model actually cited in the latest answer. Everything else
  // in `societyReviews` goes in Other. If a cited review is outside the
  // 300-row fetch window, synthesise a card so the panel never dead-links.
  const { referencedReviews, otherReviews } = useMemo(() => {
    const byId = new Map<number, SocietyReview>();
    for (const r of societyReviews) byId.set(r.id, r);

    const ref: SocietyReview[] = [];
    const refIdsSet = new Set<number>();
    for (const snippetIdx of citedSnippetIndices) {
      const snippet = activeSnippets[snippetIdx];
      if (!snippet) continue;
      const n = parseInt(snippet.snippet_id, 10);
      if (Number.isNaN(n) || refIdsSet.has(n)) continue;
      const found = byId.get(n);
      if (found) {
        ref.push(found);
      } else {
        ref.push({
          id: n,
          snippet_id: snippet.snippet_id,
          body: snippet.snippet_text,
          rating: snippet.rating,
          review_date: snippet.review_date,
          society_id: snippet.building_society_id,
          society_name: snippet.building_society_name,
          source: snippet.source,
          source_id: snippet.source.toLowerCase().replace(/[^a-z_]/g, "_"),
          sentiment_label: snippet.sentiment_label,
          source_url: snippet.source_url ?? null,
        });
      }
      refIdsSet.add(n);
    }
    const other = societyReviews.filter(r => !refIdsSet.has(r.id));
    return { referencedReviews: ref, otherReviews: other };
  }, [societyReviews, activeSnippets, citedSnippetIndices]);

  const contextByPersona: Record<string, string> = {
    loyalist: "A simulated Loyalist member · 30+ years · values branch relationships · low digital trust",
    digital: "A simulated Digital Native · first-time buyer · high expectations of the app and sign-up flow",
    family: "A simulated Family Juggler · mortgage renewal incoming · time-poor, engaged",
    business: "A simulated Business Owner · personal + business banking · expects named contacts",
  };

  // Autoscroll as new tokens land
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages]);

  // Scroll the evidence panel to the card for a given review id and flash it.
  // Review id is used as the key so referenced and non-referenced sections
  // can both be targets without clashing.
  const scrollToReview = (reviewId: number) => {
    setHighlighted(reviewId);
    const el = reviewRefs.current[reviewId];
    if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
    window.setTimeout(() => setHighlighted(h => (h === reviewId ? null : h)), 2400);
  };

  const handleSend = (text: string) => {
    if (!text.trim() || isStreaming) return;
    const userMessage: LiveMessage = { role: "user", text: text.trim() };
    const assistantPlaceholder: LiveMessage = { role: "assistant", text: "", streaming: true, snippets: [] };
    setMessages(prev => [...prev, userMessage, assistantPlaceholder]);
    setInput("");
    setIsStreaming(true);
    setErrorMsg(null);

    abortRef.current = streamMessage(
      text.trim(),
      {
        onMetadata: meta => {
          setSessionId(meta.session_id);
          setMessages(prev => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last?.role === "assistant") {
              last.snippets = meta.evidence_snippets;
            }
            return next;
          });
          // Capture total reviews for the current society from data_coverage
          const societyCounts = meta.data_coverage?.per_society_review_counts ?? [];
          const forThisSociety = societyCounts.find(c => c.building_society_id === society.id);
          if (forThisSociety) {
            setTotalReviewsForSociety(forThisSociety.review_count);
          } else if (societyCounts.length > 0) {
            setTotalReviewsForSociety(societyCounts[0].review_count);
          }
        },
        onToken: chunk => {
          setMessages(prev => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last?.role === "assistant") {
              last.text = (last.text || "") + chunk;
            }
            return next;
          });
        },
        onFollowups: () => {
          // Not rendered in the kiosk UI - the prompt chips are hardcoded per persona.
        },
        onDone: () => {
          setMessages(prev => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last?.role === "assistant") last.streaming = false;
            return next;
          });
          setIsStreaming(false);
          abortRef.current = null;
        },
        onError: err => {
          setErrorMsg(err.message);
          setMessages(prev => {
            const next = [...prev];
            const last = next[next.length - 1];
            if (last?.role === "assistant") {
              last.streaming = false;
              if (!last.text) {
                last.text = "Sorry - I couldn't reach the backend just now. Please try again.";
              }
            }
            return next;
          });
          setIsStreaming(false);
          abortRef.current = null;
        },
      },
      {
        sessionId,
        societyId: society.id,
        persona: {
          id: persona.id,
          name: persona.name,
          first_name: persona.firstName,
          age: persona.age,
          detail: persona.detail,
          concerns: persona.concerns,
        },
      }
    );
  };

  const userMessageCount = messages.filter(m => m.role === "user").length;
  const showReportNudge = userMessageCount >= 2 && !reportNudgeDismissed;

  return (
    <div style={{ width: "100%", height: "100vh", background: "var(--paper)", fontFamily: "var(--font-sans)", color: "var(--ink)", display: "flex", flexDirection: "column" }}>
      <header style={{ padding: "16px 32px", borderBottom: "1px solid var(--line)", background: "#FFFFFF", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
          <ProductMark size={16} />
          <span style={{ width: 1, height: 20, background: "var(--line)" }} />
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <SocietyLogo society={society} size={28} />
            <span style={{ fontSize: 14, fontWeight: 700, color: "var(--navy)" }}>{society.short}</span>
            <span style={{ color: "var(--ink-4)" }}>·</span>
            <Monogram initials={persona.initials} size={28} tone="navy" />
            <span style={{ fontSize: 14, fontWeight: 600, color: "var(--ink-2)" }}>{persona.name}</span>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <button className="btn" style={{ fontSize: 13, padding: "8px 14px" }} onClick={onOpenBenchmark}>
            <Icon.Chart /> Benchmark
          </button>
          <button className="btn" style={{ fontSize: 13, padding: "8px 14px", background: "var(--navy-soft)", borderColor: "var(--navy-soft)", color: "var(--navy)" }}>
            <Icon.Doc /> {totalReviewsForSociety !== null
              ? `${totalReviewsForSociety.toLocaleString()} reviews`
              : "reviews"}
          </button>
          <span style={{ width: 1, height: 20, background: "var(--line)" }} />
          <button className="btn" style={{ fontSize: 13, padding: "8px 14px", border: "none" }} onClick={onBack}>
            Start over
          </button>
        </div>
      </header>

      <div style={{ flex: 1, display: "grid", gridTemplateColumns: "1fr 360px", overflow: "hidden" }}>
        <div style={{ display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <div style={{ padding: "14px 40px", background: "var(--navy-bg)", borderBottom: "1px solid var(--line)", display: "flex", alignItems: "center", gap: 16, fontSize: 12.5 }}>
            <span className="mono" style={{ color: "var(--coral)", fontWeight: 700 }}>SPEAKING WITH</span>
            <span style={{ color: "var(--ink-2)" }}>{contextByPersona[persona.id] || contextByPersona.loyalist}</span>
            <span style={{ marginLeft: "auto", fontSize: 11.5, color: "var(--ink-3)" }}>
              Grounded in <b style={{ color: "var(--navy)" }}>real reviews</b> · Trustpilot, app stores, Smart Money People, Feefo + more
            </span>
          </div>

          <div ref={scrollRef} style={{ flex: 1, overflow: "auto", padding: "36px 40px" }}>
            <div style={{ maxWidth: 720, margin: "0 auto", display: "flex", flexDirection: "column", gap: 28 }}>
              {messages.map((m, i) => (
                <MessageBlock
                  key={i}
                  message={m}
                  persona={persona}
                  onCiteClick={scrollToReview}
                />
              ))}
              {errorMsg && (
                <div style={{ color: "var(--coral-2)", fontSize: 13 }}>⚠ {errorMsg}</div>
              )}
            </div>
          </div>

          {showReportNudge && (
            <div style={{ padding: "12px 40px", background: "linear-gradient(to right, var(--coral-soft), #FFFFFF)", borderTop: "1px solid var(--line)" }}>
              <div style={{ maxWidth: 720, margin: "0 auto", display: "flex", alignItems: "center", gap: 14 }}>
                <div style={{ width: 36, height: 36, borderRadius: 10, background: "var(--coral)", color: "#FFFFFF", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                  <Icon.Doc width={18} height={18} />
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13.5, fontWeight: 700, color: "var(--navy)", letterSpacing: "-0.005em" }}>
                    Want to take this away?
                  </div>
                  <div style={{ fontSize: 12, color: "var(--ink-2)", marginTop: 1 }}>
                    Download the full benchmark report for {society.short} - seven factors vs the sector.
                  </div>
                </div>
                <button
                  onClick={onOpenBenchmark}
                  className="btn btn-coral"
                  style={{ fontSize: 12.5, padding: "8px 14px", flexShrink: 0 }}
                >
                  See report <Icon.Arrow width={12} height={12} />
                </button>
                <button
                  onClick={() => setReportNudgeDismissed(true)}
                  aria-label="Dismiss"
                  style={{ background: "transparent", border: "none", cursor: "pointer", color: "var(--ink-3)", padding: 4, flexShrink: 0 }}
                >
                  <Icon.Close width={16} height={16} />
                </button>
              </div>
            </div>
          )}

          <div style={{ padding: "18px 40px 24px", borderTop: "1px solid var(--line)", background: "#FFFFFF" }}>
            <div style={{ maxWidth: 720, margin: "0 auto" }}>
              <div style={{ display: "flex", gap: 6, marginBottom: 12, overflow: "auto" }}>
                {suggested.map(q => (
                  <button
                    key={q}
                    onClick={() => setInput(q)}
                    disabled={isStreaming}
                    style={{
                      padding: "7px 14px",
                      borderRadius: 999,
                      background: "var(--paper-2)",
                      border: "1px solid var(--line)",
                      fontSize: 12.5,
                      fontWeight: 500,
                      color: "var(--ink-2)",
                      cursor: isStreaming ? "not-allowed" : "pointer",
                      opacity: isStreaming ? 0.5 : 1,
                      whiteSpace: "nowrap",
                      fontFamily: "var(--font-sans)",
                    }}
                  >
                    {q}
                  </button>
                ))}
              </div>
              <form
                onSubmit={e => {
                  e.preventDefault();
                  handleSend(input);
                }}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  border: "1.5px solid var(--navy)",
                  borderRadius: 14,
                  padding: "4px 4px 4px 18px",
                  background: "#FFFFFF",
                  opacity: isStreaming ? 0.85 : 1,
                }}
              >
                <input
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  disabled={isStreaming}
                  placeholder={isStreaming ? `${persona.firstName} is thinking…` : `Ask ${persona.firstName} a question…`}
                  style={{
                    flex: 1,
                    border: "none",
                    outline: "none",
                    fontFamily: "var(--font-sans)",
                    fontSize: 15,
                    color: "var(--ink)",
                    padding: "12px 0",
                    background: "transparent",
                  }}
                />
                <button
                  type="submit"
                  disabled={isStreaming || !input.trim()}
                  className="btn btn-coral"
                  style={{ padding: "10px 18px", opacity: isStreaming || !input.trim() ? 0.5 : 1 }}
                >
                  Send <Icon.Send width={14} height={14} />
                </button>
              </form>
              <div style={{ marginTop: 10, textAlign: "center", fontSize: 11, color: "var(--ink-4)" }}>
                {persona.firstName} is a simulated member. Responses are grounded in real reviews but not real individual statements.
              </div>
            </div>
          </div>
        </div>

        <aside style={{ borderLeft: "1px solid var(--line)", background: "var(--navy-bg)", overflow: "auto" }}>
          <div style={{ padding: "22px 22px 14px", position: "sticky", top: 0, background: "var(--navy-bg)", borderBottom: "1px solid var(--line)", zIndex: 2 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
              <div>
                <div style={{ fontSize: 15, fontWeight: 700, color: "var(--navy)" }}>Evidence</div>
                <div style={{ fontSize: 11.5, color: "var(--ink-3)", marginTop: 2 }}>
                  {totalReviewsForSociety !== null
                    ? `Showing ${(referencedReviews.length + otherReviews.length).toLocaleString()} of ${totalReviewsForSociety.toLocaleString()} reviews for ${society.short}`
                    : `${(referencedReviews.length + otherReviews.length).toLocaleString()} reviews for ${society.short}`}
                </div>
              </div>
            </div>
          </div>
          <div style={{ padding: "14px 22px 22px", display: "flex", flexDirection: "column", gap: 10 }}>
            {referencedReviews.length > 0 && (
              <>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 2 }}>
                  <span className="mono" style={{ color: "var(--coral-2)", fontSize: 9.5, fontWeight: 700 }}>
                    REFERENCED IN THIS ANSWER
                  </span>
                  <span style={{ flex: 1, height: 1, background: "var(--line)" }} />
                  <span style={{ fontSize: 10.5, color: "var(--ink-3)", fontWeight: 600 }}>
                    {referencedReviews.length}
                  </span>
                </div>
                {referencedReviews.map((r, i) => (
                  <ReviewCard
                    key={`ref-${r.id}`}
                    review={r}
                    referenced
                    highlighted={highlighted === r.id}
                    refCb={el => { reviewRefs.current[r.id] = el; }}
                    displayNumber={i + 1}
                  />
                ))}
              </>
            )}

            {otherReviews.length > 0 && (
              <>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: referencedReviews.length > 0 ? 18 : 2 }}>
                  <span className="mono" style={{ color: "var(--ink-3)", fontSize: 9.5, fontWeight: 700 }}>
                    {referencedReviews.length > 0 ? "OTHER REVIEWS" : "ALL REVIEWS"}
                  </span>
                  <span style={{ flex: 1, height: 1, background: "var(--line)" }} />
                  <span style={{ fontSize: 10.5, color: "var(--ink-3)", fontWeight: 600 }}>
                    {otherReviews.length}
                  </span>
                </div>
                {otherReviews.map(r => (
                  <ReviewCard
                    key={`other-${r.id}`}
                    review={r}
                    referenced={false}
                    highlighted={highlighted === r.id}
                    refCb={el => { reviewRefs.current[r.id] = el; }}
                  />
                ))}
              </>
            )}

            {referencedReviews.length === 0 && otherReviews.length === 0 && (
              <div style={{ padding: "24px 14px", background: "#FFFFFF", borderRadius: 10, border: "1px dashed var(--line)", textAlign: "center", color: "var(--ink-4)", fontSize: 12.5 }}>
                Loading reviews for {society.short}...
              </div>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}


interface MessageBlockProps {
  message: LiveMessage;
  persona: Archetype;
  onCiteClick: (reviewId: number) => void;
}

function MessageBlock({ message, persona, onCiteClick }: MessageBlockProps) {
  const isUser = message.role === "user";
  const parts = isUser ? [{ kind: "text" as const, value: message.text }] : parseMessage(message.text);
  const snippets = message.snippets || [];

  // Resolve a snippet index in this message to the review id it points at.
  // Evidence panel keys by review id so referenced + other sections share one anchor space.
  const reviewIdFor = (snippetIndex: number): number | null => {
    const s = snippets[snippetIndex];
    if (!s) return null;
    const n = parseInt(s.snippet_id, 10);
    return Number.isNaN(n) ? null : n;
  };

  // Assign each VALID, UNIQUE citation in this message a sequential display
  // number so the user sees [1], [2], ... regardless of raw snippet index.
  // Same mapping is used for the "INFORMED BY" pills so numbers line up.
  const displayNumberByIndex = new Map<number, number>();
  let nextDisplayNum = 1;
  for (const p of parts) {
    if (p.kind !== "cite") continue;
    if (!snippets[p.index]) continue; // invalid/missing snippet: skip
    if (displayNumberByIndex.has(p.index)) continue;
    displayNumberByIndex.set(p.index, nextDisplayNum++);
  }

  // Collect unique citation indices referenced in this message, in order of appearance
  const seen = new Set<number>();
  const citedIndices: number[] = [];
  for (const p of parts) {
    if (p.kind === "cite" && !seen.has(p.index)) {
      seen.add(p.index);
      citedIndices.push(p.index);
    }
  }

  return (
    <div style={{ display: "flex", gap: 14, flexDirection: isUser ? "row-reverse" : "row" }}>
      {!isUser && <Monogram initials={persona.initials} size={36} tone="navy" />}
      <div style={{ maxWidth: "78%" }}>
        {!isUser && (
          <div style={{ fontSize: 11, color: "var(--ink-3)", marginBottom: 6, fontWeight: 600 }}>
            <span style={{ color: "var(--navy)" }}>{persona.name}</span> · simulated
          </div>
        )}
        <div
          style={{
            padding: isUser ? "14px 18px" : "16px 20px",
            borderRadius: isUser ? "18px 18px 4px 18px" : "4px 18px 18px 18px",
            background: isUser ? "var(--navy)" : "#FFFFFF",
            color: isUser ? "#FFFFFF" : "var(--ink)",
            border: isUser ? "none" : "1px solid var(--line)",
            fontSize: 15.5,
            lineHeight: 1.55,
            fontWeight: isUser ? 500 : 400,
            letterSpacing: "-0.005em",
            whiteSpace: "pre-wrap",
          }}
        >
          {parts.map((p, i) => {
            if (p.kind === "text") return <span key={i}>{p.value}</span>;
            const snippet = snippets[p.index];
            // Defensive: if backend sanitisation ever misses an invalid index,
            // drop the superscript entirely rather than render a dead link.
            // This keeps superscripts and pills in one-to-one correspondence.
            if (!snippet) return null;
            const short = shortSourceName(snippet.source);
            const reviewId = reviewIdFor(p.index);
            const displayNum = displayNumberByIndex.get(p.index) ?? (p.index + 1);
            // Render the citation as an inline pill in the body text rather than
            // a 10px superscript - users (and partners on the kiosk) reported
            // missing the references entirely because the marker was visually
            // buried. A small, readable bracket pill makes it obvious the
            // sentence is grounded in a real review without disrupting flow.
            return (
              <button
                key={i}
                onClick={() => { if (reviewId !== null) onCiteClick(reviewId); }}
                title={`${short} · ${formatReviewDate(snippet.review_date)}`}
                style={{
                  display: "inline-block",
                  padding: "1px 7px",
                  margin: "0 1px 0 3px",
                  borderRadius: 5,
                  background: "var(--coral-soft)",
                  color: "var(--coral-2)",
                  border: "1px solid rgba(255,87,115,0.35)",
                  fontSize: 12,
                  lineHeight: 1.2,
                  fontWeight: 700,
                  fontFamily: "var(--font-mono)",
                  cursor: "pointer",
                  verticalAlign: "baseline",
                }}
              >
                [{displayNum}]
              </button>
            );
          })}
          {message.streaming && !message.text && (
            <span style={{ color: "var(--ink-4)", fontStyle: "italic" }}>Thinking…</span>
          )}
          {message.streaming && message.text && <span style={{ opacity: 0.5 }}>▌</span>}
        </div>
        {!isUser && citedIndices.length > 0 && (
          <div style={{ marginTop: 12, display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center" }}>
            <span className="mono" style={{ color: "var(--ink-3)", fontSize: 10.5, fontWeight: 700, letterSpacing: "0.08em" }}>SOURCES</span>
            {citedIndices.map(idx => {
              const s = snippets[idx];
              if (!s) return null;
              const reviewId = reviewIdFor(idx);
              const displayNum = displayNumberByIndex.get(idx) ?? (idx + 1);
              const isPos = sentimentOf(s) === "positive";
              const isNeg = sentimentOf(s) === "negative";
              return (
                <button
                  key={idx}
                  onClick={() => { if (reviewId !== null) onCiteClick(reviewId); }}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 6,
                    padding: "4px 10px 4px 8px",
                    borderRadius: 999,
                    background: isPos ? "var(--positive-soft)" : isNeg ? "var(--coral-soft)" : "var(--navy-soft)",
                    color: isPos ? "var(--positive)" : isNeg ? "var(--coral-2)" : "var(--navy)",
                    fontSize: 11.5,
                    fontWeight: 600,
                    border: `1px solid ${isPos ? "rgba(46,139,107,0.25)" : isNeg ? "rgba(255,87,115,0.25)" : "rgba(30,32,95,0.18)"}`,
                    fontFamily: "var(--font-sans)",
                    cursor: "pointer",
                  }}
                >
                  <Icon.Dot />
                  Review #{displayNum} · {shortSourceName(s.source)}
                  <span style={{ opacity: 0.6, fontWeight: 500 }}>· {formatReviewDate(s.review_date)}</span>
                </button>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}


interface ReviewCardProps {
  review: SocietyReview;
  referenced: boolean;
  highlighted: boolean;
  refCb: (el: HTMLDivElement | null) => void;
  /** Citation order number (1, 2, ...) shown on referenced cards only. */
  displayNumber?: number;
}

function ReviewCard({ review, referenced, highlighted, refCb, displayNumber }: ReviewCardProps) {
  const sentiment = sentimentOf(review);
  const sentimentColor =
    sentiment === "positive" ? "var(--positive)" : sentiment === "negative" ? "var(--coral)" : "var(--line-2)";
  const sentimentSoft =
    sentiment === "positive" ? "var(--positive-soft)" : sentiment === "negative" ? "var(--coral-soft)" : "var(--navy-soft)";
  const sentimentText =
    sentiment === "positive" ? "var(--positive)" : sentiment === "negative" ? "var(--coral-2)" : "var(--navy)";

  // Un-referenced cards desaturate with a filter + lower opacity so the
  // referenced set visually pops above them. Hover brings them back to normal
  // so they're still browsable.
  const baseStyle: React.CSSProperties = {
    background: highlighted ? "#FFF8E6" : "#FFFFFF",
    border: `1px solid ${highlighted ? "var(--coral)" : "var(--line)"}`,
    borderRadius: 10,
    padding: "14px 14px 13px",
    borderLeft: `3px solid ${sentimentColor}`,
    boxShadow: highlighted ? "0 0 0 3px rgba(255,87,115,0.18), 0 8px 24px -8px rgba(255,87,115,0.4)" : "none",
    transform: highlighted ? "scale(1.015)" : "scale(1)",
    transition: "all 0.35s ease",
    scrollMarginTop: 80,
  };
  if (!referenced && !highlighted) {
    baseStyle.filter = "grayscale(0.85)";
    baseStyle.opacity = 0.55;
  }

  return (
    <div
      ref={refCb}
      id={`review-${review.id}`}
      style={baseStyle}
      onMouseEnter={e => {
        if (!referenced && !highlighted) {
          e.currentTarget.style.filter = "grayscale(0)";
          e.currentTarget.style.opacity = "1";
        }
      }}
      onMouseLeave={e => {
        if (!referenced && !highlighted) {
          e.currentTarget.style.filter = "grayscale(0.85)";
          e.currentTarget.style.opacity = "0.55";
        }
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <span
          className="mono"
          style={{
            fontSize: 9,
            fontWeight: 700,
            background: sentimentSoft,
            color: sentimentText,
            padding: "2px 7px",
            borderRadius: 4,
          }}
        >
          {displayNumber !== undefined ? `REVIEW #${displayNumber} · ` : ""}{sentiment.toUpperCase()}
        </span>
        <span style={{ fontSize: 11, color: "var(--ink-3)" }}>
          {review.rating}/5 · {formatReviewDate(review.review_date)}
        </span>
      </div>
      <div style={{ fontSize: 12, fontWeight: 700, color: "var(--navy)", marginBottom: 4, letterSpacing: "-0.005em" }}>
        {shortSourceName(review.source)}
      </div>
      <p style={{ fontSize: 12.5, lineHeight: 1.5, color: "var(--ink-2)", margin: 0, fontWeight: 400 }}>
        "{review.body}"
      </p>
      {highlighted && (
        <div className="mono" style={{ marginTop: 8, fontSize: 9, color: "var(--coral-2)", fontWeight: 700 }}>
          REFERENCED IN CHAT
        </div>
      )}
    </div>
  );
}
