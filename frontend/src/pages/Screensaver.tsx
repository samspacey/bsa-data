import { useCallback, useEffect, useRef, useState } from "react";
import { WoodhurstMark } from "../components/brand/WoodhurstMark";
import { SocietyLogo } from "../components/brand/SocietyLogo";
import { Icon } from "../components/brand/Icons";
import { societies, findSociety } from "../data/societies";
import { screensaverQuotes as fallbackQuotes } from "../data/reviews";
import { fetchFeaturedReviews } from "../api/client";
import type { FeaturedReview } from "../api/types";

/**
 * Display quote shape used by the screensaver card. Whether the source is
 * a live DB review or the hardcoded fallback, we render from the same shape.
 */
interface DisplayQuote {
  q: string;
  who: string;
  where: string;
  societyId: string;
}

function formatWho(rating: number): string {
  // Real reviews don't have author age/identity - surface sentiment tone
  if (rating <= 2) return "A member · 2026";
  if (rating >= 4) return "A satisfied member · 2026";
  return "A member · 2026";
}

function formatWhere(r: FeaturedReview): string {
  const date = new Date(r.review_date).toLocaleDateString("en-GB", { month: "short", year: "numeric" });
  const sourceName: Record<string, string> = {
    trustpilot: "Trustpilot",
    smartmoneypeople: "Smart Money People",
    feefo: "Feefo",
    app_store: "App Store",
    play_store: "Play Store",
    reddit: "Reddit",
    mse: "MoneySavingExpert",
    google: "Google Reviews",
    fairer_finance: "Fairer Finance",
    which: "Which?",
  };
  const src = sourceName[r.source_id] || r.source_id;
  return `${src} · ${date}`;
}

function reviewToDisplay(r: FeaturedReview): DisplayQuote {
  return {
    q: r.quote,
    who: formatWho(r.rating),
    where: formatWhere(r),
    societyId: r.society_id,
  };
}

function NodeWeb() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const parent = canvas.parentElement;
    const W = canvas.width = parent?.clientWidth || 1440;
    const H = canvas.height = parent?.clientHeight || 900;
    const N = 62;
    const rand = (a: number, b: number) => a + Math.random() * (b - a);

    type Node = { x: number; y: number; vx: number; vy: number; r: number; pulse: number; hub: boolean };
    const nodes: Node[] = Array.from({ length: N }, () => ({
      x: Math.random() * W,
      y: Math.random() * H,
      vx: rand(-0.28, 0.28),
      vy: rand(-0.28, 0.28),
      r: rand(1.1, 2.6),
      pulse: Math.random() * Math.PI * 2,
      hub: Math.random() < 0.18,
    }));

    type Packet = { from: Node; to: Node; t: number; speed: number; hue: "coral" | "white" };
    const packets: Packet[] = [];
    const spawnPacket = () => {
      const a = nodes[Math.floor(Math.random() * N)];
      const candidates = nodes
        .map(b => ({ b, d: Math.hypot(a.x - b.x, a.y - b.y) }))
        .filter(c => c.b !== a && c.d < 260 && c.d > 40)
        .sort((x, y) => x.d - y.d);
      if (!candidates.length) return;
      const pick = candidates[Math.floor(Math.random() * Math.min(4, candidates.length))];
      packets.push({ from: a, to: pick.b, t: 0, speed: rand(0.006, 0.013), hue: Math.random() < 0.55 ? "coral" : "white" });
    };
    for (let i = 0; i < 14; i++) spawnPacket();

    let raf: number;
    const LINK = 190;
    const tick = () => {
      ctx.clearRect(0, 0, W, H);

      for (const n of nodes) {
        n.x += n.vx; n.y += n.vy;
        if (n.x < -20) n.x = W + 20;
        if (n.x > W + 20) n.x = -20;
        if (n.y < -20) n.y = H + 20;
        if (n.y > H + 20) n.y = -20;
        n.pulse += 0.018;
      }

      for (let i = 0; i < N; i++) {
        for (let j = i + 1; j < N; j++) {
          const a = nodes[i], b = nodes[j];
          const dx = a.x - b.x, dy = a.y - b.y;
          const d = Math.sqrt(dx * dx + dy * dy);
          if (d < LINK) {
            const t = 1 - d / LINK;
            const alpha = Math.pow(t, 1.6) * 0.55;
            const weight = 0.35 + t * 1.5;
            if (t > 0.55) ctx.strokeStyle = `rgba(255,87,115,${alpha})`;
            else if (t > 0.25) ctx.strokeStyle = `rgba(220,228,255,${alpha * 0.75})`;
            else ctx.strokeStyle = `rgba(150,170,240,${alpha * 0.45})`;
            ctx.lineWidth = weight;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y);
            ctx.stroke();
          }
        }
      }

      for (let i = packets.length - 1; i >= 0; i--) {
        const p = packets[i];
        p.t += p.speed;
        if (p.t >= 1) { packets.splice(i, 1); continue; }
        const x = p.from.x + (p.to.x - p.from.x) * p.t;
        const y = p.from.y + (p.to.y - p.from.y) * p.t;
        const tailT = Math.max(0, p.t - 0.12);
        const tx = p.from.x + (p.to.x - p.from.x) * tailT;
        const ty = p.from.y + (p.to.y - p.from.y) * tailT;
        const grad = ctx.createLinearGradient(tx, ty, x, y);
        const base = p.hue === "coral" ? "255,87,115" : "255,255,255";
        grad.addColorStop(0, `rgba(${base},0)`);
        grad.addColorStop(1, `rgba(${base},0.95)`);
        ctx.strokeStyle = grad;
        ctx.lineWidth = 1.6;
        ctx.lineCap = "round";
        ctx.beginPath();
        ctx.moveTo(tx, ty); ctx.lineTo(x, y);
        ctx.stroke();
        ctx.fillStyle = p.hue === "coral" ? "rgba(255,87,115,1)" : "rgba(255,255,255,1)";
        ctx.beginPath();
        ctx.arc(x, y, 2.2, 0, Math.PI * 2);
        ctx.fill();
      }
      if (packets.length < 18 && Math.random() < 0.12) spawnPacket();

      for (const n of nodes) {
        const glow = 0.5 + Math.sin(n.pulse) * 0.4;
        if (n.hub) {
          const halo = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, 14);
          halo.addColorStop(0, `rgba(255,87,115,${0.35 * glow})`);
          halo.addColorStop(1, "rgba(255,87,115,0)");
          ctx.fillStyle = halo;
          ctx.beginPath();
          ctx.arc(n.x, n.y, 14, 0, Math.PI * 2);
          ctx.fill();
          ctx.fillStyle = `rgba(255,87,115,0.9)`;
          ctx.beginPath();
          ctx.arc(n.x, n.y, n.r + 0.6, 0, Math.PI * 2);
          ctx.fill();
        } else {
          ctx.fillStyle = `rgba(255,255,255,${0.45 + glow * 0.3})`;
          ctx.beginPath();
          ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
          ctx.fill();
        }
      }
      raf = requestAnimationFrame(tick);
    };
    tick();

    const onResize = () => {
      canvas.width = parent?.clientWidth || 1440;
      canvas.height = parent?.clientHeight || 900;
    };
    window.addEventListener("resize", onResize);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
    };
  }, []);

  return <canvas ref={canvasRef} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", opacity: 0.95 }} />;
}

interface Props {
  onEnter: () => void;
}

const BATCH_SIZE = 30;
const CYCLE_MS = 5500;

export function Screensaver({ onEnter }: Props) {
  const [i, setI] = useState(0);
  const [quotes, setQuotes] = useState<DisplayQuote[]>(fallbackQuotes);
  const fetchingRef = useRef(false);

  // `/reviews/featured` orders by `func.random()` on the backend so each call
  // returns a fresh random slice. We fetch BATCH_SIZE, cycle through them,
  // and refetch another batch when we wrap - giving the screensaver
  // effectively unbounded variety without ever loading 14k rows at once.
  const loadBatch = useCallback(async () => {
    if (fetchingRef.current) return;
    fetchingRef.current = true;
    try {
      const reviews = await fetchFeaturedReviews(BATCH_SIZE);
      if (reviews.length > 0) {
        setQuotes(reviews.map(reviewToDisplay));
        setI(0);
      }
    } catch (err) {
      console.warn("featured reviews fetch failed", err);
    } finally {
      fetchingRef.current = false;
    }
  }, []);

  // Initial fetch on mount.
  useEffect(() => {
    loadBatch();
  }, [loadBatch]);

  useEffect(() => {
    if (quotes.length === 0) return;
    const t = setInterval(() => {
      setI(v => {
        const next = v + 1;
        // At the end of the current batch, pull a fresh random slice.
        if (next >= quotes.length) {
          loadBatch();
          return 0;
        }
        return next;
      });
    }, CYCLE_MS);
    return () => clearInterval(t);
  }, [quotes.length, loadBatch]);

  const q = quotes[i % quotes.length] || fallbackQuotes[0];
  const soc = findSociety(q.societyId);

  return (
    <div
      onClick={onEnter}
      style={{
        width: "100%",
        height: "100vh",
        background: "var(--navy)",
        position: "relative",
        overflow: "hidden",
        fontFamily: "var(--font-sans)",
        color: "#FFFFFF",
        cursor: "pointer",
      }}
    >
      <div style={{ position: "absolute", inset: 0, pointerEvents: "none", zIndex: 0 }}>
        <NodeWeb />
      </div>

      <div style={{ position: "absolute", inset: 0, background: "radial-gradient(ellipse at 28% 48%, rgba(30,32,95,0.35) 0%, rgba(15,16,51,0.55) 70%)", pointerEvents: "none", zIndex: 1 }} />

      <div style={{ position: "absolute", top: 0, left: 0, right: 0, padding: "30px 48px", display: "flex", justifyContent: "space-between", alignItems: "center", zIndex: 3 }}>
        <WoodhurstMark size={18} dark />
        <div style={{ fontFamily: "var(--font-mono)", fontSize: 10.5, letterSpacing: "0.14em", color: "rgba(255,255,255,0.55)", textTransform: "uppercase" }}>
          BSA Conference 2026
        </div>
      </div>

      <div style={{ padding: "min(18vh, 180px) clamp(32px, 6vw, 96px) 0", display: "grid", gridTemplateColumns: "1.15fr 1fr", gap: 72, alignItems: "start", position: "relative", zIndex: 2 }}>
        <div>
          <div className="eyebrow" style={{ color: "var(--coral)", marginBottom: 32 }}>BSA Member Chat · by Woodhurst</div>
          <h1 style={{ fontFamily: "var(--font-sans)", fontSize: "clamp(56px, 8vw, 112px)", lineHeight: 0.94, fontWeight: 800, letterSpacing: "-0.04em", margin: 0, color: "#FFFFFF" }}>
            Talk to<br />
            <span style={{ color: "var(--coral)" }}>your members.</span>
          </h1>
          <p style={{ fontSize: 21, lineHeight: 1.45, color: "rgba(255,255,255,0.78)", maxWidth: 500, marginTop: 36, fontWeight: 400 }}>
            A simulator for boards and executives. Hear what your members actually think - in their own voice, grounded in real reviews and public data.
          </p>

          <div style={{ marginTop: 56, display: "flex", alignItems: "center", gap: 24 }}>
            <div style={{ position: "relative" }}>
              <div
                style={{
                  position: "absolute",
                  inset: -10,
                  borderRadius: 999,
                  border: "1.5px solid var(--coral)",
                  animation: "softPulse 2.2s infinite ease-out",
                  pointerEvents: "none",
                }}
              />
              <button
                onClick={onEnter}
                style={{
                  background: "var(--coral)",
                  color: "#FFFFFF",
                  border: "none",
                  padding: "18px 34px",
                  borderRadius: 999,
                  fontSize: 17,
                  fontWeight: 700,
                  fontFamily: "var(--font-sans)",
                  cursor: "pointer",
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 10,
                }}
              >
                Click anywhere to begin
                <Icon.Arrow width="20" height="20" />
              </button>
            </div>
          </div>
        </div>

        <div style={{ paddingTop: 20 }}>
          <div className="eyebrow" style={{ color: "rgba(255,255,255,0.55)", marginBottom: 20 }}>What members are saying</div>
          <div
            key={i}
            style={{
              animation: "fadeUp 0.6s ease-out",
              background: "rgba(255,255,255,0.06)",
              border: "1px solid rgba(255,255,255,0.12)",
              borderRadius: 20,
              padding: "38px 36px 30px",
              backdropFilter: "blur(6px)",
              height: 320,
              display: "flex",
              flexDirection: "column",
            }}
          >
            <Icon.Quote style={{ color: "var(--coral)", marginBottom: 14 }} width="30" height="30" />
            <p
              style={{
                fontSize: 26,
                lineHeight: 1.3,
                color: "#FFFFFF",
                margin: 0,
                letterSpacing: "-0.015em",
                fontWeight: 500,
                textWrap: "pretty",
                flex: 1,
                display: "-webkit-box",
                WebkitLineClamp: 5,
                WebkitBoxOrient: "vertical",
                overflow: "hidden",
              }}
            >
              "{q.q}"
            </p>
            <div style={{ marginTop: 28, display: "flex", justifyContent: "space-between", alignItems: "flex-end", gap: 20 }}>
              <div>
                <div style={{ fontSize: 14, fontWeight: 700, color: "#FFFFFF" }}>{q.who}</div>
                <div style={{ fontSize: 12.5, color: "rgba(255,255,255,0.55)", marginTop: 2 }}>{q.where}</div>
                {soc && (
                  <div style={{ display: "inline-flex", alignItems: "center", gap: 10, marginTop: 12, padding: "6px 16px 6px 6px", borderRadius: 999, background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.12)" }}>
                    <SocietyLogo society={soc} size={36} />
                    <span style={{ fontSize: 12.5, fontWeight: 600, color: "rgba(255,255,255,0.85)" }}>{soc.name}</span>
                  </div>
                )}
              </div>
              <div style={{ display: "flex", gap: 4 }}>
                {/* Show up to ~18 dots to represent the current batch without
                    the row blowing up horizontally on a wide screen. */}
                {quotes.slice(0, 18).map((_, idx) => (
                  <div
                    key={idx}
                    style={{
                      width: idx === i % Math.min(quotes.length, 18) ? 22 : 5,
                      height: 5,
                      borderRadius: 3,
                      background: idx === i % Math.min(quotes.length, 18) ? "var(--coral)" : "rgba(255,255,255,0.25)",
                      transition: "all 0.4s",
                    }}
                  />
                ))}
              </div>
            </div>
          </div>

          <div style={{ marginTop: 28, display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 0, borderTop: "1px solid rgba(255,255,255,0.15)", borderBottom: "1px solid rgba(255,255,255,0.15)" }}>
            {[
              ["42", "societies"],
              ["4", "member types"],
              ["14,900+", "real reviews"],
            ].map(([n, l], idx) => (
              <div
                key={idx}
                style={{
                  padding: "22px 0",
                  textAlign: "center",
                  borderRight: idx < 2 ? "1px solid rgba(255,255,255,0.15)" : "none",
                }}
              >
                <div style={{ fontFamily: "var(--font-sans)", fontWeight: 800, fontSize: 38, letterSpacing: "-0.03em" }}>{n}</div>
                <div className="eyebrow" style={{ color: "rgba(255,255,255,0.55)", marginTop: 2 }}>{l}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          borderTop: "1px solid rgba(255,255,255,0.12)",
          background: "rgba(0,0,0,0.18)",
          padding: "18px 0",
          overflow: "hidden",
          zIndex: 2,
        }}
      >
        <div
          style={{
            display: "flex",
            gap: 48,
            animation: "marquee 60s linear infinite",
            whiteSpace: "nowrap",
            width: "max-content",
          }}
        >
          {[...societies, ...societies].map((s, idx) => (
            <div key={idx} style={{ display: "inline-flex", alignItems: "center", gap: 10, color: "rgba(255,255,255,0.85)" }}>
              <SocietyLogo society={s} size={26} />
              <span style={{ fontFamily: "var(--font-sans)", fontSize: 15, fontWeight: 600 }}>{s.short}</span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 9.5, color: "rgba(255,255,255,0.4)", letterSpacing: "0.1em" }}>EST · {s.founded}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
