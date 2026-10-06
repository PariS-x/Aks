"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useEffect, useState } from "react";
import { Alien } from "@/components/alien/Alien";
import { Meta, Neon, Tape } from "@/components/collage/Collage";

export const PERSONALITIES = [
  { id: "archivist", label: "Archivist", blurb: "Literal. Keeps notes." },
  { id: "skeptic", label: "Skeptic", blurb: "Suspicious of you." },
  { id: "enthusiast", label: "Enthusiast", blurb: "Delighted, lost." },
];

/* ------------------------------------------------------------ Screen 1 */

export function GameTitle({
  onBegin, busy, error, onExit, duration = 90,
}: { onBegin: (personality: string) => void; busy: boolean; error: string | null; onExit: () => void; duration?: number }) {
  const [personality, setPersonality] = useState("archivist");
  return (
    <main className="relative min-h-dvh overflow-hidden bg-ink text-white">
      {/* black/white blocks, a nod to the print references */}
      <div aria-hidden className="absolute right-0 top-0 hidden h-[46vh] w-[34vw] bg-paper md:block" />
      <div aria-hidden className="absolute bottom-0 left-0 hidden h-[24vh] w-[16vw] bg-paper md:block" />

      <header className="relative z-10 flex items-center justify-between px-4 pt-4 md:px-8">
        <button onClick={onExit} className="display text-3xl text-paper hover:text-acid" aria-label="Back to AKS">AKS</button>
        <Meta className="text-smudge md:text-ink">creativity game 01</Meta>
      </header>

      <div className="px-4 md:px-8">
        <h1 className="display relative z-30 mt-6 text-[19vw] text-white mix-blend-difference md:mt-2 md:text-[13.5vw]">
          <span className="block">Alien</span>
          <span className="block text-[9.4vw] md:text-[10vw]">Explanation</span>
        </h1>
      </div>

      <div className="pointer-events-none absolute bottom-[-3vh] left-[40vw] z-40 hidden w-[19vw] max-w-[360px] md:block">
        <Alien mood="neutral" onDark />
      </div>

      <div className="relative z-30 mt-14 grid gap-8 px-4 pb-16 md:mt-6 md:grid-cols-[1fr_1fr] md:px-8">
        <div className="space-y-5">
          <Neon tone="acid" tilt={-2} className="max-w-md px-4 py-3 text-xl font-bold leading-tight sm:text-2xl">
            An extraterrestrial has questions about Earth.
          </Neon>
          <Neon tone="magenta" tilt={1.5} className="ml-6 max-w-sm px-4 py-3 text-lg font-bold sm:text-xl">
            You have {duration} seconds to explain.
          </Neon>
        </div>

        <div className="flex flex-col items-start gap-6 md:items-end md:pt-[14vw]">
          <fieldset className="md:text-right">
            <legend className="label text-base text-paper md:ml-auto">Alien temperament</legend>
            <div className="mt-2 flex flex-wrap gap-2 md:justify-end">
              {PERSONALITIES.map((p) => (
                <label key={p.id} className={`cursor-pointer border-[3px] px-3 py-2 transition-colors ${personality === p.id ? "border-acid bg-acid text-ink" : "border-paper text-paper hover:bg-graphite"}`}>
                  <input type="radio" name="personality" value={p.id} checked={personality === p.id} onChange={() => setPersonality(p.id)} className="sr-only" />
                  <span className="label block text-lg leading-none">{p.label}</span>
                  <span className="block text-xs">{p.blurb}</span>
                </label>
              ))}
            </div>
          </fieldset>
          <button onClick={() => onBegin(personality)} disabled={busy} className="btn btn-on-dark bg-paper px-6 py-4 text-xl text-ink sm:text-3xl">
            {busy ? "Opening channel…" : "Begin transmission →"}
          </button>
          {error && <p role="alert" className="bg-alarm px-2 py-1 font-bold">{error}</p>}
          <div className="mx-auto w-[46vw] md:hidden">
            <Alien mood="neutral" onDark decorative />
          </div>
        </div>
      </div>
    </main>
  );
}

/* ------------------------------------------------------------ Screen 2 */

const GREETING = [
  "Greetings, Earth organism.",
  "I have encountered an object I cannot identify.",
  "You will explain it.",
  "Please do not use the object's human name.",
];

function useBeats(count: number, stepMs: number) {
  const reduce = useReducedMotion();
  const [n, setN] = useState(reduce ? count : 0);
  useEffect(() => {
    if (reduce) return setN(count);
    setN(0);
    const ids = Array.from({ length: count }, (_, i) => setTimeout(() => setN(i + 1), 500 + i * stepMs));
    return () => ids.forEach(clearTimeout);
  }, [count, stepMs, reduce]);
  return n;
}

export function Transmission({ onReady }: { onReady: () => void }) {
  const shown = useBeats(GREETING.length, 1000);
  const done = shown >= GREETING.length;
  return (
    <main className="grain relative grid min-h-dvh grid-rows-[auto_1fr] overflow-hidden bg-paper text-ink">
      <p className="display bg-ink px-4 py-3 text-[9vw] text-paper md:px-8 md:text-[5vw]">
        Transmission received<span className="blink" aria-hidden>_</span>
      </p>
      <div className="relative grid items-center gap-6 px-4 pb-10 md:grid-cols-[0.8fr_1.2fr] md:px-8">
        <motion.div initial={{ y: 200, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ type: "spring", stiffness: 90, damping: 14 }} className="mx-auto w-52 sm:w-72 md:w-full md:max-w-[420px]">
          <Alien mood="curious" />
        </motion.div>
        <div aria-live="polite" className="space-y-4">
          <AnimatePresence>
            {GREETING.slice(0, shown).map((line, i) => (
              <motion.p
                key={line}
                initial={{ opacity: 0, x: -20, rotate: 0 }}
                animate={{ opacity: 1, x: 0, rotate: [-1, 1, -0.5, 1.5][i] }}
                className={`hand block w-fit border-[3px] border-ink px-4 py-2 text-2xl shadow-[5px_5px_0_0_#000] sm:text-3xl lg:text-4xl ${i === 3 ? "bg-acid" : "bg-white"}`}
              >
                {line}
              </motion.p>
            ))}
          </AnimatePresence>
          <div className="pt-4">
            <button onClick={onReady} className={`btn bg-magenta px-6 py-3 text-2xl text-ink ${done ? "" : "opacity-70"}`} autoFocus>
              I&apos;m ready
            </button>
            {!done && <span className="ml-3 text-sm text-graphite">(you can skip ahead)</span>}
          </div>
        </div>
      </div>
    </main>
  );
}

/* ------------------------------------------------------------ Personalisation */

export function Personalize({ themes, reason, onGo }: { themes: string[]; reason: string; onGo: () => void }) {
  const shown = useBeats(3, 900);
  return (
    <main className="relative grid min-h-dvh items-center overflow-hidden bg-ink px-4 py-10 text-white md:px-8">
      <div className="grid items-center gap-8 md:grid-cols-[1fr_0.6fr]">
        <div className="space-y-6" aria-live="polite">
          <p className="hand text-3xl text-paper sm:text-4xl lg:text-5xl">I have examined your collection of Earth images.</p>
          {shown >= 1 && (
            <div>
              <p className="hand text-3xl text-paper sm:text-4xl lg:text-5xl">You appear to be interested in…</p>
              <ul className="mt-4 flex flex-wrap gap-3">
                {themes.map((t, i) => (
                  <motion.li key={t} initial={{ scale: 0.6, opacity: 0 }} animate={{ scale: 1, opacity: 1, rotate: [-3, 2, -1, 3][i % 4] }} transition={{ delay: i * 0.12 }}>
                    <span className={`display neon block px-3 py-2 text-3xl sm:text-5xl lg:text-6xl ${i % 2 ? "neon-magenta" : "neon-acid"}`}>{t}</span>
                  </motion.li>
                ))}
              </ul>
            </div>
          )}
          {shown >= 2 && <p className="max-w-[36ch] text-xl font-bold text-paper sm:text-2xl lg:text-3xl">{reason}</p>}
          {shown >= 3 && <p className="hand max-w-[30ch] text-3xl text-acid sm:text-4xl lg:text-5xl">I have selected an object I believe you should be able to explain.</p>}
          <button onClick={onGo} className="btn btn-on-dark bg-paper px-6 py-3 text-2xl text-ink" autoFocus>
            Show me the specimen →
          </button>
        </div>
        <div className="relative mx-auto w-56 md:w-full md:max-w-[380px]">
          <Tape className="-top-2 left-1/3 z-10" />
          <Alien mood="thinking" onDark />
        </div>
      </div>
    </main>
  );
}
