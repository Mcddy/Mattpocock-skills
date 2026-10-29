#!/usr/bin/env node
/* Smoke test for a percept course file, using jsdom (no browser needed).

   Usage: node smoke.js COURSE.html

   Opens every lesson, steps every beat, then runs autoplay to the end with timers shortened.
   Fails (exit 1) on: a script error, a drawing that does not change between the first and last
   beat, "NaN" or "undefined" in a drawing, or autoplay not finishing every lesson.
   Exit 3 means the test could not run (jsdom is not installed). That is "not run", not a pass.

   jsdom does not lay out or paint a page. This test cannot see colour, contrast, overflow or
   anything visual. Use render_check.py for those. */
const fs = require('fs');
const argv = process.argv.slice(2);
const unknown = argv.filter(a => a.startsWith('--'));
if (unknown.length) { console.log('smoke: unknown option ' + unknown[0]); process.exit(2); }
if (argv.length !== 1) { console.log('usage: node smoke.js COURSE.html'); process.exit(2); }
const file = argv[0];
if (!fs.existsSync(file)) { console.log('smoke: cannot read ' + file); process.exit(2); }
let JSDOM;
try { ({ JSDOM } = require('jsdom')); }
catch (e) { console.log('NOT RUN: the jsdom package is not installed (npm install jsdom)'); process.exit(3); }

const html = fs.readFileSync(file, 'utf8');
const errs = [];
const dom = new JSDOM(html, {
  runScripts: 'dangerously', pretendToBeVisual: true,
  beforeParse(w) {
    w.requestAnimationFrame = cb => setTimeout(cb, 0);
    w.scrollTo = () => {};
    const st = w.setTimeout.bind(w);
    w.setTimeout = (f, ms, ...a) => st(f, (ms && ms > 16) ? 8 : ms, ...a);       // shorten autoplay waits
    w.matchMedia = q => ({ matches: false, media: q, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {} });
    w.addEventListener('error', ev => errs.push((ev.error && ev.error.message) || ev.message));
  },
});
const w = dom.window, D = w.document;
w.Element.prototype.scrollIntoView = () => {};
const wait = ms => new Promise(r => setTimeout(r, ms));

setTimeout(async () => {
  const run = code => w.eval(code);
  const n = D.querySelectorAll('.ditem').length;
  if (!n) { console.log('FAIL: the course did not start (no lessons in the drawer)'); errs.slice(0, 5).forEach(e => console.log('   error: ' + e)); process.exit(1); }
  const noProgress = [], badMarkup = [];
  for (let i = 0; i < n; i++) {
    run(`goLesson(${i},'right')`);
    const total = D.querySelectorAll('.dpip').length;
    run('setStep(1)'); const a = D.querySelector('#animCanvas').innerHTML;
    run(`setStep(${total})`); const b = D.querySelector('#animCanvas').innerHTML;
    if (a === b && total >= 2) noProgress.push(i + 1);
    if (/NaN|undefined/.test(b)) badMarkup.push(i + 1);
  }
  run("goHome('up');play()");
  let guard = 0;
  while (D.querySelectorAll('.ditem.done').length < n && guard++ < 1500) await wait(9);
  const done = D.querySelectorAll('.ditem.done').length;
  console.log(`lessons: ${n} | no progress between beats: ${noProgress.length} | bad markup: ${badMarkup.length} | autoplay finished: ${done}/${n} | script errors: ${errs.length}`);
  if (noProgress.length) console.log('   lessons with no progress: ' + noProgress.join(', '));
  if (badMarkup.length) console.log('   lessons with NaN or undefined: ' + badMarkup.join(', '));
  errs.slice(0, 10).forEach(e => console.log('   error: ' + e));
  const ok = !noProgress.length && !badMarkup.length && done === n && !errs.length;
  console.log(ok ? 'RESULT: PASS (behaviour only; nothing visual was checked)' : 'RESULT: FAIL');
  process.exit(ok ? 0 : 1);
}, 300);
