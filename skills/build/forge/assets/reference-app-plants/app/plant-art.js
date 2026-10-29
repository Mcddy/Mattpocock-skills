/* Plant illustrations for the watering round: eight plant shapes in a terracotta pot, and three spot scenes
   (empty pot, watered, wilting). Drawn by the visual kit's method (assets/visual-kit/illustrations.js):
   the same forms either flat (solid fills, one shade step) or clay (offset radial gradient per material,
   the kit's rim-light filter, a soft contact shadow). Uses CLAY.ctx() and CLAY.tone() from the kit file,
   which must load first. Colours come from the plants; backdrops come from the page's tokens.
   Globals: plantArt(kind, {style, bg, label}), plantScene(name, {style}). */

const PLANT_ART = (() => {
  const T = CLAY.tone;
  const isHex = c => /^#[0-9a-f]{6}$/i.test(c);
  const r1 = n => Math.round(n * 10) / 10;
  const TERRA = '#C8673E', SOIL = '#5B3A28', STEM = '#3C6B3A';

  function painter(c, clay) {
    return {
      clay,
      // body paint for one material
      f(col, o = {}) {
        if (!clay) return isHex(col) ? `fill="${col}"` : `style="fill:${col}"`;
        return `fill="${c.rad([[0, T(col, .12, 4, -.03)], [.42, col], [1, T(col, -.16, -4, .02)]], { r: .62, fx: .3, fy: .22, ...o })}"`;
      },
      // the clay filter (volume and rim light); nothing when flat
      fx(col, drop = 0) { return clay ? ` filter="${c.clay(T(col, -.34, -8, .04), { drop })}"` : ''; },
      // flat style's single shade step; clay leaves it to the gradient
      step(col, d = -.08) { return clay ? null : T(col, d); },
      shadow(cx, cy, rx, ry) {
        return clay ? `<ellipse cx="${cx}" cy="${cy}" rx="${rx}" ry="${ry}" fill="${c.glow('#2A1A10', .28)}"/>`
          : `<ellipse cx="${cx}" cy="${cy}" rx="${rx}" ry="${ry * .7}" fill="#2A1A10" opacity=".12"/>`;
      },
    };
  }

  /* ---------- shapes ---------- */
  const leafPath = (len, w) => `M0 0C${r1(w * .62)} ${r1(-len * .16)} ${r1(w * .64)} ${r1(-len * .7)} 0 ${-len}C${r1(-w * .64)} ${r1(-len * .7)} ${r1(-w * .62)} ${r1(-len * .16)} 0 0Z`;
  const halfLeaf = (len, w) => `M0 0C${r1(w * .62)} ${r1(-len * .16)} ${r1(w * .64)} ${r1(-len * .7)} 0 ${-len}Z`;
  const heartPath = s => `M0 0C${r1(-.5 * s)} ${r1(-.05 * s)} ${r1(-.64 * s)} ${r1(-.5 * s)} ${r1(-.48 * s)} ${r1(-.8 * s)}C${r1(-.36 * s)} ${r1(-1.02 * s)} ${r1(-.1 * s)} ${r1(-1.06 * s)} 0 ${r1(-.92 * s)}C${r1(.1 * s)} ${r1(-1.06 * s)} ${r1(.36 * s)} ${r1(-1.02 * s)} ${r1(.48 * s)} ${r1(-.8 * s)}C${r1(.64 * s)} ${r1(-.5 * s)} ${r1(.5 * s)} ${r1(-.05 * s)} 0 0Z`;

  function leaf(P, x, y, len, w, rot, col, rib = true) {
    const st = P.step(col);
    return `<g transform="translate(${x} ${y}) rotate(${rot})"><path d="${leafPath(len, w)}" ${P.f(col)}${P.fx(col, 1.2)}/>`
      + (st ? `<path d="${halfLeaf(len, w)}" fill="${st}"/>` : '')
      + (rib ? `<path d="M0 -2Q${r1(w * .05)} ${r1(-len * .5)} 0 ${r1(-len * .84)}" fill="none" stroke="${T(col, .16)}" stroke-width="1.2" stroke-linecap="round" opacity=".75"/>` : '') + '</g>';
  }

  function heart(P, c, x, y, s, rot, col, slits = 0) {
    let mask = '';
    if (slits) {
      const id = c.id();
      let cuts = '';
      for (let i = 0; i < slits; i++) for (const k of [-1, 1]) {
        const yy = -s * (.3 + i * .2), ex = k * s * .62, ix = k * s * .14;
        cuts += `<path d="M${r1(ex)} ${r1(yy - s * .05)}L${r1(ix)} ${r1(yy - s * .02)}L${r1(ex)} ${r1(yy + s * .03)}Z" fill="#000"/>`;
      }
      c.defs.push(`<mask id="${id}" maskUnits="userSpaceOnUse" x="${-s}" y="${-s * 1.2}" width="${2 * s}" height="${1.4 * s}"><rect x="${-s}" y="${-s * 1.2}" width="${2 * s}" height="${1.4 * s}" fill="#fff"/>${cuts}</mask>`);
      mask = ` mask="url(#${id})"`;
    }
    const st = P.step(col);
    const half = `M0 0C${r1(.5 * s)} ${r1(-.05 * s)} ${r1(.64 * s)} ${r1(-.5 * s)} ${r1(.48 * s)} ${r1(-.8 * s)}C${r1(.36 * s)} ${r1(-1.02 * s)} ${r1(.1 * s)} ${r1(-1.06 * s)} 0 ${r1(-.92 * s)}Z`;
    return `<g transform="translate(${x} ${y}) rotate(${rot})"><g${mask}><path d="${heartPath(s)}" ${P.f(col)}${P.fx(col, 1.2)}/>`
      + (st ? `<path d="${half}" fill="${st}"/>` : '') + `</g><path d="M0 -1L0 ${r1(-s * .86)}" stroke="${T(col, .16)}" stroke-width="1.2" stroke-linecap="round" opacity=".7"/></g>`;
  }

  function pot(P, x = 60, top = 77, w = 54, h = 32, col = TERRA) {
    const bw = w * .76, L = x - w / 2, R = x + w / 2, bl = x - bw / 2, br = x + bw / 2, b = top + h;
    const body = `M${L + 2} ${top + 5}L${R - 2} ${top + 5}L${br} ${b - 3}Q${br} ${b} ${br - 4} ${b}L${bl + 4} ${b}Q${bl} ${b} ${bl} ${b - 3}Z`;
    const st = P.step(col, -.07);
    const shade = st ? `<path d="M${x + w * .12} ${top + 5}L${R - 2} ${top + 5}L${br} ${b - 3}Q${br} ${b} ${br - 4} ${b}L${x + bw * .1} ${b}Z" fill="${st}"/>` : '';
    return P.shadow(x + 2, b + 2, w * .52, 5)
      + `<path d="${body}" ${P.f(col)}${P.fx(col, 2)}/>${shade}`
      + `<rect x="${L - 3}" y="${top - 3}" width="${w + 6}" height="11" rx="4.5" ${P.f(T(col, .05, 2))}${P.fx(col)}/>`
      + (st ? `<rect x="${x + w * .14}" y="${top - 3}" width="${R + 3 - x - w * .14}" height="11" rx="4.5" fill="${T(col, -.03)}"/><rect x="${L - 3}" y="${top - 3}" width="${w + 6}" height="3" rx="1.5" fill="${T(col, .08, 4)}"/>` : '')
      + `<ellipse cx="${x}" cy="${top - 2}" rx="${w / 2 - 1}" ry="3" fill="${SOIL}"/>`;
  }

  /* ---------- the eight shapes ---------- */
  const DRAW = {
    split(P, c) { // Monstera: split heart leaves on long stems
      const col = '#2F7A45', st = (x, y) => `<path d="M60 74Q${(60 + x) / 2} ${(74 + y) / 2 + 6} ${x} ${y}" fill="none" stroke="${STEM}" stroke-width="2.4" stroke-linecap="round"/>`;
      return st(36, 50) + st(84, 44) + st(58, 34) + st(28, 66)
        + heart(P, c, 28, 66, 20, -62, '#3B8A4F', 1) + heart(P, c, 36, 50, 30, -34, col, 2) + heart(P, c, 84, 44, 30, 32, '#3B8A4F', 2) + heart(P, c, 58, 34, 28, -4, col, 2) + pot(P);
    },
    fern(P) { // Boston fern: arching fronds, leaflets from a dashed stroke
      let out = '';
      const greens = ['#4E9A47', '#3E8A3E', '#5DAA4F'];
      [-82, -62, -40, -18, 0, 18, 40, 62, 82].forEach((a, i) => {
        const rad = a * Math.PI / 180, L = 44 - Math.abs(a) * .08, sx = Math.sin(rad), cy = Math.cos(rad);
        const tx = 60 + L * sx, ty = 72 - L * cy + Math.abs(sx) * 18, qx = 60 + L * .55 * sx, qy = 72 - L * .7 * cy - 8;
        const col = greens[i % 3], d = `M60 72Q${r1(qx)} ${r1(qy)} ${r1(tx)} ${r1(ty)}`;
        out += `<path d="${d}" fill="none" ${P.clay ? `stroke="${P.f(col).slice(6, -1)}"` : `stroke="${col}"`} stroke-width="9" stroke-dasharray="2.3 1.3" stroke-linecap="round"${P.fx(col)}/>`
          + `<path d="${d}" fill="none" stroke="${T(col, -.12)}" stroke-width="1.3" stroke-linecap="round"/>`;
      });
      return out + pot(P);
    },
    upright(P) { // Snake plant: sword blades with a yellow edge and light bands
      let out = '';
      [[46, 52, -10, 6.5], [72, 56, 9, 6.5], [54, 66, -3, 7.5], [65, 60, 4, 7], [40, 38, -18, 5.5], [80, 40, 17, 5.5]].forEach(([x, h, rot, w]) => {
        const blade = (ww, hh) => `M${-ww} 0C${-ww} ${r1(-hh * .6)} ${r1(-ww * .4)} ${r1(-hh * .95)} 0 ${-hh}C${r1(ww * .4)} ${r1(-hh * .95)} ${ww} ${r1(-hh * .6)} ${ww} 0Z`;
        let bands = '';
        for (let k = 1; k <= 3; k++) bands += `<path d="M${-w * .7} ${r1(-h * k * .22)}q${w * .7} -2.4 ${w * 1.4} 0" fill="none" stroke="#6AA867" stroke-width="1.4" stroke-linecap="round" opacity=".8"/>`;
        out += `<g transform="translate(${x} 76) rotate(${rot})"><path d="${blade(w + 1.4, h + 2)}" ${P.f('#D3C258')}/><path d="${blade(w, h)}" ${P.f('#2E6B3E')}${P.fx('#2E6B3E', 1)}/>${bands}</g>`;
      });
      return out + pot(P);
    },
    round(P) { // Chinese money plant: coin leaves on thin stems
      let out = '';
      const pts = [[30, 44, 10], [44, 28, 11], [62, 20, 12], [80, 30, 11], [92, 48, 10], [52, 46, 9.5], [72, 46, 10]];
      for (const [x, y] of pts) out += `<path d="M60 74Q${(60 + x) / 2} ${(74 + y) / 2 + 8} ${x} ${y}" fill="none" stroke="${STEM}" stroke-width="1.8" stroke-linecap="round"/>`;
      for (const [x, y, r] of pts) {
        const st = P.step('#5DA352');
        out += `<circle cx="${x}" cy="${y}" r="${r}" ${P.f('#5DA352')}${P.fx('#5DA352', 1.2)}/>` + (st ? `<path d="M${x} ${y - r}A${r} ${r} 0 0 1 ${x} ${y + r}Z" fill="${st}"/>` : '')
          + `<circle cx="${x}" cy="${y}" r="1.6" fill="${T('#5DA352', -.18)}"/>`;
      }
      return out + pot(P);
    },
    trailing(P, c) { // Pothos: heart leaves on top, two vines over the rim
      let out = heart(P, c, 46, 70, 16, -40, '#4E9A4A') + heart(P, c, 74, 70, 16, 38, '#5AA552') + heart(P, c, 60, 66, 18, -4, '#4E9A4A') + heart(P, c, 52, 56, 13, -18, '#6DB35E') + heart(P, c, 69, 55, 13, 16, '#4E9A4A');
      out += pot(P);
      out += `<path d="M38 76C26 84 24 96 28 112" fill="none" stroke="${STEM}" stroke-width="2" stroke-linecap="round"/><path d="M83 76C96 82 98 94 94 106" fill="none" stroke="${STEM}" stroke-width="2" stroke-linecap="round"/>`;
      out += heart(P, c, 30, 88, 10, -120, '#5AA552') + heart(P, c, 26, 102, 9, -150, '#4E9A4A') + heart(P, c, 29, 113, 8, 170, '#6DB35E') + heart(P, c, 93, 88, 10, 115, '#4E9A4A') + heart(P, c, 96, 101, 9, 160, '#5AA552');
      return out;
    },
    tree(P) { // Fiddle-leaf fig: a trunk with large violin leaves
      const col = '#3B7A3A';
      return `<path d="M60 76C59 60 61 44 60 22" fill="none" stroke="#7A5A3C" stroke-width="3.2" stroke-linecap="round"/>`
        + leaf(P, 60, 64, 26, 24, -64, '#457F3F') + leaf(P, 60, 56, 26, 24, 62, col) + leaf(P, 60, 44, 25, 23, -52, col)
        + leaf(P, 60, 36, 24, 22, 50, '#457F3F') + leaf(P, 60, 26, 22, 20, -6, col) + pot(P);
    },
    spiky(P) { // Aloe: thick fleshy spears with pale freckles
      let out = '';
      [[-62, 30], [62, 30], [-40, 40], [40, 40], [-16, 46], [16, 46], [0, 50]].forEach(([rot, h]) => {
        const w = 7.5, col = '#78AE92';
        const spear = `M${-w} 0Q${r1(-w * .7)} ${r1(-h * .62)} 0 ${-h}Q${r1(w * .7)} ${r1(-h * .62)} ${w} 0Z`;
        const st = P.step(col);
        out += `<g transform="translate(60 76) rotate(${rot})"><path d="${spear}" ${P.f(col)}${P.fx(col, 1)}/>` + (st ? `<path d="M0 0L0 ${-h}Q${r1(w * .7)} ${r1(-h * .62)} ${w} 0Z" fill="${st}"/>` : '')
          + `<circle cx="-2" cy="${r1(-h * .35)}" r="1.1" fill="#E8F2E6"/><circle cx="2" cy="${r1(-h * .55)}" r="1" fill="#E8F2E6"/></g>`;
      });
      return out + pot(P, 60, 78, 52, 30);
    },
    flower(P) { // Peace lily: dark lance leaves and white spathes
      let out = '';
      [[-58, 34], [58, 34], [-34, 42], [34, 42], [-12, 46], [12, 46]].forEach(([rot, len], i) => { out += leaf(P, 60, 74, len, 14, rot, i % 2 ? '#2F6A3E' : '#367544'); });
      for (const [x, y, rot] of [[50, 22, -14], [72, 30, 12]]) {
        out += `<path d="M60 74Q${(60 + x) / 2 - 2} 50 ${x} ${y + 16}" fill="none" stroke="${STEM}" stroke-width="1.8" stroke-linecap="round"/>`
          + `<g transform="translate(${x} ${y + 17}) rotate(${rot})"><path d="${leafPath(25, 17)}" ${P.f('#F6F4EC')}${P.fx('#D8D4C4', 1)}/>${P.clay ? '' : `<path d="${halfLeaf(25, 17)}" fill="#E7E3D6"/>`}`
          + `<rect x="-2.2" y="-17" width="4.4" height="12" rx="2.2" ${P.f('#E2C761')}/></g>`;
      }
      return out + pot(P);
    },
  };

  /* One plant in the 120 box, on an optional token-coloured disc. */
  function plantArt(kind, { style = 'flat', bg = null, label = null } = {}) {
    const c = CLAY.ctx(), P = painter(c, style === 'clay');
    const body = (DRAW[kind] || DRAW.round)(P, c);
    const disc = bg ? `<circle cx="60" cy="60" r="58" style="fill:${bg}"/>` : '';
    const a11y = label ? `role="img" aria-label="${label.replace(/[<>&"]/g, '')}"` : 'aria-hidden="true"';
    return `<svg viewBox="0 0 120 120" class="av plant" ${a11y} focusable="false" style="color-interpolation-filters:sRGB"><defs>${c.defs.join('')}</defs>${disc}${body}</svg>`;
  }

  /* Spot scenes in a 240 by 180 box: the backdrop is the page's --sig-soft. */
  function plantScene(name, { style = 'flat' } = {}) {
    const c = CLAY.ctx(), P = painter(c, style === 'clay');
    const back = `<path d="M40 96C34 52 78 22 124 24C174 26 210 54 206 98C202 140 166 160 120 160C76 160 44 136 40 96Z" style="fill:var(--sig-soft)"/>`;
    const place = (x, y, s, inner) => `<g transform="translate(${x} ${y}) scale(${s}) translate(-60 -60)">${inner}</g>`;
    let out = back;
    if (name === 'empty') { // an empty pot of fresh soil, one seedling, a trowel
      out += place(112, 92, 1.45, pot(P) + `<path d="M60 74C60 66 60 62 61 58" fill="none" stroke="${STEM}" stroke-width="2" stroke-linecap="round"/>` + leaf(P, 61, 60, 11, 8, -58, '#6DB35E', false) + leaf(P, 61, 59, 12, 8, 54, '#5DA352', false));
      out += `<g transform="translate(176 106) rotate(28)"><rect x="-4" y="-46" width="8" height="26" rx="4" ${P.f('#9A6B43')}${P.fx('#9A6B43')}/><path d="M-11 -20H11L7 14Q0 24 -7 14Z" ${P.f('#A9B4BD')}${P.fx('#7D8A95', 1)}/></g>`;
    }
    if (name === 'done') { // watered: the can tipped over a fern, drops falling
      out += place(100, 96, 1.3, DRAW.fern(P));
      const can = P.f('var(--pop)'), stroke = P.clay ? '' : '';
      out += `<g transform="translate(170 52) rotate(-24)"><path d="M-24 -16H18L14 22Q13 28 7 28H-19Q-25 28 -25 22Z" ${can}${P.fx('#333333', 2)}/>`
        + `<path d="M-24 -10L-56 -26L-58 -21L-25 -2Z" ${can}/><rect x="-62" y="-31" width="9" height="13" rx="3" transform="rotate(-24 -57 -24)" ${can}/>`
        + `<path d="M18 -10C32 -10 34 18 16 16" fill="none" style="stroke:var(--pop)" stroke-width="5" stroke-linecap="round"/>${stroke}</g>`;
      for (const [x, y, s] of [[102, 46, 1], [110, 58, .85], [96, 62, .9], [116, 40, .7], [104, 72, .75]]) {
        out += `<path transform="translate(${x} ${y}) scale(${s})" d="M0 -6C2.6 -2 4.6 1 4.6 3.4A4.6 4.6 0 0 1 -4.6 3.4C-4.6 1 -2.6 -2 0 -6Z" ${P.f('#5FA8DB')}/>`;
      }
    }
    if (name === 'dry') { // wilting: a money plant with its coins drooping
      let inner = '';
      const pts = [[34, 66], [44, 52], [62, 46], [78, 54], [88, 68]];
      for (const [x, y] of pts) inner += `<path d="M60 74Q${(60 + x) / 2} ${y - 18} ${x} ${y}" fill="none" stroke="#7C8A4C" stroke-width="1.8" stroke-linecap="round"/>`;
      for (const [x, y] of pts) inner += `<ellipse cx="${x}" cy="${y + 6}" rx="7" ry="9" ${P.f('#B6B35E')}${P.fx('#B6B35E', 1)}/>`;
      out += place(120, 94, 1.4, inner + pot(P));
    }
    return `<svg viewBox="0 0 240 180" class="spot plant" aria-hidden="true" focusable="false" style="color-interpolation-filters:sRGB"><defs>${c.defs.join('')}</defs>${out}</svg>`;
  }

  return { plantArt, plantScene, KINDS: Object.keys(DRAW) };
})();
const plantArt = (k, o) => PLANT_ART.plantArt(k, o);
const plantScene = (n, o) => PLANT_ART.plantScene(n, o);
