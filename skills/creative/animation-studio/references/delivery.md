# Delivery

## Masters
| Use | Settings |
|---|---|
| Web master (default) | H.264 High, CRF 14-18, `-tune animation`, yuv420p, BT.709 tags, AAC 320 kbps 48 kHz, `+faststart`. Put a static dither on every frame (`finish.dither`, ~1.5 levels) so vignettes and soft gradients don't band: the encoder smooths moving grain away (measured 43-75% of gradient area in flat steps) but keeps a static dither at ~2 Mbps (0%). Moving film grain is a look, not a fix: it needs `-tune grain` and 15-50 Mbps. `reel_critic` measures banding |
| Edit/archive master | ProRes 422 HQ (`-c:v prores_ks -profile:v 3`) + PCM 24-bit audio |
| Alpha (overlays, editors) | ProRes 4444 (`deliver.prores4444`) or PNG sequence (`timeline.render_rgba`) |
| Alpha (web, stickers) | WebM VP9 with alpha (`deliver.webm_alpha`), APNG (`deliver.apng`) |
| GIF | `deliver.gif(src, out, fps=12-15, width=..., max_mb=...)`: palettegen/paletteuse, size budget |
| Web/app vector | Lottie JSON (`web.lottie_from_svg`, `web.Lottie`) or CSS keyframes (`web.css_animation`); see `ui-motion.md` |

Transparent renders: `timeline.render_rgba(draw, n, out_dir)` needs a draw() that leaves the
background unpainted. Check alpha survived with `deliver.probe_alpha(file)`.

Loops: render frames [0, N) of a cycle whose frame N equals frame 0, then
`deliver.loop_report(file)` (flags a jump at the seam and a duplicated end frame).

Platform upload guidance (YouTube SDR, verify current): 1080p ~8 Mbps at 24-30 fps,
~12 Mbps at 48-60 fps; 4K ~35-45 / 53-68 Mbps. Upload a higher-quality master and let
the platform transcode.

## Frame rate
- Character / stylised animation: 24 fps (or 25 for PAL broadcast).
- Motion graphics/UI: 24/30, 60 only when the motion benefits (UI demos, games).
- Never mix cadences unintentionally within a piece.

## Aspect ratios
16:9 (1920x1080 / 3840x2160), 9:16 (1080x1920), 1:1 (1080x1080), 4:5 (1080x1350),
2.39:1 letterbox for cinematic looks (render the real ratio, don't just add bars to
a 16:9 composition). Recompose for each (`cinematography.md`).

## Reel package (studio / client)
- Length: tight; Pixar's careers FAQ says reels should be "approximately one to three
  minutes". 60-90 s is a strong default. Best work first.
- Title card: name, role sought, contact (email/site); repeat on end card.
- Shot breakdown (`templates/breakdown.md`): per shot, what you did vs. what you used.
- Mark self-initiated / fan / tutorial-based work honestly; credit collaborators.
- Music: off or unobtrusive; original sound for dialogue pieces.
- Host where the link stays stable and the video can be replaced (e.g. Vimeo).

## Captions and accessibility
- Burned-in captions only when platform requires; otherwise ship an SRT/VTT
  (`deliver.write_srt`, `write_vtt`). Burn-in with `deliver.draw_caption` inside the safe
  zone: 1-2 lines, about 42 characters per line, at least ~1 s on screen.
- Vertical feeds: keep text and key action inside `deliver.safe_zone("vertical", w, h)`
  (clear of the platform's caption and button overlays; approximate, check current specs);
  check stills with `deliver.safe_zone_overlay`.
- Flashing: no more than three flashes in any one-second period (WCAG 2.3.1) for
  anything with strobe-like light changes.
- Text contrast >= 4.5:1 against its background (WCAG body-text ratio). Working
  default for mobile legibility (house rule, not a standard): cap height >= ~3.5% of
  frame height; tiny monospace "metadata" labels at 1-2% are unreadable on phones.

## Verify before handing over
- `ffprobe` each file: duration, fps, resolution, codecs, audio channels.
- Play the first and last seconds; check there are no black/blank frames at the ends.
- Re-run `reel_critic` on the final masters (not the previews).
- Inspect each final aspect at intended size, the actual platform crop/safe-area
  overlay and thumbnail. Record which exports were viewed; do not infer that a
  landscape preview proves the vertical version. Check text/control cuts, the first
  useful frame and the final lock-up or resting state.
- Keep editable source, the asset-origin ledger and a sidecar identifying generated,
  synthetic, sample or substituted material. Carry any mock/live distinction through
  handoff and surfaces where a user would otherwise rely on it as live evidence.
- Report measured/inspected/source-only/not-run separately. A codec probe does not
  establish visual quality, intelligible sound, accessibility or target-player support.
