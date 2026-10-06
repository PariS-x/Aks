import { z } from "zod";
import {
  DemoBoard, GameResult, Health, PublicState, Violation, VisualProfile,
} from "./schemas";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function call<T>(schema: z.ZodType<T>, path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, {
      ...init,
      headers: { "content-type": "application/json", ...(init?.headers ?? {}) },
    });
  } catch {
    throw new ApiError(0, "The transmission failed. Is the AKS server running?");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {}
    throw new ApiError(res.status, detail);
  }
  const data = await res.json();
  const parsed = schema.safeParse(data);
  if (!parsed.success) {
    console.error("AKS contract mismatch", path, parsed.error);
    throw new ApiError(500, "The server replied in an unexpected format.");
  }
  return parsed.data;
}

const post = (body?: unknown): RequestInit => ({ method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });
const G = "/api/games/alien-explanation/sessions";

export const api = {
  health: () => call(Health, "/api/health"),
  demoBoards: () => call(z.array(DemoBoard), "/api/profile/demo-boards"),
  demoProfile: (id: string) => call(VisualProfile, `/api/profile/demo/${encodeURIComponent(id)}`),
  analyzeBoard: (board_url: string) => call(VisualProfile, "/api/profile/analyze", post({ board_url })),

  createGame: (opts: { profile?: VisualProfile | null; personality?: string; duration_s?: number; difficulty?: number }) =>
    call(PublicState, G, post(opts)),
  start: (id: string) => call(PublicState, `${G}/${id}/start`, post()),
  check: (id: string, text: string) => call(z.array(Violation), `${G}/${id}/check`, post({ text })),
  transmit: (id: string, text: string) => call(PublicState, `${G}/${id}/messages`, post({ text })),
  tick: (id: string) => call(PublicState, `${G}/${id}/tick`, post()),
  giveUp: (id: string) => call(PublicState, `${G}/${id}/give-up`, post()),
  result: (id: string) => call(GameResult, `${G}/${id}/result`),
  next: (id: string) => call(PublicState, `${G}/${id}/next`, post()),
};
