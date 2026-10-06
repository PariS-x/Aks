"use client";

/**
 * The AKS alien.
 *
 * Built from the supplied hand drawing, not a redraw: the body is the original
 * artwork (with pupils and mouth removed), and only the face and a few marker
 * doodles change per mood. Coordinates are in the drawing's own pixel space
 * (1042 x 1409) so every overlay sits exactly where the artist's marks were.
 */
import { motion, useReducedMotion, type TargetAndTransition } from "framer-motion";
import type { CSSProperties } from "react";

export type AlienMood =
  | "neutral" | "curious" | "confused" | "suspicious" | "horrified"
  | "impressed" | "thinking" | "victory" | "panicking" | "loading";

const W = 1042;
const H = 1409;
const EYE = { L: { x: 304, y: 411 }, R: { x: 618, y: 390 } };
const MOUTH_INK = "#1d4646";
const MARKER = { stroke: "var(--alien-ink, #000)", strokeWidth: 14, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, fill: "none" };
// Marks drawn on the alien's body always stay black
const FACE = { ...MARKER, stroke: "#000" };

// Pupil offsets from each eye-white centre, per mood. [dx, dy, r]
const PUPILS: Record<AlienMood, { L: [number, number, number]; R: [number, number, number] }> = {
  neutral: { L: [2, 3, 10], R: [-3, 5, 10] },
  curious: { L: [7, 15, 12], R: [5, 16, 12] },
  confused: { L: [-9, -13, 10], R: [9, 16, 10] },
  suspicious: { L: [13, 10, 10], R: [12, 11, 10] },
  horrified: { L: [0, 0, 5], R: [0, 0, 5] },
  impressed: { L: [0, -12, 13], R: [-2, -12, 13] },
  thinking: { L: [10, -14, 10], R: [10, -15, 10] },
  victory: { L: [0, 0, 0], R: [0, 0, 0] },
  panicking: { L: [-6, 2, 5], R: [7, -1, 5] },
  loading: { L: [0, 22, 10], R: [0, 22, 10] },
};

const MOUTHS: Record<string, string> = {
  // The artist's original frown, traced from the drawing
  frown: "M430 615 C 440 600 448 585 455 560 C 460 542 468 532 478 534 C 490 536 500 560 510 590 C 515 606 520 612 534 610",
  squiggle: "M425 590 C 440 570 455 610 470 590 C 485 570 500 610 515 590 C 525 578 532 586 538 592",
  flat: "M440 590 C 470 594 500 588 528 592",
  zigzag: "M425 600 L 445 580 L 465 605 L 485 578 L 505 606 L 525 582 L 538 596",
};

function Mouth({ mood }: { mood: AlienMood }) {
  const s = { stroke: MOUTH_INK, strokeWidth: 10, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, fill: "none" };
  switch (mood) {
    case "horrified":
      return <path d="M450 560 C 430 600 445 655 482 652 C 520 650 528 598 508 562 C 494 538 462 538 450 560 Z" fill="#102a2a" stroke={MOUTH_INK} strokeWidth={10} />;
    case "impressed":
      return <ellipse cx={480} cy={585} rx={18} ry={22} fill="#102a2a" stroke={MOUTH_INK} strokeWidth={9} />;
    case "victory":
      return <path d="M420 560 C 430 640 535 645 545 556 C 500 570 462 570 420 560 Z" fill="#102a2a" stroke={MOUTH_INK} strokeWidth={10} strokeLinejoin="round" />;
    case "confused":
      return <path d={MOUTHS.squiggle} {...s} />;
    case "thinking":
    case "loading":
      return <path d={MOUTHS.flat} {...s} />;
    case "panicking":
      return <path d={MOUTHS.zigzag} {...s} />;
    default:
      return <path d={MOUTHS.frown} {...s} />;
  }
}

function Eyes({ mood }: { mood: AlienMood }) {
  if (mood === "victory") {
    // Eyes squeezed shut with joy: teal lids over the whites, marker arcs
    return (
      <g>
        <ellipse cx={EYE.L.x} cy={EYE.L.y} rx={32} ry={42} fill="#357a7a" />
        <ellipse cx={EYE.R.x} cy={EYE.R.y} rx={32} ry={42} fill="#357a7a" />
        <path d="M276 425 Q 304 380 334 425" {...FACE} strokeWidth={11} />
        <path d="M590 404 Q 618 359 648 404" {...FACE} strokeWidth={11} />
      </g>
    );
  }
  const p = PUPILS[mood];
  return (
    <g>
      <circle cx={EYE.L.x + p.L[0]} cy={EYE.L.y + p.L[1]} r={p.L[2]} fill="#b8407d" />
      <circle cx={EYE.R.x + p.R[0]} cy={EYE.R.y + p.R[1]} r={p.R[2]} fill="#b8407d" />
      {mood === "suspicious" && (
        <g>
          {/* heavy lids */}
          <path d="M268 392 L 340 392 L 340 370 L 268 370 Z" fill="#357a7a" />
          <path d="M582 372 L 654 372 L 654 350 L 582 350 Z" fill="#357a7a" />
          <path d="M268 396 L 340 402" {...FACE} strokeWidth={10} />
          <path d="M582 384 L 654 374" {...FACE} strokeWidth={10} />
        </g>
      )}
      {mood === "confused" && <path d="M262 352 C 282 336 312 338 336 352" {...FACE} strokeWidth={9} />}
      {mood === "horrified" && (
        <g>
          <path d="M262 350 L 336 336" {...FACE} strokeWidth={9} />
          <path d="M582 318 L 652 334" {...FACE} strokeWidth={9} />
        </g>
      )}
    </g>
  );
}

function QuestionMark({ x, y, s = 1, color = "var(--alien-ink, #000)" }: { x: number; y: number; s?: number; color?: string }) {
  return (
    <g transform={`translate(${x} ${y}) scale(${s})`}>
      <path d="M-34 -40 C -34 -86 44 -92 44 -44 C 44 -10 4 -6 4 26" {...MARKER} stroke={color} strokeWidth={18} />
      <circle cx={4} cy={66} r={11} fill={color} />
    </g>
  );
}

function Extras({ mood }: { mood: AlienMood }) {
  switch (mood) {
    case "confused":
      return (
        <g>
          <QuestionMark x={820} y={190} s={1.2} />
          <QuestionMark x={150} y={170} s={0.8} color="#d63cf5" />
        </g>
      );
    case "thinking":
      return (
        <g>
          <QuestionMark x={850} y={140} s={0.9} />
          {/* little orbit diagram doodle */}
          <circle cx={150} cy={170} r={36} {...MARKER} strokeWidth={9} />
          <ellipse cx={150} cy={170} rx={90} ry={30} transform="rotate(-20 150 170)" {...MARKER} strokeWidth={8} strokeDasharray="20 18" />
          <circle cx={232} cy={140} r={10} fill="var(--alien-ink, #000)" />
        </g>
      );
    case "impressed":
      return (
        <g {...MARKER} strokeWidth={12}>
          <path d="M150 140 L 150 230 M105 185 L 195 185" />
          <path d="M880 120 L 880 190 M845 155 L 915 155" />
          <path d="M920 300 L 960 300 M940 280 L 940 320" stroke="#d63cf5" />
          <path d="M90 330 L 120 300 M90 300 L 120 330" />
        </g>
      );
    case "horrified":
      return (
        <g {...MARKER} strokeWidth={12}>
          <path d="M170 220 L 120 170 M200 190 L 185 120 M150 270 L 85 255" />
          <path d="M840 200 L 900 150 M820 160 L 840 95 M860 260 L 930 250" />
          <text x={860} y={420} fontFamily="Archivo Variable" fontWeight={900} fontSize={130} fill="#ff2e1f" stroke="#000" strokeWidth={6}>!</text>
        </g>
      );
    case "panicking":
      return (
        <g>
          <path d="M800 300 C 780 350 790 380 815 380 C 840 380 845 350 800 300 Z" fill="#fff" stroke="#000" strokeWidth={9} />
          <path d="M210 330 C 192 372 200 398 222 398 C 244 398 248 372 210 330 Z" fill="#fff" stroke="#000" strokeWidth={9} />
          <path d="M860 220 L 920 200 M870 260 L 935 262" {...MARKER} strokeWidth={10} />
        </g>
      );
    case "victory":
      return (
        <g>
          <path d="M120 120 L 140 200 L 200 210 L 150 250 L 170 320 L 120 280 L 70 320 L 90 250 L 40 210 L 100 200 Z" fill="#8cf44a" stroke="#000" strokeWidth={10} strokeLinejoin="round" />
          <path d="M880 80 L 895 140 L 945 148 L 905 178 L 920 232 L 880 202 L 840 232 L 855 178 L 815 148 L 865 140 Z" fill="#d63cf5" stroke="#000" strokeWidth={10} strokeLinejoin="round" />
          <path d="M760 1000 Q 900 900 990 820" {...MARKER} strokeWidth={10} strokeDasharray="4 30" />
        </g>
      );
    case "loading":
      return (
        <g>
          <rect x={300} y={1180} width={440} height={60} fill="#fff" stroke="#000" strokeWidth={10} />
          <rect x={312} y={1192} width={170} height={36} fill="#000">
            <animate attributeName="width" values="40;400;40" dur="2.4s" repeatCount="indefinite" />
          </rect>
        </g>
      );
    default:
      return null;
  }
}

function pose(mood: AlienMood, reduce: boolean): TargetAndTransition {
  if (reduce) return { rotate: 0, y: 0, x: 0, scale: 1 };
  switch (mood) {
    case "curious":
      return { rotate: 7, x: 6, y: 4, transition: { type: "spring", stiffness: 140, damping: 12 } };
    case "confused":
      return { rotate: [-4, 4, -2], transition: { duration: 1.4, repeat: Infinity, repeatType: "mirror" } };
    case "suspicious":
      return { rotate: -6, x: -8, scaleX: 0.97, transition: { type: "spring", stiffness: 120, damping: 14 } };
    case "horrified":
      return { scaleY: [1, 0.9, 1.06, 1], scaleX: [1, 1.08, 0.96, 1], y: [0, 8, -6, 0], transition: { duration: 0.5 } };
    case "impressed":
      return { y: [0, -18, 0], rotate: [0, -3, 0], transition: { duration: 0.6 } };
    case "thinking":
      return { rotate: [-3, 3], transition: { duration: 2.2, repeat: Infinity, repeatType: "mirror", ease: "easeInOut" } };
    case "victory":
      return { y: [0, -50, 0, -30, 0], rotate: [0, -10, 8, -4, 0], scale: [1, 1.05, 1, 1.03, 1], transition: { duration: 1.3, repeat: Infinity, repeatDelay: 0.6 } };
    case "panicking":
      return { x: [-3, 3, -2, 2, 0], rotate: [-2, 2, -1, 1, 0], transition: { duration: 0.25, repeat: Infinity } };
    case "loading":
      return { rotate: 3, y: 6 };
    default:
      return { rotate: 0, x: 0, y: 0, scale: 1 };
  }
}

const LABELS: Record<AlienMood, string> = {
  neutral: "The alien, watching you.",
  curious: "The alien leans in, curious.",
  confused: "The alien looks confused. Question marks float around it.",
  suspicious: "The alien squints at your answer, suspicious.",
  horrified: "The alien recoils in horror.",
  impressed: "The alien looks impressed.",
  thinking: "The alien is thinking.",
  victory: "The alien celebrates. It understands.",
  panicking: "The alien is panicking. Time is running out.",
  loading: "The alien stares at a progress bar.",
};

export function Alien({
  mood = "neutral",
  className = "",
  style,
  decorative = false,
  onDark = false,
}: {
  mood?: AlienMood;
  /** Draw the marker doodles in paper colour so they read on black. */
  onDark?: boolean;
  className?: string;
  style?: CSSProperties;
  decorative?: boolean;
}) {
  const reduce = !!useReducedMotion();
  return (
    <motion.div
      className={className}
      style={{ transformOrigin: "50% 90%", ["--alien-ink" as string]: onDark ? "#ecebe6" : "#000", ...style }}
      animate={pose(mood, reduce)}
      role={decorative ? undefined : "img"}
      aria-label={decorative ? undefined : LABELS[mood]}
      aria-hidden={decorative || undefined}
    >
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" height="100%" style={{ overflow: "visible", display: "block" }}>
        <defs>
          <filter id="aks-wobble">
            <feTurbulence type="fractalNoise" baseFrequency="0.015" numOctaves="2" seed="7" />
            <feDisplacementMap in="SourceGraphic" scale="9" />
          </filter>
        </defs>
        <image href="/alien/alien-base.png" x={0} y={0} width={W} height={H} />
        <g filter="url(#aks-wobble)">
          <Eyes mood={mood} />
          <Mouth mood={mood} />
          <Extras mood={mood} />
        </g>
      </svg>
    </motion.div>
  );
}
