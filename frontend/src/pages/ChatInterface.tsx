import { useEffect, useMemo, useRef, useState } from "react";
import { ProductMark } from "../components/brand/WoodhurstMark";
import { SocietyLogo } from "../components/brand/SocietyLogo";
import { Monogram } from "../components/brand/Monogram";
import { Icon } from "../components/brand/Icons";
import type { Society } from "../data/societies";
import type { Archetype } from "../data/archetypes";
import { suggestedPrompts } from "../data/reviews";
import { streamMessage } from "../api/client";
import type { ReviewSnippet } from "../api/types";

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
   * array — NOT the global `snippets` state, which can change per turn.
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

function sentimentOf(snippet: ReviewSnippet): "positive" | "negative" | "neutral" {
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
      return `Oh, hello. Thirty-odd years I've been with ${societyShort}. Do sit down — what did you want to talk about?`;
    case "digital":
      return `Hey. Yeah, I signed up with ${societyShort} about a year ago. Happy to give you the honest read.`;
    case "family":
      return `Hi — got ten minutes. We've got the mortgage and the kids' savings with ${societyShort}, so fire away.`;
    case "business":
      return `Good to meet you. I've banked with ${societyShort} — personal and business — for a good while. What did you want to know?`;
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

  const reviewRefs = useRef<Record<number, HTMLDivElement | null>>({});
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Snippets shown in the right-hand evidence panel — always the latest
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

  const scrollToReview = (index: number) => {
    setHighlighted(index);
    const el = reviewRefs.current[index];
    if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
    window.setTimeout(() => setHighlighted(h => (h === index ? null : h)), 2400);
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
          // Not rendered in the kiosk UI — the prompt chips are hardcoded per persona.
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
                last.text = "Sorry — I couldn't reach the backend just now. Please try again.";
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

  const positiveCount = activeSnippets.filter(s => sentimentOf(s) === "positive").length;
  const negativeCount = activeSnippets.filter(s => sentimentOf(s) === "negative").length;

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
            <Icon.Doc /> {activeSnippets.length} reviews
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
                  {activeSnippets.length > 0
                    ? `${activeSnippets.length} reviews · informing this answer`
                    : `Ask a question to see supporting reviews`}
                </div>
              </div>
              <button style={{ background: "transparent", border: "none", cursor: "pointer", color: "var(--ink-3)" }}>
                <Icon.Close />
              </button>
            </div>
            <div style={{ display: "flex", gap: 4, marginTop: 12, fontSize: 11 }}>
              {([
                ["All", activeSnippets.length],
                ["Positive", positiveCount],
                ["Negative", negativeCount],
              ] as [string, number][]).map(([k, n], i) => (
                <span
                  key={k}
                  style={{
                    padding: "4px 10px",
                    borderRadius: 999,
                    background: i === 0 ? "var(--navy)" : "transparent",
                    color: i === 0 ? "#FFFFFF" : "var(--ink-2)",
                    border: `1px solid ${i === 0 ? "var(--navy)" : "var(--line-2)"}`,
                    fontWeight: 600,
                  }}
                >
                  {k} · {n}
                </span>
              ))}
            </div>
          </div>
          <div style={{ padding: "14px 22px 22px", display: "flex", flexDirection: "column", gap: 10 }}>
            {activeSnippets.length === 0 && (
              <div style={{ padding: "24px 14px", background: "#FFFFFF", borderRadius: 10, border: "1px dashed var(--line)", textAlign: "center", color: "var(--ink-4)", fontSize: 12.5 }}>
                No evidence yet — ask {persona.firstName} something to see the reviews informing their response.
              </div>
            )}
            {activeSnippets.map((s, index) => {
              const isHi = highlighted === index;
              const sentiment = sentimentOf(s);
              return (
                <div
                  key={`${s.snippet_id}-${index}`}
                  ref={el => { reviewRefs.current[index] = el; }}
                  style={{
                    background: isHi ? "#FFF8E6" : "#FFFFFF",
                    border: `1px solid ${isHi ? "var(--coral)" : "var(--line)"}`,
                    borderRadius: 10,
                    padding: "14px 14px 13px",
                    borderLeft: `3px solid ${sentiment === "positive" ? "var(--positive)" : sentiment === "negative" ? "var(--coral)" : "var(--line-2)"}`,
                    boxShadow: isHi ? "0 0 0 3px rgba(255,87,115,0.18), 0 8px 24px -8px rgba(255,87,115,0.4)" : "none",
                    transform: isHi ? "scale(1.015)" : "scale(1)",
                    transition: "all 0.35s ease",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                    <span
                      className="mono"
                      style={{
                        fontSize: 9,
                        fontWeight: 700,
                        background: sentiment === "positive" ? "var(--positive-soft)" : sentiment === "negative" ? "var(--coral-soft)" : "var(--navy-soft)",
                        color: sentiment === "positive" ? "var(--positive)" : sentiment === "negative" ? "var(--coral-2)" : "var(--navy)",
                        padding: "2px 7px",
                        borderRadius: 4,
                      }}
                    >
                      #{index + 1} · {sentiment.toUpperCase()}
                    </span>
                    <span style={{ fontSize: 11, color: "var(--ink-3)" }}>{s.rating}/5 · {formatReviewDate(s.review_date)}</span>
                  </div>
                  <div style={{ fontSize: 12, fontWeight: 700, color: "var(--navy)", marginBottom: 4, letterSpacing: "-0.005em" }}>{shortSourceName(s.source)}</div>
                  <p style={{ fontSize: 12.5, lineHeight: 1.5, color: "var(--ink-2)", margin: 0, fontWeight: 400 }}>
                    "{s.snippet_text}"
                  </p>
                  {isHi && (
                    <div className="mono" style={{ marginTop: 8, fontSize: 9, color: "var(--coral-2)", fontWeight: 700 }}>
                      ← REFERENCED IN CHAT
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </aside>
      </div>
    </div>
  );
}


interface MessageBlockProps {
  message: LiveMessage;
  persona: Archetype;
  onCiteClick: (index: number) => void;
}

function MessageBlock({ message, persona, onCiteClick }: MessageBlockProps) {
  const isUser = message.role === "user";
  const parts = isUser ? [{ kind: "text" as const, value: message.text }] : parseMessage(message.text);
  const snippets = message.snippets || [];

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
            const short = snippet ? shortSourceName(snippet.source) : `ref ${p.index + 1}`;
            return (
              <sup key={i} style={{ marginLeft: 2 }}>
                <button
                  onClick={() => onCiteClick(p.index)}
                  title={snippet ? `${short} · ${formatReviewDate(snippet.review_date)}` : `Reference ${p.index + 1}`}
                  style={{
                    padding: "1px 6px",
                    borderRadius: 6,
                    background: "var(--coral-soft)",
                    color: "var(--coral-2)",
                    border: "1px solid rgba(255,87,115,0.25)",
                    fontSize: 10,
                    fontWeight: 700,
                    fontFamily: "var(--font-mono)",
                    cursor: "pointer",
                  }}
                >
                  {p.index + 1}
                </button>
              </sup>
            );
          })}
          {message.streaming && !message.text && (
            <span style={{ color: "var(--ink-4)", fontStyle: "italic" }}>Thinking…</span>
          )}
          {message.streaming && message.text && <span style={{ opacity: 0.5 }}>▌</span>}
        </div>
        {!isUser && citedIndices.length > 0 && (
          <div style={{ marginTop: 10, display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center" }}>
            <span className="mono" style={{ color: "var(--ink-3)", fontSize: 9.5 }}>INFORMED BY</span>
            {citedIndices.map(idx => {
              const s = snippets[idx];
              if (!s) return null;
              const isPos = sentimentOf(s) === "positive";
              const isNeg = sentimentOf(s) === "negative";
              return (
                <button
                  key={idx}
                  onClick={() => onCiteClick(idx)}
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
                  Review #{idx + 1} · {shortSourceName(s.source)}
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
