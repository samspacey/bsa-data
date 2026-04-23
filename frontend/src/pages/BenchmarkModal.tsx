import { useState } from "react";
import { Icon } from "../components/brand/Icons";
import { trackEvent, getSessionId } from "../api/analytics";
import { emailReport, reportPdfUrl } from "../api/client";
import type { Society } from "../data/societies";

interface Score {
  factor: string;
  score: number;
  avg: number;
  rank: number;
  reviews: number;
  status: "above" | "near" | "below";
}

interface Props {
  society: Society;
  onClose: () => void;
}

const scores: Score[] = [
  { factor: "Customer Service",    score: 8.2, avg: 7.1, rank: 9,  reviews: 142, status: "above" },
  { factor: "Digital Experience",  score: 5.1, avg: 6.8, rank: 34, reviews: 89,  status: "below" },
  { factor: "Branch Experience",   score: 9.1, avg: 7.3, rank: 3,  reviews: 76,  status: "above" },
  { factor: "Mortgage Products",   score: 6.9, avg: 7.0, rank: 21, reviews: 58,  status: "near" },
  { factor: "Savings Rates",       score: 6.2, avg: 7.2, rank: 29, reviews: 94,  status: "below" },
  { factor: "Communication",       score: 7.4, avg: 7.1, rank: 14, reviews: 61,  status: "near" },
  { factor: "Local Community",     score: 9.4, avg: 6.9, rank: 2,  reviews: 43,  status: "above" },
];

const statusMap: Record<Score["status"], { color: string; soft: string; label: string; bar: string }> = {
  above: { color: "var(--positive)", soft: "var(--positive-soft)", label: "Above avg", bar: "var(--positive)" },
  near:  { color: "var(--warning)",  soft: "var(--warning-soft)",  label: "Near avg",  bar: "var(--warning)" },
  below: { color: "var(--coral-2)",  soft: "var(--coral-soft)",    label: "Below avg", bar: "var(--coral)" },
};

const ord = (n: number) => {
  const s = ["th", "st", "nd", "rd"], v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
};


type Status =
  | { kind: "idle" }
  | { kind: "sending" }
  | { kind: "sent"; email: string }
  | { kind: "error"; message: string; pdfBase64?: string; filename?: string };

function triggerBlobDownload(base64: string, filename: string) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  const blob = new Blob([bytes], { type: "application/pdf" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export function BenchmarkModal({ society, onClose }: Props) {
  const [emailPrompt, setEmailPrompt] = useState(false);
  const [emailInput, setEmailInput] = useState("");
  const [status, setStatus] = useState<Status>({ kind: "idle" });

  const handleDownload = () => {
    trackEvent("report_downloaded", { societyId: society.id });
    // Navigate the browser to the backend PDF endpoint - the Content-Disposition
    // header triggers a file download.
    window.location.assign(reportPdfUrl(society.id, society.region, getSessionId()));
  };

  const handleEmail = async () => {
    const to = emailInput.trim();
    if (!to) return;
    setStatus({ kind: "sending" });
    trackEvent("report_emailed", {
      societyId: society.id,
      props: { email: to, had_email: true },
    });
    try {
      const result = await emailReport(society.id, to, society.region, getSessionId());
      if (result.email_sent) {
        setStatus({ kind: "sent", email: to });
        setEmailInput("");
        // Close the form after a beat so the success message is visible.
        window.setTimeout(() => setEmailPrompt(false), 2400);
      } else {
        // Backend couldn't send. Surface the error AND offer the PDF as a
        // download so the user still has what they asked for.
        setStatus({
          kind: "error",
          message: result.error || "Email service not configured.",
          pdfBase64: result.pdf_base64 || undefined,
          filename: result.filename,
        });
      }
    } catch (err) {
      setStatus({ kind: "error", message: err instanceof Error ? err.message : String(err) });
    }
  };

  return (
    <>
      <div
        onClick={onClose}
        style={{
          position: "fixed",
          inset: 0,
          background: "rgba(15, 16, 51, 0.55)",
          backdropFilter: "blur(8px)",
          padding: "40px 48px",
          fontFamily: "var(--font-sans)",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          zIndex: 50,
        }}
      >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: "#FFFFFF",
          borderRadius: 20,
          width: 920,
          maxWidth: "100%",
          maxHeight: "90vh",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
          boxShadow: "0 40px 100px -20px rgba(15,16,51,0.5)",
        }}
      >
        <div style={{ padding: "26px 36px 24px", borderBottom: "1px solid var(--line)", display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <div className="eyebrow" style={{ color: "var(--coral)", marginBottom: 8 }}>Benchmark · Woodhurst Consulting</div>
            <h2 style={{ fontSize: 28, fontWeight: 800, letterSpacing: "-0.025em", margin: 0, color: "var(--navy)" }}>
              How {society.short} compares
            </h2>
            <div style={{ fontSize: 13, color: "var(--ink-3)", marginTop: 6 }}>
              Seven factors · against 42 UK building societies · updated {new Date().toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" })}
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "var(--paper-2)",
              border: "none",
              width: 36,
              height: 36,
              borderRadius: 999,
              cursor: "pointer",
              color: "var(--ink-2)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Icon.Close width={18} height={18} />
          </button>
        </div>

        <div style={{ padding: "20px 36px", background: "var(--navy-bg)", display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 24, borderBottom: "1px solid var(--line)" }}>
          {[
            { label: "Overall position", v: "3 strengths · 2 gaps", sub: "of 7 factors", color: "var(--navy)" },
            { label: "Top strength", v: "Local Community", sub: "9.4 · 2nd of 42", color: "var(--positive)" },
            { label: "Biggest gap", v: "Digital Experience", sub: "5.1 · 34th of 42", color: "var(--coral-2)" },
          ].map((s, i) => (
            <div key={i} style={{ borderLeft: i > 0 ? "1px solid var(--line)" : "none", paddingLeft: i > 0 ? 20 : 0 }}>
              <div className="eyebrow" style={{ color: s.color, marginBottom: 6 }}>{s.label}</div>
              <div style={{ fontSize: 17, fontWeight: 700, color: "var(--navy)", letterSpacing: "-0.015em" }}>{s.v}</div>
              <div style={{ fontSize: 12, color: "var(--ink-3)", marginTop: 3 }}>{s.sub}</div>
            </div>
          ))}
        </div>

        <div style={{ flex: 1, overflow: "auto", padding: "24px 36px" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 22 }}>
            {scores.map(s => {
              const st = statusMap[s.status];
              const pct = (s.score / 10) * 100;
              const avgPct = (s.avg / 10) * 100;
              const diff = s.score - s.avg;
              return (
                <div key={s.factor}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 8 }}>
                    <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
                      <span style={{ fontSize: 15, fontWeight: 700, color: "var(--navy)", letterSpacing: "-0.01em" }}>{s.factor}</span>
                      <span className="mono" style={{ color: "var(--ink-3)", fontSize: 9.5 }}>{s.reviews} REVIEWS · RANKED {ord(s.rank)}</span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <span style={{ fontSize: 11, fontWeight: 700, color: st.color, background: st.soft, padding: "3px 10px", borderRadius: 999 }}>{st.label}</span>
                      <span className="num" style={{ fontSize: 11.5, color: diff >= 0 ? "var(--positive)" : "var(--coral-2)", fontWeight: 700 }}>
                        {diff >= 0 ? "+" : ""}{diff.toFixed(1)}
                      </span>
                    </div>
                  </div>
                  <div style={{ position: "relative", height: 30, background: "var(--paper-2)", borderRadius: 6, overflow: "visible" }}>
                    <div style={{ position: "absolute", inset: 0, width: `${pct}%`, background: st.bar, borderRadius: 6, transition: "width 0.5s" }} />
                    <div style={{ position: "absolute", top: -3, bottom: -3, left: `${avgPct}%`, width: 2, background: "var(--ink)", zIndex: 2 }} />
                    <div style={{ position: "absolute", top: -15, left: `${avgPct}%`, transform: "translateX(-50%)", fontSize: 9, color: "var(--ink-2)", fontWeight: 700, letterSpacing: "0.08em", whiteSpace: "nowrap" }}>
                      AVG {s.avg.toFixed(1)}
                    </div>
                    <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", padding: "0 12px" }}>
                      <span className="num" style={{ fontSize: 13, fontWeight: 800, color: pct > 15 ? "#FFFFFF" : "var(--ink)" }}>{s.score.toFixed(1)}</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div
          style={{ padding: "20px 36px", borderTop: "1px solid var(--line)", background: "var(--paper)", display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16, flexWrap: "wrap" }}
        >
          <div style={{ fontSize: 12, color: "var(--ink-3)", flex: "1 1 auto", minWidth: 220 }}>
            Derived from keyword sentiment analysis of Smart Money People, Trustpilot, app store and editorial sources.
          </div>
          {emailPrompt ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 6, alignItems: "flex-end" }}>
              <form
                onSubmit={e => {
                  e.preventDefault();
                  handleEmail();
                }}
                style={{ display: "flex", gap: 6, alignItems: "center" }}
              >
                <input
                  type="email"
                  required
                  value={emailInput}
                  onChange={e => setEmailInput(e.target.value)}
                  placeholder="recipient@example.com"
                  autoFocus
                  disabled={status.kind === "sending"}
                  style={{
                    fontSize: 13,
                    padding: "8px 12px",
                    border: "1.5px solid var(--line-2)",
                    borderRadius: 8,
                    fontFamily: "var(--font-sans)",
                    minWidth: 260,
                    outline: "none",
                    opacity: status.kind === "sending" ? 0.6 : 1,
                  }}
                />
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={status.kind === "sending" || !emailInput.trim()}
                  style={{ fontSize: 13, opacity: status.kind === "sending" || !emailInput.trim() ? 0.5 : 1 }}
                >
                  {status.kind === "sending" ? "Sending..." : "Send with PDF attached"}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setEmailPrompt(false);
                    setStatus({ kind: "idle" });
                  }}
                  className="btn"
                  style={{ fontSize: 13, border: "none" }}
                  disabled={status.kind === "sending"}
                >
                  Cancel
                </button>
              </form>
              {status.kind === "sent" && (
                <div style={{ fontSize: 12, color: "var(--positive)", fontWeight: 600 }}>
                  ✓ Sent to {status.email} with the PDF attached.
                </div>
              )}
              {status.kind === "error" && (
                <div style={{ fontSize: 12, color: "var(--coral-2)", display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", justifyContent: "flex-end" }}>
                  <span>Email couldn't send: {status.message}</span>
                  {status.pdfBase64 && status.filename && (
                    <button
                      onClick={() => triggerBlobDownload(status.pdfBase64!, status.filename!)}
                      className="btn"
                      style={{ fontSize: 12, padding: "6px 12px" }}
                    >
                      Download PDF instead
                    </button>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div style={{ display: "flex", gap: 8 }}>
              <button onClick={() => { setEmailPrompt(true); setStatus({ kind: "idle" }); }} className="btn" style={{ fontSize: 13 }}>
                Email the report
              </button>
              <button onClick={handleDownload} className="btn btn-primary" style={{ fontSize: 13 }}>
                <Icon.Doc /> Download PDF
              </button>
            </div>
          )}
        </div>
      </div>
      </div>
    </>
  );
}
