# Phase 3 — Meta DAT glasses integration (activation guide)

Everything below is derived from the SDK's live docs (MCP endpoint
`mcp.developer.meta.com/wearables`, queried 2026-07-15, SDK version 0.8.0).
The capture abstraction (`capture/CaptureSource.kt`) and the contract test
(`AskContractTest`) are already in place; this documents the one gated step
and the adapter that plugs into the existing seam.

## Gate: GitHub Packages token

The SDK is distributed via GitHub Packages, which requires a **personal
access token (classic) with `read:packages`** even for public downloads.
Create one at github.com → Settings → Developer settings, then either
`export GITHUB_TOKEN=ghp_…` or add `github_token=ghp_…` to
`android/local.properties` (already gitignored).

## Gradle changes (once token exists)

`settings.gradle.kts` — add to `dependencyResolutionManagement.repositories`:

```kotlin
maven {
    url = uri("https://maven.pkg.github.com/facebook/meta-wearables-dat-android")
    credentials {
        username = ""
        password = System.getenv("GITHUB_TOKEN")
            ?: localProperties.getProperty("github_token")
    }
}
```

`gradle/libs.versions.toml`:

```toml
[versions]
mwdat = "0.8.0"

[libraries]
mwdat-core = { group = "com.meta.wearable", name = "mwdat-core", version.ref = "mwdat" }
mwdat-camera = { group = "com.meta.wearable", name = "mwdat-camera", version.ref = "mwdat" }
mwdat-mockdevice = { group = "com.meta.wearable", name = "mwdat-mockdevice", version.ref = "mwdat" }
```

(`mwdat-display` is for Ray-Ban Display rendering — not needed for capture.)

Manifest additions: `android.permission.BLUETOOTH_CONNECT` (runtime).

## Adapter sketch (documented API, to be compiled against the real artifact)

```kotlin
// capture/GlassesCaptureSource.kt
class GlassesCaptureSource(private val stream: /* DAT */ Stream) : CaptureSource {
    override suspend fun captureFrames(): List<ByteArray> {
        // Preferred: full-quality single capture during an active stream
        val photo: PhotoData = stream.capturePhoto().getOrThrow()
        return listOf(photo.jpegBytes())   // convert per PhotoData format
    }
}
```

Session lifecycle (per docs):
- `Wearables.initialize(context)` at app start; registration completes
  through the Meta AI app (MockDeviceKit auto-completes it).
- Device discovery via `devicesMetadata`; open a `DeviceSession`.
- `session.addStream(StreamConfiguration(videoQuality = MEDIUM, frameRate = 24))`
  → `stream.videoStream: Flow<frame>` for the live preview,
  `stream.capturePhoto()` for the ask frame,
  `stream.state: Flow<StreamState>` (`STARTING → STARTED → STREAMING → …`).
- Fallback rule (spec §Phase 3.5): on `StreamState.STOPPED`/session loss,
  swap the active `CaptureSource` back to `PhoneCaptureSource` — the ask
  flow doesn't change because both implement the same interface.

MockDeviceKit (instrumentation tests, runs on the phone):

```kotlin
val mdk = MockDeviceKit.getInstance(targetContext)
mdk.enable()
val device = mdk.pairGlasses(GlassesModel.RAYBAN_META).getOrThrow()
device.services.camera.setCameraFeed(getAssetUri("test_walkthrough.mp4"))
// drive the ask flow; frames now come from the mock glasses feed
```

## Quality watch item — MEASURED 2026-07-15, degradation confirmed

A/B on 8 real captured frames degraded to glasses quality (896 px, horizontal
motion blur, JPEG q30), question "What is this?", haiku vs sonnet:

- Clear subjects (AirPods ×2, key fob, iPhone, iPad, keyboard): **parity** —
  both correct.
- Ambiguous/textured frames: **haiku lost 3 of 8.** Called a patterned rug
  "a measurement tape with centimeter markings" (hallucination); twice called
  a silicone facial brush "a massage ball or sensory toy". Sonnet answered
  all three correctly and consistently.

Decision for now: keep haiku while capture is phone-only (phone frames are
sharp; parity holds there). **Before glasses ship real frames, revisit** —
options: revert `LENS_VLM_MODEL` to sonnet (perceived latency returns to
~2.5–3 s with hedging), or escalate by measured input quality (blur/size
heuristic), which keys on the frame, not the device, so it does not leak
the capture abstraction. Do NOT key model choice on device type.
