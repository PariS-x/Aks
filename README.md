# AKS — Alien Explanation

> What you save reflects you. What you create reveals you.

AKS reads a public Pinterest board, reflects your visual world back to you, then hands you to its first creativity game: **Alien Explanation**. An extraterrestrial has found an ordinary Earth object. You have 90 seconds to explain it without using its name. The alien builds a hypothesis from what you actually said, misreads you literally, and finally decides. At the end AKS tells you something about *how* you explained.

## Run it

Needs Python 3.11+ and Node 20+.

```bash
# 1. backend (port 8000)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 2. frontend (port 3000), in another terminal
cd frontend
npm install
npm run dev
```

Open http://localhost:3000. Pick a sample archive (demo mode, no Pinterest or API key needed) or paste a public board URL.

Shortcuts: `/?demo=orbit-and-concrete` jumps straight to a reflection; `/?play=1` jumps to the game.

### Turning on the LLM alien (free options first)

Without a key the alien runs on the deterministic offline interpreter (fully playable). With a model, the alien gets a real voice and AKS can *look at* your pin images (including text inside quote images).

**Free: Gemini.** Get a key at https://aistudio.google.com/apikey (no card needed), then in the backend terminal:

```powershell
$env:GEMINI_API_KEY="your-key"
python -m uvicorn app.main:app --port 8000
```

Default model is `gemini-3.8-flash`; change with `$env:AKS_LLM_MODEL="gemini-3.5-flash-lite"` if you hit rate limits. Free-tier usage is rate-limited and Google may use free-tier prompts to improve its products.

**Free and fully offline: Ollama.** Install https://ollama.com, run `ollama pull qwen2.5vl:3b`, then `$env:AKS_LLM_PROVIDER="ollama"`. Slower, needs ~4 GB RAM, nothing leaves your machine.

**Paid:** `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` (+ `OPENAI_BASE_URL` for any OpenAI-compatible API).

Optional: `AKS_GENERATE_OBJECTS=1` lets the model invent personalised specimens.

`GET /api/health` reports `alien_mode` so you can confirm which one is running.

### Tests

```bash
cd backend && pytest        # 27 tests: constraints, engine, LLM guards, profile, API
cd frontend && npm run build
```

## How it works

```
GameState → ConstraintChecker → Interpreter(s) → blend & guard → Hypothesis → status/timer → ScoreEngine
```

**The LLM interprets. The engine decides.** The engine alone owns the clock, forbidden-word detection, how far understanding may move per turn, whether the round is won, whether the alien may say the name, and every score.

- **Objects** (`games/alien_explanation/catalog.py`) carry ground truth as *facets*: things the alien needs to learn (appearance, function, mechanism, context), some marked *core*. Each has the alien's literal "take" when it learns it ("Water falls from your sky and you object to this.") and combo lines when facets meet ("So humans use a tiny broom to polish the bones inside their faces?").
- **Forbidden words** (`constraints.py`) are tiered: the name and aliases (enforced, never listed on screen) and a few revealing words. Whole-word matching with light stemming, so *oral* never matches *moral*; joined/hyphenated names and evasions (`t00th`, `t o o t h`) are caught. The same checker runs live as you type and when scoring.
- **Interpreters** (`interpreter.py`): the offline one matches facet cues; the LLM one returns strict JSON validated by Pydantic (and Zod on the client). Model output is clamped, unknown facets dropped, the name redacted before success, and a bad reply falls back to offline. Understanding can't jump more than 0.5 per turn and is capped at 0.79 until every core facet is covered.
- **Scoring** (`scoring.py`): clarity, originality, defamiliarization, metaphor, constraint, alien comprehension, each with a plain-language evidence line. A playful title. **AKS noticed**: 2–3 observations grounded in what you wrote (function-before-appearance, metaphor habits, insider vs outsider voice, whether you answered the alien's questions). Game metrics, not psychometrics.
- **Personalisation** (`personalization.py`): themes from the board pick an object that is related *sideways* rather than literally (familiar enough to explain, unexpected enough to think).
- **Pinterest** (`profile/pinterest.py`): public board RSS (`pinterest.com/<user>/<board>.rss`), no login. Keyword analyzer with evidence; optional LLM re-ranking. The full multimodal AKS pipeline can bypass this by POSTing a `VisualProfile` to `/api/profile`.

### Built for more games

`backend/app/core/game.py` defines the `CreativityGame` contract (start / begin / process_input / evaluate / public_view) and a registry; `frontend/src/games/registry.ts` mirrors it. Sessions sit behind a small store interface (swap for Redis). The state already models players and per-player messages so a multiplayer room (same object, everyone explains, alien ranks) fits without reshaping it. Only Alien Explanation is implemented.

## The alien

The mascot is the supplied drawing, not a redraw. `frontend/public/alien/alien-base.png` is the original with pupils and mouth removed; `Alien.tsx` draws only the face and marker doodles on top, in the drawing's own pixel space, for 10 moods: neutral, curious, confused, suspicious, horrified, impressed, thinking, victory, panicking, loading. `alien-original.png` is the untouched cutout.

## Specimen images

`tools/make_specimens.py` generates the 16 black-and-white halftone illustrations into `frontend/public/objects/sNN.svg`. File names are opaque so the object's name never reaches the browser. To use real B/W photos, replace a file or change `image_url` in the catalog.

## Layout

```
backend/app/
  core/            game contract, registry, session store
  games/alien_explanation/
    models.py      state, object, interpretation contract
    catalog.py     16 specimens with facets and forbidden terms
    constraints.py forbidden-word detection
    interpreter.py offline + LLM interpreters
    prompts.py     alien persona and JSON contract
    engine.py      the deterministic game engine
    scoring.py     scores, titles, AKS noticed, verdict
    personalization.py, voice.py, features.py
  profile/         Pinterest ingest, analyzer, demo boards
  llm/client.py    provider-agnostic adapter (Anthropic / OpenAI-compatible)
frontend/src/
  app/             AksApp: home → reflection → game
  components/      alien, collage primitives, AKS screens
  games/alien-explanation/   screens + flow hook
  lib/             zod schemas, API client
```
