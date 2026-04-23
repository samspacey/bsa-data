import { useMemo, useState } from "react";
import { ProductMark } from "../components/brand/WoodhurstMark";
import { SocietyLogo } from "../components/brand/SocietyLogo";
import { Icon } from "../components/brand/Icons";
import { societies, type Society } from "../data/societies";

interface Props {
  onSelect: (society: Society) => void;
}

export function SocietySelection({ onSelect }: Props) {
  const [query, setQuery] = useState("");
  const [region, setRegion] = useState("All");

  const regions = useMemo(() => {
    const set = new Set<string>();
    societies.forEach(s => set.add(s.region));
    return ["All", ...Array.from(set).sort()];
  }, []);

  const filtered = societies.filter(s => {
    const q = query.toLowerCase();
    return (
      (region === "All" || s.region === region) &&
      (!q || s.name.toLowerCase().includes(q) || s.short.toLowerCase().includes(q))
    );
  });

  return (
    <div style={{ width: "100%", minHeight: "100vh", background: "var(--paper)", fontFamily: "var(--font-sans)", color: "var(--ink)" }}>
      <header style={{ padding: "22px 48px", display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid var(--line)", background: "#FFFFFF" }}>
        <ProductMark size={18} />
        <div style={{ display: "flex", alignItems: "center", gap: 20, fontSize: 13, color: "var(--ink-3)" }}>
          <span className="mono" style={{ color: "var(--coral)", fontWeight: 600 }}>STEP 01 / 02</span>
          <span style={{ width: 1, height: 14, background: "var(--line)" }} />
          <span className="mono">CHOOSE A SOCIETY</span>
        </div>
      </header>

      <div style={{ padding: "56px 48px 32px", display: "grid", gridTemplateColumns: "1.1fr 1fr", gap: 48, alignItems: "end", borderBottom: "1px solid var(--line)", background: "#FFFFFF" }}>
        <div>
          <div className="eyebrow" style={{ color: "var(--coral)", marginBottom: 16 }}>Begin a conversation</div>
          <h1 style={{ fontSize: 68, lineHeight: 0.98, fontWeight: 800, letterSpacing: "-0.035em", margin: 0, color: "var(--navy)" }}>
            Which society<br />are <span style={{ color: "var(--coral)" }}>you</span>?
          </h1>
          <p style={{ fontSize: 17, color: "var(--ink-2)", maxWidth: 520, marginTop: 20, lineHeight: 1.5, fontWeight: 400 }}>
            Pick the building society you'd like to hear from. We'll load its members, products, recent press and review themes.
          </p>
        </div>
        <div>
          <div style={{ position: "relative" }}>
            <div style={{ position: "absolute", left: 20, top: "50%", transform: "translateY(-50%)", color: "var(--navy-3)" }}>
              <Icon.Search width="18" height="18" />
            </div>
            <input
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="Search by name or region…"
              style={{
                width: "100%",
                padding: "16px 20px 16px 50px",
                background: "var(--paper-2)",
                border: "1.5px solid transparent",
                borderRadius: 999,
                fontFamily: "var(--font-sans)",
                fontSize: 15,
                color: "var(--ink)",
                outline: "none",
                fontWeight: 500,
              }}
            />
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 14 }}>
            {regions.map(r => (
              <button
                key={r}
                onClick={() => setRegion(r)}
                style={{
                  background: region === r ? "var(--navy)" : "transparent",
                  color: region === r ? "#FFFFFF" : "var(--ink-2)",
                  border: `1px solid ${region === r ? "var(--navy)" : "var(--line-2)"}`,
                  padding: "6px 14px",
                  borderRadius: 999,
                  fontFamily: "var(--font-sans)",
                  fontSize: 12.5,
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                {r}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div style={{ padding: "32px 48px 56px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 18 }}>
          <div className="eyebrow">{filtered.length} of {societies.length} societies</div>
          <div className="eyebrow">BSA members</div>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 12 }}>
          {filtered.map(s => (
            <button
              key={s.id}
              onClick={() => onSelect(s)}
              style={{
                background: "#FFFFFF",
                border: "1px solid var(--line)",
                borderRadius: 14,
                padding: "22px 22px 20px",
                textAlign: "left",
                cursor: "pointer",
                transition: "all 0.2s",
                fontFamily: "inherit",
                color: "inherit",
              }}
              onMouseOver={e => {
                e.currentTarget.style.borderColor = "var(--navy)";
                e.currentTarget.style.transform = "translateY(-2px)";
                e.currentTarget.style.boxShadow = "0 8px 20px -8px rgba(30,32,95,0.15)";
              }}
              onMouseOut={e => {
                e.currentTarget.style.borderColor = "var(--line)";
                e.currentTarget.style.transform = "none";
                e.currentTarget.style.boxShadow = "none";
              }}
            >
              <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12 }}>
                <SocietyLogo society={s} size={44} />
                <span className="mono" style={{ color: "var(--ink-4)", fontSize: 9.5 }}>EST · {s.founded}</span>
              </div>
              <div style={{ marginTop: 18 }}>
                <div style={{ fontWeight: 700, fontSize: 17, letterSpacing: "-0.01em", lineHeight: 1.15, color: "var(--navy)" }}>{s.short}</div>
                <div style={{ fontSize: 12.5, color: "var(--ink-3)", marginTop: 6 }}>{s.region}</div>
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
