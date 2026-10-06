"use client";

import { motion, useReducedMotion } from "framer-motion";
import { useEffect, useState } from "react";
import { Alien } from "@/components/alien/Alien";
import { Circled, Meta, Neon, Scribble, Tape } from "@/components/collage/Collage";
import type { GameResult, PublicState } from "@/lib/schemas";

function useReveal(count: number, stepMs = 1100) {
  const reduce = useReducedMotion();
  const [n, setN] = useState(reduce ? count : 0);
  useEffect(() => {
    if (reduce) return setN(count);
    const ids = Array.from({ length: count }, (_, i) => setTimeout(() => setN(i + 1), 600 + i * stepMs));
    return () => ids.forEach(clearTimeout);
  }, [count, stepMs, reduce]);
  return n;
}

function ScoreRow({ label, value, evidence, i }: { label: string; value: number; evidence: string; i: number }) {
  const reduce = useReducedMotion();
  return (
    <li className="grid grid-cols-[1fr_auto] items-end gap-x-4 gap-y-1 border-b-2 border-ink pb-3 sm:grid-cols-[minmax(0,15rem)_1fr_auto]">
      <span className="display text-base leading-none [font-stretch:85%] sm:text-lg">{label}</span>
      <span className="order-3 col-span-2 sm:order-none sm:col-span-1">
        <span className="relative block h-6 border-2 border-ink bg-white" aria-hidden>
          <motion.span
            className={`absolute inset-y-0 left-0 ${i % 2 ? "bg-magenta" : "bg-teal"}`}
            initial={reduce ? false : { width: 0 }}
            animate={{ width: `${value}%` }}
            transition={{ delay: 0.2 + i * 0.12, duration: 0.7, ease: "easeOut" }}
          />
        </span>
        <span className="mt-1 block text-sm text-graphite">{evidence}</span>
      </span>
      <span className="meta text-3xl font-bold tabular-nums">{value}</span>
    </li>
  );
}

export function ResultScreen({
  result, state, onNext, onExit, hasProfile,
}: { result: GameResult; state: PublicState; onNext: () => void; onExit: () => void; hasProfile: boolean }) {
  const won = result.status === "success";
  const shown = useReveal(result.verdict.length);
  const done = shown >= result.verdict.length;

  return (
    <main className="min-h-dvh bg-ink text-white">
      {/* The decision */}
      <section className="relative overflow-hidden px-4 pb-10 pt-8 md:px-8" aria-labelledby="decided">
        <h1 id="decided" className="display text-[13vw] md:text-[8.5vw]">The alien has decided.</h1>
        <div className="mt-6 grid items-center gap-8 md:grid-cols-[1.2fr_0.8fr]">
          <div className="space-y-3" aria-live="polite">
            {result.verdict.slice(0, shown).map((l, i) => (
              <motion.p
                key={i}
                initial={{ opacity: 0, x: -14, rotate: 0 }}
                animate={{ opacity: 1, x: 0, rotate: [-1, 0.8, -0.5, 1][i % 4] }}
                className="hand w-fit border-[3px] border-paper bg-paper px-4 py-2 text-2xl text-ink sm:text-3xl"
              >
                {l}
              </motion.p>
            ))}
          </div>
          <div className="relative mx-auto w-56 sm:w-72 md:w-full md:max-w-[360px]">
            <Alien mood={won ? "victory" : "confused"} onDark />
            {state.object.image_url && (
              <figure className="absolute -bottom-6 -left-10 w-28 rotate-[8deg] sm:w-36">
                <img src={state.object.image_url} alt="" className="cutout bg-white" />
                <figcaption className="label mt-2 bg-acid px-1 text-center text-sm text-ink">It was a {result.object_name}</figcaption>
              </figure>
            )}
          </div>
        </div>
      </section>

      {/* The numbers */}
      <motion.section
        initial={false}
        animate={{ opacity: done ? 1 : 0.35 }}
        className="grain bg-paper px-4 py-12 text-ink md:px-8"
        aria-labelledby="final"
      >
        <div className="grid gap-10 lg:grid-cols-[0.8fr_1.2fr]">
          <div>
            <h2 id="final" className="label text-xl">Final score</h2>
            <div className="relative mt-2 w-fit">
              <p className="display text-[34vw] leading-[0.8] sm:text-[22vw] lg:text-[14vw]">{result.score.final}</p>
              <Circled className="-inset-6 h-[calc(100%+3rem)] w-[calc(100%+3rem)] text-magenta" />
            </div>
            <Neon tone="magenta" tilt={-2} className="mt-8 w-fit px-4 py-2">
              <p className="display text-3xl sm:text-4xl">{result.score.title}</p>
            </Neon>
            <p className="mt-3 max-w-[34ch] text-lg">{result.score.title_reason}</p>
            <Meta className="mt-6 block text-graphite">
              {result.turns} transmission{result.turns === 1 ? "" : "s"} / {result.seconds_used}s / game metrics, not a science
            </Meta>
          </div>
          <ul className="space-y-4" aria-label="Score breakdown">
            {result.score.lines.map((l, i) => (
              <ScoreRow key={l.key} label={l.label} value={l.value} evidence={l.evidence} i={i} />
            ))}
          </ul>
        </div>
      </motion.section>

      {/* What AKS noticed */}
      <section className="px-4 py-14 md:px-8" aria-labelledby="noticed">
        <div className="flex items-end gap-4">
          <h2 id="noticed" className="display text-[12vw] text-acid md:text-[6vw]">AKS noticed</h2>
          <Scribble className="mb-3 hidden w-40 text-acid sm:block" />
        </div>
        <p className="mt-1 max-w-[50ch] text-paper/80">Playful observations from this round, not a personality test.</p>
        <ul className="mt-8 grid gap-6 md:grid-cols-3">
          {result.observations.map((o, i) => (
            <li key={o.text} className="relative bg-paper p-5 pt-7 text-ink shadow-[6px_6px_0_0_#8cf44a]" style={{ transform: `rotate(${[-1.5, 1, -0.5][i % 3]}deg)` }}>
              <Tape className="-top-3 left-8" />
              <p className="text-xl font-bold leading-tight [font-stretch:95%]">{o.text}</p>
              <p className="hand mt-3 text-lg text-graphite">{o.evidence}</p>
            </li>
          ))}
        </ul>
      </section>

      {/* How the alien's mind changed */}
      {result.hypothesis_trail.length > 0 && (
        <section className="border-t-[3px] border-paper px-4 py-12 md:px-8" aria-labelledby="trail">
          <h2 id="trail" className="label text-xl text-paper">How the alien&apos;s mind changed</h2>
          <ol className="mt-5 space-y-3">
            {result.hypothesis_trail.map((h, i) => (
              <li key={i} className="grid grid-cols-[3rem_1fr_auto] items-baseline gap-3 border-b border-graphite pb-2">
                <span className="meta text-smudge">{String(i + 1).padStart(2, "0")}</span>
                <span className="hand text-xl text-paper">“{h.text}”</span>
                <span className="meta tabular-nums text-acid">{Math.round(h.confidence * 100)}%</span>
              </li>
            ))}
          </ol>
        </section>
      )}

      <section className="flex flex-wrap gap-4 px-4 pb-16 md:px-8">
        <button onClick={onNext} className="btn btn-on-dark bg-acid px-6 py-4 text-2xl text-ink">Next specimen →</button>
        <button onClick={onExit} className="btn btn-on-dark bg-paper px-6 py-4 text-xl text-ink">
          {hasProfile ? "Back to your archive" : "Back to AKS"}
        </button>
      </section>
    </main>
  );
}
