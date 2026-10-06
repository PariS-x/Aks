"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { Alien, type AlienMood } from "@/components/alien/Alien";
import { Meta, Neon, Tape } from "@/components/collage/Collage";
import { api } from "@/lib/api";
import type { Message, PublicState, Violation } from "@/lib/schemas";

const pad = (n: number) => String(n).padStart(3, "0");
const fmt = (s: number) => {
  const t = Math.ceil(s);
  return `${String(Math.floor(t / 60)).padStart(2, "0")}:${String(t % 60).padStart(2, "0")}`;
};

/* ------------------------------------------------------------ pieces */

function Timer({ left, total }: { left: number; total: number }) {
  const low = left <= 15;
  return (
    <div
      className={`meta border-[3px] border-ink px-3 py-1 text-3xl font-bold tabular-nums shadow-[4px_4px_0_0_#000] sm:text-4xl ${low ? "bg-alarm text-white" : "bg-white text-ink"} ${low && left > 0 ? "jitter" : ""}`}
      role="timer"
      aria-label={`${Math.ceil(left)} seconds remaining`}
    >
      {fmt(left)}
      <span className="sr-only">{low ? "Time is almost up." : ""}</span>
      <span aria-hidden className="block h-1 bg-current" style={{ width: `${(left / total) * 100}%`, opacity: 0.5 }} />
    </div>
  );
}

function Specimen({ state }: { state: PublicState }) {
  const o = state.object;
  return (
    <div className="relative h-full min-h-[34vh] overflow-hidden bg-ink md:min-h-0">
      <div aria-hidden className="checker absolute inset-0 opacity-90" style={{ ["--cell" as string]: "min(26vw,220px)" }} />
      <p aria-hidden className="display outline-type absolute -left-2 top-2 text-[18vw] text-white/80 mix-blend-difference md:text-[9vw]">
        Specimen
      </p>
      <div className="relative grid h-full place-items-center p-6">
        {o.image_url ? (
          <motion.img
            key={o.image_url}
            src={o.image_url}
            alt="The specimen: an everyday Earth object, shown as a black-and-white cutout. Explain what it is without naming it."
            initial={{ scale: 0.7, rotate: -18, opacity: 0 }}
            animate={{ scale: 1, rotate: -5, opacity: 1 }}
            transition={{ type: "spring", stiffness: 110, damping: 13 }}
            className="cutout relative z-10 h-auto max-h-[30vh] w-[62%] max-w-[420px] bg-white md:max-h-[44vh] md:w-[70%]"
          />
        ) : (
          <div className="relative z-10 rotate-[-4deg] border-[3px] border-ink bg-white p-6 text-ink shadow-[8px_10px_0_#000]">
            <Meta>For human eyes only</Meta>
            <p className="display mt-2 text-4xl">{o.human_only_label}</p>
          </div>
        )}
      </div>
      <Meta className="absolute bottom-3 right-3 z-20 bg-white px-2 py-1 text-ink">
        Specimen {pad(o.specimen_number)} / difficulty {"●".repeat(o.difficulty)}{"○".repeat(3 - o.difficulty)}
      </Meta>
    </div>
  );
}

function ForbiddenList({ words, hits }: { words: string[]; hits: Set<string> }) {
  return (
    <Neon tone="magenta" tilt={-2} as="aside" className="px-3 py-2">
      <p className="label text-sm">Do not say</p>
      <ul className="mt-1 flex flex-wrap gap-x-4 gap-y-1.5" aria-label="Forbidden words">
        {words.map((w) => (
          <li key={w} className={`display text-lg leading-none [font-stretch:90%] sm:text-xl ${hits.has(w) ? "bg-ink px-1 text-alarm" : ""}`}>
            <span className="line-through decoration-[3px]">{w}</span>
          </li>
        ))}
      </ul>
    </Neon>
  );
}

function Meter({ value }: { value: number }) {
  const cells = 20;
  const on = Math.round((value / 100) * cells);
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <span className="label text-base">Alien understanding</span>
        <span className="meta text-xl font-bold tabular-nums">{value}%</span>
      </div>
      <div role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={value} aria-label="Alien understanding" className="mt-1 flex gap-[3px]">
        {Array.from({ length: cells }, (_, i) => (
          <motion.span
            key={i}
            className={`h-5 flex-1 border-2 border-ink ${i < on ? (value >= 80 ? "bg-acid" : "bg-teal") : "bg-white"}`}
            animate={{ scaleY: i < on ? 1 : 0.6 }}
          />
        ))}
      </div>
    </div>
  );
}

function Hypothesis({ state }: { state: PublicState }) {
  const h = state.hypothesis;
  const solved = state.status === "success";
  const any = state.messages.some((m) => m.role === "player");
  return (
    <Neon tone="acid" tilt={1.2} as="section" className="relative px-4 py-3">
      <Tape className="-top-3 right-8" tilt={5} />
      <h2 className="label text-base">Alien hypothesis</h2>
      <AnimatePresence mode="wait">
        <motion.p
          key={h.text}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0 }}
          className="hand mt-1 text-xl leading-snug sm:text-2xl"
        >
          {any ? `“${h.text}”` : "No hypothesis yet. Possibly food. Possibly a weapon."}
        </motion.p>
      </AnimatePresence>
      <p className="meta mt-2 text-sm">
        Confidence {Math.round(h.confidence * 100)}%{solved ? " / I KNOW WHAT THIS IS." : ""}
      </p>
    </Neon>
  );
}

/* ------------------------------------------------------------ dialogue */

function AlienLines({ m, latest }: { m: Message; latest: boolean }) {
  const reduce = useReducedMotion();
  return (
    <div className="space-y-1.5">
      {m.lines.map((l, i) => {
        const shout = l === l.toUpperCase() && /[A-Z]/.test(l);
        return (
          <motion.p
            key={i}
            initial={latest && !reduce ? { opacity: 0, y: 6 } : false}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: latest && !reduce ? i * 0.55 : 0 }}
            className={`hand w-fit max-w-full border-2 border-ink px-3 py-1 text-xl leading-snug sm:text-2xl ${shout ? "bg-ink text-acid" : "bg-white"}`}
          >
            {l}
          </motion.p>
        );
      })}
    </div>
  );
}

function PlayerLine({ m }: { m: Message }) {
  const text = m.lines[0] ?? "";
  return (
    <div className="ml-auto w-fit max-w-[92%] bg-ink px-3 py-2 text-paper">
      <Meta className="block text-smudge">You</Meta>
      <p className="text-base leading-snug"><Highlighted text={text} violations={m.violations} /></p>
    </div>
  );
}

function Highlighted({ text, violations }: { text: string; violations: Violation[] }) {
  if (!violations.length) return <>{text}</>;
  const out: React.ReactNode[] = [];
  let at = 0;
  violations.forEach((v, i) => {
    out.push(text.slice(at, v.start));
    out.push(
      <mark key={i} className="forbidden">
        {text.slice(v.start, v.end)}
        <span className="sr-only"> (forbidden word)</span>
      </mark>,
    );
    at = v.end;
  });
  out.push(text.slice(at));
  return <>{out}</>;
}

/* ------------------------------------------------------------ input */

function ExplainBox({
  gameId, disabled, sending, onSend, onLive, totalWords, totalForbidden,
}: {
  gameId: string; disabled: boolean; sending: boolean;
  onSend: (t: string) => Promise<boolean>; onLive: (v: Violation[]) => void;
  totalWords: number; totalForbidden: number;
}) {
  const [text, setText] = useState("");
  const [live, setLive] = useState<Violation[]>([]);
  const backdrop = useRef<HTMLDivElement>(null);
  const area = useRef<HTMLTextAreaElement>(null);

  // Debounced server check: the same detector that scores you, so no surprises.
  useEffect(() => {
    if (!text.trim()) {
      setLive([]);
      onLive([]);
      return;
    }
    const id = setTimeout(() => {
      api.check(gameId, text).then((v) => {
        setLive(v);
        onLive(v);
      }).catch(() => {});
    }, 220);
    return () => clearTimeout(id);
  }, [text, gameId, onLive]);

  async function send() {
    const t = text.trim();
    if (!t || disabled || sending) return;
    if (await onSend(t)) {
      setText("");
      area.current?.focus();
    }
  }

  function key(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void send();
    }
  }

  const words = text.trim() ? text.trim().split(/\s+/).length : 0;

  return (
    <div>
      <label htmlFor="explain" className="sr-only">Your explanation to the alien</label>
      <div className="relative border-[3px] border-ink bg-white shadow-[6px_6px_0_0_#000]">
        <div
          ref={backdrop}
          aria-hidden
          className="hl-backdrop pointer-events-none absolute inset-0 overflow-hidden whitespace-pre-wrap break-words px-4 py-3 text-lg leading-relaxed text-transparent"
        >
          <Highlighted text={text} violations={live} />{"\n"}
        </div>
        <textarea
          id="explain"
          ref={area}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onScroll={(e) => backdrop.current && (backdrop.current.scrollTop = e.currentTarget.scrollTop)}
          onKeyDown={key}
          disabled={disabled}
          rows={3}
          maxLength={600}
          placeholder="Explain it to the alien…"
          aria-describedby="explain-help explain-live"
          className="relative block w-full resize-none bg-transparent px-4 py-3 text-lg leading-relaxed text-ink caret-ink placeholder:text-smudge focus:outline-none"
        />
      </div>
      <p id="explain-live" aria-live="assertive" className="mt-2 min-h-7">
        {live.length > 0 && (
          <span className="label inline-flex flex-wrap items-center gap-2 bg-alarm px-2 py-1 text-white">
            ✕ Forbidden: {live.map((v) => v.matched.toLowerCase()).join(", ")}
            {live.some((v) => v.evasion) && <span>(nice try)</span>}
          </span>
        )}
      </p>
      <div className="mt-1 flex flex-wrap items-end justify-between gap-4">
        <dl id="explain-help" className="meta grid grid-cols-[auto_auto] gap-x-4 text-sm">
          <dt>Words used</dt><dd className="font-bold tabular-nums">{totalWords + words}</dd>
          <dt>Forbidden</dt><dd className="font-bold tabular-nums">{totalForbidden + live.length}</dd>
        </dl>
        <button onClick={send} disabled={disabled || sending || !text.trim()} className="btn bg-acid px-6 py-3 text-xl text-ink sm:text-2xl">
          {sending ? "Transmitting…" : "Transmit →"}
        </button>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------ screen */

export function PlayScreen({
  state, left, sending, error, onSend, onGiveUp,
}: {
  state: PublicState; left: number; sending: boolean; error: string | null;
  onSend: (t: string) => Promise<boolean>; onGiveUp: () => void;
}) {
  const [live, setLive] = useState<Violation[]>([]);
  const log = useRef<HTMLDivElement>(null);
  const lastAlien = [...state.messages].reverse().find((m) => m.role === "alien");
  const playing = state.status === "playing";

  const mood: AlienMood = useMemo(() => {
    if (sending) return "thinking";
    if (playing && left <= 15 && left > 0) return "panicking";
    if (live.length) return "suspicious";
    return (lastAlien?.mood as AlienMood) ?? "curious";
  }, [sending, playing, left, live.length, lastAlien]);

  const usedHits = useMemo(() => {
    const s = new Set<string>();
    [...live, ...state.messages.flatMap((m) => m.violations)].forEach((v) => s.add(v.term.toUpperCase()));
    return s;
  }, [live, state.messages]);

  // Follow the conversation, including alien lines that arrive beat by beat
  useEffect(() => {
    const el = log.current;
    if (!el) return;
    const toEnd = () => el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    toEnd();
    const beats = lastAlien?.lines.length ?? 1;
    const ids = Array.from({ length: beats + 1 }, (_, i) => setTimeout(toEnd, 200 + i * 560));
    return () => ids.forEach(clearTimeout);
  }, [state.messages.length, lastAlien]);

  return (
    <main className="min-h-dvh bg-paper text-ink md:grid md:h-dvh md:grid-cols-[minmax(0,1.15fr)_minmax(360px,0.85fr)] md:overflow-hidden">
      {/* LEFT: the specimen and the human's tools */}
      <section className="flex flex-col md:min-h-0" aria-label="The specimen and your explanation">
        <div className="flex items-center justify-between gap-3 bg-ink px-4 py-2 text-paper md:px-6">
          <h1 className="display text-2xl sm:text-3xl">
            Specimen <span className="meta align-middle text-xl">{pad(state.object.specimen_number)}</span>
          </h1>
          <Timer left={left} total={state.duration_s} />
        </div>
        <div className="relative flex-1 md:min-h-0">
          <Specimen state={state} />
          <div className="absolute bottom-4 left-3 z-20 max-w-[78%] sm:max-w-[60%]">
            <ForbiddenList words={state.object.forbidden_display} hits={usedHits} />
          </div>
        </div>
        {/* Phones: keep the alien's latest reaction next to the input */}
        <div className="flex items-start gap-3 border-b-[3px] border-ink bg-white px-3 py-3 md:hidden" aria-hidden>
          <div className="w-16 shrink-0"><Alien mood={mood} decorative /></div>
          <div className="min-w-0 flex-1">
            <p className="meta text-xs">Understanding {state.understanding}%</p>
            <p className="hand mt-1 text-lg leading-snug">{sending ? "…" : lastAlien?.lines.slice(-2).join(" ")}</p>
          </div>
        </div>
        <div className="grain bg-paper px-4 pb-5 pt-4 md:px-6">
          <p className="display text-xl leading-none sm:text-2xl">Explain its purpose.</p>
          <p className="label mb-3 text-sm text-graphite">Do not use its human name or standard technical terms.</p>
          <ExplainBox
            gameId={state.game_id}
            disabled={!playing}
            sending={sending}
            onSend={onSend}
            onLive={setLive}
            totalWords={state.words_used}
            totalForbidden={state.violations_count}
          />
          {error && <p role="alert" className="mt-3 bg-alarm px-2 py-1 font-bold text-white">{error}</p>}
          <button onClick={onGiveUp} disabled={!playing} className="mt-3 text-sm text-graphite underline underline-offset-2 hover:text-ink">
            I give up, tell me what it was
          </button>
        </div>
      </section>

      {/* RIGHT: the alien's side of the conversation */}
      <section className="flex flex-col border-t-[3px] border-ink bg-white md:min-h-0 md:border-l-[3px] md:border-t-0" aria-label="The alien">
        <div className="relative flex items-end gap-3 border-b-[3px] border-ink bg-paper px-4 pt-3">
          <div className="w-28 shrink-0 sm:w-36 md:w-44 lg:w-52">
            <Alien mood={mood} />
          </div>
          <div className="mb-4 min-w-0 flex-1">
            <Meter value={state.understanding} />
            <Meta className="mt-2 block text-graphite">
              {sending ? "The alien is thinking…" : playing ? "Channel open" : "Channel closed"}
            </Meta>
          </div>
        </div>

        <div className="px-4 pt-5">
          <Hypothesis state={state} />
        </div>

        <div ref={log} className="mt-4 flex-1 space-y-4 overflow-y-auto px-4 pb-6 md:min-h-0" aria-live="polite" aria-label="Conversation with the alien">
          {state.messages.map((m, i) =>
            m.role === "player" ? <PlayerLine key={m.id} m={m} /> : <AlienLines key={m.id} m={m} latest={i === state.messages.length - 1} />,
          )}
        </div>
      </section>
    </main>
  );
}
