/* Clay illustrations, core and dog pack: the eight dogs from the grooming-book gallery and four spot scenes, as soft 3D
   clay in plain SVG. Globals: CLAY (the helpers below, for other subjects), clayDog(key, {bg, size}), scene(name, {palette, dog}).
   For another subject, write a pack on CLAY's helpers as illustrations-plants.js does; drawings may hold their own subject
   colours (leaf greens, coat colours), and backdrops come from the page's tokens.
   Light comes from the top left: every volume gets an offset radial gradient, a soft inner shadow and rim light (one SVG
   filter), and a contact shadow. Ids are unique per call, so any number can share a page. */

const CLAY = (() => {
  let seq = 0;
  const r1 = n => Math.round(n * 10) / 10;
  const P2 = (x, y) => `${r1(x)} ${r1(y)}`;
  const isHex = c => /^#[0-9a-f]{6}$/i.test(c);

  /* ---------- colour ---------- */
  function hsl(h) {
    const n = parseInt(h.slice(1), 16), r = (n >> 16) / 255, g = (n >> 8 & 255) / 255, b = (n & 255) / 255;
    const mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2, d = mx - mn;
    let hu = 0, s = 0;
    if (d) {
      s = d / (1 - Math.abs(2 * l - 1));
      hu = mx === r ? ((g - b) / d) % 6 : mx === g ? (b - r) / d + 2 : (r - g) / d + 4;
      hu = (hu * 60 + 360) % 360;
    }
    return [hu, s, l];
  }
  function toHex([h, s, l]) {
    s = Math.max(0, Math.min(1, s)); l = Math.max(0, Math.min(1, l)); h = ((h % 360) + 360) % 360;
    const c = (1 - Math.abs(2 * l - 1)) * s, x = c * (1 - Math.abs((h / 60) % 2 - 1)), m = l - c / 2;
    const [r, g, b] = h < 60 ? [c, x, 0] : h < 120 ? [x, c, 0] : h < 180 ? [0, c, x] : h < 240 ? [0, x, c] : h < 300 ? [x, 0, c] : [c, 0, x];
    return '#' + [r, g, b].map(v => Math.round((v + m) * 255).toString(16).padStart(2, '0')).join('');
  }
  /* Shift lightness (dl), hue (dh) and saturation (ds). Warm shadows drift toward red, highlights toward yellow.
     Palette colours (CSS variables) cannot be computed here, so they become color-mix() against white or a deep shade. */
  function tone(c, dl, dh = 0, ds = 0) {
    if (!isHex(c)) return dl >= 0 ? `color-mix(in oklab,${c} ${Math.round(100 - dl * 220)}%,#fff)`
      : `color-mix(in oklab,${c} ${Math.round(100 + dl * 190)}%,#120a1e)`;
    const [h, s, l] = hsl(c); return toHex([h + dh, s + ds, l + dl]);
  }
  const mix = (a, b, pct) => `color-mix(in oklab,${a} ${pct}%,${b})`;
  const paint = p => /^(#|url|none)/.test(p) ? `fill="${p}"` : `style="fill:${p}"`;
  const pen = p => /^(#|url|none)/.test(p) ? `stroke="${p}"` : `style="stroke:${p}"`;
  const nf = v => String(+(+v).toFixed(3)).replace(/^(-?)0\./, '$1.');  // .5 not 0.5, no float noise
  const stopTag = ([o, col, op]) => `<stop offset="${nf(o)}" ${/^#/.test(col) ? `stop-color="${col}"` : `style="stop-color:${col}"`}${op == null || op === 1 ? '' : ` stop-opacity="${nf(op)}"`}/>`;

  /* Clay ramp: highlight, body, core shadow, a touch of bounce light at the far edge. */
  function ramp(c, k = {}) {
    const hi = k.hi ?? .1, lo = k.lo ?? .14;
    if (!isHex(c)) return [[0, tone(c, hi)], [.4, c], [1, tone(c, -lo)]];
    return [[0, tone(c, hi, 4, -.03)], [.38, c], [.84, tone(c, -lo, -4, .02)], [1, tone(c, -lo * .8, -5, .02)]];
  }

  /* ---------- per-call context: unique ids, defs, memoised gradients and filters ---------- */
  function ctx() {
    const u = 'cl' + (++seq).toString(36) + '-';
    let n = 0; const defs = [], memo = {};
    const id = () => u + (n++).toString(36);
    const once = (key, make) => memo[key] || (memo[key] = make());
    return {
      defs, id, once,
      rad(stops, o = {}) {
        return once('r' + JSON.stringify([stops, o]), () => {
          const i = id(), a = [];
          for (const [k, def] of [['cx', .5], ['cy', .5], ['r', .5], ['fx', null], ['fy', null]]) if (o[k] != null && o[k] !== def) a.push(`${k}="${nf(o[k])}"`);
          if (o.u) a.push('gradientUnits="userSpaceOnUse"');
          defs.push(`<radialGradient id="${i}" ${a.join(' ')}>${stops.map(stopTag).join('')}</radialGradient>`);
          return `url(#${i})`;
        });
      },
      lin(stops, x1, y1, x2, y2, u) {
        const i = id();
        defs.push(`<linearGradient id="${i}" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"${u ? ' gradientUnits="userSpaceOnUse"' : ''}>${stops.map(stopTag).join('')}</linearGradient>`);
        return `url(#${i})`;
      },
      clip(d) { const i = id(); defs.push(`<clipPath id="${i}"><path d="${d}"/></clipPath>`); return `url(#${i})`; },
      /* Soft inner shadow (bottom right), rim light (top left) and optional drop shadow, as one filter. */
      clay(shadow = '#000000', { drop = 0, s = 1, op = .34 } = {}) {
        return once(`f${shadow}${drop}${s}${op}`, () => {
          const i = id(), b = r1(2.2 * s), o = r1(2 * s), n = nf;
          const flood = (c, a, src, res) => `<feFlood ${/^#/.test(c) ? `flood-color="${c}"` : `style="flood-color:${c}"`} flood-opacity="${n(a)}"/><feComposite in2="${src}" operator="in" result="${res}"/>`;
          const off = (dx, dy, res, cut) => `<feOffset in="b" dx="${r1(dx)}" dy="${r1(dy)}" result="${res}"/>` + (cut ? `<feComposite in="SourceAlpha" in2="${res}" operator="out" result="${res}"/>` : '');
          defs.push(`<filter id="${i}" x="-.25" y="-.25" width="1.5" height="1.6"><feGaussianBlur in="SourceAlpha" stdDeviation="${b}" result="b"/>`
            + off(-o, -o * 1.3, 'p', 1) + flood(shadow, op, 'p', 'p') + off(o * .8, o, 'q', 1) + flood('#ffffff', .5, 'q', 'q')
            + (drop ? off(drop * .45, drop, 'd') + flood(shadow, .3, 'd', 'd') : '')
            + `<feMerge>${drop ? '<feMergeNode in="d"/>' : ''}<feMergeNode in="SourceGraphic"/><feMergeNode in="p"/><feMergeNode in="q"/></feMerge></filter>`);
          return `url(#${i})`;
        });
      },
      /* Soft round blob of colour fading to nothing: contact shadows, blush, occlusion. */
      glow(c, a = .3) { return once(`g${c}${a}`, () => this.rad([[0, c, a], [.55, c, a * .55], [1, c, 0]])); },
    };
  }

  /* ---------- shape helpers ---------- */
  // A "bun": an ellipse whose top and bottom halves have their own height and fullness (k), so cheeks can sit low and wide.
  function bun(cx, cy, rx, rt, rb, kt = .56, kb = .6) {
    return `M${P2(cx, cy - rt)}C${P2(cx + kt * rx, cy - rt)} ${P2(cx + rx, cy - kt * rt)} ${P2(cx + rx, cy)}`
      + `C${P2(cx + rx, cy + kb * rb)} ${P2(cx + kb * rx, cy + rb)} ${P2(cx, cy + rb)}`
      + `C${P2(cx - kb * rx, cy + rb)} ${P2(cx - rx, cy + kb * rb)} ${P2(cx - rx, cy)}`
      + `C${P2(cx - rx, cy - kt * rt)} ${P2(cx - kt * rx, cy - rt)} ${P2(cx, cy - rt)}Z`;
  }
  const ept = (cx, cy, rx, ry, rot, a) => {
    const c = Math.cos(a), s = Math.sin(a), cr = Math.cos(rot), sr = Math.sin(rot);
    return [cx + rx * c * cr - ry * s * sr, cy + rx * c * sr + ry * s * cr];
  };
  /* Tufted outline around an ellipse. round: arc bumps (curls). Otherwise twisted pointed tufts (fluff). */
  function tufts(cx, cy, rx, ry, n, bump, { rot = 0, twist = 0, round = false, start = 0 } = {}) {
    const R = rot * Math.PI / 180; let d = '';
    for (let i = 0; i <= n; i++) {
      const a = start + i / n * 2 * Math.PI, p = ept(cx, cy, rx, ry, R, a);
      if (!i) { d = `M${P2(...p)}`; continue; }
      if (round) {
        const q = ept(cx, cy, rx, ry, R, start + (i - 1) / n * 2 * Math.PI), ch = Math.hypot(p[0] - q[0], p[1] - q[1]);
        d += `A${r1(ch * .56)} ${r1(ch * .56)} 0 0 1 ${P2(...p)}`;
      } else {
        const m = start + (i - .5 + twist) / n * 2 * Math.PI, q = ept(cx, cy, rx + bump * 2, ry + bump * 2, R, m);
        d += `Q${P2(...q)} ${P2(...p)}`;
      }
    }
    return d + 'Z';
  }

  /* Round bumps along an elliptical arc from angle a0 to a1 (degrees): cloud tops, foam, shaggy crowns. */
  function bumps(cx, cy, rx, ry, a0, a1, n, move = true) {
    const pt = a => [cx + rx * Math.cos(a * Math.PI / 180), cy + ry * Math.sin(a * Math.PI / 180)];
    let d = move ? `M${P2(...pt(a0))}` : `L${P2(...pt(a0))}`, prev = pt(a0);
    for (let i = 1; i <= n; i++) {
      const p = pt(a0 + (a1 - a0) * i / n), ch = Math.hypot(p[0] - prev[0], p[1] - prev[1]) * (i % 2 ? .56 : .6);
      d += `A${r1(ch)} ${r1(ch)} 0 0 ${a1 > a0 ? 1 : 0} ${P2(...p)}`; prev = p;
    }
    return d;
  }
  /* Smooth closed blob through n jittered points on an ellipse (Catmull-Rom as cubics): soft backdrops. */
  function blob(cx, cy, rx, ry, ks, rot = 0) {
    const n = ks.length, pts = ks.map((k, i) => { const a = rot + i / n * 2 * Math.PI; return [cx + rx * (1 + k) * Math.cos(a), cy + ry * (1 + k) * Math.sin(a)]; });
    let d = `M${P2(...pts[0])}`;
    for (let i = 0; i < n; i++) {
      const p0 = pts[(i - 1 + n) % n], p1 = pts[i], p2 = pts[(i + 1) % n], p3 = pts[(i + 2) % n];
      d += `C${P2(p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)} ${P2(p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)} ${P2(...p2)}`;
    }
    return d + 'Z';
  }

  /* ---------- the dogs ---------- */
  /* Same rule as gallery.js (fur, ears, muzzle, markings) with the extra tones clay needs. */
  const BREEDS = {
    max:     { fur: '#E6A770', curls: '#D18A50', ear: 'curl', earc: '#C77D42', muzzle: '#F6D3A9', tongue: true, lo: .12 },
    bella:   { fur: '#F3E4C9', curls: '#E7D0A8', ear: 'curl', earc: '#DDC196', muzzle: '#FCF3E3' },
    reggie:  { fur: '#EEE9E0', ear: 'flop', earc: '#959FAD', muzzle: '#FFFFFF', sheep: '#A9B2BE', lo: .1 },
    biscuit: { fur: '#9C6744', ear: 'rose', earc: '#7B4C2E', muzzle: '#F6ECE2', blaze: '#F6ECE2', tongue: true },
    kiwi:    { fur: '#F6EDE0', ear: 'long', earc: '#D8A764', muzzle: '#FFFFFF', topknot: '#FF7A8A', lo: .1 },
    rusty:   { fur: '#BA5A2F', ear: 'point', earc: '#BA5A2F', inner: '#E9A57E', muzzle: '#E4A47D', brows: '#E4A47D' },
    nala:    { fur: '#2C2727', ear: 'point', earc: '#2C2727', inner: '#6A5A5A', muzzle: '#FFFFFF', blaze: '#FFFFFF', hi: .2, lo: .1, blush: .2 },
    mochi:   { fur: '#F18B3B', ear: 'small', earc: '#F18B3B', inner: '#F9B98A', muzzle: '#FAC793', ruff: '#F8B371', lo: .11 },
  };
  const EYE = '#1B130F', LINE = '#3A241B';
  const HEAD = bun(60, 64, 35, 33, 31, .56, .68);
  const MUZZLE = bun(60, 79.5, 17.5, 11, 12.5, .58, .66);

  /* One dog head in the 120 box. o.sleep closes the eyes. Returns markup; gradients and filters go into c.defs. */
  function head(c, key, o = {}) {
    const d = BREEDS[key] || BREEDS.max, out = [];
    const deep = tone(d.fur, -.34, -8, .04);
    const fxDrop = c.clay(deep, { drop: 2.6 }), fx = o.lite ? fxDrop : c.clay(deep);  // lite (scene) heads share one filter
    // Head-space gradient (user units) so markings on the head share its light.
    const hg = col => c.rad(ramp(col, d), { u: 1, cx: 60, cy: 66, r: 40, fx: 47, fy: 46 });
    const bb = (col, k = d, o2 = {}) => c.rad(ramp(col, k), { r: .55, fx: .34, fy: .26, ...o2 });
    const side = (s, f) => f(s === -1 ? -1 : 1, x => r1(60 + s * x));

    // Pomeranian ruff: one fluffy volume behind the head, twisted tufts.
    if (d.ruff) {
      out.push(`<path d="${tufts(60, 65, 42, 39, 22, 2.6, { twist: .3, start: -.1 })}" ${paint(c.rad(ramp(d.ruff, { hi: .1, lo: .1 }), { r: .55, fx: .34, fy: .26 }))} filter="${fxDrop}"/>`);
      // a second, inner ring of lighter tufts gives the ruff depth
      out.push(`<path d="${tufts(60, 69, 36, 32, 18, 2, { twist: .35, start: .15 })}" ${paint(c.rad(ramp(tone(d.ruff, .06, 4), { hi: .08, lo: .08 }), { r: .55, fx: .34, fy: .22 }))} filter="${fx}"/>`);
    }

    // Ears that sit behind the head.
    const earG = () => bb(d.earc, { hi: .13, lo: .15 });
    if (d.ear === 'flop') for (const s of [-1, 1]) {
      const X = x => r1(60 + s * x);
      out.push(`<path d="M${X(24)} 38C${X(36)} 40 ${X(45)} 54 ${X(45)} 72C${X(45)} 86 ${X(40)} 95 ${X(31)} 95C${X(23)} 95 ${X(19)} 87 ${X(19)} 74C${X(19)} 56 ${X(17)} 40 ${X(24)} 38Z" ${paint(earG())} filter="${fx}"/>`);
    }
    if (d.ear === 'curl') {
      for (const s of [-1, 1]) out.push(`<path d="${tufts(60 + s * 31, 69, 12, 23, 10, 0, { rot: s * -12, round: true, start: -1.2 })}" ${paint(earG())} filter="${fx}"/>`);
    }
    if (d.ear === 'long') for (const s of [-1, 1]) {
      const X = x => r1(60 + s * x);
      out.push(`<path d="M${X(22)} 40C${X(34)} 40 ${X(44)} 56 ${X(44)} 76C${X(44)} 90 ${X(42)} 100 ${X(38)} 103C${X(35)} 105 ${X(33)} 101 ${X(32)} 99C${X(30)} 103 ${X(26)} 104 ${X(24)} 100C${X(21)} 94 ${X(18)} 84 ${X(18)} 70C${X(18)} 54 ${X(17)} 41 ${X(22)} 40Z" ${paint(earG())} filter="${fx}"/>`);
      out.push(`<path d="M${X(30)} 56C${X(31)} 70 ${X(32)} 84 ${X(31)} 96M${X(37)} 62C${X(38)} 74 ${X(39)} 86 ${X(37)} 97" fill="none" stroke="${tone(d.earc, -.16, -6)}" stroke-width="1.4" stroke-linecap="round" opacity=".45"/>`);
    }
    if (d.ear === 'point' || d.ear === 'small') {
      const big = d.ear === 'point';
      const ig = c.rad([[0, tone(d.inner, -.12, -6, .05)], [.6, d.inner], [1, tone(d.inner, .08)]], { r: .6, fx: .3, fy: .25 });
      for (const s of [-1, 1]) {
        const X = x => r1(60 + s * x);
        const outer = big
          ? `M${X(35)} 50C${X(37)} 38 ${X(33)} 24 ${X(28)} 19C${X(25)} 16 ${X(21)} 17 ${X(19)} 21C${X(14)} 31 ${X(13)} 43 ${X(14)} 52Z`
          : `M${X(32)} 44C${X(31)} 37 ${X(26)} 28 ${X(22)} 25C${X(19)} 23 ${X(17)} 25 ${X(16)} 28C${X(14)} 35 ${X(14)} 41 ${X(15)} 47Z`;
        const inner = big
          ? `M${X(31)} 46C${X(32)} 37 ${X(29)} 28 ${X(25)} 24C${X(23)} 22 ${X(21)} 23 ${X(20)} 26C${X(17)} 33 ${X(17)} 41 ${X(18)} 47Z`
          : `M${X(28)} 42C${X(27)} 37 ${X(25)} 32 ${X(22)} 30C${X(20)} 29 ${X(19)} 30 ${X(19)} 32C${X(18)} 36 ${X(18)} 40 ${X(19)} 44Z`;
        out.push(`<g filter="${fx}"><path d="${outer}" ${paint(earG())}/><path d="${inner}" ${paint(ig)}/></g>`);
      }
    }

    // Head volume with markings clipped to it, one filter over both so the shading reads as one surface.
    const marks = [];
    if (d.blaze) marks.push(`<path d="M56.5 26C55.5 40 52 54 49 70L71 70C68 54 64.5 40 63.5 26Z" ${paint(hg(d.blaze))}/>`);
    out.push(`<g filter="${fxDrop}"><path d="${HEAD}" ${paint(hg(d.fur))}/>${marks.length ? `<g clip-path="${c.clip(HEAD)}">${marks.join('')}</g>` : ''}</g>`);

    // Rose ears fold over the top corners of the head.
    // Rose ears: small flaps folded over the top corners, tip falling outward.
    if (d.ear === 'rose') for (const s of [-1, 1]) {
      const X = x => r1(60 + s * x);
      out.push(`<path d="M${X(9)} 32C${X(16)} 25 ${X(30)} 23 ${X(37)} 29C${X(40)} 32 ${X(39)} 38 ${X(36)} 44C${X(34.5)} 47.5 ${X(31)} 48 ${X(30)} 45C${X(28)} 40 ${X(22)} 35 ${X(9)} 32Z" ${paint(bb(d.earc, { hi: .14, lo: .12 }, { fx: s < 0 ? .3 : .45, fy: .2 }))} filter="${fxDrop}"/>`
        + `<path d="M${X(14)} 30C${X(22)} 27 ${X(31)} 27 ${X(35)} 31" fill="none" stroke="${tone(d.earc, .16, 4)}" stroke-width="1.6" stroke-linecap="round" opacity=".7"/>`);
    }

    // Poodle topknot: one curly volume (so the silhouette stays clean), with a few curls catching the light.
    if (d.curls) {
      const cg = bb(d.curls, { hi: .13, lo: .13 }, { fy: .22 });
      const hl = c.glow(tone(d.curls, .16, 4), .55);
      out.push(`<path d="${tufts(60, 36, 25.5, 12, 13, 0, { round: true, start: .25 })}" ${paint(cg)} filter="${fxDrop}"/>`
        + [[49, 31, 4.6], [61, 28, 5], [72.5, 32, 4.4], [42, 39, 3.6], [55, 38.5, 3.8], [67.5, 39, 3.8], [78.5, 40, 3.4]].map(([x, y, r]) => `<circle cx="${x}" cy="${y}" r="${r}" ${paint(hl)}/>`).join(''));
    }

    // Sheepdog mop: one shaggy volume over the crown, grey at the roots, white locks falling over the eyes.
    if (d.sheep) {
      const tips = [[27, 62], [38, 67.5], [49, 71], [60, 72.5], [71, 71], [82, 67.5], [93, 62]];
      const notch = [[32.5, 54.5], [43.5, 58.5], [54.5, 60.5], [65.5, 60.5], [76.5, 58.5], [87.5, 54.5]];
      let m = `M21.9 57.2C22 60 24 62 27 62`;
      tips.forEach(([x, y], i) => {
        if (i === tips.length - 1) return;
        const [nx, ny] = notch[i], [x2, y2] = tips[i + 1];
        m += `C${r1(x + 3.4)} ${y} ${r1(nx - .5)} ${r1(ny + 3.5)} ${nx} ${ny}C${r1(nx + .5)} ${r1(ny + 3.5)} ${r1(x2 - 3.4)} ${y2} ${x2} ${y2}`;
      });
      m += 'C96 62 98 60 98.1 57.2' + bumps(60, 52, 39, 25.5, 12, -192, 9, false);
      const roots = c.lin([[0, d.sheep], [.4, tone(d.sheep, .08)], [.8, '#FFFFFF']], 0, 27, 0, 64, 1);
      const shade = c.rad([[0, '#ffffff', .55], [.45, '#ffffff', 0], [.85, tone(d.sheep, -.3), 0], [1, tone(d.sheep, -.3), .22]], { r: .58, fx: .32, fy: .18 });
      const grooves = notch.map(([x, y], i) => { const k = i < 3 ? 1 : -1; return `M${x} ${y - 1}C${r1(x + k)} ${y - 4} ${r1(x + 1.6 * k)} ${y - 6} ${r1(x + 2.6 * k)} ${y - 7.5}`; }).join('');
      out.push(`<g filter="${fxDrop}"><path d="${m}" fill="${roots}"/><path d="${m}" ${paint(shade)}/></g>`
        + `<path d="${grooves}" fill="none" stroke="${tone(d.sheep, -.04)}" stroke-width="1.2" stroke-linecap="round" opacity=".28"/>`);
    }

    // Kelpie brows.
    if (d.brows) for (const s of [-1, 1]) out.push(`<ellipse cx="${60 + s * 13}" cy="51.5" rx="3.4" ry="2.5" ${paint(bb(d.brows, { hi: .08, lo: .1 }))}/>`);

    // Eyes: glossy beads in a faint socket, a big catch light and a small bounce.
    if (!d.sheep) {
      const sock = () => c.glow(tone(d.fur, -.3, -6), .28);
      const eg = c.rad([[0, '#5A4038'], [.45, '#24180F'], [.85, EYE], [1, '#3A2A24']], { r: .55, fx: .34, fy: .28 });
      for (const s of [-1, 1]) {
        const x = 60 + s * 13;
        if (o.sleep) { out.push(`<path d="M${x - 5} 61.5Q${x} 66 ${x + 5} 61.5" fill="none" stroke="${LINE}" stroke-width="2.3" stroke-linecap="round"/>`); continue; }
        out.push((o.lite ? '' : `<circle cx="${x}" cy="62" r="7.6" ${paint(sock())}/>`) + `<circle cx="${x}" cy="61.5" r="5.1" ${paint(eg)}/>`
          + `<ellipse cx="${x - 1.6}" cy="59.6" rx="1.9" ry="1.6" fill="#fff"/>` + (o.lite ? '' : `<circle cx="${x + 1.9}" cy="63.6" r=".8" fill="#fff" opacity=".55"/>`));
      }
    }

    // Blush.
    const bl = c.glow('#FF7E86', d.blush ?? .42);
    out.push(`<ellipse cx="38" cy="75.5" rx="8.5" ry="6.5" ${paint(bl)}/><ellipse cx="82" cy="75.5" rx="8.5" ry="6.5" ${paint(bl)}/>`);

    // Muzzle: its own soft volume that casts onto the face.
    out.push(`<path d="${MUZZLE}" ${paint(bb(d.muzzle, { hi: .05, lo: .1 }, { fy: .2 }))} filter="${fxDrop}"/>`);

    // Tongue under the smile.
    if (d.tongue && !o.sleep) out.push(`<path d="M55.4 85h9.2v4.6a4.6 4.6 0 0 1-9.2 0Z" ${paint(c.rad([[0, '#FFA3AC'], [.5, '#F7707F'], [1, '#D94A60']], { r: .7, fx: .35, fy: .1 }))}/><path d="M60 86.2v4" stroke="#C9405A" stroke-width="1" stroke-linecap="round" opacity=".6"/>`);
    // Smile.
    out.push(`<path d="M60 80.4v3.6M60 84c-2.5 2.7-6.2 2.7-8.4.6M60 84c2.5 2.7 6.2 2.7 8.4.6" stroke="${LINE}" stroke-width="2" fill="none" stroke-linecap="round"/>`);
    // Nose: soft wedge, wet specular top left, faint bounce along the bottom.
    out.push(`<path d="M52.2 72.6Q60 66.6 67.8 72.6Q67 79.8 60 80.8Q53 79.8 52.2 72.6Z" ${paint(c.rad([[0, '#6A534B'], [.35, '#2E211C'], [.8, '#140D0A'], [1, '#2A1E19']], { r: .6, fx: .38, fy: .2 }))}/>`
      + `<ellipse cx="56.8" cy="71.4" rx="2.8" ry="1.4" transform="rotate(-14 56.8 71.4)" fill="#fff" opacity=".85"/>` + (o.lite ? '' : `<path d="M56 78.2Q60 79.8 64 78.2" stroke="#fff" stroke-width=".9" fill="none" stroke-linecap="round" opacity=".22"/>`));

    // Maltese bow.
    if (d.topknot) {
      const kg = bb(d.topknot, { hi: .12, lo: .14 });
      out.push(`<g filter="${fxDrop}"><path d="M60 34C55 27 47 25 45.5 29.5C44.5 33 45 38 47 40C50 41 56 38 60 34Z" ${paint(kg)}/><path d="M60 34C65 27 73 25 74.5 29.5C75.5 33 75 38 73 40C70 41 64 38 60 34Z" ${paint(kg)}/><circle cx="60" cy="34" r="4.2" ${paint(kg)}/></g>`);
    }
    return out.join('');
  }

  function clayDog(key, { bg = null, size = null } = {}) {
    const c = ctx(), body = [];
    if (bg) body.push(`<circle cx="60" cy="60" r="58" ${paint(c.rad([[0, tone(bg, .03)], [.7, bg], [1, tone(bg, -.03)]], { r: .6, fx: .3, fy: .25 }))}/>`);
    // contact shadow under the chin
    body.push(`<ellipse cx="62" cy="99" rx="30" ry="6" ${paint(c.glow('#2A140A', bg ? .22 : .28))}/>`);
    body.push(head(c, key));
    const wh = size ? ` width="${size}" height="${size}"` : '';
    return `<svg viewBox="0 0 120 120" class="av clay"${wh} style="color-interpolation-filters:sRGB" aria-hidden="true" focusable="false"><defs>${c.defs.join('')}</defs>${body.join('')}</svg>`;
  }

  /* ---------- scenes ---------- */
  /* Palette colours are usually CSS variables, so every tint and shade below is a color-mix() and the scene
     recolours with whatever direction it sits in. Dogs keep their own fur. */
  const SCENE_DOG = { tub: 'max', nap: 'biscuit', tools: null, confirm: 'bella' };

  function scene(name, { palette = {}, dog } = {}) {
    const P = { sig: 'var(--sig)', soft: 'var(--sig-soft)', surface: 'var(--surface)', ink: 'var(--ink)', ...palette };
    const c = ctx(), out = [], key = dog || SCENE_DOG[name];
    const fxSig = c.clay(tone(P.sig, -.3), { drop: 3, s: 1.3 }), fxSigIn = () => c.clay(tone(P.sig, -.3), { s: 1.1 });
    const bbP = (col, k = {}, o = {}) => c.rad(ramp(col, k), { r: .56, fx: .32, fy: .22, ...o });
    const sigG = bbP(P.sig);
    const card = mix(P.surface, P.ink, 96);  // surface lifted a touch so it separates from dark backdrops
    const place = (x, y, s, rot = 0) => `translate(${x} ${y})${rot ? ` rotate(${rot})` : ''} scale(${s}) translate(-60 -64)`;
    const shadow = (x, y, rx, ry, a = .2) => `<ellipse cx="${x}" cy="${y}" rx="${rx}" ry="${ry}" ${paint(c.glow('#1A1014', a))}/>`;
    const orb = (x, y, r, col) => `<circle cx="${x}" cy="${y}" r="${r}" ${paint(bbP(col, { hi: .14, lo: .14 }, { fx: .3, fy: .25 }))}/>`;
    const paw = (x, y, col, rot = 0) => `<g transform="rotate(${rot} ${x} ${y})"><ellipse cx="${x}" cy="${y}" rx="8.5" ry="6.4" ${paint(col === B.fur ? furG() : c.rad(ramp(col, { hi: .06, lo: .1 }), { r: .58, fx: .34, fy: .2 }))} filter="${fxFur()}"/>`
      + `<path d="M${x - 2.6} ${y + 1.4}v3.4M${x + 2.6} ${y + 1.4}v3.4" stroke="${tone(col, -.22, -6)}" stroke-width="1.2" stroke-linecap="round" opacity=".7"/></g>`;
    // Backdrop: a soft blob in the palette's tint, lit like everything else.
    const back = (ks, rot) => `<path d="${blob(120, 92, 88, 72, ks, rot)}" ${paint(c.rad([[0, tone(P.soft, .06)], [.6, P.soft], [1, tone(P.soft, -.04)]], { r: .6, fx: .35, fy: .3 }))}/>`;
    const B = BREEDS[key] || BREEDS.max;
    const furG = () => c.once('fur', () => c.rad(ramp(B.fur, B), { r: .58, fx: .32, fy: .2 }));
    const fxFur = () => c.clay(tone(B.fur, -.34, -8, .04), { drop: 2.6 });

    if (name === 'tub') {
      const foamG = c.rad([[0, '#FFFFFF'], [.55, '#F7F9FC'], [1, '#D9E1EC']], { r: .56, fx: .35, fy: .2 });
      const fxFoam = c.clay(tone(P.sig, -.3), { drop: 2, s: .9, op: .28 });
      const bub = c.rad([[0, '#ffffff', .1], [.62, mix(P.sig, '#ffffff', 35), .12], [.9, P.sig, .38], [1, '#ffffff', .95]], { r: .5 });
      const bid = c.id();
      c.defs.push(`<g id="${bid}"><circle r="1" ${paint(bub)}/><ellipse cx="-.38" cy="-.42" rx=".3" ry=".2" transform="rotate(-35 -.38 -.42)" fill="#fff" opacity=".9"/><circle cx=".45" cy=".45" r=".09" fill="#fff" opacity=".7"/></g>`);
      const bubble = (x, y, r) => `<use href="#${bid}" transform="translate(${x} ${y}) scale(${r})"/>`;
      out.push(back([.02, -.04, .05, -.02, .04, -.05, .03, 0], .3), shadow(120, 163, 78, 8, .26));
      // feet tuck under the tub
      out.push(`<g filter="${fxSig}">${[78, 162].map(x => `<ellipse cx="${x}" cy="155" rx="8" ry="7.5" ${paint(sigG)}/>`).join('')}</g>`);
      // the dog sits in the water: shoulders under the foam, face clear of it, a foam hat on top
      out.push(`<path d="${bun(120, 97, 27, 12, 12)}" ${paint(furG())} filter="${fxFur()}"/>`);
      out.push(`<g transform="${place(120, 66, .72)}">${head(c, key, { lite: 1 })}</g>`);
      out.push(`<path d="${bumps(120, 106.5, 71, 14, 180, 360, 11)}Z" ${paint(foamG)} filter="${fxFoam}"/>`);
      out.push(`<path d="${tufts(125, 36.5, 12.5, 6, 7, 0, { round: true, start: .4 })}" ${paint(foamG)} filter="${fxFoam}"/>`);
      // tub body and rim
      out.push(`<path d="M50 108H190C190 134 179 150 152 152.5H88C61 150 50 134 50 108Z" ${paint(sigG)} filter="${fxSig}"/>`);
      out.push(`<rect x="40" y="98.5" width="160" height="14" rx="7" ${paint(bbP(P.sig, { hi: .2, lo: .06 }, { fy: .1 }))} filter="${fxSig}"/>`);
      // paws over the rim, foam spilling down the front
      out.push(paw(100, 102, B.fur, -8), paw(140, 102, B.fur, 8));
      out.push(`<g filter="${fxFoam}"><circle cx="64" cy="104" r="7" ${paint(foamG)}/><circle cx="73" cy="109" r="4.5" ${paint(foamG)}/><circle cx="172" cy="104" r="8" ${paint(foamG)}/><circle cx="184" cy="100" r="5" ${paint(foamG)}/></g>`);
      out.push(bubble(56, 62, 10), bubble(190, 58, 13), bubble(206, 88, 6.5), bubble(38, 88, 5.5), bubble(168, 26, 6), bubble(80, 30, 5));
    }

    if (name === 'nap') {
      out.push(back([0, .05, -.03, .04, -.05, .02, .04, -.03], .8), shadow(120, 160, 82, 8, .26));
      // floor cushion: sig body, lighter top face, stitched piping
      out.push(`<path d="${bun(120, 136, 82, 18, 21, .56, .72)}" ${paint(sigG)} filter="${fxSig}"/>`
        + `<ellipse cx="118" cy="131" rx="70" ry="11" ${paint(c.glow('#ffffff', .3))}/>`
        + `<path d="M44 140C70 152 170 152 196 140" fill="none" ${pen(tone(P.sig, .12))} stroke-width="1.6" stroke-dasharray="3 4" stroke-linecap="round" opacity=".8"/>`);
      // curled body with the tail wrapped round the front
      out.push(`<path d="${bun(138, 114, 44, 21, 15, .56, .74)}" ${paint(furG())} filter="${fxFur()}"/>`);
      out.push(`<path d="M177 113C186 125 179 134 162 134C152 134 144 132 138 130" fill="none" stroke="${tone(B.fur, -.03)}" stroke-width="9" stroke-linecap="round" filter="${fxFur()}"/>`);
      const pawC = B.blaze ? B.muzzle : B.fur;
      out.push(paw(91, 129, pawC, -4), paw(110, 131, pawC, 4));
      out.push(`<g transform="${place(101, 104, .66, -9)}">${head(c, key, { sleep: 1, lite: 1 })}</g>`);
      // Z z z drifting up, clay strokes
      const zz = (x, y, s, a) => `<path d="M${x} ${y}h${s}l${-s} ${s}h${s}" fill="none" ${pen(P.sig)} stroke-width="${r1(s * .3)}" stroke-linecap="round" stroke-linejoin="round" opacity="${a}"/>`;
      out.push(`<g filter="${c.clay(tone(P.sig, -.3), { drop: 1.4, s: .6 })}">${zz(136, 56, 13, 1)}${zz(158, 38, 10, .85)}${zz(175, 24, 7.5, .7)}</g>`);
      out.push(orb(44, 72, 5, P.sig), orb(202, 76, 3.5, P.sig));
    }

    if (name === 'tools') {
      out.push(back([.04, -.03, .05, -.04, .02, .05, -.02, .03], 1.4), shadow(120, 162, 62, 7, .3));
      const metal = c.lin([[0, '#F4F6F9'], [.45, '#FFFFFF'], [.55, '#C3CBD6'], [1, '#8E99A8']], 0, 0, 1, 0);
      const fxMetal = c.clay('#4A5568', { drop: 2, s: .7, op: .3 });
      const cardG = bbP(card, { hi: .03, lo: .08 });
      // paddle brush leaning left: surface frame, sig-tinted cushion, white bristle tips
      const pad = mix(P.sig, card, 42);
      const brist = c.rad([[0, '#ffffff'], [.6, mix(pad, '#ffffff', 45)], [1, mix(pad, P.ink, 72)]], { fx: .3, fy: .25 });
      let dots = '';
      for (let r = 0; r < 5; r++) for (let q = 0; q < (r % 2 ? 3 : 4); q++) dots += `<circle cx="${r1(-13.5 + q * 9 + (r % 2) * 4.5)}" cy="${r1(-49 + r * 9)}" r="2.6" ${paint(brist)}/>`;
      out.push(`<g transform="translate(100 88) rotate(-22)"><rect x="-8" y="-6" width="16" height="72" rx="8" ${paint(cardG)} filter="${fxSig}"/>`
        + `<rect x="-27" y="-66" width="54" height="64" rx="25" ${paint(cardG)} filter="${fxSig}"/>`
        + `<rect x="-21" y="-60" width="42" height="52" rx="20" ${paint(bbP(pad, { hi: .04, lo: .08 }, { fx: .62, fy: .72 }))} filter="${fxSigIn()}"/>${dots}</g>`);
      // comb standing in the middle, teeth to the right
      let teeth = '';
      for (let i = 0; i < 11; i++) teeth += `<rect x="1" y="${-40 + i * 7}" width="${i < 5 ? 17 : 13}" height="4.2" rx="2.1"/>`;
      out.push(`<g transform="translate(124 72) rotate(6)" filter="${fxSig}"><g ${paint(bbP(P.ink, { hi: .2, lo: .1 }))}>${teeth}<rect x="-8" y="-46" width="12" height="96" rx="6"/></g></g>`);
      // grooming shears: finger rings up top, blades down into the cup
      const ring = (x, y, r, w) => `<path d="M${x - r} ${y}a${r} ${r} 0 1 0 ${2 * r} 0a${r} ${r} 0 1 0 ${-2 * r} 0ZM${x - r + w} ${y}a${r - w} ${r - w} 0 1 1 ${2 * (r - w)} 0a${r - w} ${r - w} 0 1 1 ${-2 * (r - w)} 0Z" fill-rule="evenodd"/>`;
      const blade = rot => `<path d="M-3.8 -2L-1 52Q0 58 1 52L3.8 -2Z" transform="rotate(${rot})" fill="${metal}"/>`;
      out.push(`<g transform="translate(148 97) rotate(24) scale(1.1)"><g filter="${fxMetal}">${blade(-5)}${blade(5)}</g>`
        + `<g filter="${c.clay(tone(P.sig, -.3), { drop: 2, s: .55 })}" ${paint(sigG)}><path d="M-3 -2L-10 -25L-4 -27L3 -2ZM3 -2L10 -25L4 -27L-3 -2Z"/>${ring(-12.5, -36, 11.5, 6.4)}${ring(12.5, -36, 11.5, 6.4)}<path d="M-22.5 -29Q-31 -23 -28 -13" fill="none" stroke-width="4.4" stroke-linecap="round" ${pen(P.sig)}/></g>`
        + `<circle r="4.6" fill="${metal}" filter="${fxMetal}"/><circle cx="-1.2" cy="-1.2" r="1.4" fill="#fff"/></g>`);
      // the cup they stand in, a paw print on the front
      out.push(`<path d="M88 110H152L148 147Q147 160 134 160H106Q93 160 92 147Z" ${paint(sigG)} filter="${fxSig}"/>`
        + `<rect x="83" y="103" width="74" height="13" rx="6.5" ${paint(bbP(P.sig, { hi: .2, lo: .06 }, { fy: .1 }))} filter="${fxSig}"/>`
        + `<g ${paint(mix(card, 'transparent', 85))}><ellipse cx="111.5" cy="128" rx="2.6" ry="3.3"/><ellipse cx="120" cy="125" rx="2.6" ry="3.3"/><ellipse cx="128.5" cy="128" rx="2.6" ry="3.3"/><path d="M120 131.5c-4 0-7.5 5-7.5 7.6 0 2 1.6 3 3.4 3 1.6 0 2.6-.8 4.1-.8s2.5.8 4.1.8c1.8 0 3.4-1 3.4-3 0-2.6-3.5-7.6-7.5-7.6Z"/></g>`);
      out.push(orb(48, 72, 6, P.sig), orb(62, 118, 3.5, P.sig), orb(196, 132, 4.5, P.sig), orb(186, 148, 2.8, P.sig));
    }

    if (name === 'confirm') {
      out.push(back([.03, .05, -.04, .02, -.03, .05, -.04, .02], 2.1), shadow(122, 162, 86, 8, .24));
      // calendar card, tipped a little, sig header and binder rings
      const cardShape = 'M118 50Q118 40 128 40H192Q202 40 202 50V132Q202 142 192 142H128Q118 142 118 132Z';
      let grid = '';
      for (let r = 0; r < 4; r++) for (let q = 0; q < 5; q++) if (!(r === 1 && q === 3)) grid += `<rect x="${128 + q * 14.5}" y="${76 + r * 14.5}" width="8" height="8" rx="3"/>`;
      out.push(`<g transform="rotate(6 160 92)"><g filter="${fxSig}"><path d="${cardShape}" ${paint(bbP(card, { hi: .03, lo: .06 }))}/>`
        + `<path d="M118 50Q118 40 128 40H192Q202 40 202 50V62H118Z" ${paint(sigG)}/></g>`
        + `<g ${paint(mix(P.ink, 'transparent', 16))}>${grid}</g>`
        + `<circle cx="${128 + 3 * 14.5 + 4}" cy="${76 + 14.5 + 4}" r="7.5" ${paint(sigG)} filter="${fxSig}"/>`
        + `<g filter="${fxSig}">${[138, 182].map(x => `<rect x="${x}" y="31" width="7" height="17" rx="3.5" ${paint(bbP(mix(P.ink, P.surface, 70), { hi: .1, lo: .08 }))}/>`).join('')}</g></g>`);
      // the tick badge
      out.push(`<circle cx="198" cy="134" r="21" ${paint(bbP(P.sig, { hi: .14, lo: .14 }, { fx: .3, fy: .22 }))} filter="${fxSig}"/>`
        + `<path d="M188.5 134.5l6.5 6.5 12.5-13.5" fill="none" ${pen(P.surface)} stroke-width="5.4" stroke-linecap="round" stroke-linejoin="round"/>`
        + `<ellipse cx="190" cy="122" rx="6" ry="3.4" transform="rotate(-30 190 122)" fill="#fff" opacity=".45"/>`);
      // the dog sitting beside it: chest, short front legs, paws, then the head
      out.push(`<path d="${bun(68, 141, 27, 21, 17, .56, .72)}" ${paint(furG())} filter="${fxFur()}"/>`);
      out.push(`<g filter="${fxFur()}" ${paint(furG())}><rect x="53" y="136" width="14" height="22" rx="7"/><rect x="71" y="136" width="14" height="22" rx="7"/></g>`);
      out.push(paw(59.5, 157, B.fur), paw(77.5, 157, B.fur));
      out.push(`<g transform="${place(68, 102, .64, -4)}">${head(c, key, { lite: 1 })}</g>`);
      out.push(orb(222, 104, 4, P.sig), orb(214, 86, 2.6, P.sig), orb(34, 70, 5, P.sig));
    }

    return `<svg viewBox="0 0 240 180" class="spot clay" style="color-interpolation-filters:sRGB" aria-hidden="true" focusable="false"><defs>${c.defs.join('')}</defs>${out.join('')}</svg>`;
  }

  /* Exported for other subject packs (see illustrations-plants.js): ctx() for unique ids, gradients and the clay
     filter; tone() and mix() for colour; ramp() for a clay gradient; bun(), blob(), tufts() and bumps() for soft forms. */
  return { clayDog, scene, head, ctx, tone, mix, ramp, bun, blob, tufts, bumps, BREEDS };
})();

function clayDog(key, opts) { return CLAY.clayDog(key, opts); }
function scene(name, opts) { return CLAY.scene(name, opts); }
