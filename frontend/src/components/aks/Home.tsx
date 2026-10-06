"use client";

import { useEffect, useState, type FormEvent } from "react";
import { Alien } from "@/components/alien/Alien";
import { Meta, Neon, Tape } from "@/components/collage/Collage";
import { api } from "@/lib/api";
import type { DemoBoard } from "@/lib/schemas";

export function Home({
  onAnalyzeUrl, onDemo, onSkip, error, busy,
}: {
  onAnalyzeUrl: (url: string) => void;
  onDemo: (id: string) => void;
  onSkip: () => void;
  error: string | null;
  busy: boolean;
}) {
  const [url, setUrl] = useState("");
  const [boards, setBoards] = useState<DemoBoard[]>([]);
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    api.demoBoards().then(setBoards).catch(() => setOffline(true));
  }, []);

  function submit(e: FormEvent) {
    e.preventDefault();
    if (url.trim()) onAnalyzeUrl(url.trim());
  }

  return (
    <main className="relative min-h-dvh overflow-hidden bg-ink text-white">
      {/* Wordmark: the one loud thing */}
      <h1 className="display pointer-events-none select-none px-3 pt-6 text-[34vw] leading-[0.78] text-paper sm:text-[30vw] md:px-6 lg:text-[23vw]">
        AKS
      </h1>
      <div className="relative -mt-[3.2vw] grid gap-10 px-4 pb-56 md:grid-cols-[1.1fr_1fr] md:px-8 md:pb-24 lg:px-12">
        <section aria-labelledby="tagline">
          <p id="tagline" className="max-w-[18ch] text-white mix-blend-difference text-3xl font-black leading-[1.02] [font-stretch:110%] sm:text-4xl lg:text-5xl">
            What you save reflects you. What you create reveals you.
          </p>
          <form onSubmit={submit} className="mt-8 max-w-xl">
            <label htmlFor="board" className="label block text-lg text-paper">
              Paste a public Pinterest board
            </label>
            <div className="mt-2 flex flex-col gap-3 sm:flex-row">
              <input
                id="board"
                type="url"
                inputMode="url"
                autoComplete="off"
                placeholder="pinterest.com/you/your-board"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                className="min-w-0 flex-1 border-[3px] border-paper bg-ink px-4 py-3 text-lg text-white placeholder:text-smudge"
                aria-describedby={error ? "board-error" : undefined}
              />
              <button type="submit" disabled={busy || !url.trim()} className="btn btn-on-dark bg-paper px-5 py-3 text-ink">
                Analyze
              </button>
            </div>
            {error && (
              <p id="board-error" role="alert" className="mt-3 inline-block bg-alarm px-2 py-1 font-bold text-white">
                {error}
              </p>
            )}
          </form>
          <button onClick={onSkip} className="label mt-8 text-base text-paper underline decoration-[3px] underline-offset-4 hover:text-acid">
            No board? Meet the alien anyway
          </button>
        </section>

        <section aria-labelledby="demo-title" className="relative md:pt-[3.5vw]">
          <h2 id="demo-title" className="label text-lg text-paper">
            Or open a sample archive
          </h2>
          {offline && (
            <p role="alert" className="mt-3 bg-alarm px-2 py-1 font-bold">The AKS server is not reachable. Start the backend on port 8000.</p>
          )}
          <ul className="mt-4 grid gap-5 sm:grid-cols-2">
            {boards.map((b, i) => (
              <li key={b.id} style={{ transform: `rotate(${[-2, 1.5, 1, -1.5][i % 4]}deg)` }}>
                <button
                  onClick={() => onDemo(b.id)}
                  disabled={busy}
                  className="grain group relative block w-full bg-paper p-4 pt-6 text-left text-ink shadow-[6px_6px_0_0_#000] outline-offset-4 hover:-translate-y-1 transition-transform"
                >
                  <Tape className="-top-3 left-6" />
                  <span className="display block text-2xl leading-none [font-stretch:90%] normal-case">{b.name}</span>
                  <span className="mt-1 block text-sm">{b.blurb}</span>
                  <span className="mt-3 flex flex-wrap gap-1">
                    {b.pins.slice(0, 4).map((p) => (
                      <span key={p} className="label bg-ink px-1.5 py-0.5 text-[11px] text-paper">{p}</span>
                    ))}
                  </span>
                  <Meta className="mt-3 block text-graphite">{b.pin_count} pins</Meta>
                </button>
              </li>
            ))}
          </ul>
        </section>
      </div>

      <div className="pointer-events-none absolute -bottom-12 left-[42%] z-20 w-[52vw] max-w-[300px] -translate-x-1/2 sm:w-[34vw] md:left-[30%] md:w-[20vw]">
        <Neon tone="magenta" tilt={-6} className="hand absolute -right-16 top-10 z-10 px-3 py-1 text-xl sm:text-2xl">
          I have questions.
        </Neon>
        <Alien mood="curious" decorative onDark />
      </div>
    </main>
  );
}
