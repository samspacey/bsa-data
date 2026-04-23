import { ProductMark } from "../components/brand/WoodhurstMark";
import { SocietyLogo } from "../components/brand/SocietyLogo";
import { Monogram } from "../components/brand/Monogram";
import { Icon } from "../components/brand/Icons";
import type { Society } from "../data/societies";
import { archetypes, type Archetype } from "../data/archetypes";

interface Props {
  society: Society;
  onBack: () => void;
  onSelect: (archetype: Archetype) => void;
}

export function PersonaSelection({ society, onBack, onSelect }: Props) {
  return (
    <div style={{ width: "100%", minHeight: "100vh", background: "var(--paper)", fontFamily: "var(--font-sans)", color: "var(--ink)" }}>
      <header style={{ padding: "22px 48px", display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid var(--line)", background: "#FFFFFF" }}>
        <ProductMark size={18} />
        <div style={{ display: "flex", alignItems: "center", gap: 20, fontSize: 13, color: "var(--ink-3)" }}>
          <span className="mono" style={{ color: "var(--coral)", fontWeight: 600 }}>STEP 02 / 02</span>
          <span style={{ width: 1, height: 14, background: "var(--line)" }} />
          <span className="mono">CHOOSE A MEMBER</span>
        </div>
      </header>

      <div style={{ padding: "20px 48px", display: "flex", alignItems: "center", gap: 16, borderBottom: "1px solid var(--line)", background: "var(--navy-bg)" }}>
        <button
          onClick={onBack}
          style={{
            background: "transparent",
            border: "none",
            cursor: "pointer",
            color: "var(--ink-3)",
            display: "inline-flex",
            alignItems: "center",
            gap: 6,
            fontSize: 13,
            fontWeight: 600,
            fontFamily: "inherit",
          }}
        >
          <Icon.Back /> Back to societies
        </button>
        <span style={{ width: 1, height: 16, background: "var(--line-2)" }} />
        <SocietyLogo society={society} size={36} />
        <div>
          <div style={{ fontSize: 17, fontWeight: 700, letterSpacing: "-0.01em", color: "var(--navy)" }}>{society.name}</div>
          <div style={{ fontSize: 12, color: "var(--ink-3)", marginTop: 2 }}>{society.region} · Founded {society.founded}</div>
        </div>
      </div>

      <div style={{ padding: "64px 48px 32px", textAlign: "center" }}>
        <div className="eyebrow" style={{ color: "var(--coral)", marginBottom: 14 }}>Four archetypes · drawn from research</div>
        <h1 style={{ fontSize: 58, fontWeight: 800, letterSpacing: "-0.035em", margin: 0, lineHeight: 1, color: "var(--navy)" }}>
          Who would you like <span style={{ color: "var(--coral)" }}>to meet</span>?
        </h1>
      </div>

      <div style={{ padding: "0 48px 64px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, maxWidth: 1100, margin: "0 auto" }}>
          {archetypes.map(a => (
            <div
              key={a.id}
              onClick={() => onSelect(a)}
              style={{
                background: "#FFFFFF",
                border: "1px solid var(--line)",
                borderRadius: 16,
                padding: "28px 30px",
                display: "flex",
                gap: 22,
                cursor: "pointer",
                transition: "all 0.2s",
              }}
              onMouseOver={e => {
                e.currentTarget.style.borderColor = "var(--navy)";
                e.currentTarget.style.transform = "translateY(-2px)";
              }}
              onMouseOut={e => {
                e.currentTarget.style.borderColor = "var(--line)";
                e.currentTarget.style.transform = "none";
              }}
            >
              <Monogram initials={a.initials} size={72} tone={a.tone} />
              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", alignItems: "baseline", gap: 10, marginBottom: 8 }}>
                  <div style={{ fontSize: 24, fontWeight: 800, letterSpacing: "-0.02em", color: "var(--navy)" }}>{a.name}</div>
                  <div className="mono" style={{ color: "var(--ink-3)", fontSize: 9.5 }}>AGE {a.age}</div>
                </div>
                <p style={{ fontSize: 14.5, lineHeight: 1.55, color: "var(--ink-2)", margin: 0 }}>{a.blurb}</p>
                <div style={{ marginTop: 16, display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {a.concerns.map(c => (
                    <span
                      key={c}
                      style={{
                        fontSize: 11.5,
                        fontWeight: 600,
                        color: "var(--navy)",
                        padding: "4px 10px",
                        borderRadius: 999,
                        background: "var(--navy-soft)",
                      }}
                    >
                      {c}
                    </span>
                  ))}
                </div>
                <div style={{ marginTop: 20, display: "flex", alignItems: "center", gap: 8, color: "var(--coral)", fontSize: 13, fontWeight: 700 }}>
                  Start conversation <Icon.Arrow />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
