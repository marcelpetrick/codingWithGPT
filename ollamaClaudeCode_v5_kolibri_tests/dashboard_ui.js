// Copyright (C) 2026 Marcel Petrick
// SPDX-License-Identifier: GPL-3.0-or-later

(function () {
  var tip = document.getElementById("tip"), open = null;
  function show(el) {
    tip.textContent = el.getAttribute("data-tip"); tip.style.display = "block"; open = el;
    var r = el.getBoundingClientRect(), w = tip.offsetWidth, h = tip.offsetHeight;
    var x = Math.min(Math.max(8, r.left + r.width / 2 - w / 2), window.innerWidth - w - 8);
    var y = r.bottom + 8; if (y + h > window.innerHeight - 8) y = r.top - h - 8;
    tip.style.left = x + "px"; tip.style.top = Math.max(8, y) + "px";
  }
  function hide() { tip.style.display = "none"; open = null; }
  document.querySelectorAll(".info").forEach(function (el) {
    el.addEventListener("mouseenter", function () { show(el); });
    el.addEventListener("mouseleave", hide);
    el.addEventListener("focus", function () { show(el); });
    el.addEventListener("blur", hide);
    el.addEventListener("click", function (e) { e.stopPropagation(); open === el ? hide() : show(el); });
    el.addEventListener("keydown", function (e) { if (e.key === "Escape") { hide(); el.blur(); } });
  });
  window.addEventListener("scroll", hide, true);
})();
document.querySelectorAll("table").forEach(function (tbl) {
  var head = tbl.rows[0];
  Array.prototype.forEach.call(head.cells, function (th, col) {
    th.classList.add("sortable");
    th.addEventListener("click", function () {
      var asc = th.getAttribute("aria-sort") !== "ascending";
      Array.prototype.forEach.call(head.cells, function (h) { h.removeAttribute("aria-sort"); });
      th.setAttribute("aria-sort", asc ? "ascending" : "descending");
      var rows = Array.prototype.slice.call(tbl.rows, 1).filter(function (r) { return r.cells.length > 1; });
      rows.sort(function (a, b) {
        var x = a.cells[col] ? a.cells[col].getAttribute("data-v") || "" : "";
        var y = b.cells[col] ? b.cells[col].getAttribute("data-v") || "" : "";
        if (x === "" && y === "") return 0;
        if (x === "") return 1;
        if (y === "") return -1;
        var nx = parseFloat(x), ny = parseFloat(y);
        var d = (!isNaN(nx) && !isNaN(ny)) ? nx - ny : x.localeCompare(y);
        return asc ? d : -d;
      });
      var parent = tbl.rows[1] ? tbl.rows[1].parentNode : tbl;
      rows.forEach(function (r) { parent.appendChild(r); });
    });
  });
});
