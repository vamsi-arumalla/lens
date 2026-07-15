# Latency log

Running record of measured end-to-end latency per milestone.
Budget: median total_ms < 3000 for a short answer on local network.

| Date | Milestone | Runs | Median total_ms | stt_ms | vlm_first_token_ms | tts_first_byte_ms | Notes |
|------|-----------|------|-----------------|--------|--------------------|-------------------|-------|
| 2026-07-15 | Phase 1 backend, localhost curl (voice path, warm) | 3 | 5601 | ~530 | ~1600 | 2476–5072 | Over budget. total_ms includes full TTS stream; speech *starts* at tts_first_byte. Biggest lever: TTS first byte (OpenAI tts-1 round-trip per sentence). Cold run adds ~12s one-time whisper model download/load. Real 10-run phone-on-LAN measurement still pending. |
