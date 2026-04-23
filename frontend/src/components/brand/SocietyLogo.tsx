import { useState } from "react";
import type { Society } from "../../data/societies";

interface Props {
  society: Society;
  size?: number;
}

/**
 * Renders the real logo for a building society, sourced from Google's favicon
 * service (high resolution). Falls back to a clean branded monogram disc if
 * the network logo fails to load.
 */
export function SocietyLogo({ society, size = 56 }: Props) {
  const [failed, setFailed] = useState(false);
  const hue = society.hue ?? 240;
  const bg = `oklch(0.96 0.03 ${hue})`;
  const ring = `oklch(0.78 0.08 ${hue})`;
  const ink = `oklch(0.30 0.13 ${hue})`;

  // Request larger than needed for sharp rendering on retina. 256 is the max
  // Google's service serves reliably.
  const px = Math.max(128, Math.ceil(size * 2));
  const logoUrl = `https://www.google.com/s2/favicons?domain=${society.domain}&sz=${Math.min(px, 256)}`;

  // Monogram fallback — two letters for multi-word names.
  const words = society.short.split(/[\s&-]+/).filter(Boolean);
  const initials =
    words.length > 1
      ? (words[0][0] + words[1][0]).toUpperCase()
      : words[0][0].toUpperCase();
  const isDouble = initials.length > 1;

  return (
    <div
      style={{
        position: "relative",
        width: size,
        height: size,
        flexShrink: 0,
        borderRadius: "50%",
        background: "#FFFFFF",
        border: `1px solid ${ring}`,
        boxShadow: "0 1px 0 rgba(15,16,51,0.04)",
        overflow: "hidden",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
      aria-label={`${society.short} logo`}
    >
      {!failed ? (
        <img
          src={logoUrl}
          alt={`${society.short} logo`}
          onError={() => setFailed(true)}
          style={{
            width: size * 0.72,
            height: size * 0.72,
            objectFit: "contain",
            display: "block",
          }}
        />
      ) : (
        <svg width={size} height={size} viewBox="0 0 100 100" style={{ position: "absolute", inset: 0 }}>
          <circle cx="50" cy="50" r="48" fill={bg} stroke={ring} strokeWidth="1" />
          <circle cx="50" cy="50" r="42" fill="none" stroke={ring} strokeWidth="0.5" opacity="0.5" />
          <text
            x="50"
            y="52"
            dominantBaseline="central"
            textAnchor="middle"
            fontFamily="var(--font-sans)"
            fontWeight="700"
            fontSize={isDouble ? 36 : 46}
            letterSpacing={isDouble ? "-2" : "-1"}
            fill={ink}
          >
            {initials}
          </text>
        </svg>
      )}
    </div>
  );
}
