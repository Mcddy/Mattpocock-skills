// Renderers for the custom test fixture. Each receives the sample root and a context object
// {option, context, controls, el} and may return measured facts as [{label, value}]. It is run
// again whenever a tweak changes, with the new values in ctx.controls.
// Text is set with el(..., {text}) and never as markup. No requests are made.
const RENDERERS = {
  "plain-count": function (root, ctx) {
    var c = ctx.context;
    root.appendChild(ctx.el('p', {text: c.task + ': ' + c.done + ' of ' + c.total + ' done.'}));
    if (ctx.controls['show-file']) root.appendChild(ctx.el('p', {text: 'Now sending ' + c.current}));
    return [{label: 'lines of text', value: ctx.controls['show-file'] ? 2 : 1}];
  },
  "filled-bar": function (root, ctx) {
    var c = ctx.context;
    var track = ctx.el('div', {role: 'img', 'aria-label': c.done + ' of ' + c.total});
    track.style.cssText = 'height:14px;border:1px solid var(--o-line);background:var(--o-surface);border-radius:7px;overflow:hidden';
    var fill = ctx.el('div');
    fill.style.cssText = 'height:100%;background:var(--o-accent);width:' + Math.round(100 * c.done / c.total) + '%';
    track.appendChild(fill);
    root.appendChild(ctx.el('p', {text: c.task}));
    root.appendChild(track);
    root.appendChild(ctx.el('p', {text: c.done + ' of ' + c.total}));
    if (ctx.controls['show-file']) root.appendChild(ctx.el('p', {text: 'Now sending ' + c.current}));
    return [{label: 'bar filled, percent', value: Math.round(100 * c.done / c.total)}];
  },
  "eight-steps": function (root, ctx) {
    var c = ctx.context, row = ctx.el('div', {role: 'img', 'aria-label': c.done + ' of ' + c.total});
    row.style.cssText = 'display:flex;gap:4px;margin:8px 0';
    for (var i = 0; i < c.total; i++) {
      var b = ctx.el('span');
      b.style.cssText = 'flex:1;height:18px;border:1px solid var(--o-line);background:' + (i < c.done ? 'var(--o-accent)' : 'var(--o-surface)');
      row.appendChild(b);
    }
    root.appendChild(ctx.el('p', {text: c.task}));
    root.appendChild(row);
    root.appendChild(ctx.el('p', {text: c.done + ' of ' + c.total + ' photos'}));
    if (ctx.controls['show-file']) root.appendChild(ctx.el('p', {text: 'Now sending ' + c.current}));
    return [{label: 'blocks drawn', value: c.total}];
  }
};
