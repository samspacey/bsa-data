import { WoodhurstMark } from "../components/brand/WoodhurstMark";
import { Icon } from "../components/brand/Icons";
import type { Society } from "../data/societies";

/**
 * A4-format benchmark report. Rendered off-screen at all times; becomes
 * visible only inside the browser's print dialog via @media print rules
 * (see ``.print-only`` in index.css). That way "Download PDF" on the
 * BenchmarkModal prints this, not the on-screen modal.
 *
 * Layout follows the Woodhurst design handoff exactly:
 * - 8px navy rule along the top
 * - Masthead (WoodhurstMark + dateline)
 * - Report-for headline with society name
 * - 3-column summary block (overall position / top strength / biggest gap)
 * - Scores table with bars + avg marker + rank + status badge
 * - Two-column: dark quote card + numbered recommendations
 * - Absolute-positioned footer with "CONFIDENTIAL · PAGE 01/01"
 */

export interface PDFReportScore {
  factor: string;
  score: number;
  avg: number;
  rank: number;
  status: "above" | "near" | "below";
}

interface PDFReportProps {
  society: Society;
  scores: PDFReportScore[];
  quote?: string;
  quoteSource?: string;
  recommendations?: string[];
}

const statusMap: Record<PDFReportScore["status"], { c: string; soft: string; label: string }> = {
  above: { c: "var(--positive)", soft: "var(--positive-soft)", label: "Above avg" },
  near:  { c: "var(--warning)",  soft: "var(--warning-soft)",  label: "Near avg"  },
  below: { c: "var(--coral-2)",  soft: "var(--coral-soft)",    label: "Below avg" },
};

function ordinal(n: number): string {
  const s = ["th", "st", "nd", "rd"];
  const v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
}

export function PDFReport({ society, scores, quote, quoteSource, recommendations }: PDFReportProps) {
  const today = new Date().toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" });
  const aboveCount = scores.filter(s => s.status === "above").length;
  const belowCount = scores.filter(s => s.status === "below").length;

  // Top strength = highest score where status="above"; biggest gap = lowest score where status="below"
  const topStrength = [...scores].filter(s => s.status === "above").sort((a, b) => b.score - a.score)[0];
  const biggestGap = [...scores].filter(s => s.status === "below").sort((a, b) => a.score - b.score)[0];

  const summary = [
    {
      k: "Overall position",
      v: `${aboveCount > 0 ? `Above avg on ${aboveCount} of ${scores.length}` : `Parity or below on all ${scores.length}`}`,
      c: "var(--navy)",
    },
    topStrength
      ? { k: "Top strength", v: `${topStrength.factor} · ${topStrength.score.toFixed(1)}`, c: "var(--positive)" }
      : { k: "Top strength", v: "None clearly above avg", c: "var(--ink-3)" },
    biggestGap
      ? { k: "Biggest gap", v: `${biggestGap.factor} · ${biggestGap.score.toFixed(1)}`, c: "var(--coral-2)" }
      : { k: "Biggest gap", v: `${belowCount} factor${belowCount === 1 ? "" : "s"} below avg`, c: "var(--coral-2)" },
  ];

  return (
    <div
      style={{
        width: 794,
        minHeight: 1123,
        background: "#FFFFFF",
        padding: "52px 56px 60px",
        fontFamily: "var(--font-sans)",
        color: "var(--ink)",
        position: "relative",
      }}
    >
      {/* Top rule */}
      <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 8, background: "var(--navy)" }} />

      {/* Masthead */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", paddingBottom: 20, borderBottom: "1px solid var(--line)" }}>
        <WoodhurstMark size={16} />
        <div style={{ textAlign: "right", fontSize: 10, color: "var(--ink-3)" }}>
          <div className="mono" style={{ fontWeight: 700, color: "var(--navy)" }}>MEMBER EXPERIENCE BENCHMARK</div>
          <div style={{ marginTop: 3 }}>{today} · Confidential</div>
        </div>
      </div>

      {/* Headline */}
      <div style={{ marginTop: 28, marginBottom: 24 }}>
        <div className="eyebrow" style={{ color: "var(--coral)", marginBottom: 10 }}>Report for</div>
        <h1 style={{ fontSize: 38, fontWeight: 800, letterSpacing: "-0.03em", margin: 0, lineHeight: 1.05, color: "var(--navy)" }}>
          {society.name}
        </h1>
        <div style={{ fontSize: 12.5, color: "var(--ink-3)", marginTop: 8 }}>
          {society.region} · benchmarked against 42 UK building societies
        </div>
      </div>

      {/* Summary block */}
      <div style={{ background: "var(--navy-bg)", border: "1px solid var(--line)", borderRadius: 8, padding: "18px 22px", display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 20, marginBottom: 26 }}>
        {summary.map((s, i) => (
          <div key={i} style={{ borderLeft: i > 0 ? "1px solid var(--line)" : "none", paddingLeft: i > 0 ? 18 : 0 }}>
            <div className="eyebrow" style={{ fontSize: 9, color: s.c }}>{s.k}</div>
            <div style={{ fontSize: 13, fontWeight: 700, color: "var(--navy)", marginTop: 4, letterSpacing: "-0.01em" }}>{s.v}</div>
          </div>
        ))}
      </div>

      {/* Scores table */}
      <div className="eyebrow" style={{ marginBottom: 10 }}>Scores by factor</div>
      <div style={{ border: "1px solid var(--line)", borderRadius: 6, overflow: "hidden" }}>
        <div style={{ display: "grid", gridTemplateColumns: "2.2fr 0.7fr 0.7fr 2.2fr 0.8fr 1fr", padding: "9px 14px", background: "var(--paper-2)", fontSize: 9, fontWeight: 700, color: "var(--ink-3)", letterSpacing: "0.08em", textTransform: "uppercase" }}>
          <div>Factor</div>
          <div style={{ textAlign: "center" }}>Score</div>
          <div style={{ textAlign: "center" }}>Avg</div>
          <div>vs Industry (0-10)</div>
          <div style={{ textAlign: "center" }}>Rank</div>
          <div style={{ textAlign: "center" }}>Status</div>
        </div>
        {scores.map((s, i) => {
          const st = statusMap[s.status];
          const pct = (s.score / 10) * 100;
          const avgPct = (s.avg / 10) * 100;
          return (
            <div
              key={s.factor}
              style={{
                display: "grid",
                gridTemplateColumns: "2.2fr 0.7fr 0.7fr 2.2fr 0.8fr 1fr",
                padding: "11px 14px",
                alignItems: "center",
                background: i % 2 ? "var(--paper)" : "#FFFFFF",
                fontSize: 11.5,
                borderTop: "1px solid var(--line)",
              }}
            >
              <div style={{ fontWeight: 700, color: "var(--navy)" }}>{s.factor}</div>
              <div className="num" style={{ textAlign: "center", fontWeight: 800, color: "var(--navy)" }}>
                {s.score.toFixed(1)}
              </div>
              <div className="num" style={{ textAlign: "center", color: "var(--ink-3)" }}>
                {s.avg.toFixed(1)}
              </div>
              <div style={{ position: "relative", height: 9, background: "var(--paper-3)", borderRadius: 2 }}>
                <div style={{ position: "absolute", inset: 0, width: `${pct}%`, background: st.c, borderRadius: 2 }} />
                <div style={{ position: "absolute", top: -2, bottom: -2, left: `${avgPct}%`, width: 1.5, background: "var(--ink)" }} />
              </div>
              <div className="num" style={{ textAlign: "center", fontSize: 10.5, color: "var(--ink-2)", fontWeight: 600 }}>
                {ordinal(s.rank)}
              </div>
              <div style={{ textAlign: "center" }}>
                <span style={{ fontSize: 9, fontWeight: 700, color: st.c, background: st.soft, padding: "2px 7px", borderRadius: 3 }}>
                  {st.label.toUpperCase()}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Quote + Recommendations */}
      <div style={{ marginTop: 26, display: "grid", gridTemplateColumns: "1fr 1.1fr", gap: 20 }}>
        <div style={{ background: "var(--navy)", color: "#FFFFFF", borderRadius: 8, padding: "20px 22px" }}>
          <Icon.Quote style={{ color: "var(--coral)", marginBottom: 10 }} width="22" height="22" />
          <p style={{ fontSize: 14, lineHeight: 1.4, margin: 0, color: "#FFFFFF", fontWeight: 500, letterSpacing: "-0.01em" }}>
            "{quote || "Members value the branch relationships most. Loyalty rates could be sharper."}"
          </p>
          <div style={{ marginTop: 16, fontSize: 10, color: "rgba(255,255,255,0.6)", borderTop: "1px solid rgba(255,255,255,0.2)", paddingTop: 10 }}>
            {quoteSource || "Composite quote drawn from recent member reviews"}
          </div>
        </div>
        <div>
          <div className="eyebrow" style={{ marginBottom: 10 }}>Recommended focus</div>
          <ol style={{ margin: 0, padding: 0, listStyle: "none", fontSize: 11.5, lineHeight: 1.55, color: "var(--ink-2)" }}>
            {(recommendations ?? [
              "Protect branch experience for members whose relationship with the society is anchored there.",
              `Close the digital gap - app and sign-in flows are the biggest friction in recent reviews.`,
              "Lead communications with community narrative - it is your most under-expressed strength.",
            ]).map((t, i) => (
              <li
                key={i}
                style={{
                  display: "flex",
                  gap: 10,
                  marginBottom: 10,
                  paddingBottom: 10,
                  borderBottom: i < 2 ? "1px solid var(--line)" : "none",
                }}
              >
                <span style={{ fontFamily: "var(--font-sans)", fontWeight: 800, color: "var(--coral)", fontSize: 14, minWidth: 18 }}>
                  {String(i + 1).padStart(2, "0")}
                </span>
                <span>{t}</span>
              </li>
            ))}
          </ol>
        </div>
      </div>

      {/* Footer */}
      <div
        style={{
          position: "absolute",
          bottom: 24,
          left: 56,
          right: 56,
          paddingTop: 14,
          borderTop: "1px solid var(--line)",
          display: "flex",
          justifyContent: "space-between",
          fontSize: 9.5,
          color: "var(--ink-4)",
        }}
      >
        <span>Woodhurst Consulting · Data &amp; Digital Advisory</span>
        <span className="mono">CONFIDENTIAL · PAGE 01 / 01</span>
      </div>
    </div>
  );
}
