/*
  pocket-ui.js, revision 1.0.0

  Page helpers for a tool built on pocket-state.js: the sentence that says where the data lives,
  undo and redo buttons, and the export, import and start-again panel. Plain ASCII, no
  dependencies, no network requests. Paste it after pocket-state.js, inside the same script tag.
  It defines the global PocketUI.

  Everything here follows the rules a sandboxed chat preview imposes:
    - no form element and no submit event; buttons are type=button with click handlers
    - no alert, confirm or prompt; questions are asked in the page
    - text is always set with textContent, never assembled as markup
    - a download is offered together with the same content in a read-only text box, because a
      preview may block downloads; copying falls back to selecting the text for a manual copy
    - a control that is busy or unavailable is marked aria-disabled and keeps keyboard focus

  PocketUI.el(tag, attrs, children)       build an element; attrs.text sets textContent
  PocketUI.note(element, store)           keep the persistence sentence in element up to date
  PocketUI.undoButtons(container, store, {say})
  PocketUI.panel(container, store, {describe, say, idPrefix, words})
      describe(data) returns a short phrase for what the data holds, for example "14 books".
      say(text, isProblem) is the page's own status line, if it has one.
      words replaces wording where the defaults do not fit, for example a tool whose initial
      data is not empty: {exportHeading, exportHelp, importHeading, resetHeading, resetButton,
      resetNo, resetYes, resetLabel, resetNothing, resetQuestion(description, durable),
      resetDone(description)}.
  PocketUI.copyText(text, textarea)       promise for {ok}; selects the textarea when refused
  PocketUI.clock(iso)                     "14:02" in the reader's own time zone, or ""

  The panel uses these ids (with the default prefix "pk"), which tests and styles can rely on:
    pk-note  pk-conflict pk-take-theirs pk-keep-mine  pk-recovery pk-recovery-text pk-discard
    pk-size  pk-export pk-export-out pk-export-text pk-copy pk-download pk-export-msg
    pk-import-text pk-import-file pk-import pk-import-msg pk-mismatch pk-mismatch-yes pk-mismatch-no
    pk-reset pk-reset-confirm pk-reset-export pk-reset-no pk-reset-yes pk-reset-msg
  Styles are the page's job: the rules for the pk- classes are in the starter page.
*/
(function (root) {
  'use strict';

  function el(tag, attrs, kids) {
    var n = document.createElement(tag), k, ev, i;
    attrs = attrs || {};
    for (k in attrs) {
      if (!Object.prototype.hasOwnProperty.call(attrs, k)) continue;
      if (k === 'text') n.textContent = attrs[k];
      else if (k === 'on') { for (ev in attrs.on) if (Object.prototype.hasOwnProperty.call(attrs.on, ev)) n.addEventListener(ev, attrs.on[ev]); }
      else if (attrs[k] === true) n.setAttribute(k, '');
      else if (attrs[k] !== false && attrs[k] !== null && attrs[k] !== undefined) n.setAttribute(k, String(attrs[k]));
    }
    kids = kids || [];
    for (i = 0; i < kids.length; i++) if (kids[i]) n.appendChild(kids[i]);
    return n;
  }
  function clock(iso) {
    var d;
    try {
      d = new Date(iso);
      if (!iso || isNaN(d.getTime())) return '';
      return d.toLocaleTimeString([], {hour: '2-digit', minute: '2-digit'});
    } catch (e) { return ''; }
  }
  function setBusy(button, busy, text) {
    // aria-disabled keeps focus on the button; the disabled attribute would drop it.
    if (busy) button.setAttribute('aria-disabled', 'true'); else button.removeAttribute('aria-disabled');
    if (text) button.textContent = text;
  }
  function isOff(button) { return button.getAttribute('aria-disabled') === 'true'; }

  function copyText(text, area) {
    return new Promise(function (resolve) {
      function byHand() {
        var ok = false;
        try {
          area.focus(); area.select();
          ok = typeof document.execCommand === 'function' && document.execCommand('copy');
        } catch (e) { ok = false; }
        resolve({ok: !!ok});
      }
      try {
        if (root.navigator && root.navigator.clipboard && typeof root.navigator.clipboard.writeText === 'function') {
          root.navigator.clipboard.writeText(text).then(function () { resolve({ok: true}); }, byHand);
        } else byHand();
      } catch (e) { byHand(); }
    });
  }
  function fileLink(link, text, filename) {
    // A blob address where the page may make one, otherwise a data address. Either can be
    // blocked by a preview, which is why the same text is always shown in the page as well.
    var href = '';
    try {
      if (link.getAttribute('data-blob')) root.URL.revokeObjectURL(link.getAttribute('data-blob'));
      href = root.URL.createObjectURL(new root.Blob([text], {type: 'application/json'}));
      link.setAttribute('data-blob', href);
    } catch (e) {
      link.removeAttribute('data-blob');
      href = 'data:application/json;charset=utf-8,' + encodeURIComponent(text);
    }
    link.setAttribute('href', href);
    link.setAttribute('download', filename);
  }
  function readFile(file) {
    return new Promise(function (resolve) {
      var reader;
      try {
        reader = new root.FileReader();
        reader.onload = function () { resolve({ok: true, text: String(reader.result || ''), name: file.name}); };
        reader.onerror = function () { resolve({ok: false, message: 'The file "' + file.name + '" could not be read.'}); };
        reader.readAsText(file);
      } catch (e) {
        resolve({ok: false, message: 'This page could not read the file. Open it in a text editor and paste its contents instead.'});
      }
    });
  }

  // ---------- the sentence that says where the data lives ----------
  function note(target, store) {
    function draw() {
      var p = store.persistence(), at = clock(p.savedAt), text = p.text + '.';
      if (p.state === 'ok' && p.durable && at) text += ' Last saved ' + at + '.';
      if (target.textContent !== text) target.textContent = text;
      target.setAttribute('data-mode', p.mode);
      target.setAttribute('data-state', p.state);
    }
    draw();
    return store.subscribe(function (e) { if (e.type !== 'change') draw(); });
  }

  // ---------- undo and redo ----------
  function undoButtons(container, store, opts) {
    opts = opts || {};
    var prefix = opts.idPrefix || 'pk';
    var undo = el('button', {type: 'button', id: prefix + '-undo', class: 'pk-btn'});
    var redo = el('button', {type: 'button', id: prefix + '-redo', class: 'pk-btn'});
    function draw() {
      var h = store.history();
      var u = h.undo.length ? h.undo[h.undo.length - 1] : '', r = h.redo.length ? h.redo[h.redo.length - 1] : '';
      undo.textContent = u ? 'Undo: ' + u : 'Undo';
      redo.textContent = r ? 'Redo: ' + r : 'Redo';
      setBusy(undo, !u); setBusy(redo, !r);
    }
    undo.addEventListener('click', function () {
      if (isOff(undo)) return;
      var r = store.undo();
      if (opts.say) opts.say(r.ok ? 'Undone: ' + r.label + '.' : r.message, !r.ok);
    });
    redo.addEventListener('click', function () {
      if (isOff(redo)) return;
      var r = store.redo();
      if (opts.say) opts.say(r.ok ? 'Done again: ' + r.label + '.' : r.message, !r.ok);
    });
    container.appendChild(undo); container.appendChild(redo);
    draw();
    return store.subscribe(function (e) { if (e.type === 'change') draw(); });
  }

  // ---------- export, import, start again ----------
  function panel(container, store, opts) {
    opts = opts || {};
    var prefix = opts.idPrefix || 'pk';
    var describe = typeof opts.describe === 'function' ? opts.describe : function () { return 'the data'; };
    var say = typeof opts.say === 'function' ? opts.say : function () {};
    function id(name) { return prefix + '-' + name; }
    function what(data) { try { return String(describe(data)); } catch (e) { return 'the data'; } }
    var given = opts.words || {};
    var words = {
      exportHeading: given.exportHeading || 'Export',
      exportHelp: given.exportHelp || 'A copy you keep yourself: the only one that survives a cleared browser, another device, or a page that cannot store data.',
      importHeading: given.importHeading || 'Import',
      resetHeading: given.resetHeading || 'Start again',
      resetButton: given.resetButton || 'Remove everything',
      resetNo: given.resetNo || 'Keep everything',
      resetYes: given.resetYes || 'Remove everything',
      resetLabel: given.resetLabel || 'Remove everything',
      resetNothing: given.resetNothing || 'There was nothing to remove.',
      resetQuestion: typeof given.resetQuestion === 'function' ? given.resetQuestion : function (desc, durable) {
        return 'This removes ' + desc + ' from this page' + (durable ? ' and from where it is saved' : '') +
          '. Undo brings it back only until this page is closed or reloaded. An exported copy is the lasting way back.';
      },
      resetDone: typeof given.resetDone === 'function' ? given.resetDone : function (desc) { return 'Removed ' + desc + '. Undo brings it back.'; }
    };

    // -- where the data lives, and the two cases where saving has stopped
    var noteEl = el('p', {id: id('note'), class: 'pk-note', role: 'status'});
    var conflictText = el('p', {});
    var takeTheirs = el('button', {type: 'button', id: id('take-theirs'), class: 'pk-btn', text: 'Load the other copy here'});
    var keepMine = el('button', {type: 'button', id: id('keep-mine'), class: 'pk-btn', text: 'Keep this copy and save it'});
    var conflictBox = el('div', {id: id('conflict'), class: 'pk-alert', role: 'alert', hidden: true}, [conflictText, el('div', {class: 'pk-row'}, [takeTheirs, keepMine])]);
    var recoveryText = el('p', {});
    var recoveryArea = el('textarea', {id: id('recovery-text'), class: 'pk-text', readonly: true, rows: 4, 'aria-label': 'The stored copy that could not be read'});
    var discard = el('button', {type: 'button', id: id('discard'), class: 'pk-btn pk-danger', text: 'Start fresh and save over it'});
    var recoveryBox = el('div', {id: id('recovery'), class: 'pk-alert', role: 'alert', hidden: true}, [recoveryText, recoveryArea, el('div', {class: 'pk-row'}, [discard])]);
    var sizeEl = el('p', {id: id('size'), class: 'pk-warn', hidden: true});

    // -- export
    var exportBtn = el('button', {type: 'button', id: id('export'), class: 'pk-btn pk-primary', text: 'Export a copy', 'aria-expanded': 'false', 'aria-controls': id('export-out')});
    var exportArea = el('textarea', {id: id('export-text'), class: 'pk-text', readonly: true, rows: 5, spellcheck: 'false'});
    var copyBtn = el('button', {type: 'button', id: id('copy'), class: 'pk-btn', text: 'Copy the text'});
    var download = el('a', {id: id('download'), class: 'pk-btn pk-link', text: 'Download as a file', href: '#'});
    var exportMsg = el('p', {id: id('export-msg'), class: 'pk-msg', role: 'status'});
    var exportOut = el('div', {id: id('export-out'), class: 'pk-out', hidden: true}, [
      el('label', {for: id('export-text'), text: 'Your data as text. This is the whole saved copy'}),
      exportArea, el('div', {class: 'pk-row'}, [copyBtn, download]), exportMsg
    ]);

    // -- import
    var importArea = el('textarea', {id: id('import-text'), class: 'pk-text', rows: 4, spellcheck: 'false', autocomplete: 'off'});
    var importFile = el('input', {type: 'file', id: id('import-file'), class: 'pk-file', accept: '.json,.txt,application/json,text/plain'});
    var importBtn = el('button', {type: 'button', id: id('import'), class: 'pk-btn pk-primary', text: 'Import'});
    var importMsg = el('p', {id: id('import-msg'), class: 'pk-msg', role: 'status'});
    var mismatchText = el('p', {});
    var mismatchYes = el('button', {type: 'button', id: id('mismatch-yes'), class: 'pk-btn', text: 'Import it anyway'});
    var mismatchNo = el('button', {type: 'button', id: id('mismatch-no'), class: 'pk-btn', text: 'Cancel'});
    var mismatchBox = el('div', {id: id('mismatch'), class: 'pk-alert', role: 'alert', hidden: true}, [mismatchText, el('div', {class: 'pk-row'}, [mismatchNo, mismatchYes])]);

    // -- start again
    var resetBtn = el('button', {type: 'button', id: id('reset'), class: 'pk-btn pk-danger', text: words.resetButton, 'aria-expanded': 'false', 'aria-controls': id('reset-confirm')});
    var resetText = el('p', {});
    var resetExport = el('button', {type: 'button', id: id('reset-export'), class: 'pk-btn', text: 'Export a copy first'});
    var resetNo = el('button', {type: 'button', id: id('reset-no'), class: 'pk-btn', text: words.resetNo});
    var resetYes = el('button', {type: 'button', id: id('reset-yes'), class: 'pk-btn pk-danger', text: words.resetYes});
    var resetBox = el('div', {id: id('reset-confirm'), class: 'pk-alert', hidden: true}, [resetText, el('div', {class: 'pk-row'}, [resetNo, resetExport, resetYes])]);
    var resetMsg = el('p', {id: id('reset-msg'), class: 'pk-msg', role: 'status'});

    container.appendChild(el('div', {class: 'pk-panel'}, [
      noteEl, conflictBox, recoveryBox, sizeEl,
      el('div', {class: 'pk-block'}, [
        el('h3', {text: words.exportHeading}),
        el('p', {class: 'pk-help', text: words.exportHelp}),
        exportBtn, exportOut
      ]),
      el('div', {class: 'pk-block'}, [
        el('h3', {text: words.importHeading}),
        el('label', {for: id('import-text'), text: 'Paste a saved copy here'}), importArea,
        el('label', {for: id('import-file'), text: 'or choose a saved file'}), importFile,
        el('div', {class: 'pk-row'}, [importBtn]), importMsg, mismatchBox
      ]),
      el('div', {class: 'pk-block'}, [
        el('h3', {text: words.resetHeading}),
        resetBtn, resetBox, resetMsg
      ])
    ]));

    function message(target, text, isProblem) {
      target.textContent = text;
      target.className = 'pk-msg' + (isProblem ? ' pk-bad' : (text ? ' pk-good' : ''));
    }

    // -- drawing the parts that follow the store
    function draw() {
      var c = store.conflict(), r = store.recovery(), s = store.size(), at;
      conflictBox.hidden = !c;
      if (c) {
        at = clock(c.savedAt);
        conflictText.textContent = 'Another tab saved a different copy' + (at ? ' at ' + at : '') + '. Saving is paused here so that neither copy is lost. ' +
          (c.readable ? 'Loading the other copy can be undone.' : 'The other copy cannot be read by this page (' + c.message + ')');
        setBusy(takeTheirs, !c.readable);
      }
      recoveryBox.hidden = !r;
      if (r) {
        recoveryText.textContent = 'The copy stored here could not be opened. ' + r.message + ' It has been left exactly as it was, and nothing is being saved. Copy the text below somewhere safe if it matters.';
        if (recoveryArea.value !== r.text) recoveryArea.value = r.text;
      }
      sizeEl.hidden = !s.over;
      if (s.over) sizeEl.textContent = s.text + '.';
    }
    var stopNote = note(noteEl, store);
    var stopDraw = store.subscribe(function () { draw(); });
    draw();

    takeTheirs.addEventListener('click', function () {
      if (isOff(takeTheirs)) return;
      var r = store.resolveConflict('theirs');
      say(r.ok ? 'Loaded the copy from the other tab. Undo brings back what was here.' : r.message, !r.ok);
      draw();
    });
    keepMine.addEventListener('click', function () {
      var r = store.resolveConflict('mine');
      say(r.ok ? 'Kept this copy. It has replaced the one the other tab saved.' : r.message, !r.ok);
      draw();
    });
    var discardArmed = false;
    discard.addEventListener('click', function () {
      if (!discardArmed) {
        discardArmed = true;
        discard.textContent = 'Yes, replace the stored copy';
        return;
      }
      discardArmed = false;
      discard.textContent = 'Start fresh and save over it';
      var r = store.discardStored();
      say(r.ok ? 'The stored copy was replaced with what is on this page.' : r.message, !r.ok);
      draw();
    });

    function showExport() {
      var ex = store.exportEnvelope();
      exportArea.value = ex.text;
      fileLink(download, ex.text, ex.filename);
      exportOut.hidden = false;
      exportBtn.setAttribute('aria-expanded', 'true');
      exportBtn.textContent = 'Export again';
      message(exportMsg, 'A copy of ' + what(store.get()) + ', ' + ex.bytes + ' bytes, made at ' + (clock(ex.envelope.saved_at) || ex.envelope.saved_at) +
        '. If the download does not arrive, the text above is the same thing: copy it into a file or a note.', false);
      return ex;
    }
    exportBtn.addEventListener('click', function () { showExport(); });
    copyBtn.addEventListener('click', function () {
      copyText(exportArea.value, exportArea).then(function (r) {
        message(exportMsg, r.ok ? 'Copied ' + exportArea.value.length + ' characters.' : 'Copying was refused here. The text is selected: copy it by hand.', !r.ok);
      });
    });
    download.addEventListener('click', function (ev) {
      if (download.getAttribute('href') === '#') { ev.preventDefault(); return; }
      message(exportMsg, 'Download asked for: ' + download.getAttribute('download') + '. If no file arrives, this page is not allowed to download here; copy the text above instead.', false);
    });

    // -- import: one path for pasted text and for a chosen file
    var waiting = null;      // the open question about a file that belongs to other content
    function closeMismatch(answer) {
      var w = waiting;
      waiting = null;
      mismatchBox.hidden = true;
      if (w) w(answer);
    }
    function runImport() {
      if (isOff(importBtn)) return;
      var text = importArea.value, before = what(store.get()), wasBlank = store.isInitial();
      setBusy(importBtn, true, 'Importing');
      message(importMsg, '', false);
      store.importText(text, {
        label: 'Import',
        onContentMismatch: function (m) {
          return new Promise(function (resolve) {
            waiting = resolve;
            mismatchText.textContent = 'This file belongs to ' + (m.found === null ? 'content with no name' : '"' + m.found + '"') + ', and this page holds "' + m.expected +
              '". Importing it ' + (wasBlank ? 'loads what the file holds.' : 'replaces ' + before + ' with what the file holds.') + ' That can be undone.';
            mismatchBox.hidden = false;
            mismatchNo.focus();
          });
        }
      }).then(function (r) {
        setBusy(importBtn, false, 'Import');
        if (r.ok) {
          importArea.value = '';
          try { importFile.value = ''; } catch (e) { importArea.value = ''; }
          message(importMsg, 'Imported ' + what(store.get()) + (r.migratedFrom !== null ? ', brought up from schema ' + r.migratedFrom + ' to schema ' + store.info().schema : '') +
            '.' + (wasBlank ? '' : ' It replaced ' + before + ', which Undo brings back.'), false);
          say('Imported ' + what(store.get()) + '.', false);
        } else {
          message(importMsg, 'Not imported. ' + r.message, true);
          say('Not imported. ' + r.message, true);
        }
        importBtn.focus();
      });
    }
    importBtn.addEventListener('click', runImport);
    mismatchYes.addEventListener('click', function () { closeMismatch(true); });
    mismatchNo.addEventListener('click', function () { closeMismatch(false); });
    importFile.addEventListener('change', function () {
      var f = importFile.files && importFile.files[0];
      if (!f) return;
      message(importMsg, 'Reading ' + f.name + '.', false);
      readFile(f).then(function (r) {
        if (!r.ok) { message(importMsg, 'Not imported. ' + r.message + ' Nothing was changed.', true); return; }
        importArea.value = r.text;
        message(importMsg, 'Read ' + r.name + ' (' + r.text.length + ' characters). Press Import to check it and load it.', false);
        importBtn.focus();
      });
    });

    // -- start again: confirmed in the page, names what will go, offers a copy first
    function closeReset() {
      resetBox.hidden = true;
      resetBtn.setAttribute('aria-expanded', 'false');
    }
    resetBtn.addEventListener('click', function () {
      if (!resetBox.hidden) { closeReset(); return; }
      var p = store.persistence();
      resetText.textContent = String(words.resetQuestion(what(store.get()), p.durable));
      resetBox.hidden = false;
      resetBtn.setAttribute('aria-expanded', 'true');
      message(resetMsg, '', false);
      resetNo.focus();
    });
    resetNo.addEventListener('click', function () { closeReset(); resetBtn.focus(); });
    resetExport.addEventListener('click', function () { showExport(); exportArea.focus(); exportArea.select(); });
    resetYes.addEventListener('click', function () {
      var before = what(store.get()), r = store.reset({label: words.resetLabel});
      closeReset();
      if (r.ok && r.changed) { message(resetMsg, String(words.resetDone(before)), false); say(String(words.resetDone(before)), false); }
      else if (r.ok) message(resetMsg, words.resetNothing, false);
      else message(resetMsg, r.message, true);
      resetBtn.focus();
    });

    return {
      refresh: draw,
      showExport: showExport,
      destroy: function () { stopNote(); stopDraw(); }
    };
  }

  var api = {el: el, clock: clock, note: note, undoButtons: undoButtons, panel: panel, copyText: copyText, readFile: readFile, fileLink: fileLink, setBusy: setBusy, isOff: isOff, version: '1.0.0'};
  if (typeof module === 'object' && module && module.exports) module.exports = api;
  else root.PocketUI = api;
})(typeof globalThis !== 'undefined' ? globalThis : (typeof self !== 'undefined' ? self : this));
