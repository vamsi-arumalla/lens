# `/ask` ingestion contract (canonical)

This is the byte-level contract every capture client (phone, glasses, anything
later) must produce. It was extracted from the Phase 1 Android client — the
request builder in `android/.../net/LensClient.kt` and the streaming executor
in `android/.../net/StreamingDataSource.kt` — and the backend router in
`backend/app/api/ask.py`. **The backend never knows what the capture device
is**; conformance to this document is what keeps that true. If a new capture
path seems to need anything not listed here, that is an abstraction leak —
stop and flag it, do not extend the contract ad hoc.

A machine-readable summary of the normative fields lives at the bottom; the
Android unit test `AskContractTest` asserts the app's request builder matches
it.

> **Decision record (2026-07-15):** `device_type` is intentionally absent.
> Device identity is a client-declared label — it can describe, never drive
> behavior. The glasses-provenance badge is deferred; if revived it goes on
> `/ingest` only, as explicitly-labeled stored-verbatim never-read metadata —
> never on `/ask`, never branched on.

## Request

```
POST {base}/ask
X-API-Key: <shared static key>            ← required, exact header name
Content-Type: multipart/form-data; boundary=<any>
```

- `{base}` is the backend origin, no trailing slash (e.g. `http://192.168.0.170:8400`).
- Auth is the single static `X-API-Key` header. No cookies, no bearer tokens.
  Wrong or missing key → `401` with a JSON body; nothing is processed.
- The body is standard `multipart/form-data`. Boundary is free choice.

### Parts

| # | Field name | Filename | Part Content-Type | Payload | Required |
|---|-----------|----------|-------------------|---------|----------|
| 1…3 | `frames` | any `*.jpg` (informational) | `image/jpeg` | JPEG-encoded frame | ≥ 1, ≤ 3 |
| 0…1 | `audio` | any (informational) | `audio/mp4` | AAC-LC in an MPEG-4 container | optional |
| 0…1 | `text` | — (plain field, no filename, no part Content-Type) | — | UTF-8 question text | optional |

Normative rules:

1. **Field names are exact and lowercase**: `frames`, `audio`, `text`.
   Repeating `frames` up to 3 times sends a burst; the server rejects > 3
   with `422`. The phone sends exactly 1; glasses may send up to 3.
2. **At least one of `audio` / `text` must produce a non-empty question**,
   otherwise `422`. When both are present the server transcribes the audio
   and appends the text after it.
3. **Image encoding**: JPEG, any resolution — but the server downscales to
   1280 px longest edge before the VLM, so anything larger is wasted upload.
   The Phase 1 phone sends the raw `ImageCapture` JPEG.
4. **Audio encoding** (what the phone produces and whisper is known to
   decode): AAC-LC, MPEG-4 container (`.m4a`), 16 kHz sample rate, mono.
   The server decodes via PyAV, so other rates/containers (e.g. `.webm`)
   also work, but 16 kHz mono AAC/MP4 is the reference encoding.
5. **Filenames are informational** — the server ignores them. The phone
   happens to send `frame.jpg` and `question-<millis>.m4a`.
6. Speech-to-text is pinned to English on the server (`LENS_STT_LANGUAGE`).

## Response

- `200` — `Content-Type: audio/mpeg`, `Transfer-Encoding: chunked`. The body
  is a stream of concatenated MP3 (MPEG-1/2 Layer III) segments, 24 kHz mono;
  playable progressively — clients must start playback as bytes arrive, not
  buffer to end. The stream ends when the answer is fully spoken.
- Headers on the `200`:
  - `X-Stage-Timings: stt_ms=…,vlm_first_token_ms=…` — stages known when
    headers are sent. Stages that finish after streaming starts
    (`tts_first_byte_ms`, `vlm_total_ms`, `total_ms`) appear only in the
    server log, not in the header.
  - `X-Lens-Error: vlm_failed` — present when the VLM failed; the body is
    still `200` + `audio/mpeg`, a spoken apology clip ("Sorry, I couldn't
    process that."), never a raw 500 on the user path.
- `401` — bad/missing `X-API-Key`.
- `422` — validation: > 3 frames, or no question derivable.

## Client execution semantics

- The Phase 1 client executes the request lazily inside a media3
  `DataSource.open()` (`StreamingDataSource.kt`) and feeds the response
  stream directly into the audio player. Any client must consume the body
  as a live stream.
- **Do not auto-retry the POST.** Every `/ask` has side effects (the ask is
  ingested as a memory moment, and hedged VLM calls cost tokens); a client
  retry produces duplicate moments. Surface failures to the user instead.
- Connect timeout 5 s / read timeout ≥ 60 s are the reference settings; the
  answer stream stays open for as long as the model speaks.

## Machine-readable summary (asserted by `AskContractTest`)

```json
{
  "method": "POST",
  "path": "/ask",
  "headers": { "X-API-Key": "<key>" },
  "multipart": {
    "frames": { "content_type": "image/jpeg", "min": 1, "max": 3, "has_filename": true },
    "audio":  { "content_type": "audio/mp4",  "min": 0, "max": 1, "has_filename": true },
    "text":   { "content_type": null,          "min": 0, "max": 1, "has_filename": false }
  },
  "question_rule": "audio or text required",
  "response_ok": { "status": 200, "content_type": "audio/mpeg", "streaming": true }
}
```
