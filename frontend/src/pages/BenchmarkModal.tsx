import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { Icon } from "../components/brand/Icons";
import { trackEvent } from "../api/analytics";
import type { Society } from "../data/societies";
import { PDFReport, type PDFReportScore } from "./PDFReport";

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

/**
 * Render the seven-factor benchmark as a clean plain-text email body.
 * mailto: bodies are plain-text only - most clients strip or escape HTML -
 * so we lean on Unicode box-drawing + padding to keep it readable.
 */
function buildEmailBody(society: Society): string {
  const today = new Date().toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });
  const aboveCount = scores.filter(s => s.status === "above").length;
  const belowCount = scores.filter(s => s.status === "below").length;
  const topStrength = [...scores].filter(s => s.status === "above").sort((a, b) => b.score - a.score)[0];
  const biggestGap = [...scores].filter(s => s.status === "below").sort((a, b) => a.score - b.score)[0];

  const rule = "━".repeat(64);
  const soft = "─".repeat(64);

  const lines: string[] = [];
  lines.push(rule);
  lines.push(`  MEMBER EXPERIENCE BENCHMARK`);
  lines.push(`  ${society.name}`);
  lines.push(`  ${society.region}  ·  benchmarked against 42 UK building societies`);
  lines.push(`  ${today}  ·  Woodhurst Consulting  ·  Confidential`);
  lines.push(rule);
  lines.push("");

  lines.push("HEADLINE");
  lines.push(soft);
  lines.push(`  Overall position   ${aboveCount > 0 ? `Above average on ${aboveCount} of ${scores.length}` : `Parity or below on all ${scores.length}`}${belowCount > 0 ? `, gaps on ${belowCount}` : ""}`);
  if (topStrength) {
    lines.push(`  Top strength       ${topStrength.factor.padEnd(24)} ${topStrength.score.toFixed(1)} / 10  ·  ranked ${ord(topStrength.rank)}`);
  }
  if (biggestGap) {
    lines.push(`  Biggest gap        ${biggestGap.factor.padEnd(24)} ${biggestGap.score.toFixed(1)} / 10  ·  ranked ${ord(biggestGap.rank)}`);
  }
  lines.push("");

  lines.push("SCORES BY FACTOR");
  lines.push(soft);
  lines.push(`  ${"FACTOR".padEnd(22)} ${"SCORE".padStart(6)}  ${"AVG".padStart(5)}  ${"DIFF".padStart(6)}  ${"RANK".padStart(5)}  STATUS`);
  scores.forEach(s => {
    const diff = s.score - s.avg;
    const diffStr = `${diff >= 0 ? "+" : ""}${diff.toFixed(1)}`;
    const statusLabel = s.status === "above" ? "Above avg" : s.status === "below" ? "Below avg" : "Near avg";
    lines.push(
      `  ${s.factor.padEnd(22)} ${s.score.toFixed(1).padStart(6)}  ${s.avg.toFixed(1).padStart(5)}  ${diffStr.padStart(6)}  ${ord(s.rank).padStart(5)}  ${statusLabel}`
    );
  });
  lines.push("");

  lines.push("RECOMMENDED FOCUS");
  lines.push(soft);
  const recs = [
    "Protect branch experience for members whose relationship with the society is anchored there.",
    "Close the digital gap: app and sign-in flows are the biggest friction in recent reviews.",
    "Lead communications with community narrative, it is your most under-expressed strength.",
  ];
  recs.forEach((t, i) => {
    const prefix = `  ${String(i + 1).padStart(2, "0")}  `;
    // Simple word-wrap at 62 cols so it reads in a 72-col mail client.
    const indent = " ".repeat(prefix.length);
    const wrapped = wrapParagraph(t, 62);
    lines.push(prefix + wrapped[0]);
    for (const w of wrapped.slice(1)) lines.push(indent + w);
  });
  lines.push("");

  lines.push(rule);
  lines.push(
    "  Derived from keyword sentiment analysis of Smart Money People,"
  );
  lines.push(
    "  Trustpilot, app stores, Feefo and editorial sources."
  );
  lines.push("  Read the full dashboard: https://bsa-member-chat.vercel.app/");
  lines.push(rule);

  return lines.join("\n");
}

function wrapParagraph(text: string, width: number): string[] {
  const words = text.split(/\s+/);
  const out: string[] = [];
  let line = "";
  for (const w of words) {
    if ((line + " " + w).trim().length > width) {
      if (line) out.push(line);
      line = w;
    } else {
      line = line ? line + " " + w : w;
    }
  }
  if (line) out.push(line);
  return out;
}

/**
 * Ensure a <div id="print-root"> exists at document.body level. The
 * BenchmarkModal portals the PDFReport into it so it sits OUTSIDE React's
 * normal #root tree. That matters because @media print hides #root
 * entirely - otherwise the print output also includes the chat screen
 * behind the modal.
 */
function usePrintRoot(): HTMLElement | null {
  const [node, setNode] = useState<HTMLElement | null>(null);
  useEffect(() => {
    let el = document.getElementById("print-root");
    if (!el) {
      el = document.createElement("div");
      el.id = "print-root";
      document.body.appendChild(el);
    }
    setNode(el);
  }, []);
  return node;
}

export function BenchmarkModal({ society, onClose }: Props) {
  const [emailPrompt, setEmailPrompt] = useState(false);
  const [emailInput, setEmailInput] = useState("");
  const printRoot = usePrintRoot();

  const handleDownload = () => {
    trackEvent("report_downloaded", { societyId: society.id });
    // Print flow: #root is hidden by @media print rules and the portaled
    // PDFReport (in #print-root) becomes the only visible element. See
    // index.css @media print.
    window.print();
  };

  const handleEmail = () => {
    const to = emailInput.trim();
    trackEvent("report_emailed", {
      societyId: society.id,
      props: { email: to || null, had_email: Boolean(to) },
    });
    const subject = encodeURIComponent(`${society.short} - BSA benchmark report`);
    const body = encodeURIComponent(buildEmailBody(society));
    const recipient = to ? encodeURIComponent(to) : "";
    // mailto opens the user's default mail client with the report pre-filled.
    window.location.href = `mailto:${recipient}?subject=${subject}&body=${body}`;
    setEmailPrompt(false);
    setEmailInput("");
  };

  // PDFReport takes a slightly narrower score shape (no `reviews` count).
  const pdfScores: PDFReportScore[] = scores.map(s => ({
    factor: s.factor,
    score: s.score,
    avg: s.avg,
    rank: s.rank,
    status: s.status,
  }));

  return (
    <>
      {/* Render the A4 PDFReport into body > #print-root (outside React's
          #root tree). On screen #print-root is display:none; in print mode
          #root is hidden and #print-root takes over. */}
      {printRoot && createPortal(<PDFReport society={society} scores={pdfScores} />, printRoot)}

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
            <form
              onSubmit={e => {
                e.preventDefault();
                handleEmail();
              }}
              style={{ display: "flex", gap: 6, alignItems: "center" }}
            >
              <input
                type="email"
                value={emailInput}
                onChange={e => setEmailInput(e.target.value)}
                placeholder="recipient@example.com (optional)"
                autoFocus
                style={{
                  fontSize: 13,
                  padding: "8px 12px",
                  border: "1.5px solid var(--line-2)",
                  borderRadius: 8,
                  fontFamily: "var(--font-sans)",
                  minWidth: 260,
                  outline: "none",
                }}
              />
              <button type="submit" className="btn btn-primary" style={{ fontSize: 13 }}>
                Compose email
              </button>
              <button
                type="button"
                onClick={() => setEmailPrompt(false)}
                className="btn"
                style={{ fontSize: 13, border: "none" }}
              >
                Cancel
              </button>
            </form>
          ) : (
            <div style={{ display: "flex", gap: 8 }}>
              <button onClick={() => setEmailPrompt(true)} className="btn" style={{ fontSize: 13 }}>
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
