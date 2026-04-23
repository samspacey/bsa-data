interface Props {
  size?: number;
  dark?: boolean;
  showWordmark?: boolean;
}

export function WoodhurstMark({ size = 18, dark = false, showWordmark = true }: Props) {
  const color = dark ? "#FFFFFF" : "#1E205F";
  const src = dark ? "/woodhurst-mark-white.png" : "/woodhurst-mark.png";
  return (
    <div style={{ display: "inline-flex", alignItems: "center", gap: 10, color, fontFamily: "var(--font-sans)", fontWeight: 700, fontSize: size, letterSpacing: "-0.015em", lineHeight: 1 }}>
      <img src={src} alt="Woodhurst" style={{ height: size * 1.15, width: "auto", display: "block" }} />
      {showWordmark && <span>Woodhurst</span>}
    </div>
  );
}

export function WoodhurstIcon({ size = 24, dark = false }: { size?: number; dark?: boolean }) {
  const src = dark ? "/woodhurst-mark-white.png" : "/woodhurst-mark.png";
  return <img src={src} alt="" style={{ height: size * 0.9, width: "auto", display: "inline-block" }} />;
}

export function ProductMark({ size = 18, dark = false }: { size?: number; dark?: boolean }) {
  const ink = dark ? "#FFFFFF" : "var(--navy)";
  const muted = dark ? "rgba(255,255,255,0.6)" : "var(--ink-3)";
  return (
    <div style={{ display: "inline-flex", alignItems: "center", gap: 12 }}>
      <WoodhurstIcon size={size * 1.3} dark={dark} />
      <div style={{ display: "inline-flex", flexDirection: "column", gap: 1 }}>
        <span style={{ fontFamily: "var(--font-sans)", fontSize: size * 0.85, fontWeight: 700, letterSpacing: "-0.015em", color: ink, lineHeight: 1 }}>Member Chat</span>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: size * 0.42, letterSpacing: "0.16em", color: muted, textTransform: "uppercase", lineHeight: 1, marginTop: 3 }}>by Woodhurst</span>
      </div>
    </div>
  );
}
