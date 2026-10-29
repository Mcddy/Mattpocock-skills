---
name: heirloom-verify-media-deliverable
description: "Verify a completed audio/video/media package against a concrete delivery specification, including actual streams, timing, captions, content fidelity and archive contents. Use for final conformance evidence; producing the media or directing narration is separate."
---

# Inspect the delivered bytes

Collect the actual exported files, agreed specification, source/script revision, caption files, required attachments and target playback environment. If no specification exists, derive a provisional checklist from the requested use and label defaults; do not claim contractual conformance. Preserve original exports and inspect copies. A filename ending in mp4 does not prove container, codec or stream properties.

Inventory filenames, sizes and hashes. With a capable local probe, inspect container, codecs, duration, resolution, frame rate mode, audio channels and sample rate. Distinguish nominal metadata from measured playback. If tools cannot inspect a requested property, mark it unverified rather than infer it from the editor settings. Check current official platform requirements only when platform acceptance is part of the task and browsing is available.

Compare the actual streams with the specification, including silent or missing audio, unexpected extra tracks, rotation flags and duration mismatch. Sample the opening, closing, decisive demonstrations and every known risky edit; targeted sampling must be reported as sampling. A full decode can reveal corruption but cannot judge intelligibility or factual accuracy. If the whole file is reviewed, state exactly which modalities were observed.

Validate caption syntax, timestamps, ordering and bounds against the final media duration. Check overlap policy, readability and technical spellings. Cross-check spoken and displayed numbers, negations and units against the approved script and claim evidence. Caption text matching the script does not prove the audio says the same thing. If playback or hearing is unavailable, keep audible fidelity pending.

Inspect the package contents and archive extraction paths without executing embedded files. Reject missing required attachments, private source leakage and paths that escape the intended directory. Use a fresh staging directory if extracting; never overwrite existing user files. If a defect is found, record the conformance finding and a proposed repair. Make a new revised export only when the task authorises repair and repair tools are available, then rerun the affected checks on the revised bytes actually produced. Preserve the defective original and evidence, unless the user has requested a replacement workflow.

Deliver `media_verification.json` and `delivery_report.md` with file hashes, measured properties, requirement IDs, pass/fail/unverified status, tool versions, sampled intervals, defects and revised-output mapping. Do not upload or send a deliverable just because it passes locally; distribution needs its own instruction.

Acceptance includes a known conforming sample and a negative control with either out-of-bounds captions, missing audio or misleading metadata. Confirm the selected defect is caught. A local pass establishes the inspected requirements under the tested environment, not acceptance by an untested platform or correctness of every unsampled frame.

Worked situation: an editor preset says stereo, but the export contains no audio stream. The package fails narration delivery even though the picture plays correctly and its filename looks right.
