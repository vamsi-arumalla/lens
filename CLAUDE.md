# Project: Lens — Real-Time Vision Agent (Phone-First, Glasses-Ready)

## What this is

A multimodal AI agent a user talks to while pointing a camera at the world.
Loop: camera frame + voice question in → vision-language model → spoken answer out, under 3 seconds.
Every capture is stored and embedded so the user can later ask "what did I see" questions
(e.g., "where did I park?", "what was written on that whiteboard?").

Capture device is abstracted: Phase 1–2 uses an Android phone camera; Phase 3 swaps in
Meta Ray-Ban glasses via the Meta Wearables Device Access Toolkit without changing the backend.

## Architecture (target state)

```
[Capture Client]                    [Backend]                          [External]
Android app (Kotlin)   --HTTPS-->   FastAPI service (Python 3.12)
  CameraX frames                      /ingest    (image + audio)       Anthropic API (vision + agent)
  Mic audio                           /ask       (voice query)         Deepgram or Whisper (STT)
  Audio playback       <--stream--    /answer    (streaming TTS)       OpenAI tts / ElevenLabs (TTS)
                                      Postgres + pgvector (memory)
                                      Object storage: local disk now,
                                      S3-compatible interface
```

Design rules:
- The backend NEVER knows what the capture device is. One ingestion contract for phone and glasses.
- Every external service (STT, TTS, VLM, embeddings) sits behind an interface so providers can be swapped.
- Latency is a feature. Log timing for every stage of every request from day one.

## Tech stack (do not substitute without asking)

- Backend: Python 3.12, FastAPI, uvicorn, pydantic v2
- DB: Postgres 16 + pgvector extension (docker-compose for local dev)
- VLM + agent: Anthropic API (claude-sonnet-4-6), tool use for agent actions
- Embeddings: open-clip (image) + a sentence-transformers model (text). Run locally in the backend.
- STT: faster-whisper locally for dev; interface allows swapping to Deepgram for lower latency
- TTS: OpenAI tts-1 streaming via API (interface allows swap)
- Android client: Kotlin, Jetpack Compose, CameraX, OkHttp/Retrofit, media3 for audio playback
- Auth: single static API key header for now (X-API-Key). No user accounts in v1.
- Secrets: environment variables only (.env, never committed). Provide .env.example.

## Repository layout

```
/backend
  /app
    main.py
    /api          # routers: ingest, ask, memory, health
    /services     # vlm.py, stt.py, tts.py, embeddings.py — each behind an ABC interface
    /memory       # store.py (pgvector), retrieval.py (search + rerank)
    /models       # pydantic schemas
    /core         # config, timing middleware, logging
  /tests
  docker-compose.yml   # postgres+pgvector
  pyproject.toml
/android
  (standard Kotlin/Compose project)
/docs
  latency-log.md   # running record of measured end-to-end latency per milestone
```

---

## PHASE 1 — Core loop (build this first, nothing else)

Goal: point phone camera at something, hold a button, ask a question by voice,
hear a spoken answer. End-to-end under 3 seconds for a short answer.

### Backend

1. `POST /ask` — multipart: one JPEG frame + one audio clip (webm/m4a) + optional text field.
   Pipeline: STT(audio) → build prompt with image → Anthropic vision call (streaming) →
   stream TTS audio back to the client as it generates (chunked transfer or websocket — pick
   the simpler that works with Android media3 streaming playback).
2. `GET /health` — returns ok + versions.
3. Timing middleware: every response includes header `X-Stage-Timings`
   (stt_ms, vlm_first_token_ms, vlm_total_ms, tts_first_byte_ms, total_ms) and logs it.
4. Frame handling: accept up to 3 frames per request (client sends 1 now; glasses may send burst later).
   Downscale to max 1280px longest edge before sending to the VLM to control cost/latency.
5. Error behavior: if VLM fails, return a spoken "Sorry, I couldn't process that" TTS clip, never a raw 500 to the user path.

### Android client

1. Single screen: live camera preview (CameraX), one big push-to-talk button.
2. Press and hold: captures current frame + records mic. Release: uploads both to `/ask`.
3. Plays the streamed audio answer immediately as bytes arrive (do not wait for full file).
4. Show the stage timings in a small debug overlay (toggleable).
5. Backend URL and API key configurable in a settings screen (points at local network IP during dev).

### Acceptance criteria (verify before moving on)

- [ ] Ask "what is this?" pointing at 5 different household objects — correct, spoken answers.
- [ ] Median total_ms < 3000 over 10 runs on local network (log results in /docs/latency-log.md).
- [ ] Kill the backend mid-request: app shows a friendly error, doesn't crash.
- [ ] No secrets in git history.

---

## PHASE 2 — Memory (visual RAG)

Goal: everything captured is searchable later by natural language.

1. `POST /ingest` — same multipart contract as /ask but no question required; stores a "moment":
   frame(s) saved to object storage, STT transcript if audio present, timestamp, optional lat/lng.
   Also: every /ask request is automatically ingested as a moment (the question + answer become part of its text).
2. Embeddings on ingest: CLIP image embedding + text embedding of (transcript + VLM-generated
   one-line caption of the frame). Store both vectors in pgvector with the moment row.
3. `POST /memory/search` — natural-language query → embed → hybrid search (vector similarity on
   both image and text vectors + recency boost) → return top-k moments with thumbnails + captions.
4. Wire memory into /ask as a tool: give the VLM a `search_memory` tool (Anthropic tool use).
   If the user asks about the past ("where did I…", "what was…yesterday"), the model calls the tool,
   gets moments back as images+text context, and answers from them.
5. Android: add a "Memories" tab — chronological grid of moments, tap to view, plus a search bar
   hitting /memory/search.
6. Retention: add a `DELETE /memory/{id}` and a "delete all" — user's data, user's control.

### Acceptance criteria

- [ ] Capture 20 moments around the house. Ask "where did I leave my keys?" (having filmed them) — correct answer citing the right moment.
- [ ] Search "text on the whiteboard" returns the whiteboard moment in top 3.
- [ ] /ask still meets the <3s budget when memory tool is NOT triggered; <6s when it is.

---

## PHASE 3 — Meta Ray-Ban glasses capture client

Goal: replace the phone camera with glasses POV camera. Backend unchanged.

1. Integrate Meta Wearables Device Access Toolkit (Android/Kotlin SDK:
   github.com/facebook/meta-wearables-dat-android). Use its MockDeviceKit to develop
   before/without physical glasses.
2. New capture mode in the Android app: when glasses are connected, frames come from the
   glasses camera stream; mic/speaker via the glasses' standard Bluetooth profiles.
3. Push-to-talk trigger: a button in the phone app is fine for v1 (glasses-native triggers later).
4. Same /ask and /ingest contracts. Add a `device_type` field ("phone" | "glasses") to moments.
5. Handle session lifecycle per the SDK docs (pause/resume, device availability). Fail gracefully
   back to phone camera when glasses disconnect.
6. NOTE for implementer: consult the SDK's live docs via its MCP endpoint
   (https://mcp.developer.meta.com/wearables, tool search_dat_docs, no auth) rather than guessing APIs.

### Acceptance criteria

- [ ] Full ask loop works hands-free wearing glasses (button on phone acceptable).
- [ ] Moments from glasses appear in Memories tagged as glasses captures.
- [ ] Disconnecting glasses mid-session falls back to phone camera without crash.

---

## PHASE 4 — Vertical flow: hands-free inspection report

Goal: one end-to-end professional workflow that turns a walkthrough into a deliverable.

1. "Inspection mode" in the app: user starts a session, walks a property/site, talks continuously
   ("water stain on ceiling here… breaker panel looks dated…"), camera auto-captures a frame
   whenever the user speaks and on significant scene change (simple frame-diff heuristic is fine).
2. All captures in a session are grouped. On "end session": backend runs an agent pass over the
   session — orders findings, pairs each spoken note with its best frame, drafts a structured
   report (sections: summary, findings with photos, severity, recommendations).
3. `GET /session/{id}/report.pdf` — render the report to PDF (weasyprint or reportlab), photos inline.
4. Android: session list, tap to view report, share sheet for the PDF.

### Acceptance criteria

- [ ] 5-minute walkthrough of an apartment with 8 spoken observations → PDF with all 8 findings,
      each paired with a sensible photo, in under 2 minutes of processing.

---

## Non-goals for v1 (do not build)

- User accounts, billing, multi-tenancy
- iOS client
- Always-on / continuous ambient capture (privacy + battery; explicit trigger only)
- On-device inference
- Any drone anything

## Working agreements for Claude Code

- Work strictly one phase at a time. Do not scaffold future phases.
- After each numbered item, run the app/tests and show me it works before continuing.
- Small commits with clear messages, one logical change each.
- If a library choice or API shape is ambiguous, ask ONE concise question instead of guessing.
- Never hardcode secrets; always read from env. Maintain .env.example.
- Every latency-relevant change: re-measure and append to /docs/latency-log.md.
