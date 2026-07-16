# Resuming Phase 3 on real hardware

Where the project is parked (2026-07-15), written so it can be picked up cold.

## Current state

Phase 3 is code complete and verified end-to-end against the Meta Wearables
Device Access Toolkit's **MockDeviceKit**: mock Ray-Ban pairing, mock camera
feed driving the real `/ask` flow, and lifecycle hardening (fold/doff death
signals, reconnect re-dons the device, disconnect falls back to the phone
camera without a crash). No physical glasses have been touched. The SDK
integration details and the GitHub Packages token gate are in
[phase3-glasses-integration.md](phase3-glasses-integration.md).

## What to buy

A current-generation **standard Ray-Ban Meta** (camera + open-ear audio is
all LENS needs). Not the Display model; its rendering stack (`mwdat-display`)
is irrelevant to capture.

## Steps to resume

1. Pair the glasses with the phone via the **Meta AI app** (standard consumer
   pairing; the SDK discovers devices the app has paired).
2. **Registration flow.** `Wearables.initialize()` registration completes
   through the Meta AI app on a real device. MockDeviceKit auto-completes
   this step, so it has never been exercised for real. Expect this to be the
   first thing to debug.
3. **Run the Phase 3 acceptance criteria on real Bluetooth-compressed
   frames** (full hands-free ask loop, moments appearing in Memories,
   mid-session disconnect fallback).

## The model decision this settles

Step 3 also settles the open **Haiku vs Sonnet** question. The pre-hardware
A/B on glasses-degraded frames (896 px, motion blur, JPEG q30) showed Haiku
losing 3 of 8 ambiguous subjects where Sonnet was clean; parity holds on
sharp phone frames. Real Bluetooth-compressed frames are the deciding data.

If escalation is needed, the principle is already logged: key the decision on
**measured frame quality, never on a device label**. See the decision record
in [ask-contract.md](ask-contract.md) (labels describe, never drive; no
`device_type` on `/ask`), the measured A/B and escalation options in
[phase3-glasses-integration.md](phase3-glasses-integration.md), and the
latency context (hedged Haiku is what bought the sub-2s perceived latency)
in [latency-log.md](latency-log.md).
