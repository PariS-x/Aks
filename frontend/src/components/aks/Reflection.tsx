"use client";

import { motion, useReducedMotion } from "framer-motion";
import { Alien } from "@/components/alien/Alien";
import { Arrow, Meta, Neon, Tape } from "@/components/collage/Collage";
import type { VisualProfile } from "@/lib/schemas";

const TILTS = [-3, 2.5, -1.5, 3.5, -2.5, 1];

const READ_AS: Record<string, string> = {
  vision: "images read",
  "text-llm": "text read, images not seen",
  keywords: "text keywords only",
  demo: "sample",
};

/** Aesthetic, motifs and a contradiction: only present when a model looked at the board. */
function ArchiveDetails({ profile }: { profile: VisualProfile }) {
  const { aesthetic, motifs, contradiction, analysis_note } = profile;
  return (
    <div className="mt-10 space-y-8">
      {aesthetic.length > 0 && (
        <section aria-labelledby="aesthetic">
          <h2 id="aesthetic" className="label text-lg">How it looks</h2>
          <ul className="mt-2 flex flex-wrap gap-2">
            {aesthetic.map((a) => (
              <li key={a} className="border-[3px] border-ink bg-white px-3 py-1 text-lg font-bold">{a}</li>
            ))}
          </ul>
        </section>
      )}
      {motifs.length > 0 && (
        <section aria-labelledby="motifs">
          <h2 id="motifs" className="label text-lg">What keeps coming back</h2>
          <ul className="mt-2 space-y-1">
            {motifs.map((m) => (
              <li key={m} className="hand text-2xl leading-tight">→ {m}</li>
            ))}
          </ul>
        </section>
      )}
      {contradiction && (
        <Neon tone="magenta" tilt={-1.5} as="section" className="relative max-w-[40ch] px-4 py-3">
          <Tape className="-top-3 right-6" tilt={4} />
          <h2 className="label text-base">A contradiction</h2>
          <p className="mt-1 text-xl font-bold leading-tight">{contradiction}</p>
        </Neon>
      )}
      {analysis_note && (
        <p role="note" className="max-w-[48ch] border-l-4 border-alarm pl-3 text-sm text-graphite">{analysis_note}</p>
      )}
    </div>
  );
}

export function Analyzing({ label }: { label: string }) {
  return (
    <main className="grid min-h-dvh place-items-center bg-paper px-6 text-ink" aria-busy="true">
      <div className="w-full max-w-md text-center">
        <Alien mood="loading" className="mx-auto w-48 sm:w-60" />
        <p className="display mt-4 text-4xl sm:text-5xl" role="status">Reading your archive</p>
        <Meta className="mt-2 block text-graphite">{label}</Meta>
      </div>
    </main>
  );
}

export function Reflection({ profile, onPlay, onBack }: { profile: VisualProfile; onPlay: () => void; onBack: () => void }) {
  const reduce = useReducedMotion();
  const themes = profile.themes.slice(0, 5);
  const max = Math.max(...themes.map((t) => t.weight), 0.01);

  return (
    <main className="grain relative min-h-dvh overflow-hidden bg-paper text-ink">
      <header className="flex items-center justify-between px-4 pt-4 md:px-8">
        <button onClick={onBack} className="display text-3xl hover:text-teal" aria-label="Back to AKS home">AKS</button>
        <Meta className="text-graphite">
          {profile.source === "demo" ? "sample archive" : "public board"} / {profile.pin_count} pins / {READ_AS[profile.analysis] ?? "read from text"}
        </Meta>
      </header>

      <section className="relative px-4 pt-6 md:px-8" aria-labelledby="archive-title">
        <p className="label text-lg">Your archive</p>
        <h1 id="archive-title" className="display mt-1 max-w-[12ch] text-[15vw] normal-case md:text-[9vw]">
          {profile.board_name || "untitled"}
        </h1>

        <div className="mt-8 grid gap-10 md:grid-cols-[1.2fr_1fr]">
          <div>
            <h2 className="sr-only">Themes AKS found</h2>
            <ul className="flex flex-wrap items-end gap-x-4 gap-y-6">
              {themes.map((t, i) => (
                <motion.li
                  key={t.name}
                  initial={reduce ? false : { opacity: 0, y: 30, rotate: 0 }}
                  animate={{ opacity: 1, y: 0, rotate: TILTS[i] }}
                  transition={{ delay: 0.15 * i, type: "spring", stiffness: 200, damping: 16 }}
                  className="relative"
                >
                  <span
                    className={`display neon block px-3 py-2 ${i % 2 ? "neon-magenta" : "neon-acid"}`}
                    style={{ fontSize: `${1.4 + (t.weight / max) * 2.6}rem` }}
                  >
                    {t.label}
                  </span>
                  <span className="sr-only">strength {Math.round(t.weight * 100)} percent</span>
                  {t.evidence[0] && (
                    <span className="hand mt-1 block max-w-[22ch] text-base text-graphite">“{t.evidence[0]}”</span>
                  )}
                </motion.li>
              ))}
            </ul>
            <div className="mt-10 max-w-[38ch] space-y-3">
              {profile.reflection.map((l) => (
                <p key={l} className="text-2xl font-bold leading-tight [font-stretch:95%] sm:text-3xl">{l}</p>
              ))}
            </div>
            <ArchiveDetails profile={profile} />
          </div>

          <div className="relative">
            <h2 className="sr-only">Some of the pins</h2>
            <ul className="columns-2 gap-3">
              {profile.sample_pins.slice(0, 8).map((p, i) => (
                <li key={i} className="mb-3 break-inside-avoid bg-ink p-2 text-paper shadow-[4px_4px_0_0_#000]" style={{ transform: `rotate(${TILTS[i % 6] / 2}deg)` }}>
                  {p.image_url && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={p.image_url}
                      alt={p.title || "A saved pin"}
                      loading="lazy"
                      referrerPolicy="no-referrer"
                      className="block w-full grayscale contrast-125"
                    />
                  )}
                  {(p.title || p.description) && (
                    <span className="label mt-1 block px-1 text-sm leading-tight">{(p.title || p.description).slice(0, 60)}</span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* Hand-off to the game: the alien has been watching */}
      <section className="relative mt-16 bg-ink px-4 pb-16 pt-10 text-white md:px-8" aria-labelledby="cta">
        <div className="grid items-end gap-6 md:grid-cols-[1fr_auto]">
          <div>
            <p className="hand text-2xl text-acid sm:text-3xl">Someone else has been looking at your archive too.</p>
            <h2 id="cta" className="display mt-3 text-[13vw] md:text-[7vw]">Want to test your creativity?</h2>
            <button onClick={onPlay} className="btn btn-on-dark mt-8 bg-magenta px-6 py-4 text-xl text-ink sm:text-2xl">
              Play Alien Explanation →
            </button>
          </div>
          <div className="relative mx-auto w-48 md:w-64">
            <Tape className="-top-2 left-10 z-10" tilt={6} />
            <Alien mood="suspicious" onDark />
            <Arrow className="absolute -left-28 top-6 hidden w-28 text-acid md:block" d="M190 20 C 120 10 50 40 15 95" head="M10 70 L 14 98 L 40 90" />
          </div>
        </div>
      </section>
    </main>
  );
}