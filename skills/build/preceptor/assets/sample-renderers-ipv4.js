{
  "bit-toggles": function (host, data, api) {
    // Eight buttons, one per bit of an octet. Pressing one flips that bit; the sum is redrawn.
    var values = [128, 64, 32, 16, 8, 4, 2, 1];
    var start = String(data.start || "00000000");
    var bits = values.map(function (v, i) { return start.charAt(i) === "1" ? 1 : 0; });
    var buttons = [];
    var row = api.el("div", {role: "group", "aria-label": "The eight bits of an octet. Each button flips one bit.",
      style: "display:grid;grid-template-columns:repeat(auto-fit,minmax(64px,1fr));gap:8px;margin:12px 0"});
    var out = api.el("dl", {class: "facts", "aria-live": "polite"});
    function line(label, value, key) {
      out.appendChild(api.el("dt", {text: label}));
      out.appendChild(api.el("dd", {text: value, "data-bits-out": key}));
    }
    function draw() {
      var sum = 0, parts = [], text = "";
      bits.forEach(function (b, i) {
        text += String(b);
        if (b) { sum += values[i]; parts.push(String(values[i])); }
        buttons[i].setAttribute("aria-pressed", String(b === 1));
        buttons[i].firstChild.textContent = String(b);
      });
      out.textContent = "";
      line("Binary", text, "binary");
      line("Place values that count", parts.length ? parts.join(" + ") : "none", "parts");
      line("Decimal", String(sum), "decimal");
    }
    values.forEach(function (v, i) {
      var b = api.el("button", {type: "button", class: "seg", "data-bit": String(i), "aria-label": "Bit with place value " + v,
        style: "min-height:64px;padding:6px 2px;text-align:center",
        on: {click: function () { bits[i] = bits[i] ? 0 : 1; draw(); api.say("Decimal " + bits.reduce(function (s, x, k) { return s + x * values[k]; }, 0)); }}},
        [api.el("b", {style: "display:block;font-family:var(--mono);font-size:1.35rem;line-height:1.2"}),
         api.el("span", {style: "display:block;font-size:.8rem", text: String(v)})]);
      buttons.push(b);
      row.appendChild(b);
    });
    host.appendChild(row);
    host.appendChild(out);
    draw();
  }
}
