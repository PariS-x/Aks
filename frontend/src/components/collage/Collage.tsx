// Collage primitives: annotation blocks, tape, marker scribbles.
// Kept deliberately small; the layouts do the composing.
import type { CSSProperties, ReactNode } from "react";

export function Neon({
  children, tone = "acid", tilt = 0, className = "", style, as: Tag = "div",
}: {
  children: ReactNode; tone?: "acid" | "magenta"; tilt?: number; className?: string; style?: CSSProperties;
  as?: "div" | "p" | "section" | "aside" | "span";
}) {
  return (
    <Tag
      className={`neon ${tone === "acid" ? "neon-acid" : "neon-magenta"} ${className}`}
      style={{ transform: `rotate(${tilt}deg)`, ...style }}
    >
      {children}
    </Tag>
  );
}

export function Tape({ className = "", tilt = -4, style }: { className?: string; tilt?: number; style?: CSSProperties }) {
  return <span aria-hidden className={`tape absolute block h-6 w-20 ${className}`} style={{ transform: `rotate(${tilt}deg)`, ...style }} />;
}

/** Hand-drawn marker arrow. `d` is a path in a 200x120 box. */
export function Arrow({ className = "", color = "currentColor", d = "M10 100 C 60 20 130 20 180 50", head = "M160 30 L 182 52 L 154 62" }: {
  className?: string; color?: string; d?: string; head?: string;
}) {
  return (
    <svg aria-hidden viewBox="0 0 200 120" className={className} fill="none" stroke={color} strokeWidth={7} strokeLinecap="round" strokeLinejoin="round">
      <path d={d} />
      <path d={head} />
    </svg>
  );
}

/** Loose marker circle, drawn around something. */
export function Circled({ className = "", color = "currentColor" }: { className?: string; color?: string }) {
  return (
    <svg aria-hidden viewBox="0 0 300 160" preserveAspectRatio="none" className={`pointer-events-none absolute ${className}`} fill="none" stroke={color} strokeWidth={6} strokeLinecap="round">
      <path d="M40 30 C 120 -5 280 10 290 70 C 300 140 140 160 60 140 C -10 120 0 50 70 22 C 100 12 140 8 170 10" />
    </svg>
  );
}

export function Scribble({ className = "", color = "currentColor" }: { className?: string; color?: string }) {
  return (
    <svg aria-hidden viewBox="0 0 200 40" className={className} fill="none" stroke={color} strokeWidth={5} strokeLinecap="round">
      <path d="M5 25 C 20 5 30 40 45 20 C 60 0 70 38 85 18 C 100 0 110 36 125 18 C 140 2 150 34 165 18 C 175 8 185 20 195 15" />
    </svg>
  );
}

/** Field-notebook metadata line, e.g. SPECIMEN 001 / LOG 14:02 */
export function Meta({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <span className={`meta text-[11px] uppercase ${className}`}>{children}</span>;
}
