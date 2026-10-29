# Sound

Sound is half the picture. Most "cheap animation" verdicts are sound verdicts.

## Spotting
- Every visible contact, impact, prop handling, switch, door, landing and big body
  move (cloth) gets a sound. Log them in the animation code: `cues.add(frame, kind, ...)`.
- Decide what *not* to hear: silence before a reveal makes the reveal land.

## Foley and SFX (animkit.audio)
| Event | Generator | Notes |
|---|---|---|
| Footstep | `footstep(seed, wet, weight)` | vary seed per step; heavier = lower, longer |
| Cloth / body move | `cloth()` | on big pose changes, low level |
| Paper | `paper()` | keep quiet; it's broadband |
| Metal flap / latch | `metal_flap()` | inharmonic partials + click |
| Switch | `switch_click()` | two clicks ~18 ms apart |
| Landing / thump | `thump()` or layered footsteps | |
| Whoosh | `whoosh(dur)` | fast moves only, not every move |
| Rain | `rain(dur, intensity)` | shaped bed + droplets + drips, stereo |
| Hum | `hum(dur, 50 or 60 Hz)` | practical lights, appliances |

Rules: per-instance variation (pitch, level, timbre); pan to screen position;
micro-fades on every sample (no clicks); a little shared reverb for space.

## Ambience
Textured, not flat: a shaped bed (pink/brown noise filtered for the place), discrete
events (drops, distant cars, birds), and space (reverb, stereo width). A flat white
noise hiss is the tell `reel_critic` flags.

## Score
- Sections follow beats (intro, development, turn, resolve). Change density,
  register or harmony at the turn. Use silence.
- Sync where it helps: tempo from the walk (one beat per two steps in the doorstep
  shot), hits on key accents; avoid "mickey-mousing" every move unless it's the style.
- Never loop one phrase under a multi-piece reel; give each piece its own sonic identity.
- For reels intended for studio recruiters: keep music unobtrusive or off; original
  sound for dialogue pieces.

## Mix
- Buses: amb, sfx, music (VO if any). Duck music under key SFX/VO (`Mix.render(duck=...)`).
- Check on small speakers and headphones; check at low volume (does the story survive?).
- Loudness range (LRA) for a short with dynamics: ~5-12 LU. Under 3 LU = flat.

## Loudness targets (check the current spec of the destination)
| Destination | Target |
|---|---|
| Web/social (YouTube etc. normalise playback) | about -14 to -16 LUFS integrated, true peak <= -1.5 dBTP for AAC |
| Podcast intro / sting | match the episode mix, commonly about -16 LUFS integrated (Apple Podcasts guidance), true peak <= -1 dBTP. A short sting with silence measures low integrated; check that its hit sits at the episode's loudness (short-term max), not just the integrated number |
| EBU R128 broadcast | -23 LUFS, true peak <= -1 dBTP |
| ATSC A/85 (US broadcast) | -24 LKFS |
| Film festival / cinema | follow the festival's DCP/audio spec |

`audio.master()` runs two-pass loudnorm and reports I / LRA / TP of the result;
re-measure the final muxed file with `reel_critic` (lossy encoding can raise true peak).
