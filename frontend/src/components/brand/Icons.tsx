import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement>;

export const Icon = {
  Search: (p: IconProps) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" {...p}>
      <circle cx="10.5" cy="10.5" r="6.2" stroke="currentColor" strokeWidth="2" />
      <circle cx="10.5" cy="10.5" r="3" fill="currentColor" opacity="0.18" />
      <path d="m15.2 15.2 4.3 4.3" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
    </svg>
  ),
  Arrow: (p: IconProps) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" {...p}>
      <path d="M3 12h16.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path d="M14 6.5c1.8 2.8 3.8 4.7 5.5 5.5-1.7.8-3.7 2.7-5.5 5.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
    </svg>
  ),
  Back: (p: IconProps) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" {...p}>
      <path d="M21 12H4.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <path d="M10 6.5c-1.8 2.8-3.8 4.7-5.5 5.5 1.7.8 3.7 2.7 5.5 5.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
    </svg>
  ),
  Close: (p: IconProps) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" {...p}>
      <path d="M6.5 6.5c3.5 3.5 7.5 7.5 11 11M17.5 6.5c-3.5 3.5-7.5 7.5-11 11" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
    </svg>
  ),
  Quote: (p: IconProps) => (
    <svg width="22" height="22" viewBox="0 0 32 32" fill="currentColor" {...p}>
      <path d="M4 19c0-5 2.5-9 7-11l1.5 2.5C9.5 12 8 14 8 16h3.5c.8 0 1.5.7 1.5 1.5v6c0 .8-.7 1.5-1.5 1.5h-6c-.8 0-1.5-.7-1.5-1.5V19Zm14 0c0-5 2.5-9 7-11l1.5 2.5C23.5 12 22 14 22 16h3.5c.8 0 1.5.7 1.5 1.5v6c0 .8-.7 1.5-1.5 1.5h-6c-.8 0-1.5-.7-1.5-1.5V19Z" />
    </svg>
  ),
  Doc: (p: IconProps) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" {...p}>
      <path d="M6 3h9l4 4v13a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
      <path d="M15 3v4h4" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" />
      <path d="M8 13h8M8 16h5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" opacity="0.55" />
    </svg>
  ),
  Chart: (p: IconProps) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" {...p}>
      <rect x="3"  y="14" width="4" height="7"  rx="1" fill="currentColor" opacity="0.35" />
      <rect x="10" y="9"  width="4" height="12" rx="1" fill="currentColor" opacity="0.6" />
      <rect x="17" y="4"  width="4" height="17" rx="1" fill="currentColor" />
      <path d="M3 21h18" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" opacity="0.3" />
    </svg>
  ),
  Send: (p: IconProps) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" {...p}>
      <path d="M3.5 11.5 21 4l-7.5 17-3-7z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" fill="currentColor" fillOpacity="0.18" />
      <path d="m10.5 14 6-7" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
      <path d="M2 8h3M1 12h3" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" opacity="0.5" />
    </svg>
  ),
  Dot: (p: IconProps) => (
    <svg width="8" height="8" viewBox="0 0 8 8" fill="currentColor" {...p}>
      <circle cx="4" cy="4" r="3.5" opacity="0.25" />
      <circle cx="4" cy="4" r="1.8" />
    </svg>
  ),
  Sparkle: (p: IconProps) => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" {...p}>
      <path d="M12 2c.4 4.2 3.8 7.6 8 8-4.2.4-7.6 3.8-8 8-.4-4.2-3.8-7.6-8-8 4.2-.4 7.6-3.8 8-8Z" />
    </svg>
  ),
  Chat: (p: IconProps) => (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" {...p}>
      <path d="M4 5.5A2.5 2.5 0 0 1 6.5 3h11A2.5 2.5 0 0 1 20 5.5v9a2.5 2.5 0 0 1-2.5 2.5H11l-4 4v-4H6.5A2.5 2.5 0 0 1 4 14.5v-9Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" fill="currentColor" fillOpacity="0.12" />
      <circle cx="9" cy="10" r="1" fill="currentColor" />
      <circle cx="12" cy="10" r="1" fill="currentColor" />
      <circle cx="15" cy="10" r="1" fill="currentColor" />
    </svg>
  ),
  Filter: (p: IconProps) => (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" {...p}>
      <path d="M4 5h16l-6 8v6l-4-2v-4L4 5Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" fill="currentColor" fillOpacity="0.15" />
    </svg>
  ),
  Pin: (p: IconProps) => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" {...p}>
      <path d="M12 2a7 7 0 0 0-7 7c0 5 7 13 7 13s7-8 7-13a7 7 0 0 0-7-7Z" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" fill="currentColor" fillOpacity="0.2" />
      <circle cx="12" cy="9" r="2.2" fill="currentColor" />
    </svg>
  ),
};
