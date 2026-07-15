# Latency log

Running record of measured end-to-end latency per milestone.
Budget: median total_ms < 3000 for a short answer on local network.

| Date | Milestone | Runs | Median total_ms | stt_ms | vlm_first_token_ms | tts_first_byte_ms | Notes |
|------|-----------|------|-----------------|--------|--------------------|-------------------|-------|
| 2026-07-15 | Phase 1 backend, localhost curl (voice path, warm) | 3 | 5601 | ~530 | ~1600 | 2476–5072 | Over budget. total_ms includes full TTS stream; speech *starts* at tts_first_byte. Biggest lever: TTS first byte (OpenAI tts-1 round-trip per sentence). Cold run adds ~12s one-time whisper model download/load. Real 10-run phone-on-LAN measurement still pending. |
| 2026-07-15 | Phase 1 acceptance run: phone on LAN (moto g 5G 2022), 10 asks at household objects | 10 | 8847 | 511 | 3363 | 5151 (median) | All 10 answers correct (5-object criterion PASSED). Latency criterion FAILED: 8.8s median vs 3s budget; one 21s outlier from a VLM first-token spike. Client now uploads ~1280px frames; first TTS chunk splits at first clause. Remaining levers, biggest first: OpenAI tts-1 first-byte (~2s per chunk) → swap TTS provider or stream PCM; VLM first token ~2.8s after STT → try smaller image / faster model; STT 0.5s → Deepgram. The service ABCs exist for exactly these swaps. |
