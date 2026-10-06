// Zod mirrors of the backend's Pydantic models. Every API response is parsed
// through these, so a backend change that breaks the contract fails loudly
// here instead of silently rendering nonsense.
import { z } from "zod";

export const Mood = z.enum(["curious", "confused", "suspicious", "horrified", "impressed", "thinking", "victory"]);
export type Mood = z.infer<typeof Mood>;

export const Violation = z.object({
  term: z.string(),
  matched: z.string(),
  start: z.number(),
  end: z.number(),
  tier: z.enum(["name", "revealing"]),
  evasion: z.boolean(),
});
export type Violation = z.infer<typeof Violation>;

export const TurnMetrics = z.object({
  clarity: z.number(),
  originality: z.number(),
  defamiliarization: z.number(),
  metaphor: z.number(),
  redundancy: z.number(),
  coverage_gain: z.number(),
});

export const Message = z.object({
  id: z.string(),
  role: z.enum(["alien", "player", "system"]),
  player_id: z.string().nullable().optional(),
  lines: z.array(z.string()),
  mood: Mood.nullable().optional(),
  violations: z.array(Violation),
  metrics: TurnMetrics.nullable().optional(),
  facets_covered: z.array(z.string()),
  at: z.number(),
});
export type Message = z.infer<typeof Message>;

export const Hypothesis = z.object({
  text: z.string(),
  confidence: z.number(),
  known_properties: z.array(z.string()),
  unknown_properties: z.array(z.string()),
});
export type Hypothesis = z.infer<typeof Hypothesis>;

export const Personalization = z.object({
  themes: z.array(z.string()),
  reason: z.string(),
  source: z.enum(["demo", "pinterest", "manual", "none"]),
});
export type Personalization = z.infer<typeof Personalization>;

export const GameStatus = z.enum(["intro", "playing", "success", "failed", "timeout"]);
export type GameStatus = z.infer<typeof GameStatus>;

export const PublicState = z.object({
  game_id: z.string(),
  game_type: z.string(),
  status: GameStatus,
  round_number: z.number(),
  object: z.object({
    id: z.string(),
    image_url: z.string(),
    specimen_number: z.number(),
    difficulty: z.number(),
    forbidden_display: z.array(z.string()),
    generated: z.boolean(),
    human_only_label: z.string().nullable().optional(),
  }),
  messages: z.array(Message),
  hypothesis: Hypothesis,
  understanding: z.number(),
  violations_count: z.number(),
  words_used: z.number(),
  time_remaining: z.number(),
  duration_s: z.number(),
  personality: z.string(),
  personalization: Personalization.nullable().optional(),
  revealed_name: z.string().nullable().optional(),
  alien_summary: z.string().nullable().optional(),
});
export type PublicState = z.infer<typeof PublicState>;

export const ScoreLine = z.object({ key: z.string(), label: z.string(), value: z.number(), evidence: z.string() });
export type ScoreLine = z.infer<typeof ScoreLine>;

export const GameResult = z.object({
  game_id: z.string(),
  status: GameStatus,
  object_name: z.string(),
  alien_summary: z.string(),
  verdict: z.array(z.string()),
  score: z.object({
    lines: z.array(ScoreLine),
    final: z.number(),
    title: z.string(),
    title_reason: z.string(),
  }),
  observations: z.array(z.object({ text: z.string(), evidence: z.string() })),
  turns: z.number(),
  seconds_used: z.number(),
  hypothesis_trail: z.array(Hypothesis),
});
export type GameResult = z.infer<typeof GameResult>;

export const Theme = z.object({
  name: z.string(),
  label: z.string(),
  weight: z.number(),
  evidence: z.array(z.string()),
});
export type Theme = z.infer<typeof Theme>;

export const VisualProfile = z.object({
  source: z.enum(["demo", "pinterest", "manual"]),
  board_name: z.string(),
  board_url: z.string().nullable().optional(),
  pin_count: z.number(),
  themes: z.array(Theme),
  sample_pins: z.array(
    z.object({
      title: z.string(),
      description: z.string(),
      image_url: z.string().nullable().optional(),
      link: z.string().nullable().optional(),
    }),
  ),
  reflection: z.array(z.string()),
  analysis: z.enum(["keywords", "text-llm", "vision", "demo"]).default("keywords"),
  aesthetic: z.array(z.string()).default([]),
  motifs: z.array(z.string()).default([]),
  contradiction: z.string().nullable().optional(),
  analysis_note: z.string().nullable().optional(),
});
export type VisualProfile = z.infer<typeof VisualProfile>;

export const DemoBoard = z.object({
  id: z.string(),
  name: z.string(),
  blurb: z.string(),
  pins: z.array(z.string()),
  pin_count: z.number(),
});
export type DemoBoard = z.infer<typeof DemoBoard>;

export const Health = z.object({
  ok: z.boolean(),
  alien_mode: z.string(),
  personalities: z.record(z.string(), z.object({ label: z.string(), blurb: z.string() })),
});
export type Health = z.infer<typeof Health>;
