/*
  test_pocket_state.js: tests for pocket-state.js. Node, no dependencies beyond Node itself.

  Usage:
    node test_pocket_state.js                  run every test against pocket-state.js beside this file
    node test_pocket_state.js --lib PATH       run against another copy of the library
    node test_pocket_state.js --only NAME      run one test
    node test_pocket_state.js --planted        make deliberately broken copies of the library in a
                                               temporary folder, run the tests against each, and
                                               check that the named test fails for each one
    node test_pocket_state.js --json           machine-readable results

  Storage, timers and the clock are small fakes passed in through create({env}). No browser is
  involved, so this shows the library's logic and not any browser's storage behaviour.

  pocket-lib.sha256, beside this file, records the SHA-256 of the released pocket-state.js and
  pocket-ui.js, one "HASH  NAME" line each. The test released_files_match_the_recorded_hashes
  fails when either file differs from its line. A tool that carries its own copies of the two
  files carries the same record, so its own test can show the copies are the released files
  without reading this folder. After a deliberate change to either file, raise its revision and
  rewrite the record: sha256sum pocket-state.js pocket-ui.js > pocket-lib.sha256

  Exit codes: 0 every test passed (or, with --planted, every broken copy was caught by its named
  test). 1 a test failed (or a broken copy was not caught). 2 bad arguments or unreadable library.
*/
'use strict';
var assert = require('assert');
var fs = require('fs');
var os = require('os');
var path = require('path');
var childProcess = require('child_process');
var crypto = require('crypto');

var HASH_FILE = 'pocket-lib.sha256';
var RELEASED = ['pocket-state.js', 'pocket-ui.js'];

var FLAGS = {'--planted': true, '--json': true};
var VALUES = {'--lib': true, '--only': true};
var args = {lib: path.join(__dirname, 'pocket-state.js'), only: null, planted: false, json: false};
(function parse(argv) {
  var i, a;
  for (i = 0; i < argv.length; i++) {
    a = argv[i];
    if (FLAGS[a]) { args[a.slice(2)] = true; continue; }
    if (VALUES[a]) {
      if (i + 1 >= argv.length || argv[i + 1].indexOf('--') === 0) { process.stderr.write('test_pocket_state: ' + a + ' needs a value\n'); process.exit(2); }
      args[a.slice(2)] = argv[++i];
      continue;
    }
    process.stderr.write('test_pocket_state: unknown argument ' + a + '\n');
    process.exit(2);
  }
})(process.argv.slice(2));

// ---------- fakes ----------
var T0 = Date.parse('2026-10-09T02:00:00.000Z');

function named(name, code) {
  var e = new Error(name);
  e.name = name;
  if (code) e.code = code;
  return e;
}
function fakeClock() {
  var now = T0, queue = [], nextId = 0;
  return {
    now: function () { return now; },
    setTimeout: function (fn, ms) { queue.push({id: ++nextId, at: now + ms, fn: fn}); return nextId; },
    clearTimeout: function (id) { queue = queue.filter(function (q) { return q.id !== id; }); },
    advance: function (ms) {
      // Time moves to each timer's own moment before it fires, as a real clock would.
      var due, end = now + ms;
      for (;;) {
        due = queue.filter(function (q) { return q.at <= end; }).sort(function (a, b) { return a.at - b.at; })[0];
        if (!due) break;
        queue = queue.filter(function (q) { return q.id !== due.id; });
        now = Math.max(now, due.at);
        due.fn();
      }
      now = end;
    },
    waiting: function () { return queue.length; }
  };
}
// One browser profile's localStorage, shared by any number of tabs.
function fakeProfile() {
  var map = {}, tabs = [];
  var profile = {
    map: map, writes: 0, failRead: false, failWrite: false, quotaChars: null,
    tab: function (opts) {
      opts = opts || {};
      var listeners = [];
      var tab = {
        getItem: function (k) {
          if (profile.failRead) throw named('SecurityError', 18);
          return Object.prototype.hasOwnProperty.call(map, k) ? map[k] : null;
        },
        setItem: function (k, v) {
          if (profile.failWrite) throw named('SecurityError', 18);
          if (profile.quotaChars !== null && String(v).length > profile.quotaChars) throw named('QuotaExceededError', 22);
          map[k] = String(v);
          profile.writes++;
          if (opts.events !== false) {
            tabs.forEach(function (other) {
              if (other !== tab && other.events) other.listeners.forEach(function (fn) { fn({key: k, newValue: String(v)}); });
            });
          }
        },
        removeItem: function (k) { delete map[k]; },
        listeners: listeners,
        events: opts.events !== false,
        onStorage: function (fn) { listeners.push(fn); return function () { listeners.splice(listeners.indexOf(fn), 1); }; }
      };
      tabs.push(tab);
      return tab;
    }
  };
  return profile;
}
function fakeHost(opts) {
  opts = opts || {};
  var host = {
    map: {}, gets: 0, sets: 0, failSet: false,
    get: function (k) {
      host.gets++;
      if (opts.never) return new Promise(function () {});
      if (!Object.prototype.hasOwnProperty.call(host.map, k)) {
        if (opts.rejectMissing) return Promise.reject(new Error('key not found'));
        return Promise.resolve(null);
      }
      return Promise.resolve(opts.objects ? {key: k, value: host.map[k]} : host.map[k]);
    },
    set: function (k, v) {
      host.sets++;
      if (opts.never) return new Promise(function () {});
      if (host.failSet) return Promise.reject(named('QuotaExceededError', 22));
      host.map[k] = v;
      return Promise.resolve({key: k, value: v});
    }
  };
  return host;
}
function envFor(tab, clock, host) {
  var env = {root: {}, local: tab || null, host: host || null, setTimeout: clock.setTimeout, clearTimeout: clock.clearTimeout, now: clock.now};
  if (tab && tab.onStorage) env.onStorage = tab.onStorage;
  env.onLeave = function (fn) { env.leave = fn; return function () { env.leave = null; }; };
  return env;
}

// ---------- a small tool to test with: a list of notes, schema 3 ----------
// schema 1: {notes: ["text", ...]}
// schema 2: {notes: [{text: "..."}]}
// schema 3: {notes: [{id: 1, text: "...", done: false}], nextId: 2}
var order = [];
var MIGRATIONS = {
  1: function (d) { order.push(1); return {notes: d.notes.map(function (t) { return {text: t}; })}; },
  2: function (d) { order.push(2); return {notes: d.notes.map(function (n, i) { return {id: i + 1, text: n.text, done: false}; }), nextId: d.notes.length + 1}; }
};
function validate(d) {
  var p = [];
  if (!d || typeof d !== 'object' || !Array.isArray(d.notes)) return ['notes must be a list'];
  if (typeof d.nextId !== 'number') p.push('nextId must be a number');
  d.notes.forEach(function (n, i) {
    if (!n || typeof n !== 'object') { p.push('note ' + i + ' is not an object'); return; }
    if (typeof n.id !== 'number') p.push('note ' + i + ' has no numeric id');
    if (typeof n.text !== 'string' || !n.text) p.push('note ' + i + ' has no text');
    if (typeof n.done !== 'boolean') p.push('note ' + i + ' has no done flag');
  });
  return p;
}
function make(Lib, env, extra) {
  var cfg = {app: 'notes', schema: 3, contentId: 'notes@1', initial: {notes: [], nextId: 1}, migrations: MIGRATIONS, validate: validate, env: env};
  var k;
  for (k in (extra || {})) cfg[k] = extra[k];
  return Lib.create(cfg);
}
function add(store, text) {
  return store.update(function (d) { d.notes.push({id: d.nextId, text: text, done: false}); d.nextId++; }, {label: 'Add ' + text});
}
function envelope(over) {
  var e = {app: 'notes', schema: 3, content_id: 'notes@1', saved_at: '2026-10-09T01:00:00.000Z', data: {notes: [{id: 1, text: 'from a file', done: true}], nextId: 2}};
  var k;
  for (k in (over || {})) { if (over[k] === undefined) delete e[k]; else e[k] = over[k]; }
  return JSON.stringify(e);
}
function snapshot(store, profile) {
  return {ref: store.get(), bytes: JSON.stringify(store.get()), history: JSON.stringify(store.history()), stored: profile ? JSON.stringify(profile.map) : null, writes: profile ? profile.writes : null};
}
function assertUntouched(store, before, profile, what) {
  assert.strictEqual(store.get(), before.ref, what + ': the state object was replaced');
  assert.deepStrictEqual(JSON.parse(JSON.stringify(store.get())), JSON.parse(before.bytes), what + ': the state is no longer deep-equal');
  assert.strictEqual(JSON.stringify(store.get()), before.bytes, what + ': the serialised bytes changed');
  assert.strictEqual(JSON.stringify(store.history()), before.history, what + ': the undo history changed');
  if (profile) {
    assert.strictEqual(JSON.stringify(profile.map), before.stored, what + ': stored data changed');
    assert.strictEqual(profile.writes, before.writes, what + ': something was written to storage');
  }
}

// ---------- tests ----------
var tests = [];
var notes = [];
function test(name, fn) { tests.push({name: name, fn: fn}); }

function define(Lib) {
  test('envelope_has_the_five_contract_fields', async function () {
    var clock = fakeClock(), store = make(Lib, envFor(null, clock));
    add(store, 'one');
    var ex = store.exportEnvelope();
    assert.deepStrictEqual(Object.keys(ex.envelope), ['app', 'schema', 'content_id', 'saved_at', 'data']);
    assert.deepStrictEqual(Object.keys(JSON.parse(ex.text)), ['app', 'schema', 'content_id', 'saved_at', 'data']);
    assert.strictEqual(ex.envelope.saved_at, '2026-10-09T02:00:00.000Z');
    assert.strictEqual(ex.bytes, Buffer.byteLength(ex.text, 'utf8'));
    assert.ok(/^notes-2026-10-09\.json$/.test(ex.filename), ex.filename);
  });

  test('round_trip_export_then_import_reproduces_state', async function () {
    var clock = fakeClock(), a = make(Lib, envFor(null, clock)), b = make(Lib, envFor(null, clock));
    add(a, 'milk'); add(a, 'eggs');
    a.update(function (d) { d.notes[0].done = true; });
    var text = a.exportEnvelope().text;
    var r = await b.importText(text);
    assert.strictEqual(r.ok, true, JSON.stringify(r));
    assert.deepStrictEqual(b.get(), a.get());
    assert.strictEqual(JSON.stringify(b.get()), JSON.stringify(a.get()));
    assert.strictEqual(JSON.stringify(JSON.parse(b.exportEnvelope().text).data), JSON.stringify(JSON.parse(text).data));
  });

  test('import_refusals_leave_state_identical', async function () {
    var clock = fakeClock(), profile = fakeProfile(), store = make(Lib, envFor(profile.tab(), clock));
    add(store, 'keep me'); add(store, 'and me');
    await store.flush();
    var events = 0;
    store.subscribe(function (e) { if (e.type === 'change') events++; });
    var cases = [
      ['empty', '', {}],
      ['empty', '   \n\t ', {}],
      ['empty', null, {}],
      ['not_json', '{"app": "notes", ', {}],
      ['not_json', 'claim_id,question_id\nC1,Q1', {}],
      ['not_envelope', '[1, 2, 3]', {}],
      ['not_envelope', '"just text"', {}],
      ['not_envelope', envelope({app: undefined}), {}],
      ['not_envelope', envelope({data: undefined}), {}],
      ['not_envelope', envelope({schema: undefined}), {}],
      ['not_envelope', envelope({app: 7}), {}],
      ['not_envelope', envelope({data: null}), {}],
      ['wrong_app', envelope({app: 'reading-log'}), {}],
      ['bad_schema', envelope({schema: '3'}), {}],
      ['bad_schema', envelope({schema: 2.5}), {}],
      ['bad_schema', envelope({schema: 0}), {}],
      ['bad_schema', envelope({schema: true}), {}],
      ['newer_schema', envelope({schema: 4}), {}],
      ['invalid_data', envelope({data: {notes: [{id: 1, text: '', done: false}], nextId: 2}}), {}],
      ['invalid_data', envelope({data: {notes: 'none'}}), {}],
      ['invalid_data', envelope({data: 5}), {}],
      ['content_mismatch', envelope({content_id: 'notes@2'}), {}],
      ['content_mismatch', envelope({content_id: undefined}), {}],
      ['content_mismatch', envelope({content_id: 'notes@2'}), {onContentMismatch: function () { return false; }}],
      ['content_mismatch', envelope({content_id: 'notes@2'}), {onContentMismatch: function () { return 'yes'; }}],
      ['content_mismatch', envelope({content_id: 'notes@2'}), {onContentMismatch: function () { throw new Error('page bug'); }}],
      ['content_mismatch', envelope({content_id: 'notes@2'}), {onContentMismatch: function () { return Promise.reject(new Error('closed')); }}],
      ['content_mismatch', envelope({content_id: 'notes@2'}), {allowContentMismatch: 'true'}]
    ];
    var i, c, before, r;
    for (i = 0; i < cases.length; i++) {
      c = cases[i];
      before = snapshot(store, profile);
      r = await store.importText(c[1], c[2]);
      assert.strictEqual(r.ok, false, 'case ' + i + ' (' + c[0] + ') was accepted');
      assert.strictEqual(r.reason, c[0], 'case ' + i + ' gave reason ' + r.reason + ': ' + r.message);
      assert.ok(/Nothing was changed\.$/.test(r.message), 'case ' + i + ' message does not say nothing changed: ' + r.message);
      clock.advance(5000);
      await store.flush();
      assertUntouched(store, before, profile, 'case ' + i + ' (' + c[0] + ')');
    }
    assert.strictEqual(events, 0, 'a refused import emitted a change event');
    notes.push('import refusals checked: ' + cases.length + ' inputs, each leaving the same object, the same bytes, the same history and no storage write');
  });

  test('import_valid_neighbours_are_accepted', async function () {
    var clock = fakeClock(), r, store;
    // the current schema, next to the refused schema 4
    store = make(Lib, envFor(null, clock));
    r = await store.importText(envelope({schema: 3}));
    assert.strictEqual(r.ok, true, JSON.stringify(r));
    assert.strictEqual(store.get().notes[0].text, 'from a file');
    // a byte-order mark in front
    store = make(Lib, envFor(null, clock));
    r = await store.importText(String.fromCharCode(0xFEFF) + envelope());
    assert.strictEqual(r.ok, true, JSON.stringify(r));
    // other content, and the page says yes
    store = make(Lib, envFor(null, clock));
    var asked = null;
    r = await store.importText(envelope({content_id: 'notes@2'}), {onContentMismatch: function (m) { asked = m; return Promise.resolve(true); }});
    assert.strictEqual(r.ok, true, JSON.stringify(r));
    assert.deepStrictEqual({expected: asked.expected, found: asked.found}, {expected: 'notes@1', found: 'notes@2'});
    assert.deepStrictEqual(r.contentMismatch, {expected: 'notes@1', found: 'notes@2'});
    // other content, allowed outright
    store = make(Lib, envFor(null, clock));
    r = await store.importText(envelope({content_id: 'notes@2'}), {allowContentMismatch: true});
    assert.strictEqual(r.ok, true, JSON.stringify(r));
    // inspect on its own reports and changes nothing
    store = make(Lib, envFor(null, clock));
    var before = snapshot(store, null);
    var seen = store.inspect(envelope());
    assert.strictEqual(seen.ok, true);
    assert.strictEqual(seen.contentMismatch, null);
    assertUntouched(store, before, null, 'inspect');
  });

  test('migration_chain_1_to_3_runs_in_order', async function () {
    var clock = fakeClock(), store = make(Lib, envFor(null, clock));
    order.length = 0;
    var r = await store.importText(JSON.stringify({app: 'notes', schema: 1, content_id: 'notes@1', saved_at: '2025-01-01T00:00:00.000Z', data: {notes: ['alpha', 'beta']}}));
    assert.strictEqual(r.ok, true, JSON.stringify(r));
    assert.deepStrictEqual(order, [1, 2], 'steps ran as ' + JSON.stringify(order));
    assert.deepStrictEqual(r.steps, [1, 2]);
    assert.strictEqual(r.migratedFrom, 1);
    assert.deepStrictEqual(JSON.parse(JSON.stringify(store.get())), {notes: [{id: 1, text: 'alpha', done: false}, {id: 2, text: 'beta', done: false}], nextId: 3});
    // schema 2 enters the chain part way and runs only step 2
    order.length = 0;
    store = make(Lib, envFor(null, clock));
    r = await store.importText(JSON.stringify({app: 'notes', schema: 2, content_id: 'notes@1', saved_at: '2025-06-01T00:00:00.000Z', data: {notes: [{text: 'gamma'}]}}));
    assert.strictEqual(r.ok, true, JSON.stringify(r));
    assert.deepStrictEqual(order, [2]);
    assert.strictEqual(store.get().notes[0].text, 'gamma');
  });

  test('migration_producing_invalid_data_is_refused_state_intact', async function () {
    var clock = fakeClock(), profile = fakeProfile(), before, r, store;
    function v1(notesList) { return JSON.stringify({app: 'notes', schema: 1, content_id: 'notes@1', saved_at: '2025-01-01T00:00:00.000Z', data: {notes: notesList}}); }
    // An empty string in schema 1 migrates to a note with no text, which the validator refuses.
    store = make(Lib, envFor(profile.tab(), clock));
    add(store, 'existing'); await store.flush();
    before = snapshot(store, profile);
    r = await store.importText(v1(['fine', '']));
    assert.strictEqual(r.ok, false);
    assert.strictEqual(r.reason, 'migration_invalid', r.message);
    assert.ok(/note 1 has no text/.test(r.message), r.message);
    clock.advance(5000); await store.flush();
    assertUntouched(store, before, profile, 'invalid after migration');
    // A step that throws (schema 1 data with no notes list).
    r = await store.importText(JSON.stringify({app: 'notes', schema: 1, content_id: 'notes@1', saved_at: 'x', data: {}}));
    assert.strictEqual(r.reason, 'migration_failed', r.message);
    assert.strictEqual(r.step, 1);
    assertUntouched(store, before, profile, 'step threw');
    // A step that returns nothing, a step that is missing, and a check on an intermediate schema.
    var broken = make(Lib, envFor(null, clock), {migrations: {1: function () { return undefined; }, 2: MIGRATIONS[2]}});
    before = snapshot(broken, null);
    r = await broken.importText(v1(['a']));
    assert.strictEqual(r.reason, 'migration_failed', r.message);
    assertUntouched(broken, before, null, 'step returned nothing');
    var gap = make(Lib, envFor(null, clock), {migrations: {2: MIGRATIONS[2]}});
    before = snapshot(gap, null);
    r = await gap.importText(v1(['a']));
    assert.strictEqual(r.reason, 'no_migration', r.message);
    assertUntouched(gap, before, null, 'missing step');
    var strict = make(Lib, envFor(null, clock), {validateOlder: {2: function (d) { return d.notes.length > 1 ? ['schema 2 allowed one note'] : []; }}});
    before = snapshot(strict, null);
    r = await strict.importText(v1(['a', 'b']));
    assert.strictEqual(r.reason, 'migration_invalid', r.message);
    assert.strictEqual(r.step, 1);
    assertUntouched(strict, before, null, 'intermediate check');
    r = await strict.importText(v1(['a']));
    assert.strictEqual(r.ok, true, 'the valid neighbour (one note) was refused: ' + r.message);
  });

  test('newer_schema_is_refused_current_schema_is_accepted', async function () {
    var clock = fakeClock(), store = make(Lib, envFor(null, clock)), before = snapshot(store, null);
    var r = await store.importText(envelope({schema: 4}));
    assert.strictEqual(r.ok, false);
    assert.strictEqual(r.reason, 'newer_schema');
    assert.ok(/schema 4/.test(r.message) && /schema 3/.test(r.message), r.message);
    assertUntouched(store, before, null, 'newer schema');
    r = await store.importText(envelope({schema: 3}));
    assert.strictEqual(r.ok, true);
  });

  test('undo_and_redo_across_updates', async function () {
    var clock = fakeClock(), store = make(Lib, envFor(null, clock), {historyLimit: 3}), i;
    assert.strictEqual(store.undo().ok, false);
    add(store, 'a'); add(store, 'b');
    assert.deepStrictEqual(store.history().undo, ['Add a', 'Add b']);
    assert.deepStrictEqual(store.undo(), {ok: true, label: 'Add b'});
    assert.strictEqual(store.get().notes.length, 1);
    assert.deepStrictEqual(store.redo(), {ok: true, label: 'Add b'});
    assert.strictEqual(store.get().notes.length, 2);
    store.undo();
    add(store, 'c');
    assert.strictEqual(store.canRedo(), false, 'a new change must clear redo');
    assert.deepStrictEqual(store.get().notes.map(function (n) { return n.text; }), ['a', 'c']);
    // an update that changes nothing is not a step
    var h = JSON.stringify(store.history());
    assert.deepStrictEqual(store.update(function () {}), {ok: true, changed: false});
    assert.strictEqual(JSON.stringify(store.history()), h);
    // bounded: limit 3 keeps the last three steps
    for (i = 0; i < 6; i++) add(store, 'n' + i);
    assert.strictEqual(store.history().undo.length, 3);
    store.undo(); store.undo(); store.undo();
    assert.strictEqual(store.undo().ok, false);
    assert.strictEqual(store.get().notes.length, 5);
    // limit 0 keeps no history
    var none = make(Lib, envFor(null, clock), {historyLimit: 0});
    add(none, 'x');
    assert.strictEqual(none.canUndo(), false);
  });

  test('undo_and_redo_across_an_import', async function () {
    var clock = fakeClock(), store = make(Lib, envFor(null, clock));
    add(store, 'mine');
    var mine = JSON.stringify(store.get());
    var r = await store.importText(envelope());
    assert.strictEqual(r.ok, true);
    assert.strictEqual(store.get().notes[0].text, 'from a file');
    add(store, 'after import');
    store.undo();
    assert.deepStrictEqual(store.undo(), {ok: true, label: 'Import'});
    assert.strictEqual(JSON.stringify(store.get()), mine);
    store.redo();
    assert.strictEqual(store.get().notes[0].text, 'from a file');
    store.redo();
    assert.strictEqual(store.get().notes[1].text, 'after import');
  });

  test('update_refused_by_validator_or_throwing_fn_changes_nothing', async function () {
    var clock = fakeClock(), profile = fakeProfile(), store = make(Lib, envFor(profile.tab(), clock));
    add(store, 'a'); await store.flush();
    var before = snapshot(store, profile), r;
    r = store.update(function (d) { d.notes[0].text = ''; });
    assert.strictEqual(r.ok, false); assert.strictEqual(r.reason, 'invalid');
    assert.deepStrictEqual(r.problems, ['note 0 has no text']);
    r = store.update(function (d) { d.notes.push({id: 2, text: 'half'}); throw new Error('stopped half way'); });
    assert.strictEqual(r.reason, 'threw');
    r = store.update(function (d) { d.notes[0].when = new Date(0); });
    assert.strictEqual(r.reason, 'not_json', r.message);
    r = store.update(function (d) { d.nextId = NaN; });
    assert.strictEqual(r.reason, 'not_json', r.message);
    r = store.update(function (d) { d.nextId = Infinity; });
    assert.strictEqual(r.reason, 'not_json', r.message);
    r = store.update(function (d) { d.loop = d; });
    assert.strictEqual(r.ok, false, 'a value that contains itself was accepted');
    r = store.update('not a function');
    assert.strictEqual(r.reason, 'bad_call');
    clock.advance(5000); await store.flush();
    assertUntouched(store, before, profile, 'refused updates');
    // the valid neighbour
    r = store.update(function (d) { d.notes[0].text = 'b'; });
    assert.deepStrictEqual(r, {ok: true, changed: true});
  });

  test('state_snapshot_is_frozen', async function () {
    var clock = fakeClock(), store = make(Lib, envFor(null, clock));
    add(store, 'a');
    var s = store.get();
    assert.throws(function () { s.notes.push({id: 9, text: 'sneak', done: false}); }, TypeError);
    assert.throws(function () { s.notes[0].text = 'edited in place'; }, TypeError);
    assert.strictEqual(store.get().notes.length, 1);
    assert.strictEqual(store.get().notes[0].text, 'a');
  });

  test('storage_read_throw_does_not_break_the_store', async function () {
    var clock = fakeClock(), profile = fakeProfile();
    var first = make(Lib, envFor(profile.tab(), clock));
    add(first, 'saved earlier'); await first.flush();
    profile.failRead = true;
    var store;
    assert.doesNotThrow(function () { store = make(Lib, envFor(profile.tab(), clock)); });
    var report = await store.ready;
    assert.strictEqual(report.restored, false);
    assert.deepStrictEqual(add(store, 'still works'), {ok: true, changed: true});
    assert.doesNotThrow(function () { clock.advance(1000); });
    var p = await store.flush();
    assert.ok(typeof p.text === 'string' && p.text.length > 0);
    assert.strictEqual(store.get().notes[0].text, 'still works');
  });

  test('storage_write_throw_degrades_to_memory_and_says_so', async function () {
    var clock = fakeClock(), profile = fakeProfile(), store = make(Lib, envFor(profile.tab(), clock)), events = [];
    store.subscribe(function (e) { if (e.type === 'persistence') events.push(e); });
    assert.strictEqual(store.persistence().mode, 'local');
    assert.strictEqual(store.persistence().text, 'Saved in this browser');
    add(store, 'a');
    clock.advance(1000);
    assert.strictEqual(store.persistence().savedAt, '2026-10-09T02:00:00.400Z');
    profile.failWrite = true;
    assert.deepStrictEqual(add(store, 'b'), {ok: true, changed: true});
    assert.doesNotThrow(function () { clock.advance(1000); }, 'the storage exception escaped from the autosave timer');
    var p = store.persistence();
    assert.strictEqual(p.mode, 'memory', 'still claims ' + p.mode + ' after a write was refused');
    assert.strictEqual(p.durable, false);
    assert.strictEqual(p.text, 'Not saved: the browser refused to store the data. Export to keep your work');
    assert.strictEqual(p.savedAt, '2026-10-09T02:00:00.400Z', 'the saved time must stay at the last real save');
    assert.strictEqual(events.length, 1);
    assert.strictEqual(events[0].degraded, true);
    assert.strictEqual(store.get().notes.length, 2);
    assert.ok(JSON.parse(store.exportEnvelope().text).data.notes.length === 2, 'export must still work');
    // storage comes back: the next save recovers and says so
    profile.failWrite = false;
    add(store, 'c'); clock.advance(1000);
    assert.strictEqual(store.persistence().mode, 'local');
    assert.strictEqual(events.length, 2);
    assert.strictEqual(events[1].recovered, true);
    assert.strictEqual(JSON.parse(profile.map['pocket:notes:notes@1']).data.notes.length, 3);
  });

  test('storage_quota_degrades_then_recovers_when_data_shrinks', async function () {
    var clock = fakeClock(), profile = fakeProfile(), store = make(Lib, envFor(profile.tab(), clock)), events = [];
    store.subscribe(function (e) { if (e.type === 'persistence') events.push(e); });
    add(store, 'small'); clock.advance(1000);
    var storedSmall = profile.map['pocket:notes:notes@1'];
    profile.quotaChars = storedSmall.length + 20;
    add(store, 'this note is long enough to push the saved text past the quota set above');
    assert.doesNotThrow(function () { clock.advance(1000); });
    assert.strictEqual(store.persistence().mode, 'memory');
    assert.strictEqual(store.persistence().text, 'Not saved: the browser\'s storage is full. Export to keep your work');
    assert.strictEqual(store.persistence().reason, 'the browser\'s storage is full');
    assert.strictEqual(profile.map['pocket:notes:notes@1'], storedSmall, 'the last good copy must still be in storage');
    assert.strictEqual(events.length, 1);
    store.undo(); clock.advance(1000);
    assert.strictEqual(store.persistence().mode, 'local', 'saving should resume once the data fits again');
    assert.strictEqual(store.persistence().reason, null);
    assert.strictEqual(events.length, 2);
  });

  test('storage_access_itself_throwing_is_survived', async function () {
    var clock = fakeClock(), hostile = {};
    Object.defineProperty(hostile, 'localStorage', {get: function () { throw named('SecurityError', 18); }});
    Object.defineProperty(hostile, 'storage', {get: function () { throw named('SecurityError', 18); }});
    hostile.addEventListener = function () { throw named('SecurityError', 18); };
    var store;
    assert.doesNotThrow(function () { store = make(Lib, {root: hostile, setTimeout: clock.setTimeout, clearTimeout: clock.clearTimeout, now: clock.now}); });
    assert.strictEqual(store.persistence().mode, 'memory');
    assert.strictEqual(store.persistence().text, 'Not saved: this page cannot store data here. Export to keep your work');
    add(store, 'a'); clock.advance(1000);
    assert.strictEqual(store.persistence().savedAt, null, 'memory must not report a saved time');
    assert.strictEqual(JSON.parse(store.exportEnvelope().text).data.notes[0].text, 'a');
    // a storage whose setItem always throws (the probe fails) is the same case
    var profile = fakeProfile(); profile.failWrite = true;
    var blocked = make(Lib, envFor(profile.tab(), clock));
    assert.strictEqual(blocked.persistence().mode, 'memory');
  });

  test('host_storage_is_preferred_when_present', async function () {
    var clock = fakeClock(), profile = fakeProfile(), host = fakeHost({objects: true});
    var store = make(Lib, envFor(profile.tab(), clock, host));
    assert.strictEqual(store.persistence().state, 'loading');
    assert.strictEqual(store.persistence().text, 'Opening saved data');
    var report = await store.ready;
    assert.strictEqual(report.mode, 'host');
    assert.strictEqual(host.gets, 1, 'opening should ask the host for the saved copy once, and asked ' + host.gets + ' times');
    assert.strictEqual(store.persistence().text, 'Saved in this app\'s storage');
    add(store, 'in the host'); await store.flush();
    assert.ok(host.map['pocket:notes:notes@1'], 'nothing reached the host');
    assert.strictEqual(profile.map['pocket:notes:notes@1'], undefined, 'localStorage was written although the host works');
    // reopen: the host copy comes back (the host answers with {key, value} objects here)
    var again = make(Lib, envFor(profile.tab(), clock, host));
    var before = host.gets;
    report = await again.ready;
    assert.strictEqual(report.restored, true);
    assert.strictEqual(host.gets - before, 0, 'the saved copy was already asked for when the store was made');
    assert.strictEqual(again.get().notes[0].text, 'in the host');
  });

  test('host_storage_failing_falls_back_to_local', async function () {
    var clock = fakeClock(), profile = fakeProfile(), host = fakeHost(), events = [];
    var store = make(Lib, envFor(profile.tab(), clock, host));
    store.subscribe(function (e) { if (e.type === 'persistence') events.push(e); });
    await store.ready;
    add(store, 'a'); await store.flush();
    host.failSet = true;
    add(store, 'b'); await store.flush();
    assert.strictEqual(store.persistence().mode, 'local');
    assert.strictEqual(store.persistence().text, 'Saved in this browser');
    assert.strictEqual(JSON.parse(profile.map['pocket:notes:notes@1']).data.notes.length, 2);
    assert.strictEqual(events.filter(function (e) { return e.degraded; }).length, 1);
    // a host that refuses the very first write is skipped from the start
    var dead = fakeHost(); dead.failSet = true;
    var other = make(Lib, envFor(fakeProfile().tab(), clock, dead));
    var report = await other.ready;
    assert.strictEqual(report.mode, 'local');
  });

  test('host_get_rejecting_for_a_missing_key_is_not_fatal', async function () {
    var clock = fakeClock(), host = fakeHost({rejectMissing: true});
    var store = make(Lib, envFor(null, clock, host));
    var report = await store.ready;
    assert.strictEqual(report.mode, 'host');
    assert.strictEqual(report.restored, false);
    add(store, 'first'); await store.flush();
    assert.strictEqual(JSON.parse(host.map['pocket:notes:notes@1']).data.notes[0].text, 'first');
  });

  test('host_that_never_answers_times_out', async function () {
    var clock = fakeClock(), profile = fakeProfile(), host = fakeHost({never: true});
    var store = make(Lib, envFor(profile.tab(), clock, host), {hostTimeoutMs: 4000});
    assert.strictEqual(store.persistence().state, 'loading');
    add(store, 'typed while waiting');
    clock.advance(4000);            // the read gives up
    await Promise.resolve(); await Promise.resolve();
    clock.advance(4000);            // the probe gives up
    var report = await store.ready;
    assert.strictEqual(report.mode, 'local');
    assert.strictEqual(store.get().notes[0].text, 'typed while waiting');
    clock.advance(1000);
    assert.strictEqual(JSON.parse(profile.map['pocket:notes:notes@1']).data.notes[0].text, 'typed while waiting');
  });

  test('change_made_while_host_is_still_loading_is_not_lost', async function () {
    var clock = fakeClock(), host = fakeHost();
    host.map['pocket:notes:notes@1'] = envelope();
    var store = make(Lib, envFor(null, clock, host));
    add(store, 'typed before the host answered');
    var report = await store.ready;
    assert.strictEqual(report.held, true);
    assert.strictEqual(store.persistence().state, 'conflict');
    assert.strictEqual(store.get().notes[0].text, 'typed before the host answered');
    assert.strictEqual(JSON.parse(host.map['pocket:notes:notes@1']).data.notes[0].text, 'from a file', 'the stored copy was overwritten');
    assert.strictEqual(store.resolveConflict('theirs').ok, true);
    assert.strictEqual(store.get().notes[0].text, 'from a file');
    store.undo();
    assert.strictEqual(store.get().notes[0].text, 'typed before the host answered');
  });

  test('autosave_is_debounced_and_flush_saves_now', async function () {
    var clock = fakeClock(), profile = fakeProfile(), store = make(Lib, envFor(profile.tab(), clock), {debounceMs: 400});
    var w0 = profile.writes, saved = [];
    store.subscribe(function (e) { if (e.type === 'saved') saved.push(e.savedAt); });
    add(store, 'a'); clock.advance(399);
    add(store, 'b'); clock.advance(399);
    add(store, 'c');
    assert.strictEqual(profile.writes, w0, 'saved before the pause ended');
    assert.strictEqual(store.persistence().pending, true);
    clock.advance(399);
    assert.strictEqual(profile.writes, w0, 'saved one millisecond early');
    clock.advance(1);
    assert.strictEqual(profile.writes, w0 + 1, 'three quick changes should make one write');
    assert.strictEqual(store.persistence().pending, false);
    assert.deepStrictEqual(saved, ['2026-10-09T02:00:01.198Z']);
    assert.strictEqual(store.persistence().savedAt, '2026-10-09T02:00:01.198Z');
    add(store, 'd');
    var p = await store.flush();
    assert.strictEqual(profile.writes, w0 + 2, 'flush did not save at once');
    assert.strictEqual(p.pending, false);
    assert.strictEqual(clock.waiting(), 0, 'flush left a timer behind');
    await store.flush();
    assert.strictEqual(profile.writes, w0 + 2, 'flush with nothing pending wrote again');
  });

  test('leaving_the_page_saves_without_waiting_for_the_pause', async function () {
    var clock = fakeClock(), profile = fakeProfile(), env = envFor(profile.tab(), clock), store = make(Lib, env);
    add(store, 'typed just before closing the tab');
    assert.strictEqual(profile.map['pocket:notes:notes@1'], undefined, 'the pause has not ended, so nothing should be stored yet');
    env.leave();
    assert.strictEqual(JSON.parse(profile.map['pocket:notes:notes@1']).data.notes[0].text, 'typed just before closing the tab');
    var w = profile.writes;
    env.leave();
    assert.strictEqual(profile.writes, w, 'leaving with nothing pending wrote again');
    // the real hooks: pagehide on the window, and visibilitychange on the document when it is hidden
    var handlers = {}, doc = {visibilityState: 'visible', addEventListener: function (n, f) { handlers['doc:' + n] = f; }, removeEventListener: function () {}};
    var win = {document: doc, localStorage: profile.tab(), addEventListener: function (n, f) { handlers[n] = f; }, removeEventListener: function () {}};
    var p2 = fakeProfile(); win.localStorage = p2.tab();
    var real = make(Lib, {root: win, setTimeout: clock.setTimeout, clearTimeout: clock.clearTimeout, now: clock.now});
    add(real, 'one');
    handlers['doc:visibilitychange']();
    assert.strictEqual(p2.map['pocket:notes:notes@1'], undefined, 'saved although the page is still visible');
    doc.visibilityState = 'hidden'; handlers['doc:visibilitychange']();
    assert.strictEqual(JSON.parse(p2.map['pocket:notes:notes@1']).data.notes.length, 1);
    add(real, 'two'); handlers.pagehide();
    assert.strictEqual(JSON.parse(p2.map['pocket:notes:notes@1']).data.notes.length, 2);
    assert.strictEqual(typeof handlers.storage, 'function', 'the storage event was not listened for');
  });

  test('reload_restores_saved_state', async function () {
    var clock = fakeClock(), profile = fakeProfile(), first = make(Lib, envFor(profile.tab(), clock));
    add(first, 'kept'); add(first, 'also kept'); await first.flush();
    first.destroy();
    var second = make(Lib, envFor(profile.tab(), clock));
    assert.strictEqual(second.get().notes.length, 2, 'state must be there as soon as create returns when storage answers at once');
    var report = await second.ready;
    assert.deepStrictEqual({mode: report.mode, restored: report.restored, held: report.held}, {mode: 'local', restored: true, held: false});
    assert.strictEqual(second.canUndo(), false, 'opening saved data is not an undo step');
    assert.strictEqual(second.persistence().savedAt, first.persistence().savedAt);
  });

  test('stored_older_schema_is_migrated_on_load_and_original_kept', async function () {
    var clock = fakeClock(), profile = fakeProfile();
    var old = JSON.stringify({app: 'notes', schema: 1, content_id: 'notes@1', saved_at: '2025-01-01T00:00:00.000Z', data: {notes: ['from schema one']}});
    profile.map['pocket:notes:notes@1'] = old;
    var store = make(Lib, envFor(profile.tab(), clock));
    var report = await store.ready;
    assert.strictEqual(report.migratedFrom, 1);
    assert.deepStrictEqual(JSON.parse(JSON.stringify(store.get())), {notes: [{id: 1, text: 'from schema one', done: false}], nextId: 2});
    assert.strictEqual(profile.map[report.backupKey], old, 'the copy from before the migration was not kept');
    clock.advance(1000);
    assert.strictEqual(JSON.parse(profile.map['pocket:notes:notes@1']).schema, 3);
  });

  test('stored_copy_from_a_newer_schema_is_never_overwritten', async function () {
    var clock = fakeClock(), profile = fakeProfile();
    var newer = envelope({schema: 4, data: {notes: [], nextId: 1, extra: 'from the future'}});
    profile.map['pocket:notes:notes@1'] = newer;
    var store = make(Lib, envFor(profile.tab(), clock));
    var report = await store.ready;
    assert.strictEqual(report.held, true);
    assert.strictEqual(store.persistence().state, 'recovery');
    assert.ok(/^Not saving/.test(store.persistence().text));
    assert.strictEqual(store.recovery().reason, 'newer_schema');
    assert.strictEqual(store.recovery().text, newer);
    add(store, 'work done anyway'); clock.advance(5000); await store.flush();
    assert.strictEqual(profile.map['pocket:notes:notes@1'], newer, 'an unreadable stored copy was overwritten');
    assert.strictEqual(store.discardStored().ok, true);
    assert.strictEqual(JSON.parse(profile.map['pocket:notes:notes@1']).data.notes[0].text, 'work done anyway');
    assert.strictEqual(store.persistence().state, 'ok');
    // garbage in storage is held the same way
    var p2 = fakeProfile(); p2.map['pocket:notes:notes@1'] = '{half a file';
    var s2 = make(Lib, envFor(p2.tab(), clock));
    assert.strictEqual(s2.recovery().reason, 'not_json');
    add(s2, 'x'); clock.advance(5000);
    assert.strictEqual(p2.map['pocket:notes:notes@1'], '{half a file');
  });

  test('two_tabs_conflict_is_surfaced_and_not_overwritten', async function () {
    var clock = fakeClock(), profile = fakeProfile();
    var a = make(Lib, envFor(profile.tab(), clock)), b = make(Lib, envFor(profile.tab(), clock)), seen = [];
    b.subscribe(function (e) { if (e.type === 'external') seen.push(e); });
    add(a, 'written in tab A'); clock.advance(1000);
    assert.strictEqual(seen.length, 1, 'tab B was not told');
    assert.strictEqual(b.persistence().state, 'conflict');
    assert.strictEqual(b.persistence().text, 'Not saving: another tab changed this data. Choose which copy to keep');
    assert.strictEqual(b.conflict().savedAt, '2026-10-09T02:00:00.400Z');
    assert.strictEqual(b.conflict().readable, true);
    add(b, 'written in tab B'); clock.advance(5000); await b.flush();
    assert.strictEqual(JSON.parse(profile.map['pocket:notes:notes@1']).data.notes[0].text, 'written in tab A', 'tab B overwrote tab A');
    assert.strictEqual(b.get().notes[0].text, 'written in tab B', 'tab B lost its own change');
    // tab A saves again while B is still waiting: B's held copy is the newest one
    add(a, 'second note from A'); clock.advance(1000);
    assert.strictEqual(seen.length, 2);
    assert.strictEqual(b.resolveConflict('theirs').ok, true);
    assert.deepStrictEqual(b.get().notes.map(function (n) { return n.text; }), ['written in tab A', 'second note from A']);
  });

  test('two_tabs_conflict_is_caught_at_write_time_without_an_event', async function () {
    var clock = fakeClock(), profile = fakeProfile();
    var a = make(Lib, envFor(profile.tab({events: false}), clock)), b = make(Lib, envFor(profile.tab({events: false}), clock));
    add(a, 'written in tab A'); await a.flush();
    assert.strictEqual(b.persistence().state, 'ok', 'no event was delivered, so B cannot know yet');
    add(b, 'written in tab B'); await b.flush();
    assert.strictEqual(b.persistence().state, 'conflict', 'B saved over A without noticing');
    assert.strictEqual(JSON.parse(profile.map['pocket:notes:notes@1']).data.notes[0].text, 'written in tab A', 'tab B overwrote tab A');
    // two tabs that hold the same data are not in conflict
    var p2 = fakeProfile(), c = make(Lib, envFor(p2.tab({events: false}), clock)), d = make(Lib, envFor(p2.tab({events: false}), clock));
    add(c, 'same'); await c.flush();
    add(d, 'same'); await d.flush();
    assert.strictEqual(d.persistence().state, 'ok');
  });

  test('conflict_can_be_settled_either_way', async function () {
    var clock = fakeClock(), profile = fakeProfile();
    var a = make(Lib, envFor(profile.tab(), clock)), b = make(Lib, envFor(profile.tab(), clock));
    add(b, 'B draft');                       // not yet saved
    add(a, 'A saved'); await a.flush();
    assert.strictEqual(b.persistence().state, 'conflict');
    assert.strictEqual(b.resolveConflict('neither').ok, false);
    assert.strictEqual(b.resolveConflict('theirs').ok, true);
    assert.strictEqual(b.get().notes[0].text, 'A saved');
    assert.strictEqual(b.persistence().state, 'ok');
    clock.advance(5000);
    assert.strictEqual(a.persistence().state, 'ok', 'settling in B must not raise a conflict back in A');
    b.undo();
    assert.strictEqual(b.get().notes[0].text, 'B draft', 'taking the other copy must be undoable');
    // keep mine
    var p2 = fakeProfile(), c = make(Lib, envFor(p2.tab(), clock)), d = make(Lib, envFor(p2.tab(), clock));
    add(d, 'D draft');
    add(c, 'C saved'); await c.flush();
    assert.strictEqual(d.resolveConflict('mine').ok, true);
    assert.strictEqual(JSON.parse(p2.map['pocket:notes:notes@1']).data.notes[0].text, 'D draft');
    assert.strictEqual(d.resolveConflict('mine').ok, false, 'there is no conflict left to settle');
  });

  test('adopt_policy_takes_changes_from_another_tab', async function () {
    var clock = fakeClock(), profile = fakeProfile();
    var a = make(Lib, envFor(profile.tab(), clock), {externalPolicy: 'adopt'}), b = make(Lib, envFor(profile.tab(), clock), {externalPolicy: 'adopt'});
    add(a, 'theme: dark'); await a.flush();
    assert.strictEqual(b.persistence().state, 'ok');
    assert.strictEqual(b.get().notes[0].text, 'theme: dark');
    var w = profile.writes; clock.advance(5000);
    assert.strictEqual(profile.writes, w, 'adopting a change must not write it back');
  });

  test('size_report_and_warning_threshold', async function () {
    var clock = fakeClock(), store = make(Lib, envFor(null, clock));
    add(store, 'abc');
    var bytes = store.size().bytes;
    assert.strictEqual(bytes, store.exportEnvelope().bytes);
    var at = make(Lib, envFor(null, clock), {warnBytes: bytes});
    add(at, 'abc');
    assert.strictEqual(at.size().over, false, 'exactly at the level is not over it');
    var under = make(Lib, envFor(null, clock), {warnBytes: bytes - 1});
    add(under, 'abc');
    assert.strictEqual(under.size().over, true, 'one byte above the level must warn');
    assert.ok(under.size().text.indexOf(String(bytes)) >= 0 && under.size().text.indexOf(String(bytes - 1)) >= 0, under.size().text);
  });

  test('utf8_bytes_counts_multibyte_text', async function () {
    var eAcute = String.fromCharCode(0xE9), euro = String.fromCharCode(0x20AC), emoji = String.fromCharCode(0xD83D, 0xDE00);
    [['plain', 5], ['caf' + eAcute, 5], [euro, 3], [emoji, 4], ['a' + emoji + euro + eAcute, 10], ['', 0]].forEach(function (c) {
      assert.strictEqual(Lib.utf8Bytes(c[0]), c[1]);
      assert.strictEqual(Lib.utf8Bytes(c[0]), Buffer.byteLength(c[0], 'utf8'));
    });
  });

  test('large_state_5000_items_round_trip', async function () {
    var clock = fakeClock(), profile = fakeProfile(), store = make(Lib, envFor(profile.tab(), clock)), i, t, ms = {};
    t = process.hrtime.bigint();
    store.update(function (d) {
      for (i = 0; i < 5000; i++) d.notes.push({id: d.nextId++, text: 'Note number ' + i + ' with a realistic amount of text in it, about one sentence long.', done: i % 3 === 0});
    }, {label: 'Add 5000'});
    ms.build = Number(process.hrtime.bigint() - t) / 1e6;
    t = process.hrtime.bigint();
    store.update(function (d) { d.notes[2500].done = !d.notes[2500].done; });
    ms.update = Number(process.hrtime.bigint() - t) / 1e6;
    t = process.hrtime.bigint();
    await store.flush();
    ms.save = Number(process.hrtime.bigint() - t) / 1e6;
    t = process.hrtime.bigint();
    var ex = store.exportEnvelope();
    ms.exportMs = Number(process.hrtime.bigint() - t) / 1e6;
    var other = make(Lib, envFor(null, clock));
    t = process.hrtime.bigint();
    var r = await other.importText(ex.text);
    ms.importMs = Number(process.hrtime.bigint() - t) / 1e6;
    assert.strictEqual(r.ok, true);
    assert.strictEqual(other.get().notes.length, 5000);
    assert.strictEqual(JSON.stringify(other.get()), JSON.stringify(store.get()));
    t = process.hrtime.bigint();
    store.undo();
    ms.undo = Number(process.hrtime.bigint() - t) / 1e6;
    assert.strictEqual(store.get().notes[2500].done, false);
    [ms.update, ms.save, ms.exportMs, ms.importMs].forEach(function (v) { assert.ok(v < 2000, 'an operation on 5,000 items took ' + v.toFixed(0) + ' ms'); });
    notes.push('large state: 5,000 items, ' + ex.bytes + ' bytes. one update ' + ms.update.toFixed(1) + ' ms, save ' + ms.save.toFixed(1) + ' ms, export ' +
      ms.exportMs.toFixed(1) + ' ms, import with validation ' + ms.importMs.toFixed(1) + ' ms, undo ' + ms.undo.toFixed(2) + ' ms (this machine, Node ' + process.version + ')');
  });

  test('listener_that_throws_does_not_break_updates', async function () {
    var clock = fakeClock(), store = make(Lib, envFor(null, clock)), calls = 0;
    store.subscribe(function () { throw new Error('page bug'); });
    store.subscribe(function () { calls++; });
    var off = store.subscribe(function () { calls += 100; });
    off();
    assert.deepStrictEqual(add(store, 'a'), {ok: true, changed: true});
    assert.strictEqual(calls, 1);
    assert.doesNotThrow(function () { clock.advance(1000); });
  });

  test('garbage_arguments_never_throw', async function () {
    var clock = fakeClock(), store = make(Lib, envFor(null, clock)), junk = [undefined, null, 0, NaN, '', 'x', [], {}, function () { throw new Error('x'); }], i, r;
    for (i = 0; i < junk.length; i++) {
      assert.doesNotThrow(function () {
        store.update(junk[i]); store.update(junk[i], junk[i]); store.inspect(junk[i]); store.resolveConflict(junk[i]);
        store.subscribe(junk[i])(); store.reset(junk[i]); store.undo(); store.redo(); store.discardStored();
      }, 'junk ' + i);
      r = await store.importText(junk[i], junk[i]);
      assert.strictEqual(r.ok, false);
    }
    assert.strictEqual(typeof (await store.flush()).text, 'string');
  });

  test('create_rejects_bad_configuration', async function () {
    var clock = fakeClock(), env = envFor(null, clock);
    function bad(over, why) {
      assert.throws(function () { make(Lib, env, over); }, /PocketState\.create/, why);
    }
    bad({app: ''}, 'empty app'); bad({app: 5}, 'numeric app');
    bad({schema: '3'}, 'schema as text'); bad({schema: 0}, 'schema 0'); bad({schema: 2.5}, 'schema 2.5');
    bad({contentId: ''}, 'empty content id');
    bad({initial: {notes: 'x'}}, 'initial fails validate');
    bad({migrations: {3: function (d) { return d; }}}, 'a step at the current schema');
    bad({migrations: {1: 'not a function'}}, 'a step that is not a function');
    bad({validate: 'yes'}, 'validate not a function');
    bad({historyLimit: -1}, 'negative history'); bad({debounceMs: 1.5}, 'fractional debounce'); bad({warnBytes: 0}, 'zero warn level');
    bad({externalPolicy: 'merge'}, 'unknown policy');
    assert.doesNotThrow(function () { make(Lib, env, {schema: 3, historyLimit: 0, debounceMs: 0, warnBytes: 1, migrations: {1: MIGRATIONS[1], 2: MIGRATIONS[2]}}); });
  });

  test('reset_returns_to_initial_and_can_be_undone', async function () {
    var clock = fakeClock(), store = make(Lib, envFor(null, clock));
    add(store, 'a'); add(store, 'b');
    assert.strictEqual(store.isInitial(), false);
    assert.deepStrictEqual(store.reset(), {ok: true, changed: true});
    assert.strictEqual(store.isInitial(), true);
    assert.deepStrictEqual(JSON.parse(JSON.stringify(store.get())), {notes: [], nextId: 1});
    assert.deepStrictEqual(store.reset(), {ok: true, changed: false});
    assert.deepStrictEqual(store.undo(), {ok: true, label: 'Reset'});
    assert.strictEqual(store.get().notes.length, 2);
  });

  // Only the released files beside this test are held to the record. A copy named with --lib is
  // another file on purpose.
  if (path.resolve(args.lib) === path.join(__dirname, 'pocket-state.js')) {
    test('released_files_match_the_recorded_hashes', async function () {
      var record = {}, lines, text;
      try { text = fs.readFileSync(path.join(__dirname, HASH_FILE), 'utf8'); }
      catch (e) { assert.fail(HASH_FILE + ' is missing beside this test'); }
      lines = text.split('\n').filter(function (l) { return l !== ''; });
      lines.forEach(function (l) {
        var m = /^([0-9a-f]{64})  ([A-Za-z0-9._-]+)$/.exec(l);
        assert.ok(m, HASH_FILE + ' has a line that is not "HASH  NAME": ' + l.slice(0, 80));
        assert.ok(!(m[2] in record), HASH_FILE + ' names ' + m[2] + ' twice');
        record[m[2]] = m[1];
      });
      assert.deepStrictEqual(Object.keys(record).sort(), RELEASED.slice().sort(), HASH_FILE + ' must name exactly ' + RELEASED.join(' and '));
      RELEASED.forEach(function (name) {
        var got = crypto.createHash('sha256').update(fs.readFileSync(path.join(__dirname, name))).digest('hex');
        assert.strictEqual(got, record[name], name + ' is not the file the record describes. If the change is deliberate, rewrite ' + HASH_FILE +
          ' and update every tool that carries a copy');
      });
      notes.push('released files: pocket-state.js sha256 ' + record['pocket-state.js'].slice(0, 16) + ', pocket-ui.js sha256 ' + record['pocket-ui.js'].slice(0, 16) + ' (first 16 characters), as recorded in ' + HASH_FILE);
    });
  }
}

// ---------- planted failures ----------
// Each entry breaks the library in one deliberate way and names the tests that must then fail.
var PLANTED = [
  {
    id: 'a', what: 'a failed import partially applies (the first field of the file is written into the state before the data is validated)',
    caughtBy: ['import_refusals_leave_state_identical', 'migration_producing_invalid_data_is_refused_state_intact'],
    edits: [['      problems = problemsOf(cfg.validate, data);\n      if (problems.length) {\n        if (steps.length) {',
      '      (function () { var k0 = Object.keys(Object(data))[0], half = JSON.parse(stateText); if (k0 !== undefined) { half[k0] = data[k0]; state = half; stateText = JSON.stringify(half); } })();\n' +
      '      problems = problemsOf(cfg.validate, data);\n      if (problems.length) {\n        if (steps.length) {']]
  },
  {
    id: 'b', what: 'migration steps run out of order (highest step first)',
    caughtBy: ['migration_chain_1_to_3_runs_in_order'],
    edits: [['      for (v = from; v < cfg.schema; v++) {', '      for (v = cfg.schema - 1; v >= from; v--) {']]
  },
  {
    id: 'c', what: 'a storage exception escapes (the try and catch around the localStorage write and around the save are removed)',
    caughtBy: ['storage_write_throw_degrades_to_memory_and_says_so'],
    edits: [
      ['        try { ls.setItem(key, text); return {ok: true}; } catch (e) { return {ok: false, error: e}; }', '        ls.setItem(key, text); return {ok: true};'],
      ['      try { out = attempt(0, envelopeText(at), at, null); } catch (e) { out = null; }', '      out = attempt(0, envelopeText(at), at, null);']
    ]
  },
  {
    id: 'd', what: 'a second tab silently overwrites the first (the check before each write is removed)',
    caughtBy: ['two_tabs_conflict_is_caught_at_write_time_without_an_event'],
    edits: [['          else { pending = true; raiseConflict(r.value, layer.name); return null; }', '          else { seen[layer.name] = r.value; }']]
  },
  {
    id: 'e', what: 'a released file differs from the record (one comment line added to a copy of pocket-ui.js, in a copy of this folder)',
    caughtBy: ['released_files_match_the_recorded_hashes'],
    release: {file: 'pocket-ui.js', append: '// drift\n'}
  }
];

function runPlanted() {
  var source, dir, failures = 0, lines = [];
  try { source = fs.readFileSync(args.lib, 'utf8'); } catch (e) { process.stderr.write('test_pocket_state: cannot read ' + args.lib + '\n'); process.exit(2); }
  dir = fs.mkdtempSync(path.join(os.tmpdir(), 'pocket-planted-'));
  PLANTED.forEach(function (p) {
    var text = source, file = path.join(dir, 'pocket-state-planted-' + p.id + '.js'), out, res, failed, missed, copy;
    if (p.release) {
      // A copy of the released folder with one file altered, tested by a copy of this test.
      copy = path.join(dir, 'release-' + p.id);
      fs.mkdirSync(copy);
      RELEASED.concat([HASH_FILE, path.basename(__filename)]).forEach(function (name) {
        fs.copyFileSync(path.join(__dirname, name), path.join(copy, name));
      });
      fs.appendFileSync(path.join(copy, p.release.file), p.release.append);
      out = childProcess.spawnSync(process.execPath, [path.join(copy, path.basename(__filename)), '--json'], {encoding: 'utf8'});
    } else {
      p.edits.forEach(function (e) {
        if (text.split(e[0]).length !== 2) { process.stderr.write('test_pocket_state: planted failure ' + p.id + ' no longer matches the library source; update PLANTED\n'); process.exit(2); }
        text = text.replace(e[0], function () { return e[1]; });
      });
      fs.writeFileSync(file, text);
      out = childProcess.spawnSync(process.execPath, [__filename, '--lib', file, '--json'], {encoding: 'utf8'});
    }
    try { res = JSON.parse(out.stdout); } catch (e) { res = null; }
    if (!res) { failures++; lines.push('PLANTED ' + p.id + ': NOT CAUGHT, the test run gave no result (' + String(out.stderr).slice(0, 120) + ')'); return; }
    failed = res.results.filter(function (r) { return !r.ok; }).map(function (r) { return r.name; });
    missed = p.caughtBy.filter(function (n) { return failed.indexOf(n) < 0; });
    if (missed.length) { failures++; lines.push('PLANTED ' + p.id + ': NOT CAUGHT by ' + missed.join(', ') + '. ' + p.what); }
    else {
      lines.push('PLANTED ' + p.id + ': caught. ' + p.what);
      p.caughtBy.forEach(function (n) {
        var hit = res.results.filter(function (r) { return r.name === n; })[0];
        lines.push('    ' + n + ' FAILED: ' + String(hit.error).split('\n')[0].slice(0, 150));
      });
      lines.push('    tests failing against this copy: ' + failed.length + ' of ' + res.results.length);
    }
  });
  try { fs.rmSync(dir, {recursive: true, force: true}); } catch (e) { lines.push('(could not remove ' + dir + ')'); }
  lines.push(failures ? 'RESULT: FAIL. ' + failures + ' planted failure(s) were not caught.' : 'RESULT: PASS. ' + PLANTED.length + ' of ' + PLANTED.length + ' planted failures were caught by their named tests.');
  process.stdout.write(lines.join('\n') + '\n');
  process.exit(failures ? 1 : 0);
}

async function runAll() {
  var Lib, results = [], i, t, started, failed;
  try { Lib = require(path.resolve(args.lib)); } catch (e) { process.stderr.write('test_pocket_state: cannot load ' + args.lib + ' (' + String(e.message).split('\n')[0].slice(0, 100) + ')\n'); process.exit(2); }
  define(Lib);
  var escaped = [];
  process.on('unhandledRejection', function (e) { escaped.push(String((e && e.message) || e)); });
  for (i = 0; i < tests.length; i++) {
    t = tests[i];
    if (args.only && t.name !== args.only) continue;
    started = Date.now();
    try { await t.fn(); results.push({name: t.name, ok: true, ms: Date.now() - started}); }
    catch (e) { results.push({name: t.name, ok: false, ms: Date.now() - started, error: String((e && e.message) || e)}); }
  }
  await new Promise(function (r) { setTimeout(r, 20); });
  results.push({name: 'no_promise_rejection_escaped_during_the_run', ok: escaped.length === 0, ms: 0, error: escaped.length ? escaped.join('; ') : undefined});
  if (args.only && results.length === 1) { process.stderr.write('test_pocket_state: no test is named ' + args.only + '\n'); process.exit(2); }
  failed = results.filter(function (r) { return !r.ok; });
  if (args.json) process.stdout.write(JSON.stringify({lib: args.lib, version: Lib.version, results: results, notes: notes}, null, 1) + '\n');
  else {
    results.forEach(function (r) { process.stdout.write((r.ok ? 'PASS  ' : 'FAIL  ') + r.name + (r.ok ? '' : '\n      ' + String(r.error).split('\n')[0]) + '\n'); });
    notes.forEach(function (n) { process.stdout.write('NOTE  ' + n + '\n'); });
    process.stdout.write('RESULT: ' + (failed.length ? 'FAIL' : 'PASS') + '. ' + (results.length - failed.length) + ' of ' + results.length + ' tests passed against ' + path.basename(args.lib) + ' ' + Lib.version + '.\n');
  }
  process.exit(failed.length ? 1 : 0);
}

if (args.planted) runPlanted(); else runAll();
