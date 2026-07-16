# LENS

LENS is a real-time multimodal AI assistant: point a camera, hold a button, ask a question by voice, hear a spoken answer.

## What it does

The client captures a camera frame and a voice question while you hold a push-to-talk button. On release, both are uploaded to a FastAPI backend that transcribes the audio, sends the frame and question to a vision-language model, and streams synthesized speech back before the model has even finished answering. Every capture is stored and embedded (image + text vectors in pgvector), so you can later ask memory questions like "where did I leave my keys?" and the model answers by searching past moments with a tool call. The capture device is abstracted behind a single byte-level contract: today it is an Android phone, and a Meta Ray-Ban glasses capture path is integrated and mock-verified against the same contract.

```
[Capture Client]                    [Backend]                          [External]
Android app (Kotlin)   --HTTPS-->   FastAPI service (Python 3.12)
  CameraX / glasses frames            /ask       (frames + voice query)  Anthropic API (vision + agent)
  Mic audio                           /ingest    (memory moments)        faster-whisper (STT, local)
  Audio playback       <--stream--    /memory    (search, delete)        Kokoro or OpenAI tts-1 (TTS)
                                      Postgres + pgvector (memory)
```

## Key engineering decisions

**A device-agnostic capture contract, enforced by a test.** The backend never knows what the capture device is. The full byte-level `/ask` contract (multipart fields, encodings, auth, streaming response semantics) is written down in [docs/ask-contract.md](docs/ask-contract.md), and the Android unit test `AskContractTest` asserts the app's request builder matches the machine-readable summary at the bottom of that document. Swapping the phone camera for glasses (Phase 3) required zero backend changes; any drift in the request shape fails the test instead of failing in the field. A deliberate corollary, recorded in the contract's decision log: device identity is a label that may describe but never drive behavior, so there is no `device_type` field to branch on.

**Latency treated as a feature, with measurements to show for it.** Every request logs per-stage timings (`X-Stage-Timings`), and every latency-relevant change is re-measured and appended to [docs/latency-log.md](docs/latency-log.md). Each external service (STT, TTS, VLM, embeddings) sits behind an interface so providers can be swapped when the measurements say so. That produced, in order: swapping OpenAI tts-1 for local Kokoro-82M running on the Apple GPU (MPS), which cut roughly 2 seconds of per-answer network round-trips; first-token request hedging that duplicates a slow VLM request after 1.8 s to clip the time-to-first-token tail (about 30% duplicate rate); and a model swap to Haiku behind a one-line env revert. Net result: median perceived latency (time to first spoken audio) went from over 5 s to 1.73 s on localhost, roughly 2.9 s measured from the phone.

**Glasses integration built and verified against a mock before buying hardware.** The Meta Ray-Ban path uses the Meta Wearables Device Access Toolkit and was developed entirely against the SDK's MockDeviceKit: mock pairing, a mock camera feed driving the real ask flow, and lifecycle hardening (fold/doff, disconnect mid-session falls back to the phone camera without a crash). A frame-quality A/B on glasses-degraded images was run ahead of time and already caught that Haiku loses accuracy on blurred frames where Sonnet does not, so the model decision point is documented before real frames exist. See [docs/phase3-glasses-integration.md](docs/phase3-glasses-integration.md).

## Tech stack

- **Backend:** Python 3.12, FastAPI, uvicorn, pydantic v2, uv for dependency management
- **Android client:** Kotlin, Jetpack Compose, CameraX, OkHttp, media3 for progressive audio playback
- **Memory:** Postgres 16 + pgvector (docker compose), open-clip image embeddings, sentence-transformers text embeddings
- **Models:** Anthropic (vision + agent tool use), faster-whisper (STT, local), Kokoro-82M (TTS, local, Apple GPU) with OpenAI tts-1 as the swappable alternative
- **Glasses:** Meta Wearables Device Access Toolkit (Android SDK)

## Setup

No secrets are committed to this repo. All keys come from the environment.

```bash
# 1. Configure secrets
cp .env.example .env   # fill in LENS_API_KEY, LENS_ANTHROPIC_API_KEY, etc.

# 2. Memory store (optional; leave LENS_DATABASE_URL unset to disable memory)
cd backend && docker compose up -d

# 3. Run the backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 8400
```

Android: open `android/` in Android Studio, build, and point the app at the backend from its settings screen (base URL, e.g. `http://<your-lan-ip>:8400`, and the API key). The glasses dependency requires a GitHub Packages token; see [docs/phase3-glasses-integration.md](docs/phase3-glasses-integration.md).

Backend tests: `cd backend && uv run pytest`. Contract test: `cd android && ./gradlew testDebugUnitTest --tests '*AskContractTest'`.

## Status

- **Phase 1 (core ask loop):** complete and live-verified on a physical phone. 10/10 correct spoken answers in the acceptance run; latency history in [docs/latency-log.md](docs/latency-log.md).
- **Phase 2 (visual memory / RAG):** complete and live-verified, including memory search wired into `/ask` as a tool.
- **Phase 3 (Ray-Ban glasses capture):** code complete and verified end-to-end against the SDK's MockDeviceKit; acceptance on physical hardware is pending. See [docs/hardware-todo.md](docs/hardware-todo.md) for exactly what remains.
- **Phase 4 (hands-free inspection reports):** specced, not started.
