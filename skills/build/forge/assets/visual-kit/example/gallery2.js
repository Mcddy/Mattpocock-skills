/* Second direction set: four bolder compositions on the same real data.
   Loaded after gallery.js and reuses its globals: I (icons), DOGS, dog(), DAY, status().
   Each direction owns a class prefix: ce- Coral Editorial, sk- Sky Illustrated, mf- Mono Flood, cp- Candy Pastel. */

const I2 = {
  dots: '<svg viewBox="0 0 24 24" fill="currentColor"><circle cx="5.5" cy="12" r="1.8"/><circle cx="12" cy="12" r="1.8"/><circle cx="18.5" cy="12" r="1.8"/></svg>',
  chev: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m9.5 5.5 6.5 6.5-6.5 6.5"/></svg>',
  grid: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linejoin="round"><rect x="4" y="4" width="7" height="7" rx="2"/><rect x="13" y="4" width="7" height="7" rx="2"/><rect x="4" y="13" width="7" height="7" rx="2"/><rect x="13" y="13" width="7" height="7" rx="2"/></svg>',
};

/* ---------- Shared data (all from the brief's day; nothing invented) ---------- */
const NOTE = {
  max: 'Nervous of the dryer; use the quiet one',
  mochi: 'Muzzle: bites at nails',
  reggie: 'Senior, lift onto table',
  biscuit: 'No oatmeal shampoo',
};
const HANDLING = 'Matts behind the ears. Senior: lift him onto the table, do not let him jump.';
const DAY_FULL = [...DAY, { t: '16:30', end: '17:00', free: '30m' }];
const toMin = (hm) => { const [h, m] = hm.split(':').map(Number); return h * 60 + m; };
const SHORT = { reggie: 'Sir Reginald' };
const STATS = [['5', 'dogs booked'], ['6h 15', 'of grooming'], ['$400', 'expected']];

/* Head-and-shoulders figure built from the same dog() head, so it reads as a cut-out pet photo on a coloured tile.
   Returns a nested <svg> placed at x,y with size s (in the parent's units). */
function figure(key, x = 0, y = 0, s = 300) {
  const d = DOGS[key];
  const head = dog(key).replace(/^<svg[^>]*>/, '<svg x="45" y="18" width="210" height="210" viewBox="0 0 120 120">');
  const body = d.sheep ? d.sheep : d.fur;
  const parts = [`<path d="M20 300C28 234 88 202 150 202S272 234 280 300Z" fill="${body}"/>`];
  if (d.curly) [[58, 268, 17], [86, 244, 16], [116, 230, 15], [184, 230, 15], [214, 244, 16], [242, 268, 17], [150, 226, 14]]
    .forEach(([cx, cy, r]) => parts.push(`<circle cx="${cx}" cy="${cy}" r="${r}" fill="${d.dark}"/>`));
  const chest = d.sheep ? d.fur : (d.blaze || d.ruff || (d.curly ? null : d.muzzle));
  if (chest) parts.push(`<path d="M112 300C114 258 128 226 150 222C172 226 186 258 188 300Z" fill="${chest}"/>`);
  parts.push(`<ellipse cx="150" cy="198" rx="56" ry="18" fill="#000" opacity=".08"/>`);
  return `<svg x="${x}" y="${y}" width="${s}" height="${s}" viewBox="0 0 300 300">${parts.join('')}${head}</svg>`;
}

/* Photo stand-in: a tile-coloured frame that a real <img class="k2-photo"> (object-fit: cover) can replace one for one. */
function photo(key, { bg = null, label = '', align = 'xMidYMin', fit = 'slice', vb = '30 40 240 240' } = {}) {
  return `<svg class="k2-photo" viewBox="${vb}" preserveAspectRatio="${align} ${fit}" role="img" aria-label="${label}">${bg ? `<rect x="-600" y="-600" width="1500" height="1500" fill="${bg}"/>` : ''}${figure(key)}</svg>`;
}

/* ============================================================
   1. CORAL EDITORIAL: white, coral, black. Media-led tiles, big black display type.
   ============================================================ */
const CE_TILE = { rusty: 'var(--t-butter)', max: 'var(--t-peach)', mochi: 'var(--t-sky)', reggie: 'var(--t-lilac)', biscuit: 'var(--t-mint)', bella: 'var(--t-rose)' };

function ceNav() {
  return `<nav class="ce-nav" aria-label="Main"><a class="is-on" href="#">${I.cal}<span>Today</span></a><a href="#">${I.users}<span>Clients</span></a>
    <button class="ce-nav-cta" aria-label="New booking">${I.plus}<span>Book</span></button></nav>`;
}

function ceToday(dir) {
  const next = DAY.filter(s => toMin(s.t) >= toMin('11:15'));
  const tiles = next.map(s => s.free
    ? `<div class="ce-card"><button class="ce-media ce-free" aria-label="Book ${s.t}"><span class="ce-time">${s.t}</span><span class="ce-free-plus">${I.plus}</span><span class="ce-free-len">${s.free} free</span></button>
        <h4>Free slot</h4><p>${s.t} to ${s.end}</p></div>`
    : `<div class="ce-card"><div class="ce-media" style="background:${CE_TILE[s.dog]}">${photo(s.dog, { label: s.name })}<span class="ce-time">${s.t}</span>${NOTE[s.dog] && s.dog === 'mochi' ? `<span class="ce-flag">${I.alert}Muzzle</span>` : ''}</div>
        <h4>${SHORT[s.dog] || s.name}</h4><p>${s.svc}</p></div>`).join('');
  return `<div class="screen" data-dir="${dir}">${status()}
  <header class="ce-mast"><div class="ce-mast-row ce-dateline"><span class="ce-kicker">Tuesday 2 March</span><span class="ce-kicker ce-kicker-2">5 dogs · 6h 15 · $400</span></div>
    <div class="ce-mast-row ce-mast-low"><h1 class="display ce-h1">Today<i></i></h1><button class="ce-icon" aria-label="Pick a date">${I.cal}</button></div></header>
  <section class="ce-hero" aria-label="On the table now">
    <div class="ce-media ce-hero-media" style="background:${CE_TILE.max}">${photo('max', { label: 'Max', vb: '-62 38 282 227' })}
      <span class="ce-live"><i></i>On the table</span>
      <div class="display ce-hero-name">Max</div>
      <div class="ce-hero-bar"><div class="ce-hero-meta"><b>Full groom</b><span>until 11:15</span></div>
        <div class="ce-meter" role="img" aria-label="15 of 120 minutes"><i style="width:12.5%"></i></div>
        <div class="ce-hero-foot"><span>15 min in</span><span>1 h 45 min left</span></div></div>
    </div>
    <p class="ce-caption">${I.alert}<span>${NOTE.max}</span></p>
  </section>
  <div class="ce-sec"><h2>Up next</h2><a href="#">1 cancelled</a></div>
  <div class="ce-rail">${tiles}</div>
  <div class="ce-fade"></div>${ceNav()}
  </div>`;
}

function ceBook(dir) {
  const svc = (name, mins, p, on) => `<button class="ce-opt ${on ? 'is-on' : ''}" aria-pressed="${on}"><span class="ce-radio">${on ? I.check : ''}</span><span class="ce-opt-name">${name}<small>${mins}</small></span><span class="ce-opt-p">$${p}</span></button>`;
  return `<div class="screen" data-dir="${dir}">${status()}
  <div class="ce-top"><button class="ce-icon" aria-label="Back">${I.back}</button><span class="ce-kicker">New booking</span><span style="width:44px"></span></div>
  <section class="ce-media ce-dog" style="background:${CE_TILE.bella}">${photo('bella', { label: 'Bella', vb: '-84 28 305 214' })}
    <div class="ce-dog-text"><span class="ce-kicker">Dog</span><h1 class="display">Bella</h1><p>Toy poodle<br>Jane Smith</p></div>
    <button class="ce-chip">Change</button></section>
  <div class="ce-sec ce-sec-tight"><h2>Service</h2></div>
  <div class="ce-opts">${svc('Bath & brush', '60 min', 70, true)}${svc('Full groom', '120 min', 120)}${svc('Nail trim', '15 min', 20)}</div>
  <div class="ce-sec ce-sec-tight"><h2>Start</h2><a href="#">Tue 2 Mar</a></div>
  <div class="ce-times"><button class="is-on" aria-pressed="true">11:30</button><button>11:45</button><button>12:00</button></div>
  <p class="ce-later">A 60 min bath fits nowhere else today. Wednesday 3 March is open from 08:00.</p>
  <div class="ce-cta"><button class="ce-cta-btn"><span><b>Book Bella for 11:30</b><small>11:30 to 12:30</small></span><span class="ce-cta-p">$70</span></button></div>
  </div>`;
}

function ceProfile(dir) {
  return `<div class="screen" data-dir="${dir}">
  <section class="ce-media ce-cover" style="background:${CE_TILE.reggie}">${photo('reggie', { label: 'Sir Reginald Fluffington III', vb: '0 -40 300 340' })}
    <div class="ce-cover-top">${status()}<div class="ce-top"><button class="ce-icon ce-icon-solid" aria-label="Back">${I.back}</button><button class="ce-icon ce-icon-solid" aria-label="Call owner">${I.phone}</button></div></div>
    <span class="ce-live"><i></i>Today 13:00</span></section>
  <h1 class="display ce-name">Sir Reginald Fluffington III</h1>
  <p class="ce-breed">Old English sheepdog</p>
  <div class="ce-rows">
    <div class="ce-row"><span class="ce-ini">MO</span><div><small>Owner</small><b>Margaret O'Sullivan-Whitehouse</b><span>+61 7 4162 3301</span></div></div>
    <div class="ce-row ce-handling"><div><small>Handling</small><p>${HANDLING}</p></div></div>
    <div class="ce-row"><div><small>Booked</small><b>Today, 13:00 to 15:00</b><span>Full groom · $120</span></div><button class="ce-chip ce-chip-line">Move</button></div>
  </div>
  <p class="ce-later ce-first">First visit. Past grooms will list here.</p>
  </div>`;
}

function ceDesk(dir) {
  const span = (a, b) => `left:${(toMin(a) - 480) / 540 * 100}%;width:${(toMin(b) - toMin(a)) / 540 * 100}%`;
  const strip = DAY_FULL.map(s => s.free
    ? `<button class="ce-blk ce-blk-free" style="${span(s.t, s.end)}" aria-label="Book ${s.t}">${s.free === '1h 30m' ? `<b>${s.free} free</b><span>Book ${s.t}</span>` : `<b>${I.plus}</b>`}</button>`
    : `<div class="ce-blk ${s.state ? 'is-' + s.state : ''}" style="${span(s.t, s.end)};--tile:${CE_TILE[s.dog]}">${toMin(s.end) - toMin(s.t) >= 60 ? `<b>${SHORT[s.dog] || s.name}</b><span>${s.t}</span>` : ''}</div>`).join('');
  const hours = [8, 9, 10, 11, 12, 13, 14, 15, 16, 17].map(h => `<span style="left:${(h - 8) / 9 * 100}%">${String(h).padStart(2, '0')}</span>`).join('');
  const card = (key, t, name, svc, flag) => `<div class="ce-card"><div class="ce-media" style="background:${CE_TILE[key]}">${photo(key, { label: name })}<span class="ce-time">${t}</span>${flag ? `<span class="ce-flag">${I.alert}${flag}</span>` : ''}</div><h4>${name}</h4><p>${svc}</p></div>`;
  return `<div class="browser"><div class="browser-bar"><i></i><i></i><i></i><span>127.0.0.1:8851 · Grooming book</span></div>
  <div class="screen ce-desk" data-dir="${dir}">
    <header class="ce-dtop"><nav aria-label="Main"><a class="is-on" href="#">Today</a><a href="#">Clients</a></nav>
      <span class="ce-kicker">Open 08:00 to 17:00 · Brisbane</span><button class="ce-cta-btn ce-cta-sm">${I.plus}<b>New booking</b></button></header>
    <div class="ce-dmast"><div><span class="ce-kicker">Tuesday 2 March</span><h1 class="display ce-h1 ce-h1-xl">Today<i></i></h1></div>
      <dl class="ce-dstats">${STATS.map(([v, l]) => `<div><dt>${l}</dt><dd>${v}</dd></div>`).join('')}<div><dt>cancelled</dt><dd>1</dd></div></dl></div>
    <div class="ce-dgrid">
      <section class="ce-media ce-hero-media ce-dhero" style="background:${CE_TILE.max}">${photo('max', { label: 'Max', vb: '-78 -58 336 343' })}
        <span class="ce-live"><i></i>On the table</span><div class="display ce-hero-name">Max</div>
        <div class="ce-hero-bar"><div class="ce-hero-meta"><b>Full groom</b><span>09:15 to 11:15</span></div>
          <div class="ce-meter"><i style="width:12.5%"></i></div><div class="ce-hero-foot"><span>15 min in</span><span>1 h 45 min left</span></div>
          <p class="ce-caption ce-caption-in">${I.alert}<span>${NOTE.max}</span></p></div></section>
      <div class="ce-dright">
        <div class="ce-sec ce-sec-desk"><h2>Up next</h2><a href="#">See the week</a></div>
        <div class="ce-dcards">${card('mochi', '11:15', 'Mochi', 'Nail trim · 15 min', 'Muzzle')}${card('reggie', '13:00', 'Sir Reginald', 'Full groom · 2 h', 'Senior')}${card('biscuit', '15:30', 'Biscuit', 'Bath & brush · 1 h', 'No oatmeal')}</div>
        <div class="ce-strip"><div class="ce-sec ce-sec-desk"><h2>The day, to scale</h2><span class="ce-kicker">Free 11:30, 15:00, 16:30</span></div>
          <div class="ce-hours">${hours}</div><div class="ce-track">${strip}<i class="ce-now" style="left:${90 / 540 * 100}%"><b>09:30</b></i></div></div>
      </div>
    </div>
  </div></div>`;
}

/* ============================================================
   2. SKY ILLUSTRATED: sky blue, sunshine yellow, navy. An SVG scene header (sky, clouds, the sun on the day's arc,
   the current dog) with the hero card overlapping it. The sun sits where 09:30 falls between opening and closing.
   ============================================================ */
let skN = 0;
const SK = { navy: '#10224B', sun: '#FFD23F', sunSoft: '#FFE68A', hill: '#FFD95A', hill2: '#FFE9A3', cloud: '#FFFFFF' };
const skCloud = (x, y, s = 1, o = 1) => `<g transform="translate(${x} ${y}) scale(${s})" fill="${SK.cloud}" opacity="${o}"><rect x="0" y="20" width="96" height="24" rx="12"/><circle cx="30" cy="22" r="16"/><circle cx="54" cy="16" r="20"/><circle cx="76" cy="26" r="12"/></g>`;
const skSun = (x, y, r) => `<circle cx="${x}" cy="${y}" r="${r * 2}" fill="${SK.sunSoft}" opacity=".28"/><circle cx="${x}" cy="${y}" r="${r * 1.45}" fill="${SK.sunSoft}" opacity=".55"/><circle cx="${x}" cy="${y}" r="${r}" fill="${SK.sun}"/>`;
const skSky = (w, h, id) => `<defs><linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#5DB8F4"/><stop offset="1" stop-color="#BDE5FF"/></linearGradient></defs><rect width="${w}" height="${h}" fill="url(#${id})"/>`;
/* Day arc from opening (08:00) to closing (17:00); returns the path and a point-at-time function. */
function skArc(x0, x1, base, peak) {
  const cy = 2 * peak - base, at = (hm) => { const t = (toMin(hm) - 480) / 540; return [x0 + (x1 - x0) * t, (1 - t) ** 2 * base + 2 * t * (1 - t) * cy + t * t * base]; };
  return { d: `M${x0} ${base}Q${(x0 + x1) / 2} ${cy} ${x1} ${base}`, at };
}
function skScene({ w, h, sky = true, arc = null, sunAt = '09:30', sunR = 22, sun = null, clouds = [], hills = null, dogKey = null, dogBox = null, tub = null, extra = '' }) {
  const id = 'skg' + (++skN), p = [skSky(w, h, id)];
  clouds.forEach(c => p.push(skCloud(...c)));
  if (arc) {
    p.push(`<path d="${arc.path.d}" fill="none" stroke="#fff" stroke-width="2.5" stroke-dasharray="2 9" stroke-linecap="round" opacity=".9"/>`);
    (arc.labels || []).forEach(([hm, txt, dy = 22, anchor = 'middle']) => { const [lx, ly] = arc.path.at(hm); p.push(`<text x="${lx}" y="${ly + dy}" text-anchor="${anchor}" class="sk-arc-t">${txt}</text>`); });
    const [sx, sy] = arc.path.at(sunAt); p.push(skSun(sx, sy, sunR));
    (arc.marks || []).forEach(m => p.push(m(arc.path)));
  } else if (sun) p.push(skSun(...sun));
  if (hills) p.push(`<path d="${hills[0]}" fill="${SK.hill2}"/>`);
  if (dogKey) p.push(figure(dogKey, ...dogBox));
  if (hills) p.push(`<path d="${hills[1]}" fill="${SK.hill}"/>`);
  if (tub) p.push(tub);
  p.push(extra);
  return `<svg class="sk-scene" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}" role="img" aria-label="${dogKey ? 'Illustration of ' + (dogKey === 'reggie' ? 'Sir Reginald' : dogKey[0].toUpperCase() + dogKey.slice(1)) : ''}" preserveAspectRatio="xMidYMin slice">${p.join('')}</svg>`;
}
function skTub(cx, top, w) {
  const l = cx - w / 2, r = cx + w / 2, b = top + 66;
  const bub = [[l + 14, top - 6, 13], [l + 40, top - 14, 9], [l + 30, top - 34, 6], [r - 20, top - 8, 14], [r - 46, top - 16, 9], [r - 30, top - 40, 7], [cx + 64, top - 58, 5], [cx - 70, top - 62, 4]];
  return `<g><rect x="${l + 20}" y="${b - 4}" width="12" height="18" rx="6" fill="${SK.navy}"/><rect x="${r - 32}" y="${b - 4}" width="12" height="18" rx="6" fill="${SK.navy}"/>
    <path d="M${l} ${top}H${r}V${top + 22}C${r} ${b} ${r - 26} ${b + 6} ${cx} ${b + 6}S${l} ${b} ${l} ${top + 22}Z" fill="#FFFFFF"/>
    <path d="M${l + 8} ${top + 30}C${l + 16} ${b - 4} ${cx - 40} ${b} ${cx} ${b}" stroke="#D6ECFC" stroke-width="7" fill="none" stroke-linecap="round"/>
    <rect x="${l - 8}" y="${top - 8}" width="${w + 16}" height="16" rx="8" fill="#EAF6FF"/>
    ${bub.map(([x, y, rr]) => `<circle cx="${x}" cy="${y}" r="${rr}" fill="#fff" stroke="#A8D8F8" stroke-width="2"/>`).join('')}</g>`;
}

function skNav() {
  return `<nav class="sk-nav" aria-label="Main"><a class="is-on" href="#"><span class="sk-nav-ic">${I.cal}</span>Today</a>
    <button class="sk-fab" aria-label="New booking">${I.plus}</button><a href="#"><span class="sk-nav-ic">${I.users}</span>Clients</a></nav>`;
}
const skRing = (pct, big, small, size = 84) => {
  const r = size / 2 - 7, c = 2 * Math.PI * r;
  return `<div class="sk-ring" style="width:${size}px;height:${size}px"><svg viewBox="0 0 ${size} ${size}" aria-hidden="true"><circle cx="${size / 2}" cy="${size / 2}" r="${r}" fill="none" stroke="#E3F1FD" stroke-width="9"/>
    <circle cx="${size / 2}" cy="${size / 2}" r="${r}" fill="none" stroke="${SK.navy}" stroke-width="9" stroke-linecap="round" stroke-dasharray="${c * pct} ${c}" transform="rotate(-90 ${size / 2} ${size / 2})"/></svg><b>${big}</b><small>${small}</small></div>`;
};

function skToday(dir) {
  const arc = skArc(18, 350, 236, 136);
  const scene = skScene({ w: 368, h: 340, arc: { path: arc, labels: [['08:00', '08:00', -12, 'start'], ['17:00', '17:00', -12, 'end']] }, sunR: 20,
    clouds: [[146, 150, .5, .95], [262, 112, .72, 1], [6, 150, .48, .85]],
    hills: ['M0 272C70 252 140 256 200 264S320 250 368 242V340H0Z', 'M0 304C50 294 110 272 180 263C230 256 300 254 368 262V340H0Z'],
    dogKey: 'max', dogBox: [166, 144, 176] });
  const rows = DAY.filter(s => toMin(s.t) >= toMin('11:15') && toMin(s.t) < toMin('15:00')).map(s => s.free
    ? `<li class="sk-li"><span class="sk-t">${s.t}</span><span class="sk-node sk-node-free"></span><div class="sk-item sk-free"><div><h4>${s.free} free</h4><p>until ${s.end}</p></div><button class="sk-btn-sm">Book</button></div></li>`
    : `<li class="sk-li"><span class="sk-t">${s.t}</span><span class="sk-node"></span><div class="sk-item">${dog(s.dog, { bg: '#E3F1FD' })}<div style="min-width:0"><h4>${SHORT[s.dog] || s.name}</h4><p>${s.svc} · to ${s.end}</p></div>${s.dog === 'mochi' ? `<span class="sk-tag">${I.alert}Muzzle</span>` : `<span class="sk-price">$${s.price}</span>`}</div></li>`).join('');
  return `<div class="screen" data-dir="${dir}">
  <div class="sk-head sk-head-lg">${scene}<div class="sk-over">${status()}<div class="sk-title"><div><div class="sk-eyebrow">Tuesday 2 March</div><h1 class="display sk-h1">Today</h1></div>
    <button class="sk-icon" aria-label="Pick a date">${I.cal}</button></div></div></div>
  <section class="sk-hero" aria-label="On the table now">
    <div class="sk-hero-top"><div><div class="sk-eyebrow">On the table now</div><div class="display sk-hero-name">Max</div><div class="sk-hero-meta">Full groom · until 11:15</div></div>
      ${skRing(.125, '1:45', 'left')}</div>
    <div class="sk-note">${I.alert}<span>${NOTE.max}</span></div>
  </section>
  <div class="sk-sec"><h2>Coming up</h2><a href="#">1 cancelled</a></div>
  <ol class="sk-list">${rows}</ol>
  <div class="sk-fade"></div>${skNav()}
  </div>`;
}

function skBook(dir) {
  const scene = skScene({ w: 368, h: 282, sun: [306, 122, 26], clouds: [[22, 118, .7, .95], [222, 172, .5, .9]],
    dogKey: 'bella', dogBox: [100, 70, 168], tub: skTub(184, 196, 196) });
  const svc = (name, mins, p, icon, on) => `<button class="sk-opt ${on ? 'is-on' : ''}" aria-pressed="${on}"><span class="sk-opt-ic">${icon}</span><span class="sk-opt-name"><b>${name}</b><small>${mins}</small></span><span class="sk-opt-p">$${p}</span>${on ? `<span class="sk-opt-check">${I.check}</span>` : ''}</button>`;
  return `<div class="screen" data-dir="${dir}">
  <div class="sk-head sk-head-sm">${scene}<div class="sk-over">${status()}<div class="sk-bar"><button class="sk-icon" aria-label="Back">${I.back}</button><span class="sk-eyebrow">New booking</span><span style="width:44px"></span></div></div></div>
  <section class="sk-hero sk-dogcard"><div><div class="sk-eyebrow">Dog</div><h1 class="display">Bella</h1><p>Toy poodle · Jane Smith</p></div><button class="sk-chip">Change</button></section>
  <div class="sk-sec"><h2>Service</h2></div>
  <div class="sk-opts">${svc('Bath & brush', '60 min', 70, I.drop, true)}${svc('Full groom', '120 min', 120, I.scissors)}${svc('Nail trim', '15 min', 20, I.paw)}</div>
  <div class="sk-sec"><h2>Free starts</h2><a href="#">Tue 2 Mar</a></div>
  <div class="sk-times"><button class="is-on" aria-pressed="true">11:30</button><button>11:45</button><button>12:00</button></div>
  <p class="sk-later">A 60 min bath fits nowhere else today. Wednesday 3 March is open from 08:00.</p>
  <div class="sk-cta"><button class="sk-cta-btn sk-cta-2"><span><b>Book Bella for 11:30</b><small>Bath & brush · 11:30 to 12:30</small></span><span class="sk-cta-p">$70</span></button></div>
  </div>`;
}

function skProfile(dir) {
  const scene = skScene({ w: 368, h: 384, sun: [304, 176, 32], clouds: [[20, 146, .72, .95], [250, 250, .48, .85]],
    hills: ['M0 310C80 288 160 292 230 302S330 286 368 280V384H0Z', 'M0 338C80 322 160 320 240 328S340 336 368 332V384H0Z'],
    dogKey: 'reggie', dogBox: [54, 112, 246] });
  return `<div class="screen" data-dir="${dir}">
  <div class="sk-head sk-head-xl">${scene}<div class="sk-over">${status()}<div class="sk-bar"><button class="sk-icon" aria-label="Back">${I.back}</button><span class="sk-eyebrow">Dog</span><button class="sk-icon" aria-label="Call owner">${I.phone}</button></div></div></div>
  <section class="sk-hero sk-namecard"><h1 class="display">Sir Reginald Fluffington III</h1><span class="sk-pill">Old English sheepdog</span>
    <div class="sk-owner"><span class="sk-ini">MO</span><div style="min-width:0"><div class="sk-eyebrow">Owner</div><b>Margaret O'Sullivan-Whitehouse</b><span>+61 7 4162 3301</span></div></div></section>
  <div class="sk-handle"><div class="sk-eyebrow">${I.alert}Handling</div><p>${HANDLING}</p></div>
  <div class="sk-booked"><span class="sk-opt-ic">${I.scissors}</span><div><b>Today, 13:00 to 15:00</b><span>Full groom · $120</span></div><button class="sk-chip">Move</button></div>
  <p class="sk-later" style="margin-top:12px">First visit. Past grooms will list here.</p>
  </div>`;
}

function skDesk(dir) {
  const arc = skArc(430, 1000, 230, 92);
  const mark = (key, hm, done) => (path) => { const [x, y] = path.at(hm); return `<g opacity="${done ? .55 : 1}"><circle cx="${x}" cy="${y}" r="21" fill="#fff"/>${dog(key).replace(/^<svg[^>]*>/, `<svg x="${x - 19}" y="${y - 19}" width="38" height="38" viewBox="0 0 120 120">`)}<text x="${x}" y="${y - 30}" text-anchor="middle" class="sk-arc-t">${hm}</text></g>`; };
  const scene = skScene({ w: 1280, h: 340, arc: { path: arc, labels: [['17:00', 'Close 17:00', -14, 'middle']], marks: [mark('rusty', '08:00', true), mark('mochi', '11:15'), mark('reggie', '13:00'), mark('biscuit', '15:30')] }, sunR: 24,
    clouds: [[300, 52, .8, .9], [700, 40, .6, .85], [1100, 70, .7, .95], [560, 150, .5, .8]],
    hills: ['M0 280C200 250 420 262 640 274S1040 236 1280 214V340H0Z', 'M0 298C240 280 520 280 760 292S1100 228 1280 214V340H0Z'],
    dogKey: 'max', dogBox: [1046, 98, 200] });
  const list = DAY_FULL.map(s => s.free
    ? `<div class="sk-drow sk-drow-free"><span class="sk-t">${s.t}</span><div class="sk-item sk-free"><div><h4>${s.free} free</h4><p>${s.t} to ${s.end}</p></div><button class="sk-btn-sm">Book ${s.t}</button></div></div>`
    : `<div class="sk-drow ${s.state ? 'is-' + s.state : ''}"><span class="sk-t">${s.t}</span><div class="sk-item">${dog(s.dog, { bg: '#E3F1FD' })}<div style="min-width:0"><h4>${s.name}</h4><p>${s.svc} · ${s.t} to ${s.end}${NOTE[s.dog] && s.dog !== 'max' ? ' · ' + NOTE[s.dog] : ''}</p></div>${s.state === 'done' ? `<span class="sk-tag sk-tag-ok">${I.check}Done</span>` : s.state === 'now' ? `<span class="sk-tag sk-tag-now">On the table</span>` : `<span class="sk-price">$${s.price}</span>`}</div></div>`).join('');
  return `<div class="browser"><div class="browser-bar"><i></i><i></i><i></i><span>127.0.0.1:8851 · Grooming book</span></div>
  <div class="screen sk-desk" data-dir="${dir}">
    <div class="sk-dscene">${scene}</div>
    <header class="sk-dtop"><nav aria-label="Main"><a class="is-on" href="#">${I.cal}Today</a><a href="#">${I.users}Clients</a></nav><button class="sk-cta-btn sk-cta-sm">${I.plus}New booking</button></header>
    <div class="sk-dtitle"><div class="sk-eyebrow">Tuesday 2 March</div><h1 class="display">Today</h1><p>5 dogs · 6h 15 of grooming · $400 expected</p></div>
    <section class="sk-hero sk-dhero"><div class="sk-hero-top"><div><div class="sk-eyebrow">On the table now</div><div class="display sk-hero-name">Max</div><div class="sk-hero-meta">Full groom · 09:15 to 11:15</div></div>${skRing(.125, '1:45', 'left', 96)}</div>
      <div class="sk-note">${I.alert}<span>${NOTE.max}</span></div>
      <div class="sk-dnext">${dog('mochi', { bg: '#E3F1FD' })}<div><div class="sk-eyebrow">Next · 11:15</div><b>Mochi</b><span>Nail trim · 15 min</span></div><span class="sk-tag">${I.alert}Muzzle: bites at nails</span></div></section>
    <section class="sk-dweek"><div class="sk-sec sk-sec-desk"><h2>This week</h2><a href="#">March</a></div><div class="sk-week">
      <div class="is-closed"><small>Mon</small><b>1</b><small>Closed</small></div><div class="is-on"><small>Tue</small><b>2</b><small>5 dogs</small></div>
      <div><small>Wed</small><b>3</b><small>1 dog</small></div><div><small>Thu</small><b>4</b><small>1 dog</small></div><div><small>Fri</small><b>5</b><small>Free</small></div><div><small>Sat</small><b>6</b><small>Free</small></div></div></section>
    <section class="sk-dlist"><div class="sk-sec sk-sec-desk"><h2>The day</h2><a href="#">1 cancelled</a></div>${list}</section>
  </div></div>`;
}

/* ============================================================
   3. MONO FLOOD: off-white, black, one cobalt flood block per screen. Oversized Anton, numbered index rows on hairlines.
   ============================================================ */
const MF_POR = '#FFFFFF';
const mfNo = (n) => String(n).padStart(2, '0');
function mfNav() {
  return `<nav class="mf-nav" aria-label="Main"><a class="is-on" href="#">${I.cal}<span>Today</span></a><a href="#">${I.users}<span>Clients</span></a><button class="mf-nav-new">${I.plus}<span>New booking</span></button></nav>`;
}
const mfSeg = (n, on) => `<div class="mf-seg" role="img" aria-label="${on * 15} of ${n * 15} minutes">${Array.from({ length: n }, (_, i) => `<i class="${i < on ? 'on' : ''}"></i>`).join('')}</div>`;
function mfRows(items, { notes = false } = {}) {
  let n = 0;
  return items.map(s => {
    if (s.free) return `<li class="mf-ir is-free"><span class="mf-no">··</span><span class="mf-tm">${s.t}</span><div class="mf-nm"><b>Free, ${s.free}</b><small>${s.t} to ${s.end}</small></div><button class="mf-btn">Book</button></li>`;
    n++;
    const tag = s.dog === 'mochi' ? `<span class="mf-inv">Muzzle</span>` : s.state === 'now' ? `<span class="mf-inv mf-inv-flood">Now</span>` : '';
    return `<li class="mf-ir ${s.state ? 'is-' + s.state : ''}"><span class="mf-no">${mfNo(n)}</span><span class="mf-tm">${s.t}</span><div class="mf-nm"><b>${s.name}${tag}</b><small>${s.svc}${s.state === 'done' ? ' · done' : ` · to ${s.end}`}${notes && NOTE[s.dog] && s.dog !== 'mochi' && s.dog !== 'max' ? ' · ' + NOTE[s.dog] : ''}</small></div><span class="mf-pr">$${s.price}</span></li>`;
  }).join('');
}

function mfToday(dir) {
  return `<div class="screen" data-dir="${dir}">${status()}
  <div class="mf-top"><span class="mf-lab">Tuesday 2 March</span><button class="mf-sq" aria-label="Pick a date">${I.cal}</button></div>
  <section class="mf-flood" aria-label="On the table now">
    <div class="mf-row"><span class="mf-lab">On the table</span><span class="mf-lab">Dog 02 of 05</span></div>
    <div class="mf-mid"><h1 class="mf-xl">Max</h1><div class="mf-por">${photo('max', { label: 'Max', vb: '20 30 260 260' })}</div></div>
    <p class="mf-meta">Full groom · 09:15 to 11:15</p>
    ${mfSeg(8, 1)}
    <div class="mf-row mf-small"><span>15 min in</span><span>1 h 45 min left</span></div>
    <p class="mf-note">${I.alert}<span>${NOTE.max}</span></p>
  </section>
  <dl class="mf-stats">${STATS.map(([v, l]) => `<div><dd>${v.replace(' ', '')}</dd><dt>${l}</dt></div>`).join('')}</dl>
  <div class="mf-ih"><span class="mf-lab">Schedule</span><a href="#">1 cancelled</a></div>
  <ol class="mf-index">${mfRows(DAY)}</ol>
  <div class="mf-fade"></div>${mfNav()}
  </div>`;
}

function mfBook(dir) {
  const opt = (n, name, mins, p, on) => `<li><button class="mf-ir mf-opt ${on ? 'is-on' : ''}" aria-pressed="${on}"><span class="mf-no">${n}</span><div class="mf-nm"><b>${name}</b><small>${mins}</small></div><span class="mf-pr">$${p}</span><span class="mf-box">${on ? I.check : ''}</span></button></li>`;
  return `<div class="screen" data-dir="${dir}">${status()}
  <div class="mf-top"><button class="mf-sq" aria-label="Back">${I.back}</button><span class="mf-lab">New booking</span><span style="width:44px"></span></div>
  <section class="mf-dog"><div><span class="mf-lab">Dog</span><h1 class="mf-xl">Bella</h1><p>Toy poodle · Jane Smith · <a class="mf-link" href="#">Change</a></p></div><div class="mf-por mf-por-line">${photo('bella', { label: 'Bella', vb: '20 30 260 260' })}</div></section>
  <div class="mf-ih"><span class="mf-lab">Service</span></div>
  <ol class="mf-index mf-opts">${opt('01', 'Bath & brush', '60 min', 70, true)}${opt('02', 'Full groom', '120 min', 120)}${opt('03', 'Nail trim', '15 min', 20)}</ol>
  <div class="mf-ih"><span class="mf-lab">Start · Tue 2 Mar</span></div>
  <div class="mf-times"><button class="is-on" aria-pressed="true">11:30</button><button>11:45</button><button>12:00</button></div>
  <p class="mf-later">A 60 min bath fits nowhere else today. Wednesday 3 March is open from 08:00.</p>
  <section class="mf-flood mf-foot"><div class="mf-row"><span class="mf-lab">Booking</span><span class="mf-lab">Bella · Bath & brush</span></div>
    <div class="mf-foot-mid"><span class="mf-xl">11:30</span><span class="mf-to">to<br>12:30</span><span class="mf-xl mf-fee">$70</span></div>
    <button class="mf-cta">Book Bella for 11:30 ${I.arrow}</button></section>
  </div>`;
}

function mfProfile(dir) {
  const row = (n, lab, main, sub, btn) => `<li class="mf-ir mf-kv"><span class="mf-no">${n}</span><div class="mf-nm"><small>${lab}</small><b>${main}</b>${sub ? `<small class="mf-sub">${sub}</small>` : ''}</div>${btn || ''}</li>`;
  return `<div class="screen" data-dir="${dir}">${status()}
  <div class="mf-top"><button class="mf-sq" aria-label="Back">${I.back}</button><span class="mf-lab">Dog</span><button class="mf-sq" aria-label="Call owner">${I.phone}</button></div>
  <section class="mf-namewrap"><h1 class="mf-xl mf-name">Sir<br>Reginald<br>Fluffington<br>III</h1><div class="mf-por mf-por-line mf-por-name">${photo('reggie', { label: 'Sir Reginald Fluffington III', vb: '20 30 260 260' })}</div>
    <span class="mf-inv mf-breed">Old English sheepdog</span></section>
  <section class="mf-flood mf-handle"><span class="mf-lab">${I.alert}Handling</span><p>${HANDLING}</p></section>
  <ol class="mf-index mf-kvs">
    ${row('01', 'Owner', "Margaret O'Sullivan-Whitehouse", '+61 7 4162 3301', `<button class="mf-btn mf-btn-icon" aria-label="Call">${I.phone}</button>`)}
    ${row('02', 'Booked', 'Today, 13:00 to 15:00', 'Full groom · $120', '<button class="mf-btn mf-btn-line">Move</button>')}
    ${row('03', 'History', 'First visit', 'Past grooms will list here.')}
  </ol>
  </div>`;
}

function mfDesk(dir) {
  return `<div class="browser"><div class="browser-bar"><i></i><i></i><i></i><span>127.0.0.1:8851 · Grooming book</span></div>
  <div class="screen mf-desk" data-dir="${dir}">
    <section class="mf-flood mf-dflood" aria-label="On the table now">
      <div class="mf-row"><span class="mf-lab">On the table · 09:30</span><span class="mf-lab">Dog 02 of 05</span></div>
      <h1 class="mf-xl mf-dmax">Max</h1>
      <div class="mf-drow"><div class="mf-por">${photo('max', { label: 'Max', vb: '20 30 260 260' })}</div><div><p class="mf-meta mf-meta-l">Full groom</p><p class="mf-meta">09:15 to 11:15</p></div></div>
      ${mfSeg(8, 1)}
      <div class="mf-row mf-small"><span>15 min in</span><span>1 h 45 min left</span></div>
      <p class="mf-note">${I.alert}<span>${NOTE.max}</span></p>
      <div class="mf-dnext"><span class="mf-lab">Next · 11:15</span><div class="mf-row"><b class="mf-xl">Mochi</b><span class="mf-inv mf-inv-w">Muzzle: bites at nails</span></div><p>Nail trim · 15 min</p></div>
    </section>
    <div class="mf-dmain">
      <header class="mf-dtop"><nav aria-label="Main"><a class="is-on" href="#">Today</a><a href="#">Clients</a></nav><span class="mf-lab">Tuesday 2 March · Open 08:00 to 17:00 · Brisbane</span>
        <button class="mf-btn mf-btn-lg">${I.plus}New booking</button></header>
      <dl class="mf-stats mf-dstats">${STATS.map(([v, l]) => `<div><dd>${v.replace(' ', '')}</dd><dt>${l}</dt></div>`).join('')}<div><dd>1</dd><dt>cancelled</dt></div></dl>
      <div class="mf-ih mf-dih"><span class="mf-lab">No.</span><span class="mf-lab">Time</span><span class="mf-lab">Dog and service</span><span class="mf-lab">Fee</span></div>
      <ol class="mf-index mf-dindex">${mfRows(DAY_FULL, { notes: true })}</ol>
    </div>
  </div></div>`;
}

/* ============================================================
   4. CANDY PASTEL: each dog owns a pastel tile; the day is laid out as tiles whose size is the groom's length.
   Fredoka with Nunito, black ink outlines.
   ============================================================ */
const CP = { rusty: 'var(--c-sky)', max: 'var(--c-butter)', mochi: 'var(--c-peach)', reggie: 'var(--c-lilac)', biscuit: 'var(--c-mint)', bella: 'var(--c-rose)' };
const cpPx = (a, b, k, min = 48) => Math.max(min, Math.round((toMin(b) - toMin(a)) * k));
function cpTile(s, k) {
  const h = cpPx(s.t, s.end, k), mins = toMin(s.end) - toMin(s.t);
  if (s.free) return `<button class="cp-tile cp-free ${h < 70 ? 'is-s' : ''}" style="height:${h}px" aria-label="Book ${s.t}"><span class="cp-plus">${I.plus}</span><span><b>${h < 70 ? s.t : 'Free ' + s.t}</b><small>${s.free}${h < 70 ? ' free' : ' to ' + s.end}</small></span></button>`;
  const name = SHORT[s.dog] || s.name, bg = `background:${CP[s.dog]}`;
  if (mins < 60) return `<div class="cp-tile is-s" style="height:${h}px;${bg}">${dog(s.dog, { bg: '#fff' })}<span><b>${name}</b><small>${s.t} · ${s.svc}</small></span></div>`;
  if (s.state === 'now') return `<div class="cp-tile is-l is-now" style="height:${h}px;${bg}"><div class="cp-tile-top"><span class="cp-badge">Now</span>${dog(s.dog, { bg: '#fff' })}</div>
    <b class="cp-big">${name}</b><small>${s.svc} · to ${s.end}</small><div class="cp-meter"><i style="width:12.5%"></i></div><small class="cp-left">1 h 45 min left</small></div>`;
  if (mins >= 120) return `<div class="cp-tile is-l" style="height:${h}px;${bg}"><div class="cp-tile-top">${dog(s.dog, { bg: '#fff' })}<span class="cp-price">$${s.price}</span></div>
    <b class="cp-big cp-big-s">${name}</b><small>${s.t} to ${s.end}</small><small>${s.svc}</small></div>`;
  return `<div class="cp-tile is-m ${s.state === 'done' ? 'is-done' : ''}" style="height:${h}px;${bg}">${dog(s.dog, { bg: '#fff' })}<span><b>${name}</b><small>${s.t} to ${s.end}</small><small>${s.svc}</small></span>${s.state === 'done' ? `<span class="cp-done" aria-label="Done">${I.check}</span>` : ''}</div>`;
}
function cpNav() {
  return `<nav class="cp-nav" aria-label="Main"><a class="is-on" href="#">${I.cal}<span>Today</span></a><a href="#">${I.users}<span>Clients</span></a><button class="cp-fab" aria-label="New booking">${I.plus}</button></nav>`;
}

function cpToday(dir) {
  const k = 1.25, am = DAY.filter(s => toMin(s.t) < 780), pm = DAY_FULL.filter(s => toMin(s.t) >= 780);
  const lane = (items) => items.map((s, i) => { const prev = items[i - 1]; const gap = prev && toMin(s.t) > toMin(prev.end) ? `<i class="cp-gap" style="height:${(toMin(s.t) - toMin(prev.end)) * k}px"></i>` : ''; return gap + cpTile(s, k); }).join('');
  return `<div class="screen" data-dir="${dir}">${status()}
  <div class="cp-top"><div><span class="cp-date">Tuesday 2 March</span><h1 class="display cp-h1">Today</h1></div><button class="cp-icon" aria-label="Pick a date">${I.cal}</button></div>
  <div class="cp-stats"><span><b>5</b> dogs</span><span><b>6h 15</b> grooming</span><span><b>$400</b> expected</span></div>
  <div class="cp-lanes">
    <div class="cp-lane"><div class="cp-lane-h"><b>Morning</b><small>08:00 to 13:00</small></div>${lane(am)}</div>
    <div class="cp-lane"><div class="cp-lane-h"><b>Afternoon</b><small>13:00 to 17:00</small></div>${lane(pm)}</div>
  </div>
  <div class="cp-notes"><p>${I.alert}<span><b>Max</b> ${NOTE.max}</span></p><p>${I.alert}<span><b>Mochi</b> ${NOTE.mochi}</span></p></div>
  ${cpNav()}
  </div>`;
}

function cpBook(dir) {
  const svc = (name, mins, p, icon, bg, cls, on) => `<button class="cp-svc ${cls} ${on ? 'is-on' : ''}" style="background:${bg}" aria-pressed="${on}"><span class="cp-svc-ic">${icon}</span><span class="cp-svc-txt"><b>${name}</b><small>${mins}</small></span><span class="cp-svc-p">$${p}</span>${on ? `<span class="cp-check">${I.check}</span>` : ''}</button>`;
  return `<div class="screen" data-dir="${dir}">${status()}
  <div class="cp-bar"><button class="cp-icon" aria-label="Back">${I.back}</button><span class="cp-date">New booking</span><span style="width:44px"></span></div>
  <section class="cp-dogtile" style="background:${CP.bella}">${dog('bella', { bg: '#fff' })}<div><span class="cp-date">Dog</span><h1 class="display">Bella</h1><p>Toy poodle<br>Jane Smith</p></div><button class="cp-chip">Change</button></section>
  <div class="cp-sec"><h2>Service</h2><small>Bigger tile, longer groom</small></div>
  <div class="cp-svcs">${svc('Full groom', '120 min', 120, I.scissors, 'var(--c-butter)', 'is-l')}<div class="cp-svcs-col">${svc('Bath & brush', '60 min', 70, I.drop, 'var(--c-sky)', 'is-m', true)}${svc('Nail trim', '15 min', 20, I.paw, 'var(--c-peach)', 'is-s')}</div></div>
  <div class="cp-sec"><h2>Free starts</h2><small>Tue 2 Mar</small></div>
  <div class="cp-times"><button class="is-on" aria-pressed="true">11:30</button><button>11:45</button><button>12:00</button></div>
  <p class="cp-later">A 60 min bath fits nowhere else today. Wednesday 3 March is open from 08:00.</p>
  <div class="cp-cta"><button class="cp-cta-btn"><span><b>Book Bella for 11:30</b><small>Bath & brush · 11:30 to 12:30</small></span><span class="cp-cta-p">$70</span></button></div>
  </div>`;
}

function cpProfile(dir) {
  return `<div class="screen" data-dir="${dir}">${status()}
  <div class="cp-bar"><button class="cp-icon" aria-label="Back">${I.back}</button><span class="cp-date">Dog</span><button class="cp-icon" aria-label="More">${I2.dots}</button></div>
  <section class="cp-ptile" style="background:${CP.reggie}"><div class="cp-ptile-txt"><h1 class="display">Sir Reginald Fluffington III</h1><span class="cp-chip cp-chip-static">Old English sheepdog</span></div>
    <div class="cp-ptile-por">${photo('reggie', { label: 'Sir Reginald Fluffington III', vb: '10 30 280 280' })}</div></section>
  <div class="cp-pgrid">
    <div class="cp-pt" style="background:var(--c-peach)"><span class="cp-ini">MO</span><small>Owner</small><b>Margaret O'Sullivan-Whitehouse</b></div>
    <button class="cp-pt cp-pt-call" style="background:var(--c-mint)"><span class="cp-pt-ic">${I.phone}</span><small>Call</small><b>+61 7 4162 3301</b></button>
    <div class="cp-pt cp-pt-wide" style="background:var(--c-butter)"><small>${I.alert}Handling</small><p>${HANDLING}</p></div>
    <div class="cp-pt cp-pt-wide cp-pt-row" style="background:var(--c-sky)"><div><small>Booked</small><b>Today, 13:00 to 15:00</b><span>Full groom · $120</span></div><button class="cp-chip">Move</button></div>
  </div>
  <p class="cp-later" style="margin-top:12px">First visit. Past grooms will list here.</p>
  </div>`;
}

function cpDesk(dir) {
  const k = 1; // flex-grow = minutes, so tile width is the groom's length
  const tile = (s) => {
    const m = toMin(s.end) - toMin(s.t);
    const da = `data-a="${toMin(s.t)}" data-b="${toMin(s.end)}"`;
    if (s.free) return `<button class="cp-dt cp-free" ${da} style="flex-grow:${m}" aria-label="Book ${s.t}"><span class="cp-plus">${I.plus}</span><b>${s.free} free</b><small>Book ${s.t}</small></button>`;
    const name = s.name;
    if (s.state === 'now') return `<div class="cp-dt is-now" ${da} style="flex-grow:${m};background:${CP[s.dog]}"><div class="cp-tile-top"><span class="cp-badge">Now · ${s.t} to ${s.end}</span></div>
      <div class="cp-dt-por">${dog(s.dog, { bg: '#fff' })}</div><b class="cp-big">${name}</b><small>${s.svc}</small><div class="cp-meter"><i style="width:12.5%"></i></div><small class="cp-left">15 min in · 1 h 45 min left</small>
      <p class="cp-dt-note">${I.alert}<span>${NOTE.max}</span></p></div>`;
    const short = m < 30;
    return `<div class="cp-dt ${short ? 'is-s' : ''} ${s.state === 'done' ? 'is-done' : ''}" ${da} style="flex-grow:${m};background:${CP[s.dog]}"><div class="cp-tile-top">${dog(s.dog, { bg: '#fff' })}${s.state === 'done' ? `<span class="cp-done">${I.check}</span>` : short ? '' : `<span class="cp-price">$${s.price}</span>`}</div>
      <b class="${m >= 120 ? 'cp-big' : ''}">${short ? name : (SHORT[s.dog] && m < 120 ? SHORT[s.dog] : name)}</b><small>${short ? s.t : `${s.t} to ${s.end} · ${s.svc}`}</small>${NOTE[s.dog] && !short ? `<p class="cp-dt-note">${I.alert}<span>${NOTE[s.dog]}</span></p>` : ''}${short ? `<span class="cp-warn">${I.alert}</span>` : ''}</div>`;
  };
  const band = (label, range, from, to, items, extra = '') => {
    const ticks = []; for (let h = from; h <= Math.min(to, 17); h++) ticks.push(`<span data-t="${h * 60}" style="left:${(h - from) / 5 * 100}%">${String(h).padStart(2, '0')}:00</span>`);
    let html = ''; items.forEach((s, i) => { const prev = items[i - 1]; if (prev && toMin(s.t) > toMin(prev.end)) html += `<i class="cp-dgap" data-a="${toMin(prev.end)}" data-b="${toMin(s.t)}" style="flex-grow:${toMin(s.t) - toMin(prev.end)}"></i>`; html += tile(s); });
    return `<section class="cp-band"><div class="cp-band-h"><b>${label}</b><small>${range}</small></div><div class="cp-ticks">${ticks.join('')}</div><div class="cp-band-row">${html}${extra}</div></section>`;
  };
  const am = DAY.filter(s => toMin(s.t) < 780), pm = DAY_FULL.filter(s => toMin(s.t) >= 780);
  return `<div class="browser"><div class="browser-bar"><i></i><i></i><i></i><span>127.0.0.1:8851 · Grooming book</span></div>
  <div class="screen cp-desk" data-dir="${dir}">
    <header class="cp-dtop">
      <div><span class="cp-date">Tuesday 2 March</span><h1 class="display cp-h1 cp-h1-xl">Today</h1></div>
      <div class="cp-dstats"><div style="background:var(--c-butter)"><b>5</b><small>dogs booked</small></div><div style="background:var(--c-mint)"><b>6h 15</b><small>of grooming</small></div><div style="background:var(--c-lilac)"><b>$400</b><small>expected</small></div></div>
      <nav class="cp-dnav" aria-label="Main"><a class="is-on" href="#">${I.cal}Today</a><a href="#">${I.users}Clients</a></nav>
      <button class="cp-cta-btn cp-cta-sm">${I.plus}<b>New booking</b></button>
    </header>
    ${band('Morning', '08:00 to 13:00', 8, 13, am)}
    ${band('Afternoon', '13:00 to 17:00', 13, 18, pm, `<div class="cp-dt cp-closed" data-a="1020" data-b="1080" style="flex-grow:60"><b>Closed</b><small>from 17:00</small></div>`)}
  </div></div>`;
}

/* ---------- Board ---------- */
const DIRS2 = [
  { id: 'coral-editorial', name: 'Coral Editorial', note: 'White, coral, black. Photo-led tiles. Schibsted Grotesk.', fns: [ceToday, ceBook, ceProfile, ceDesk] },
  { id: 'sky-illustrated', name: 'Sky Illustrated', note: 'Sky blue, sunshine yellow, navy. Rubik with Figtree.', fns: [skToday, skBook, skProfile, skDesk] },
  { id: 'mono-flood', name: 'Mono Flood', note: 'Off-white, black, one cobalt flood. Anton with Archivo.', fns: [mfToday, mfBook, mfProfile, mfDesk] },
  { id: 'candy-pastel', name: 'Candy Pastel', note: 'A pastel per dog; tile size is groom length. Fredoka with Nunito.', fns: [cpToday, cpBook, cpProfile, cpDesk] },
];

document.getElementById('board').insertAdjacentHTML('beforeend', DIRS2.map(d => (CURRENT_DIR = d.id, '') + `
  <section class="shot" data-dir="${d.id}" id="shot-${d.id}" style="background:var(--backdrop)">
    <div class="shot-label">${d.name}<span style="opacity:.7;letter-spacing:0;text-transform:none;font-weight:600;margin-left:12px">${d.note}</span></div>
    <div class="phone">${d.fns[0](d.id)}</div><div class="phone mid">${d.fns[1](d.id)}</div><div class="phone">${d.fns[2](d.id)}</div>
  </section>
  <section class="desk-shot" data-dir="${d.id}" id="desk-${d.id}" style="background:var(--backdrop)">${d.fns[3](d.id)}</section>`).join(''));

/* Candy desktop: the hour ruler follows the real tile edges, because short tiles keep a readable minimum width. */
document.querySelectorAll('.cp-band').forEach(band => {
  const row = band.querySelector('.cp-band-row'), r0 = row.getBoundingClientRect().left;
  const segs = [...row.children].map(el => { const b = el.getBoundingClientRect(); return { a: +el.dataset.a, b: +el.dataset.b, l: b.left - r0, r: b.right - r0 }; });
  band.querySelectorAll('.cp-ticks span').forEach(sp => {
    const t = +sp.dataset.t, g = segs.find(x => t >= x.a && t <= x.b) || segs[segs.length - 1];
    sp.style.left = (g.l + (g.r - g.l) * (t - g.a) / (g.b - g.a)) + 'px';
  });
});
