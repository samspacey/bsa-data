interface Props {
  initials: string;
  size?: number;
  tone?: "navy" | "ink" | "coral" | "mint" | "sand" | "hue";
  hue?: number;
}

export function Monogram({ initials, size = 44, tone = "navy", hue = 30 }: Props) {
  const palettes: Record<string, { bg: string; fg: string }> = {
    navy:  { bg: "var(--navy-soft)", fg: "var(--navy)" },
    ink:   { bg: "var(--navy)", fg: "#FFFFFF" },
    coral: { bg: "var(--coral-soft)", fg: "var(--coral-2)" },
    mint:  { bg: "var(--positive-soft)", fg: "var(--positive)" },
    sand:  { bg: "var(--warning-soft)", fg: "var(--warning)" },
    hue:   { bg: `oklch(0.93 0.05 ${hue})`, fg: `oklch(0.35 0.1 ${hue})` },
  };
  const p = palettes[tone] || palettes.navy;
  return (
    <span
      className="monogram"
      style={{
        width: size,
        height: size,
        fontSize: size * 0.36,
        background: p.bg,
        color: p.fg,
      }}
    >
      {initials}
    </span>
  );
}
