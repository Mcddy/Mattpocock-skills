/* Direction board for the grooming book: the same real data in four expressive directions. */

const I = {
  cal: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="3.5" y="5" width="17" height="15.5" rx="4"/><path d="M8 3v4M16 3v4M3.5 10h17"/></svg>',
  users: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="8.5" r="3.5"/><path d="M2.5 20c.8-3.6 3.4-5.5 6.5-5.5s5.7 1.9 6.5 5.5"/><path d="M16 5.5a3.2 3.2 0 0 1 0 6.2M18 14.8c1.8.7 3 2.4 3.5 5.2"/></svg>',
  plus: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>',
  clock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/></svg>',
  alert: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.3 4.3 2.8 17.5A2 2 0 0 0 4.5 20.5h15a2 2 0 0 0 1.7-3L13.7 4.3a2 2 0 0 0-3.4 0Z"/><path d="M12 9.5v4M12 17h.01"/></svg>',
  phone: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M5 4h3.5l1.8 4.4-2.3 1.4a11 11 0 0 0 6.2 6.2l1.4-2.3L20 15.5V19a1.5 1.5 0 0 1-1.6 1.5C10.6 20 4 13.4 3.5 5.6A1.5 1.5 0 0 1 5 4Z"/></svg>',
  back: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m14.5 5.5-6.5 6.5 6.5 6.5"/></svg>',
  search: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="6.5"/><path d="m16 16 4 4"/></svg>',
  check: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="m5 12.5 4.5 4.5L19 7.5"/></svg>',
  scissors: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"><circle cx="6.5" cy="7" r="2.8"/><circle cx="6.5" cy="17" r="2.8"/><path d="M8.8 8.7 20 17M8.8 15.3 20 7"/></svg>',
  drop: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linejoin="round"><path d="M12 3.5s6 6.4 6 10.7a6 6 0 0 1-12 0C6 9.9 12 3.5 12 3.5Z"/><path d="M9.5 14.5a2.6 2.6 0 0 0 2.5 2.6" stroke-linecap="round"/></svg>',
  paw: '<svg viewBox="0 0 24 24" fill="currentColor"><ellipse cx="7" cy="9" rx="2" ry="2.6"/><ellipse cx="12" cy="6.8" rx="2" ry="2.6"/><ellipse cx="17" cy="9" rx="2" ry="2.6"/><ellipse cx="4.6" cy="13.6" rx="1.7" ry="2.2"/><path d="M12 11.5c-3 0-6 4.3-6 6.5 0 1.6 1.3 2.5 2.8 2.5 1.2 0 2-.6 3.2-.6s2 .6 3.2.6c1.5 0 2.8-.9 2.8-2.5 0-2.2-3-6.5-6-6.5Z"/></svg>',
  arrow: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg>',
};

/* Dog portraits drawn from a rule: breed sets fur, ears, muzzle and markings; the same face geometry makes them one family. */
const DOGS = {
  max:    { fur: '#E6A770', dark: '#C98249', ear: 'flop', earc: '#C27940', muzzle: '#F5CEA2', curly: true, tongue: true },
  bella:  { fur: '#F3E4C9', dark: '#E2CBA4', ear: 'flop', earc: '#DDC196', muzzle: '#FCF3E3', curly: true },
  reggie: { fur: '#F6F4EE', ear: 'flop', earc: '#8F99A7', muzzle: '#FFFFFF', sheep: '#A4ADB9' },
  biscuit:{ fur: '#9C6744', ear: 'rose', earc: '#7B4C2E', muzzle: '#F6ECE2', blaze: '#F6ECE2', tongue: true },
  kiwi:   { fur: '#F6EDE0', ear: 'long', earc: '#D8A764', muzzle: '#FFFFFF', topknot: '#FF7A8A' },
  rusty:  { fur: '#BA5A2F', ear: 'point', earc: '#BA5A2F', inner: '#E9A57E', muzzle: '#E4A47D', brows: '#E4A47D' },
  nala:   { fur: '#2C2727', ear: 'point', earc: '#2C2727', inner: '#5A4E4E', muzzle: '#FFFFFF', blaze: '#FFFFFF' },
  mochi:  { fur: '#F18B3B', ear: 'small', earc: '#F18B3B', inner: '#F9B98A', muzzle: '#F9BE88', ruff: '#F6A25C' },
};

/* Illustration style is part of a direction: clay (soft 3D) or flat. */
const DOG_STYLE = { 'warm-pop': 'clay', 'lime-night': 'clay', 'lilac-soft': 'clay', 'fresh-green': 'flat',
  'coral-editorial': 'clay', 'sky-illustrated': 'clay', 'mono-flood': 'flat', 'candy-pastel': 'clay',
  'cherry-noir': 'clay', 'aqua-mint': 'clay', 'rose-studio': 'clay', 'terracotta-arch': 'clay', 'arcade-pixel': 'flat', 'navy-gold': 'clay', 'photo-bold': 'clay', 'plum-peach': 'flat', 'ink-paper': 'flat' };
let CURRENT_DIR = null;
function dog(key, opts = {}) {
  return (DOG_STYLE[CURRENT_DIR] === 'clay' && typeof clayDog === 'function') ? clayDog(key, opts) : flatDog(key, opts);
}
function flatDog(key, { bg = null, ring = null } = {}) {
  const d = DOGS[key], eye = '#1B130F';
  const parts = [];
  if (bg) parts.push(`<circle cx="60" cy="60" r="58" fill="${bg}"/>`);
  if (ring) parts.push(`<circle cx="60" cy="60" r="57" fill="none" stroke="${ring}" stroke-width="3"/>`);
  if (d.ruff) for (let a = 0; a < 360; a += 30) {
    const r = a * Math.PI / 180; parts.push(`<circle cx="${60 + 33 * Math.cos(r)}" cy="${68 + 30 * Math.sin(r)}" r="15" fill="${d.ruff}"/>`);
  }
  const ears = {
    flop: `<ellipse cx="29" cy="64" rx="14" ry="26" transform="rotate(16 29 64)" fill="${d.earc}"/><ellipse cx="91" cy="64" rx="14" ry="26" transform="rotate(-16 91 64)" fill="${d.earc}"/>`,
    long: `<path d="M30 46c-12 6-16 30-10 46 4 10 14 8 17-2 3-12 2-30-7-44Z" fill="${d.earc}"/><path d="M90 46c12 6 16 30 10 46-4 10-14 8-17-2-3-12-2-30 7-44Z" fill="${d.earc}"/>`,
    point: `<path d="M27 52 34 17 54 40Z" fill="${d.earc}" stroke="${d.earc}" stroke-width="7" stroke-linejoin="round"/><path d="M33 44 37 26 47 38Z" fill="${d.inner}"/><path d="M93 52 86 17 66 40Z" fill="${d.earc}" stroke="${d.earc}" stroke-width="7" stroke-linejoin="round"/><path d="M87 44 83 26 73 38Z" fill="${d.inner}"/>`,
    small: `<path d="M35 45 40 24 54 38Z" fill="${d.earc}" stroke="${d.earc}" stroke-width="6" stroke-linejoin="round"/><path d="M40 39 42 30 48 36Z" fill="${d.inner}"/><path d="M85 45 80 24 66 38Z" fill="${d.earc}" stroke="${d.earc}" stroke-width="6" stroke-linejoin="round"/><path d="M80 39 78 30 72 36Z" fill="${d.inner}"/>`,
    rose: `<path d="M30 42c-4-6 2-14 10-12l10 8c-6 2-13 4-20 4Z" fill="${d.earc}"/><path d="M90 42c4-6-2-14-10-12l-10 8c6 2 13 4 20 4Z" fill="${d.earc}"/>`,
  };
  parts.push(ears[d.ear]);
  parts.push(`<ellipse cx="60" cy="64" rx="34" ry="32" fill="${d.fur}"/>`);
  if (d.curly) [[42, 40, 10], [52, 33, 10], [64, 31, 11], [76, 36, 10], [84, 46, 8], [36, 48, 8]].forEach(([x, y, r]) =>
    parts.push(`<circle cx="${x}" cy="${y}" r="${r}" fill="${d.dark}"/>`));
  if (d.blaze) parts.push(`<path d="M60 33c-5 12-8 24-9 40h18c-1-16-4-28-9-40Z" fill="${d.blaze}"/>`);
  if (d.sheep) {
    parts.push(`<path d="M26 60c0-22 15-32 34-32s34 10 34 32c-10-4-22-5-34-5s-24 1-34 5Z" fill="${d.sheep}"/>`);
    for (let x = 30; x <= 90; x += 8) parts.push(`<circle cx="${x}" cy="${57 + (x % 16 ? 2 : 0)}" r="7.5" fill="${x % 16 ? d.fur : '#E7E8EA'}"/>`);
  }
  parts.push(`<ellipse cx="60" cy="79" rx="18" ry="13" fill="${d.muzzle}"/>`);
  if (!d.sheep) {
    if (d.brows) parts.push(`<circle cx="47" cy="51" r="2.6" fill="${d.brows}"/><circle cx="73" cy="51" r="2.6" fill="${d.brows}"/>`);
    parts.push(`<circle cx="47" cy="61" r="4.8" fill="${eye}"/><circle cx="73" cy="61" r="4.8" fill="${eye}"/><circle cx="48.6" cy="59.4" r="1.5" fill="#fff"/><circle cx="74.6" cy="59.4" r="1.5" fill="#fff"/>`);
  }
  parts.push(`<circle cx="40" cy="74" r="5" fill="#FF8E8E" opacity=".28"/><circle cx="80" cy="74" r="5" fill="#FF8E8E" opacity=".28"/>`);
  parts.push(`<path d="M52.5 72.5Q60 67 67.5 72.5 66.5 79.5 60 80.5 53.5 79.5 52.5 72.5Z" fill="${eye}"/><ellipse cx="57.5" cy="71.8" rx="2.4" ry="1.2" fill="#fff" opacity=".55"/>`);
  if (d.tongue) parts.push(`<path d="M55.5 85.5h9v4.5a4.5 4.5 0 0 1-9 0Z" fill="#FF7B86"/>`);
  parts.push(`<path d="M60 80.5v4M60 84.5c-2.6 2.8-6.4 2.8-8.5.6M60 84.5c2.6 2.8 6.4 2.8 8.5.6" stroke="${eye}" stroke-width="2.2" fill="none" stroke-linecap="round"/>`);
  if (d.topknot) parts.push(`<path d="M52 30 60 35 52 40Z M68 30 60 35 68 40Z" fill="${d.topknot}"/><circle cx="60" cy="35" r="3" fill="${d.topknot}"/>`);
  return `<svg viewBox="0 0 120 120" class="av" aria-hidden="true">${parts.join('')}</svg>`;
}

const DAY = [
  { t: '08:00', end: '09:00', dog: 'rusty', name: 'Rusty', svc: 'Bath & brush', price: 70, state: 'done' },
  { t: '09:15', end: '11:15', dog: 'max', name: 'Max', svc: 'Full groom', price: 120, state: 'now' },
  { t: '11:15', end: '11:30', dog: 'mochi', name: 'Mochi', svc: 'Nail trim', price: 20 },
  { t: '11:30', end: '13:00', free: '1h 30m' },
  { t: '13:00', end: '15:00', dog: 'reggie', name: 'Sir Reginald Fluffington III', svc: 'Full groom', price: 120 },
  { t: '15:00', end: '15:30', free: '30m' },
  { t: '15:30', end: '16:30', dog: 'biscuit', name: 'Biscuit', svc: 'Bath & brush', price: 70 },
];

const status = () => `<div class="status"><span>9:30</span><span class="isl"></span><span>5G</span></div>`;

function today(dir) {
  const sched = DAY.map(s => s.free
    ? `<div class="t">${s.t}</div><div class="slot free"><div><h4>Free ${s.t} to ${s.end}</h4><p>${s.free} open</p></div><button class="btn btn-sig" style="margin-left:auto;min-height:38px;padding:9px 14px;font-size:13.5px">Book</button></div>`
    : `<div class="t">${s.t}</div><div class="slot ${s.state === 'done' ? 'is-done' : ''} ${s.state === 'now' ? 'is-now' : ''}">${dog(s.dog, { bg: 'var(--surface-2)' })}<div style="min-width:0"><h4>${s.name}</h4><p>${s.svc} · to ${s.end}</p></div><span class="price">$${s.price}</span></div>`).join('');
  return `<div class="screen" data-dir="${dir}">${status()}
  <div class="topbar"><div><div class="eyebrow">Tuesday 2 March</div><h1 class="display title">Today</h1></div>
    <button class="iconbtn" aria-label="Pick a date">${I.cal}</button></div>
  <div class="week">
    <div class="day is-closed"><small>Mon</small><b>1</b><small>Closed</small></div>
    <div class="day is-on"><small>Tue</small><b>2</b><small>5 dogs</small></div>
    <div class="day"><small>Wed</small><b>3</b><small>1 dog</small></div>
    <div class="day"><small>Thu</small><b>4</b><small>1 dog</small></div>
    <div class="day"><small>Fri</small><b>5</b><small>Free</small></div>
    <div class="day"><small>Sat</small><b>6</b><small>Free</small></div>
  </div>
  <section class="hero" aria-label="On the table now">
    <div class="hero-top"><div><div class="eyebrow">On the table now</div>
    <div class="display hero-name">Max</div>
    <div class="hero-meta">Full groom · until 11:15</div></div>
    <div class="hero-avatar">${dog('max', { bg: 'var(--surface)' })}</div></div>
    <div class="meter"><i style="width:12.5%"></i></div>
    <div class="hero-foot"><span>15 min in</span><span>1 h 45 min left</span></div>
    <div class="hero-note">${I.alert}<span>Nervous of the dryer; use the quiet one</span></div>
  </section>
  <div class="card next">${dog('mochi', { bg: 'var(--surface-2)' })}<div style="min-width:0"><div class="eyebrow">Next · 11:15</div><h3>Mochi</h3>
    <div class="row" style="margin-top:6px;gap:6px;flex-wrap:wrap"><span class="tag tag-soft">Nail trim · 15 min</span><span class="tag tag-warn">${I.alert}Muzzle: bites at nails</span></div></div></div>
  <div class="stats"><div class="stat"><b>5</b><span>dogs booked</span></div><div class="stat"><b>6h 15</b><span>of grooming</span></div><div class="stat"><b>$400</b><span>expected</span></div></div>
  <div class="section-h"><h2>Schedule</h2><a href="#">1 cancelled</a></div>
  <div class="sched">${sched}</div>
  <div class="fade"></div><nav class="nav" aria-label="Main"><a class="is-on" href="#">${I.cal}Today</a><span class="fab" aria-label="New booking">${I.plus}</span><a href="#">${I.users}Clients</a></nav>
  </div>`;
}

function book(dir) {
  const svc = (k, name, mins, p, icon, on) => `<button class="svc ${on ? 'is-on' : ''}"><span class="icon">${icon}</span><b>${name}</b><small>${mins}</small><span class="p">$${p}</span></button>`;
  return `<div class="screen" data-dir="${dir}">${status()}
  <div class="topbar" style="align-items:center"><button class="iconbtn" aria-label="Back">${I.back}</button><span class="eyebrow">New booking</span><span style="width:44px"></span></div>
  <div class="dogpick">${dog('bella', { bg: 'var(--surface)' })}<div><div class="eyebrow">Dog</div><h3>Bella</h3><div class="muted" style="font-weight:600;font-size:13.5px">Toy poodle · Jane Smith</div></div>
    <button class="chip" style="margin-left:auto">Change</button></div>
  <div class="section-h"><h2>Service</h2></div>
  <div class="svcs">${svc('bath', 'Bath & brush', '60 min', 70, I.drop, true)}${svc('full', 'Full groom', '120 min', 120, I.scissors)}${svc('nail', 'Nail trim', '15 min', 20, I.paw)}</div>
  <div class="section-h"><h2>Free starts</h2><a href="#">Tue 2 Mar</a></div>
  <div class="times"><button class="time is-on">11:30</button><button class="time">11:45</button><button class="time">12:00</button><button class="time" style="visibility:hidden"></button></div>
  <p class="later">A 60 min bath fits nowhere else today. Wednesday 3 March is open from 08:00.</p>
  <div class="summary"><div class="eyebrow">Booking</div><div class="row between" style="margin-top:6px"><span class="big">11:30 to 12:30</span><span class="big">$70</span></div>
    <div class="muted" style="font-weight:600;margin-top:6px">Bella, Bath & brush, Tuesday 2 March</div></div>
  <div class="ctabar"><button class="btn btn-ink btn-block">Book Bella for 11:30 ${I.arrow}</button></div>
  </div>`;
}

function profile(dir) {
  return `<div class="screen" data-dir="${dir}">${status()}
  <div class="profile-hero"><div class="row between" style="padding-top:4px"><button class="iconbtn" aria-label="Back">${I.back}</button><span class="eyebrow">Dog</span><button class="iconbtn" aria-label="Call owner">${I.phone}</button></div>
    ${dog('reggie', { bg: 'var(--surface)' })}<h1 class="display">Sir Reginald Fluffington III</h1><span class="tag tag-soft" style="background:var(--surface)">Old English sheepdog</span></div>
  <div class="card owner"><span class="initials">MO</span><div style="min-width:0"><div class="eyebrow">Owner</div><div style="font-weight:700">Margaret O'Sullivan-Whitehouse</div><div class="muted" style="font-weight:600;font-size:13.5px">+61 7 4162 3301</div></div></div>
  <div class="notecard"><div class="eyebrow">Handling</div><p>Matts behind the ears. Senior: lift him onto the table, do not let him jump.</p></div>
  <div class="section-h"><h2>Booked</h2></div>
  <div class="card" style="margin:0 16px;display:flex;align-items:center;gap:12px"><div class="booked-icon">${I.scissors}</div>
    <div><div style="font-weight:700">Today, 13:00 to 15:00</div><div class="muted" style="font-weight:600;font-size:13.5px">Full groom · $120</div></div><button class="chip" style="margin-left:auto">Move</button></div>
  <p class="later" style="margin-top:14px">First visit. Past grooms will list here.</p>
  </div>`;
}


function desktop(dir) {
  const H = 64, start = 8, y = (hm) => { const [h, m] = hm.split(':').map(Number); return (h + m / 60 - start) * H; };
  const items = [
    { a: '08:00', b: '09:00', cls: 'bath done', dog: 'rusty', name: 'Rusty', meta: 'Bath & brush · done' },
    { a: '09:15', b: '11:15', cls: 'full now', dog: 'max', name: 'Max', meta: 'Full groom · on the table' },
    { a: '11:15', b: '11:30', cls: 'nail', dog: 'mochi', name: 'Mochi', meta: 'Nail trim · muzzle', min: 34 },
    { a: '11:30', b: '13:00', cls: 'free', free: '1h 30m free', shift: 18 },
    { a: '13:00', b: '15:00', cls: 'full', dog: 'reggie', name: 'Sir Reginald Fluffington III', meta: 'Full groom · senior, lift onto table' },
    { a: '15:00', b: '15:30', cls: 'free', free: '30m free' },
    { a: '15:30', b: '16:30', cls: 'bath', dog: 'biscuit', name: 'Biscuit', meta: 'Bath & brush · no oatmeal shampoo' },
    { a: '16:30', b: '17:00', cls: 'free', free: '30m free' },
  ];
  const hours = [8, 9, 10, 11, 12, 13, 14, 15, 16, 17].map(h => `<div class="tl-hour" style="top:${(h - start) * H}px"><span>${String(h).padStart(2, '0')}:00</span></div>`).join('');
  const blocks = items.map(it => {
    const top = y(it.a) + 2 + (it.shift || 0), h = Math.max(it.min || 0, y(it.b) - y(it.a) - 4 - (it.shift || 0));
    if (it.free) return `<div class="tl-item free ${h < 40 ? 'short' : ''}" style="top:${top}px;height:${h}px"><h4>${it.free}</h4><button class="btn btn-sig" style="margin-left:auto;min-height:34px;padding:8px 14px;font-size:13px">Book ${it.a}</button></div>`;
    return `<div class="tl-item ${it.cls}" style="top:${top}px;height:${h}px">${dog(it.dog, { bg: 'var(--surface)' })}<div style="min-width:0"><h4>${it.name}</h4>${it.cls === 'nail' ? '' : `<p>${it.a} to ${it.b} · ${it.meta}</p>`}</div>${it.cls === 'nail' ? `<p style="margin:0 0 0 auto;font-size:12.5px;font-weight:700">11:15 · ${it.meta}</p>` : ''}</div>`;
  }).join('');
  return `<div class="browser"><div class="browser-bar"><i></i><i></i><i></i><span>127.0.0.1:8851 · Grooming book</span></div>
  <div class="screen desk" data-dir="${dir}">
    <nav class="rail" aria-label="Main"><div class="mark">${I.paw}</div><a class="is-on" href="#">${I.cal}</a><a href="#">${I.users}</a><a href="#">${I.plus}</a></nav>
    <div class="colA">
      <div class="row between" style="align-items:flex-end"><div><div class="eyebrow">Tuesday 2 March</div><h1 class="display" style="font-size:54px;margin:4px 0 0">Today</h1></div>
        <button class="btn btn-ink">${I.plus}New booking</button></div>
      <div class="week" style="padding:16px 0 4px">
        <div class="day is-closed"><small>Mon</small><b>1</b><small>Closed</small></div><div class="day is-on"><small>Tue</small><b>2</b><small>5 dogs</small></div>
        <div class="day"><small>Wed</small><b>3</b><small>1 dog</small></div><div class="day"><small>Thu</small><b>4</b><small>1 dog</small></div>
        <div class="day"><small>Fri</small><b>5</b><small>Free</small></div><div class="day"><small>Sat</small><b>6</b><small>Free</small></div></div>
      <section class="hero"><div class="hero-top"><div><div class="eyebrow">On the table now</div><div class="display hero-name">Max</div><div class="hero-meta">Full groom · until 11:15</div></div>
        <div class="hero-avatar">${dog('max', { bg: 'var(--surface)' })}</div></div>
        <div class="meter"><i style="width:12.5%"></i></div><div class="hero-foot"><span>15 min in</span><span>1 h 45 min left</span></div>
        <div class="hero-note">${I.alert}<span>Nervous of the dryer; use the quiet one</span></div></section>
      <div class="card next">${dog('mochi', { bg: 'var(--surface-2)' })}<div style="min-width:0"><div class="eyebrow">Next · 11:15</div><h3>Mochi</h3>
        <div class="row" style="margin-top:6px;gap:6px;flex-wrap:wrap"><span class="tag tag-soft">Nail trim · 15 min</span><span class="tag tag-warn">${I.alert}Muzzle: bites at nails</span></div></div></div>
      <div class="stats"><div class="stat"><b>5</b><span>dogs booked</span></div><div class="stat"><b>6h 15</b><span>of grooming</span></div><div class="stat"><b>$400</b><span>expected</span></div></div>
    </div>
    <div class="colB"><div class="timeline"><div class="row between"><h2 class="display" style="font-size:26px;margin:0">The day, to scale</h2><span class="tag tag-soft">Open 08:00 to 17:00 · Brisbane</span></div>
      <div class="tl-grid">${hours}${blocks}<div class="tl-now" style="top:${y('09:30')}px"></div></div></div></div>
  </div></div>`;
}

const DIRS = [
  { id: 'warm-pop', name: 'Warm Pop', note: 'Cream, tangerine, black pills. Bricolage Grotesque with Plus Jakarta Sans.' },
  { id: 'lime-night', name: 'Lime Night', note: 'Near-black, electric lime, light pill nav. Sora with Manrope.' },
  { id: 'lilac-soft', name: 'Lilac Soft', note: 'Lavender, violet, coral pop. Outfit.' },
  { id: 'fresh-green', name: 'Fresh Green', note: 'Forest green, mint, cream, yolk yellow. Fraunces with DM Sans.' },
];

document.getElementById('board').innerHTML = DIRS.map(d => (CURRENT_DIR = d.id, '') + `
  <section class="shot" data-dir="${d.id}" id="shot-${d.id}" style="background:var(--backdrop)">
    <div class="shot-label">${d.name}<span style="opacity:.6;letter-spacing:0;text-transform:none;font-weight:600;margin-left:12px">${d.note}</span></div>
    <div class="phone">${today(d.id)}</div><div class="phone mid">${book(d.id)}</div><div class="phone">${profile(d.id)}</div>
  </section>
  <section class="desk-shot" data-dir="${d.id}" id="desk-${d.id}" style="background:var(--backdrop)">${desktop(d.id)}</section>`).join('');
