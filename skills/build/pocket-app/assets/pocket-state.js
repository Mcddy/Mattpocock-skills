/*
  pocket-state.js, revision 1.0.0

  State for a single-file tool that keeps its data without a server.
  Plain ASCII, no dependencies, no network requests. Paste the whole file into the page inside
  one script tag, before the page's own code. In a page it defines the global PocketState.
  Under Node it is a module: var PocketState = require('./pocket-state.js').

  var store = PocketState.create({
    app: 'reading-log',            stable id of the tool; an import from another app is refused
    schema: 2,                     whole number, starts at 1, goes up by one when the shape changes
    contentId: 'my-books@1',       what this state belongs to, with its version
    initial: {books: []},          a JSON value, or a function returning one
    migrations: {1: function (data) { return dataForSchema2; }},
    validate: function (data) { return []; }      list of problems; empty means the data is fine
  });

  Reading and changing
    store.get()                    the current data, frozen. Never edit it; use update
    store.update(fn, {label})      fn receives a private copy; edit it or return a new value.
                                   Returns {ok, changed} or {ok: false, reason, message, problems}.
                                   A refused update changes nothing. Each change is one undo step
    store.undo() / store.redo()    {ok, label}. store.history() lists the labels
    store.reset({label})           back to the initial data, as one undo step
    store.isInitial()              true while the data is exactly the initial data
    store.subscribe(fn)            fn({type}) on 'change', 'saved', 'persistence', 'external'.
                                   Returns a function that unsubscribes

  Keeping
    store.ready                    a promise for {mode, restored, migratedFrom, held}. It never rejects
    store.persistence()            {mode: 'host' | 'local' | 'memory', durable, state, text, savedAt,
                                   pending, reason}. text is a sentence to show the user. savedAt is
                                   the last time a layer that outlives the page took the data
    store.flush()                  save now; a promise for persistence(). It never rejects.
                                   The store also saves at once when the page is hidden or closed
    store.size()                   {bytes, warnBytes, over, text} for the saved envelope
    Storage is tried in this order: a host object with async get and set (window.storage), then
    localStorage, then memory. Every access is inside try and catch. A layer that fails later is
    left for the next one down, a 'persistence' event says so, and the layer is tried again on
    later saves.

  Export and import
    store.exportEnvelope()         {envelope, text, bytes, filename}
    store.inspect(text)            checks a file without changing anything
    store.importText(text, {onContentMismatch, allowContentMismatch, label})
                                   a promise for {ok: true, ...} or {ok: false, reason, message}.
                                   Order of checks: not empty, parses as JSON, is an envelope, app
                                   matches, schema is a whole number this page can read (older
                                   schemas go through the numbered migration steps in order, newer
                                   ones are refused), the data passes validate, then content_id.
                                   A failed import never changes the state. A good one is an undo step

  Other tabs and unreadable saves
    store.conflict()               set when another tab saved different data. Saving stops until
                                   store.resolveConflict('mine' | 'theirs') is called
    store.recovery()               set when the stored copy could not be read (for example it was
                                   written by a newer schema). It is left untouched and saving
                                   stops until store.discardStored() is called

  The only call that throws is create, and only for a mistake in its own arguments. Everything
  else returns a result object.
*/
(function (root) {
  'use strict';

  var VERSION = '1.0.0';
  var WORDS = {
    host: 'Saved in this app\'s storage',
    local: 'Saved in this browser',
    memory: 'Not saved: this page cannot store data here. Export to keep your work',
    loading: 'Opening saved data',
    conflict: 'Not saving: another tab changed this data. Choose which copy to keep',
    held: 'Not saving: the copy stored here could not be read and has been left as it was. Copy it out, or start fresh'
  };

  // ---------- small helpers ----------
  function msg(e) {
    try { return String((e && e.message) || e); } catch (x) { return 'unknown error'; }
  }
  function isPlain(v) {
    if (v === null || typeof v !== 'object' || Array.isArray(v)) return false;
    var p = Object.getPrototypeOf(v);
    return p === Object.prototype || p === null;
  }
  function whole(n) {
    return typeof n === 'number' && isFinite(n) && Math.floor(n) === n;
  }
  function thenable(v) {
    return !!v && typeof v.then === 'function';
  }
  // Run fn on a value now, or when it arrives if it is a promise. Keeps one code path for
  // storage that answers at once (localStorage, memory) and storage that answers later (a host).
  function when(v, fn) {
    return thenable(v) ? v.then(fn) : fn(v);
  }
  function utf8Bytes(text) {
    var n = 0, i, c;
    for (i = 0; i < text.length; i++) {
      c = text.charCodeAt(i);
      if (c < 0x80) n += 1;
      else if (c < 0x800) n += 2;
      else if (c >= 0xD800 && c <= 0xDBFF && i + 1 < text.length) { n += 4; i++; }
      else n += 3;
    }
    return n;
  }
  // Freeze a JSON value all the way down. Returns false if any part cannot be saved as JSON.
  function seal(value, depth) {
    var t = typeof value, i, keys, ok = true;
    if (value === null || t === 'string' || t === 'boolean') return true;
    if (t === 'number') return isFinite(value);
    if (depth > 100) return false;
    if (Array.isArray(value)) {
      for (i = 0; i < value.length; i++) if (!seal(value[i], depth + 1)) ok = false;
      Object.freeze(value);
      return ok;
    }
    if (isPlain(value)) {
      keys = Object.keys(value);
      for (i = 0; i < keys.length; i++) if (!seal(value[keys[i]], depth + 1)) ok = false;
      Object.freeze(value);
      return ok;
    }
    return false;
  }
  // The slow pass, run only after seal has said no, to name what is wrong and where.
  function unsafeParts(value, path, out, depth) {
    var t = typeof value, i, keys;
    if (out.length >= 5 || value === null || t === 'string' || t === 'boolean') return out;
    if (t === 'number') {
      if (!isFinite(value)) out.push(path + ' is not a finite number');
      return out;
    }
    if (depth > 100) { out.push(path + ' is nested too deeply or contains itself'); return out; }
    if (Array.isArray(value)) {
      for (i = 0; i < value.length; i++) unsafeParts(value[i], path + '[' + i + ']', out, depth + 1);
      return out;
    }
    if (isPlain(value)) {
      keys = Object.keys(value);
      for (i = 0; i < keys.length; i++) unsafeParts(value[keys[i]], path + '.' + keys[i], out, depth + 1);
      return out;
    }
    out.push(path + ' is ' + (t === 'object' ? 'an object that is not plain data' : (t === 'undefined' ? 'undefined' : 'a ' + t)) + ', which cannot be saved as JSON');
    return out;
  }
  function problemsOf(fn, data) {
    var out, i, list = [];
    if (typeof fn !== 'function') return list;
    try { out = fn(data); } catch (e) { return ['the validator threw: ' + msg(e)]; }
    if (!Array.isArray(out)) return ['the validator did not return a list of problems'];
    for (i = 0; i < out.length; i++) list.push(String(out[i]));
    return list;
  }
  function listed(problems) {
    var shown = problems.slice(0, 3).join('; ');
    return problems.length > 3 ? shown + '; and ' + (problems.length - 3) + ' more' : shown;
  }
  function fail(reason, message, extra) {
    var r = {ok: false, reason: reason, message: message}, k;
    if (extra) for (k in extra) if (Object.prototype.hasOwnProperty.call(extra, k)) r[k] = extra[k];
    return r;
  }
  function storageWhy(layerName, error) {
    var name = '', code = 0;
    try { name = String((error && error.name) || ''); code = Number((error && error.code) || 0); } catch (x) { name = ''; }
    if (name === 'QuotaExceededError' || name === 'NS_ERROR_DOM_QUOTA_REACHED' || code === 22 || code === 1014) {
      return layerName === 'host' ? 'this app\'s storage is full' : 'the browser\'s storage is full';
    }
    if (name === 'timeout') return 'this app\'s storage did not answer';
    return layerName === 'host' ? 'this app\'s storage refused the data' : 'the browser refused to store the data';
  }

  // ---------- storage layers ----------
  // Each layer answers {ok, value} to read and {ok, error} to write, and never throws.
  function memoryLayer() {
    var mem = {};
    return {
      name: 'memory',
      read: function (key) { return {ok: true, value: Object.prototype.hasOwnProperty.call(mem, key) ? mem[key] : null}; },
      write: function (key, text) { mem[key] = text; return {ok: true}; }
    };
  }
  function localLayer(ls) {
    return {
      name: 'local',
      read: function (key) {
        try { var v = ls.getItem(key); return {ok: true, value: typeof v === 'string' ? v : null}; } catch (e) { return {ok: false, error: e}; }
      },
      write: function (key, text) {
        try { ls.setItem(key, text); return {ok: true}; } catch (e) { return {ok: false, error: e}; }
      },
      probe: function (key) {
        try { ls.setItem(key, '1'); ls.removeItem(key); return true; } catch (e) { return false; }
      }
    };
  }
  function hostLayer(h, env, timeoutMs) {
    // Wrap a call that may throw, reject or never answer into a promise that always resolves.
    function settle(call) {
      return new Promise(function (resolve) {
        var done = false, timer = null;
        function finish(r) {
          if (done) return;
          done = true;
          if (timer !== null) { try { env.clearTimeout(timer); } catch (x) { timer = null; } }
          resolve(r);
        }
        try {
          timer = env.setTimeout(function () { finish({ok: false, error: {name: 'timeout'}}); }, timeoutMs);
          Promise.resolve(call()).then(function (v) { finish({ok: true, value: v}); }, function (e) { finish({ok: false, error: e}); });
        } catch (e) {
          finish({ok: false, error: e});
        }
      });
    }
    function textOf(v) {
      if (typeof v === 'string') return v;
      if (v && typeof v === 'object' && typeof v.value === 'string') return v.value;
      return null;
    }
    return {
      name: 'host',
      read: function (key) {
        return settle(function () { return h.get(key); }).then(function (r) {
          return r.ok ? {ok: true, value: textOf(r.value)} : {ok: false, error: r.error};
        });
      },
      write: function (key, text) {
        return settle(function () { return h.set(key, text); }).then(function (r) {
          return r.ok ? {ok: true} : {ok: false, error: r.error};
        });
      },
      probe: function (key) {
        return settle(function () { return h.set(key, '1'); }).then(function (r) {
          if (r.ok && typeof h.delete === 'function') settle(function () { return h.delete(key); });
          return r.ok;
        });
      }
    };
  }
  function resolveEnv(e) {
    e = e || {};
    var r = Object.prototype.hasOwnProperty.call(e, 'root') ? e.root : root;
    return {
      host: function () {
        try {
          var h = Object.prototype.hasOwnProperty.call(e, 'host') ? e.host : (r && r.storage);
          return (h && typeof h.get === 'function' && typeof h.set === 'function') ? h : null;
        } catch (x) { return null; }
      },
      local: function () {
        try {
          var ls = Object.prototype.hasOwnProperty.call(e, 'local') ? e.local : (r && r.localStorage);
          return (ls && typeof ls.getItem === 'function' && typeof ls.setItem === 'function') ? ls : null;
        } catch (x) { return null; }
      },
      setTimeout: function (fn, ms) { return (e.setTimeout || setTimeout)(fn, ms); },
      clearTimeout: function (id) { return (e.clearTimeout || clearTimeout)(id); },
      now: function () { return e.now ? e.now() : Date.now(); },
      leaving: function (fn) {
        // Call fn when the page is being hidden or closed, so the last change is not lost to the pause.
        var offs = [];
        function on(target, name, handler) {
          try {
            if (target && typeof target.addEventListener === 'function') {
              target.addEventListener(name, handler);
              offs.push(function () { try { target.removeEventListener(name, handler); } catch (x) { return; } });
            }
          } catch (x) { return; }
        }
        try {
          if (typeof e.onLeave === 'function') return e.onLeave(fn) || function () {};
          on(r, 'pagehide', fn);
          on(r && r.document, 'visibilitychange', function () {
            try { if (r.document.visibilityState === 'hidden') fn(); } catch (x) { return; }
          });
        } catch (x) { return function () {}; }
        return function () { offs.forEach(function (off) { off(); }); };
      },
      listen: function (fn) {
        try {
          if (typeof e.onStorage === 'function') return e.onStorage(fn) || function () {};
          if (r && typeof r.addEventListener === 'function') {
            r.addEventListener('storage', fn);
            return function () { try { r.removeEventListener('storage', fn); } catch (x) { return; } };
          }
        } catch (x) { return function () {}; }
        return function () {};
      }
    };
  }

  // ---------- create ----------
  function create(config) {
    var cfg = config || {};
    function bad(what) { throw new Error('PocketState.create: ' + what); }
    if (typeof cfg.app !== 'string' || !cfg.app.trim()) bad('app must be a non-empty string');
    if (!whole(cfg.schema) || cfg.schema < 1) bad('schema must be a whole number of 1 or more');
    if (typeof cfg.contentId !== 'string' || !cfg.contentId.trim()) bad('contentId must be a non-empty string');
    if (cfg.validate !== undefined && typeof cfg.validate !== 'function') bad('validate must be a function that returns a list of problems');
    var migrations = cfg.migrations || {};
    var validateOlder = cfg.validateOlder || {};
    var step;
    for (step in migrations) {
      if (Object.prototype.hasOwnProperty.call(migrations, step)) {
        if (!/^[1-9][0-9]*$/.test(step) || Number(step) >= cfg.schema) bad('migrations key ' + step + ' must be a schema number below ' + cfg.schema);
        if (typeof migrations[step] !== 'function') bad('migrations[' + step + '] must be a function');
      }
    }
    var historyLimit = cfg.historyLimit === undefined ? 50 : cfg.historyLimit;
    var debounceMs = cfg.debounceMs === undefined ? 400 : cfg.debounceMs;
    var warnBytes = cfg.warnBytes === undefined ? 1000000 : cfg.warnBytes;
    var hostTimeoutMs = cfg.hostTimeoutMs === undefined ? 4000 : cfg.hostTimeoutMs;
    if (!whole(historyLimit) || historyLimit < 0) bad('historyLimit must be a whole number of 0 or more');
    if (!whole(debounceMs) || debounceMs < 0) bad('debounceMs must be a whole number of 0 or more');
    if (!whole(warnBytes) || warnBytes < 1) bad('warnBytes must be a whole number of 1 or more');
    if (!whole(hostTimeoutMs) || hostTimeoutMs < 1) bad('hostTimeoutMs must be a whole number of 1 or more');
    var adopt = cfg.externalPolicy === 'adopt';
    if (cfg.externalPolicy !== undefined && cfg.externalPolicy !== 'adopt' && cfg.externalPolicy !== 'hold') bad('externalPolicy must be "hold" or "adopt"');

    var env = resolveEnv(cfg.env);
    var key = typeof cfg.storageKey === 'string' && cfg.storageKey ? cfg.storageKey : 'pocket:' + cfg.app + ':' + cfg.contentId;

    function freshInitial() {
      var v = typeof cfg.initial === 'function' ? cfg.initial() : cfg.initial;
      return JSON.parse(JSON.stringify(v === undefined ? null : v));
    }
    var state, stateText;
    try { state = freshInitial(); } catch (e) { bad('initial could not be copied as JSON (' + msg(e) + ')'); }
    if (!seal(state, 0)) bad('initial is not plain JSON data: ' + unsafeParts(state, 'data', [], 0).join('; '));
    var initialProblems = problemsOf(cfg.validate, state);
    if (initialProblems.length) bad('initial does not pass validate: ' + listed(initialProblems));
    stateText = JSON.stringify(state);
    var initialText = stateText;

    var listeners = [];
    var undoStack = [], redoStack = [];
    var chain = [memoryLayer()];      // replaced in start()
    var active = 0;                   // index in chain of the layer that took the last save
    var seen = {};                    // per layer name: the exact text we believe is stored there
    var hold = null;                  // null | 'loading' | 'conflict' | 'recovery'
    var conflictInfo = null, recoveryInfo = null;
    var pending = false, timer = null, busy = null, again = false;
    var savedAt = null, degradeReason = null, changedWhileLoading = false;
    var sizeCache = null, stopListening = function () {}, stopLeaving = function () {}, destroyed = false;

    // ---------- events ----------
    function emit(event) {
      var i, copy = listeners.slice();
      for (i = 0; i < copy.length; i++) {
        try { copy[i](event); } catch (e) { continue; }
      }
    }
    function subscribe(fn) {
      if (typeof fn !== 'function') return function () {};
      listeners.push(fn);
      return function () {
        var i = listeners.indexOf(fn);
        if (i >= 0) listeners.splice(i, 1);
      };
    }

    // ---------- the envelope ----------
    function envelopeText(at) {
      return '{"app":' + JSON.stringify(cfg.app) + ',"schema":' + cfg.schema + ',"content_id":' + JSON.stringify(cfg.contentId) +
        ',"saved_at":' + JSON.stringify(at) + ',"data":' + stateText + '}';
    }
    function isoNow() {
      try { return new Date(env.now()).toISOString(); } catch (e) { return new Date().toISOString(); }
    }

    // Check a saved file. Pure: works on copies and never touches the store's state.
    function inspect(text) {
      var parsed, data, from, v, fn, problems, i, steps = [], older;
      if (typeof text !== 'string' || !text.trim()) return fail('empty', 'Nothing to import: the box is empty.');
      if (text.charCodeAt(0) === 0xFEFF) text = text.slice(1);
      try { parsed = JSON.parse(text); } catch (e) {
        return fail('not_json', 'This is not a saved file: it could not be read as JSON (' + msg(e) + ').');
      }
      if (!isPlain(parsed)) return fail('not_envelope', 'This is JSON, but it is not a file saved by this tool: it is not an object with app, schema and data.');
      var need = ['app', 'schema', 'data'];
      for (i = 0; i < need.length; i++) {
        if (!Object.prototype.hasOwnProperty.call(parsed, need[i])) {
          return fail('not_envelope', 'This is JSON, but it is not a file saved by this tool: it has no "' + need[i] + '" field.');
        }
      }
      if (typeof parsed.app !== 'string') return fail('not_envelope', 'This is JSON, but it is not a file saved by this tool: its "app" field is not text.');
      if (parsed.app !== cfg.app) {
        return fail('wrong_app', 'This file was saved by "' + parsed.app + '". This page is "' + cfg.app + '" and cannot read it.', {found: parsed.app, expected: cfg.app});
      }
      from = parsed.schema;
      if (!whole(from) || from < 1) {
        return fail('bad_schema', 'The schema in this file must be a whole number of 1 or more, and it is ' + JSON.stringify(from === undefined ? null : from) + '.');
      }
      if (from > cfg.schema) {
        return fail('newer_schema', 'This file uses schema ' + from + ', which is newer than this page (schema ' + cfg.schema + '). Open it with a newer copy of the tool.', {found: from, expected: cfg.schema});
      }
      data = parsed.data;
      if (data === null) return fail('not_envelope', 'This file has no data in it.');
      for (v = from; v < cfg.schema; v++) {
        fn = migrations[v];
        if (typeof fn !== 'function') {
          return fail('no_migration', 'This file uses schema ' + from + ', and this page has no step to bring schema ' + v + ' up to schema ' + (v + 1) + '.', {step: v});
        }
        try { data = fn(JSON.parse(JSON.stringify(data))); } catch (e) {
          return fail('migration_failed', 'Bringing this file from schema ' + v + ' to schema ' + (v + 1) + ' failed: ' + msg(e) + '.', {step: v});
        }
        if (data === undefined || data === null || !seal(data, 0)) {
          return fail('migration_failed', 'Bringing this file from schema ' + v + ' to schema ' + (v + 1) + ' did not produce plain data.', {step: v});
        }
        steps.push(v);
        older = validateOlder[v + 1];
        if (v + 1 < cfg.schema && typeof older === 'function') {
          problems = problemsOf(older, data);
          if (problems.length) {
            return fail('migration_invalid', 'Bringing this file from schema ' + v + ' to schema ' + (v + 1) + ' produced data that does not fit: ' + listed(problems) + '.', {step: v, problems: problems});
          }
        }
      }
      if (!seal(data, 0)) return fail('invalid_data', 'The data in this file is not plain JSON data.');
      problems = problemsOf(cfg.validate, data);
      if (problems.length) {
        if (steps.length) {
          return fail('migration_invalid', 'After bringing this file from schema ' + from + ' to schema ' + cfg.schema + ', the data does not fit this tool: ' + listed(problems) + '.', {step: steps[steps.length - 1], problems: problems});
        }
        return fail('invalid_data', 'The data in this file does not fit this tool: ' + listed(problems) + '.', {problems: problems});
      }
      var found = typeof parsed.content_id === 'string' ? parsed.content_id : null;
      return {
        ok: true, data: data, migratedFrom: steps.length ? from : null, steps: steps,
        savedAt: typeof parsed.saved_at === 'string' ? parsed.saved_at : null,
        contentId: found,
        contentMismatch: found === cfg.contentId ? null : {expected: cfg.contentId, found: found}
      };
    }

    // ---------- committing a new state ----------
    function commit(next, text, origin, label, opts) {
      if (historyLimit > 0 && origin !== 'load' && origin !== 'undo' && origin !== 'redo') {
        undoStack.push({data: state, text: stateText, label: label || origin});
        if (undoStack.length > historyLimit) undoStack.splice(0, undoStack.length - historyLimit);
        redoStack = [];
      }
      state = next;
      stateText = text;
      sizeCache = null;
      if (hold === 'loading') changedWhileLoading = true;
      emit({type: 'change', origin: origin, label: label || origin});
      if (!opts || opts.save !== false) scheduleSave();
    }
    function update(fn, opts) {
      var draft, out, next, problems, text;
      try {
        if (typeof fn !== 'function') return fail('bad_call', 'update needs a function.');
        draft = JSON.parse(stateText);
        try { out = fn(draft); } catch (e) {
          return fail('threw', 'The change was not made: ' + msg(e) + '.');
        }
        next = out === undefined ? draft : out;
        if (!seal(next, 0)) {
          return fail('not_json', 'The change was not made: ' + unsafeParts(next, 'data', [], 0).join('; ') + '.');
        }
        problems = problemsOf(cfg.validate, next);
        if (problems.length) return fail('invalid', 'The change was not made: ' + listed(problems) + '.', {problems: problems});
        text = JSON.stringify(next);
        if (text === stateText) return {ok: true, changed: false};
        commit(next, text, 'update', opts && typeof opts.label === 'string' ? opts.label : 'Change');
        return {ok: true, changed: true};
      } catch (e) {
        return fail('internal', 'The change was not made: ' + msg(e) + '.');
      }
    }
    function undo() {
      var step;
      if (!undoStack.length) return fail('nothing', 'There is nothing to undo.');
      step = undoStack.pop();
      redoStack.push({data: state, text: stateText, label: step.label});
      state = step.data; stateText = step.text; sizeCache = null;
      if (hold === 'loading') changedWhileLoading = true;
      emit({type: 'change', origin: 'undo', label: step.label});
      scheduleSave();
      return {ok: true, label: step.label};
    }
    function redo() {
      var step;
      if (!redoStack.length) return fail('nothing', 'There is nothing to redo.');
      step = redoStack.pop();
      undoStack.push({data: state, text: stateText, label: step.label});
      state = step.data; stateText = step.text; sizeCache = null;
      if (hold === 'loading') changedWhileLoading = true;
      emit({type: 'change', origin: 'redo', label: step.label});
      scheduleSave();
      return {ok: true, label: step.label};
    }
    function history() {
      function labels(stack) { return stack.map(function (s) { return s.label; }); }
      return {undo: labels(undoStack), redo: labels(redoStack), limit: historyLimit};
    }
    function reset(opts) {
      var next, text;
      try {
        next = freshInitial();
        if (!seal(next, 0) || problemsOf(cfg.validate, next).length) next = JSON.parse(initialText);
        seal(next, 0);
        text = JSON.stringify(next);
        if (text === stateText) return {ok: true, changed: false};
        commit(next, text, 'reset', opts && typeof opts.label === 'string' ? opts.label : 'Reset');
        return {ok: true, changed: true};
      } catch (e) {
        return fail('internal', 'Reset did not happen: ' + msg(e) + '.');
      }
    }

    // ---------- import ----------
    function importText(text, opts) {
      opts = opts || {};
      return new Promise(function (resolve) {
        var r, answer;
        function refuse(res) {
          res.message = res.message + ' Nothing was changed.';
          resolve(res);
        }
        function apply() {
          try {
            commit(r.data, JSON.stringify(r.data), 'import', typeof opts.label === 'string' ? opts.label : 'Import');
            resolve({ok: true, migratedFrom: r.migratedFrom, steps: r.steps, savedAt: r.savedAt, contentId: r.contentId, contentMismatch: r.contentMismatch});
          } catch (e) {
            refuse(fail('internal', 'The import failed: ' + msg(e) + '.'));
          }
        }
        function mismatch() {
          return fail('content_mismatch', 'This file belongs to ' + (r.contentMismatch.found === null ? 'no named content' : '"' + r.contentMismatch.found + '"') +
            ', and this page holds "' + r.contentMismatch.expected + '".', {expected: r.contentMismatch.expected, found: r.contentMismatch.found, canContinue: true});
        }
        try { r = inspect(text); } catch (e) { r = fail('internal', 'The file could not be checked: ' + msg(e) + '.'); }
        if (!r.ok) return refuse(r);
        if (!r.contentMismatch || opts.allowContentMismatch === true) return apply();
        if (typeof opts.onContentMismatch !== 'function') return refuse(mismatch());
        try {
          answer = opts.onContentMismatch({expected: r.contentMismatch.expected, found: r.contentMismatch.found, savedAt: r.savedAt});
        } catch (e) { answer = false; }
        Promise.resolve(answer).then(function (yes) {
          if (yes === true) apply(); else refuse(mismatch());
        }, function () { refuse(mismatch()); });
      });
    }
    function exportEnvelope() {
      var at = isoNow();
      var text = envelopeText(at);
      return {
        envelope: {app: cfg.app, schema: cfg.schema, content_id: cfg.contentId, saved_at: at, data: state},
        text: text, bytes: utf8Bytes(text),
        filename: cfg.app.replace(/[^A-Za-z0-9_-]+/g, '-') + '-' + at.slice(0, 10) + '.json'
      };
    }
    function size() {
      if (sizeCache === null) sizeCache = utf8Bytes(envelopeText('2000-01-01T00:00:00.000Z'));
      var over = sizeCache > warnBytes;
      return {
        bytes: sizeCache, warnBytes: warnBytes, over: over,
        text: over ? 'This data is ' + sizeCache + ' bytes, above the ' + warnBytes + ' byte level set for this tool. Storage may refuse it. Export a copy'
          : 'This data is ' + sizeCache + ' bytes'
      };
    }

    // ---------- saving ----------
    function persistence() {
      var mode = chain[active].name, text;
      if (hold === 'loading') text = WORDS.loading;
      else if (hold === 'conflict') text = WORDS.conflict;
      else if (hold === 'recovery') text = WORDS.held;
      else if (mode === 'memory') text = degradeReason ? 'Not saved: ' + degradeReason + '. Export to keep your work' : WORDS.memory;
      else text = WORDS[mode];
      return {
        mode: mode, durable: mode !== 'memory', state: hold === null ? 'ok' : hold, text: text,
        savedAt: savedAt, pending: pending, reason: mode === 'memory' ? degradeReason : null
      };
    }
    function clearTimer() {
      if (timer !== null) { try { env.clearTimeout(timer); } catch (e) { timer = null; } }
      timer = null;
    }
    function scheduleSave() {
      pending = true;
      if (hold !== null || destroyed) return;
      clearTimer();
      try { timer = env.setTimeout(function () { timer = null; saveNow(); }, debounceMs); } catch (e) { saveNow(); }
    }
    function sameData(text) {
      // True when a stored envelope holds exactly the data this store holds now.
      try {
        var p = JSON.parse(text);
        return isPlain(p) && JSON.stringify(p.data) === stateText;
      } catch (e) { return false; }
    }
    function raiseConflict(text, where) {
      var at = null;
      try { at = JSON.parse(text).saved_at || null; } catch (e) { at = null; }
      conflictInfo = {text: text, savedAt: typeof at === 'string' ? at : null, where: where};
      hold = 'conflict';
      clearTimer();
      emit({type: 'external', conflict: conflict()});
      emit({type: 'persistence', persistence: persistence(), degraded: false, recovered: false});
    }
    function attempt(i, text, at, why) {
      var layer = chain[i];
      return when(layer.read(key), function (r) {
        var known = seen[layer.name];
        if (r.ok && r.value !== null && known !== undefined && r.value !== known) {
          if (sameData(r.value)) seen[layer.name] = r.value;
          else { pending = true; raiseConflict(r.value, layer.name); return null; }
        }
        return when(layer.write(key, text), function (w) {
          var was = active, reason;
          if (w.ok) {
            seen[layer.name] = text;
            active = i;
            degradeReason = layer.name === 'memory' ? (why || degradeReason) : null;
            if (was !== i) emit({type: 'persistence', persistence: persistence(), degraded: i > was, recovered: i < was});
            // Memory is not a save. Only a layer that outlives the page sets the saved time.
            if (layer.name !== 'memory') {
              savedAt = at;
              emit({type: 'saved', savedAt: at, mode: layer.name});
            }
            return null;
          }
          reason = storageWhy(layer.name, w.error);
          return attempt(i + 1, text, at, why || reason);
        });
      });
    }
    function saveNow() {
      var at, out;
      clearTimer();
      if (destroyed) return null;
      if (hold !== null) { pending = true; return null; }
      if (busy) { again = true; return busy; }
      pending = false;
      at = isoNow();
      try { out = attempt(0, envelopeText(at), at, null); } catch (e) { out = null; }
      if (thenable(out)) {
        busy = out.then(function () {
          busy = null;
          if (again) { again = false; return saveNow(); }
          return null;
        }, function () { busy = null; return null; });
        return busy;
      }
      return null;
    }
    function flush() {
      var out;
      try { out = (pending && hold === null) ? saveNow() : busy; } catch (e) { out = null; }
      return Promise.resolve(out).then(function () { return persistence(); }, function () { return persistence(); });
    }

    // ---------- other tabs, and stored copies that cannot be read ----------
    function conflict() {
      if (!conflictInfo) return null;
      var r = inspect(conflictInfo.text);
      return {savedAt: conflictInfo.savedAt, readable: r.ok && !r.contentMismatch, message: r.ok ? '' : r.message, text: conflictInfo.text};
    }
    function resolveConflict(choice) {
      var r, info = conflictInfo;
      if (!info) return fail('nothing', 'There is no conflict to settle.');
      if (choice === 'mine') {
        seen[info.where] = info.text;
        conflictInfo = null; hold = null;
        emit({type: 'persistence', persistence: persistence(), degraded: false, recovered: false});
        pending = true;
        saveNow();
        return {ok: true, kept: 'mine'};
      }
      if (choice === 'theirs') {
        r = inspect(info.text);
        if (!r.ok) return fail(r.reason, 'The other copy could not be loaded. ' + r.message + ' Nothing was changed.');
        if (r.contentMismatch) return fail('content_mismatch', 'The other copy belongs to different content. Nothing was changed.');
        seen[info.where] = info.text;
        conflictInfo = null; hold = null;
        pending = false;
        commit(r.data, JSON.stringify(r.data), 'external', 'Load the copy from another tab', {save: r.migratedFrom !== null});
        emit({type: 'persistence', persistence: persistence(), degraded: false, recovered: false});
        return {ok: true, kept: 'theirs'};
      }
      return fail('bad_call', 'resolveConflict needs "mine" or "theirs".');
    }
    function recovery() {
      return recoveryInfo ? {reason: recoveryInfo.reason, message: recoveryInfo.message, text: recoveryInfo.text} : null;
    }
    function discardStored() {
      if (!recoveryInfo) return fail('nothing', 'There is no unread stored copy.');
      seen[recoveryInfo.where] = recoveryInfo.text;
      recoveryInfo = null; hold = null;
      emit({type: 'persistence', persistence: persistence(), degraded: false, recovered: false});
      pending = true;
      saveNow();
      return {ok: true};
    }
    function onStorageEvent(ev) {
      var v, r;
      try {
        if (destroyed || !ev || ev.key !== key || chain[active].name !== 'local') return;
        v = ev.newValue;
        if (typeof v !== 'string') return;
        if (hold === 'conflict' && conflictInfo && conflictInfo.where === 'local') {
          // The other tab saved again while this one was waiting for a choice: keep its newest copy.
          conflictInfo.text = v;
          try { conflictInfo.savedAt = JSON.parse(v).saved_at || null; } catch (e) { conflictInfo.savedAt = null; }
          emit({type: 'external', conflict: conflict()});
          return;
        }
        if (hold !== null || v === seen.local) return;
        if (sameData(v)) { seen.local = v; return; }
        if (adopt) {
          r = inspect(v);
          if (r.ok && !r.contentMismatch) {
            seen.local = v;
            pending = false; clearTimer();
            commit(r.data, JSON.stringify(r.data), 'external', 'Change from another tab', {save: false});
            return;
          }
        }
        raiseConflict(v, 'local');
      } catch (e) { return; }
    }

    // ---------- start: find the storage that works and what it holds ----------
    function finishLoad(found, resolve) {
      var r, report = {mode: chain[active].name, restored: false, migratedFrom: null, held: false, backupKey: null};
      var releasePending = pending || changedWhileLoading;
      hold = null;
      if (found) {
        r = inspect(found.text);
        if (r.ok && !r.contentMismatch) {
          if (changedWhileLoading && !sameData(found.text)) {
            raiseConflict(found.text, chain[found.index].name);
            report.held = true;
          } else {
            if (r.migratedFrom !== null) {
              // Keep the copy as it was before migration, if the storage will take it.
              report.backupKey = key + ':before-migration';
              try { chain[found.index].write(report.backupKey, found.text); } catch (e) { report.backupKey = null; }
            }
            state = r.data; stateText = JSON.stringify(state); sizeCache = null;
            savedAt = r.savedAt;
            report.restored = true;
            report.migratedFrom = r.migratedFrom;
            emit({type: 'change', origin: 'load', label: 'Open saved data'});
            if (r.migratedFrom !== null || found.index !== 0) releasePending = true;
          }
        } else {
          recoveryInfo = {
            reason: r.ok ? 'content_mismatch' : r.reason,
            message: r.ok ? 'The copy stored here belongs to "' + r.contentMismatch.found + '", and this page holds "' + r.contentMismatch.expected + '".' : r.message,
            text: found.text, where: chain[found.index].name
          };
          hold = 'recovery';
          report.held = true;
        }
      }
      report.mode = chain[active].name;
      emit({type: 'persistence', persistence: persistence(), degraded: false, recovered: false});
      if (releasePending && hold === null) scheduleSave();
      resolve(report);
      return null;
    }
    function restoreFrom(i, resolve) {
      var layer;
      if (i >= chain.length) return finishLoad(null, resolve);
      layer = chain[i];
      return when(layer.read(key), function (r) {
        if (r.ok) seen[layer.name] = r.value;
        if (r.ok && r.value !== null) return finishLoad({index: i, text: r.value}, resolve);
        return restoreFrom(i + 1, resolve);
      });
    }
    function start(resolve) {
      var h = env.host(), ls = env.local(), local = ls ? localLayer(ls) : null, host;
      function build(hostOk, first) {
        chain = [];
        if (hostOk) chain.push(host);
        if (local && local.probe(key + ':probe')) chain.push(local);
        chain.push(memoryLayer());
        active = 0;
        if (!hostOk) return restoreFrom(0, resolve);
        // The host has already been asked once; its answer is used and it is not asked again.
        if (first.ok) seen.host = first.value;
        if (first.ok && first.value !== null) return finishLoad({index: 0, text: first.value}, resolve);
        return restoreFrom(1, resolve);
      }
      if (!h) return build(false, null);
      hold = 'loading';
      host = hostLayer(h, env, hostTimeoutMs);
      return host.read(key).then(function (first) {
        if (first.ok && first.value !== null) return build(true, first);
        return host.probe(key + ':probe').then(function (ok) { return build(ok, first); });
      }).then(null, function () {
        chain = [memoryLayer()]; active = 0;
        return finishLoad(null, resolve);
      });
    }

    var ready = new Promise(function (resolve) {
      try {
        var out = start(resolve);
        if (thenable(out)) out.then(null, function () { chain = [memoryLayer()]; active = 0; hold = null; resolve({mode: 'memory', restored: false, migratedFrom: null, held: false}); });
      } catch (e) {
        chain = [memoryLayer()]; active = 0; hold = null;
        resolve({mode: 'memory', restored: false, migratedFrom: null, held: false});
      }
    });
    stopListening = env.listen(onStorageEvent);
    stopLeaving = env.leaving(function () {
      try { if (pending && hold === null && !destroyed) saveNow(); } catch (e) { return; }
    });

    return {
      get: function () { return state; },
      isInitial: function () { return stateText === initialText; },
      update: update,
      undo: undo,
      redo: redo,
      canUndo: function () { return undoStack.length > 0; },
      canRedo: function () { return redoStack.length > 0; },
      history: history,
      reset: reset,
      subscribe: subscribe,
      ready: ready,
      persistence: persistence,
      flush: flush,
      size: size,
      exportEnvelope: exportEnvelope,
      inspect: function (text) { try { return inspect(text); } catch (e) { return fail('internal', 'The file could not be checked: ' + msg(e) + '.'); } },
      importText: importText,
      conflict: conflict,
      resolveConflict: function (choice) { try { return resolveConflict(choice); } catch (e) { return fail('internal', msg(e)); } },
      recovery: recovery,
      discardStored: function () { try { return discardStored(); } catch (e) { return fail('internal', msg(e)); } },
      info: function () { return {app: cfg.app, schema: cfg.schema, contentId: cfg.contentId, storageKey: key}; },
      destroy: function () { destroyed = true; clearTimer(); try { stopListening(); stopLeaving(); } catch (e) { destroyed = true; } listeners = []; }
    };
  }

  var api = {create: create, version: VERSION, utf8Bytes: utf8Bytes, words: WORDS};
  if (typeof module === 'object' && module && module.exports) module.exports = api;
  else root.PocketState = api;
})(typeof globalThis !== 'undefined' ? globalThis : (typeof self !== 'undefined' ? self : this));
