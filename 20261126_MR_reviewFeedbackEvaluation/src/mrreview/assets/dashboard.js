/* Copyright (C) 2026 Marcel Petrick. SPDX-License-Identifier: GPL-3.0-or-later */
/* mrreview dashboard. Plain JavaScript, no libraries, no network access.
   All data text goes into the page with textContent, never as HTML. */
"use strict";
(function () {
const DATA = JSON.parse(document.getElementById("data").textContent);
const M = DATA.meta;
const MIN_N = 8;
const C = { deep: "#003B70", blue: "#0078D4", teal: "#00B8A9", green: "#38A169", red: "#E54865",
  amber: "#F2A900", gray: "#8A94A6", purple: "#7B61FF", orange: "#DD6B20", dgreen: "#276749", lgreen: "#68D391", steel: "#5B8DB8" };
/* Valence scale for outcomes, responses, tone and evidence (validated for colour blindness, 2026-11-27):
   fixed = greens and blue-teal, legitimate closure = blue and violet, warning = amber, negative = red, worst = dark red. */
const V = { good: "#2E9E5B", good2: "#007C92", part: "#9BBF3E", legit: "#22A3C4", legit2: "#6A6FD8", warn: "#C98200", bad: "#F06464", worst: "#A3162D", none: "#8A94A6" };

/* ---------- vocabulary: one label, one colour and one explanation per category ---------- */
const OUTCOME = {
  implemented: ["Implemented", V.good, "The requested change is stated as done. See the verification column for code evidence."],
  alternative_implemented: ["Alternative fix", V.good2, "A different change than requested is stated as done."],
  partially_implemented: ["Partly implemented", V.part, "Part of the request is stated as done."],
  justified_no_change: ["Justified no change", V.legit, "A reasoned answer or decision shows that no change is needed. This is a legitimate closure, not a failure."],
  optional_declined: ["Optional, declined", V.legit2, "An optional suggestion (nit) was declined. This is a legitimate closure."],
  declined_unjustified: ["Declined, no reason", V.worst, "A request was rejected without a technical reason."],
  deferred: ["Deferred", V.warn, "Moved to later work, for example an issue. See the reference column."],
  open: ["Open", V.bad, "No decision and no confirmed change by the snapshot. Promises without code evidence stay open."],
  unknown: ["Unknown", V.none, "Not enough evidence, or the model abstained."],
};
const VER = {
  direct: ["Direct", V.good, "A commented line changed in a later MR version. This is evidence of a change, not proof of a correct fix."],
  indirect: ["Indirect", V.part, "The commented file (or, for a general comment, any file) changed later, but not the commented lines."],
  textual_only: ["Text only", V.warn, "Someone states a change, but no later MR version shows one."],
  unavailable: ["Unavailable", C.gray, "The diffs needed for a check are missing (API gap or diff too large)."],
  not_applicable: ["n/a", "#CBD5E1", "No code change is expected for this outcome."],
};
const INTENT = {
  defect: ["Defect", C.red, "A correctness bug."], security: ["Security / reliability", C.purple, "A security or reliability risk."],
  design: ["Design", C.deep, "Architecture or design."], maintainability: ["Maintainability", C.blue, "Structure, duplication, documentation or complexity."],
  test: ["Test", C.teal, "Tests or coverage."], clarification: ["Clarification", C.steel, "Asks for information."],
  style: ["Style / nit", C.gray, "Formatting, naming or personal preference."], approval: ["Approval", "#A0AEC0", "Routine approval."],
  other: ["Other", "#B7C1CF", "None of the above, or unclear."],
};
const ACT = {
  change_request: ["Change request", "Asks for a code change. These are the actionable findings."],
  optional_suggestion: ["Optional suggestion", "A nit or a 'maybe'. Declining it is fine."],
  question: ["Question", "Asks only for information."], none: ["None", "Not a request."],
};
const VALIDITY = {
  supported: ["Supported", V.good, "A reply or evidence confirms the finding."],
  rebutted: ["Rebutted", V.legit, "A reasoned technical counterargument shows that it does not apply."],
  partially_supported: ["Partly supported", V.part, "Part of the finding is confirmed."],
  indeterminate: ["Indeterminate", C.gray, "The thread does not show enough evidence. Needs a human check."],
};
const RESP = {
  acknowledgement: ["Acknowledgement", C.steel, "Notes the comment without a decision, for example 'will do'."],
  agreement: ["Agreement", V.good, "Agrees with the finding."], partial_agreement: ["Partial agreement", V.part, "Agrees with part of it."],
  clarification_request: ["Asks back", C.blue, "Asks for clarification."], explanation: ["Explanation", V.legit, "Answers or explains."],
  reasoned_disagreement: ["Reasoned disagreement", C.deep, "Disagrees and gives a technical reason. This can be a good outcome."],
  alternative_proposal: ["Alternative", V.legit2, "Proposes a different solution."],
  unsupported_rejection: ["Rejection, no reason", V.worst, "Rejects without a reason."],
  deferral: ["Deferral", V.warn, "Moves it to later work."], unclear: ["Unclear", C.gray, "The reaction is unclear."],
  none_observed: ["No response", V.bad, "Nobody reacted to the finding."],
};
const TONE = {
  appreciative: ["Appreciative", V.good, "Thanks or praise."], constructive: ["Constructive", V.legit, "Helpful and specific."],
  neutral: ["Neutral", C.steel, "Plain technical text. Short is not hostile."], dismissive: ["Dismissive", V.bad, "Brushes the point aside."],
  confrontational: ["Confrontational", V.worst, "Hostile wording."], uncertain: ["Uncertain", C.gray, "Tone cannot be read reliably."],
};
const REASON = {
  substantive: ["Substantive", "At least one human note adds more than routine approval: a finding, a question, a rationale."],
  routine_only: ["Routine only", "Only 'LGTM', thanks or emoji. Not analysed."],
  author_self_note: ["Author note", "A note by the MR author with no reply from others, for example 'rebased'. Not review."],
  bot_initiated: ["Bot", "Started by a bot or automation, with no human reaction. Not analysed."],
  bot_review: ["Bot review", "An automated review comment that a human replied to. Analysed, and labelled as source 'bot'."],
};
const CHANGE = new Set(["implemented", "alternative_implemented", "partially_implemented"]);
const LEGIT = new Set(["justified_no_change", "optional_declined"]);

/* ---------- indexes ---------- */
const projById = new Map(DATA.projects.map(p => [p.id, p]));
const mrByKey = new Map(DATA.mrs.map(m => [m.p + ":" + m.iid, m]));
const thById = new Map(DATA.threads.map(t => [t.id, t]));
DATA.findings.forEach(f => { f.T = thById.get(f.t); f.MR = mrByKey.get(f.T.p + ":" + f.T.iid); });
const months = (() => {
  const all = DATA.threads.map(t => t.created.slice(0, 7)).concat(DATA.mrs.map(m => (m.created || "").slice(0, 7))).filter(Boolean).sort();
  if (!all.length) return [];
  const out = []; let [y, mo] = all[0].split("-").map(Number); const [ey, em] = all[all.length - 1].split("-").map(Number);
  while (y < ey || (y === ey && mo <= em)) { out.push(y + "-" + String(mo).padStart(2, "0")); mo++; if (mo > 12) { mo = 1; y++; } }
  return out;
})();
// A project counts when it is selected now or has collected MRs (the selected flag follows the current widening step).
const withMrs = new Set(DATA.mrs.map(m => m.p));
const selectedProjects = DATA.projects.filter(p => p.selected || withMrs.has(p.id)).sort((a, b) => a.label.localeCompare(b.label));

/* ---------- state ---------- */
const S = { tab: "overview", projects: new Set(selectedProjects.map(p => p.id)), from: months[0] || "", to: months[months.length - 1] || "",
  person: M.focus_user ? String(M.focus_user) : "", role: "any", source: "all", names: false, ev: { facets: [], search: "", page: 0, sort: ["created", -1], open: null } };

/* ---------- helpers ---------- */
function h(tag, attrs, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") el.className = v;
    else if (k === "text") el.textContent = v;
    else if (k === "tip") el.dataset.tip = v;
    else if (k === "style") el.setAttribute("style", v);
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "href") { if (/^https?:\/\//i.test(v)) { el.href = v; el.target = "_blank"; el.rel = "noopener noreferrer"; } }
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat()) if (kid !== null && kid !== undefined && kid !== false) el.append(kid instanceof Node ? kid : String(kid));
  return el;
}
const svgNS = "http://www.w3.org/2000/svg";
function s(tag, attrs, ...kids) {
  const el = document.createElementNS(svgNS, tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (k === "tip") el.dataset.tip = v; else if (k === "text") el.textContent = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v); else el.setAttribute(k, v);
  }
  kids.flat().forEach(k => k && el.append(k));
  return el;
}
const info = text => h("span", { class: "info", tabindex: "0", tip: text, "aria-label": text, role: "img" }, "i");
const pct = (n, d) => d ? (100 * n / d).toFixed(d >= 100 ? 1 : 0) + "%" : "–";
const fmtH = v => v === null || v === undefined ? "–" : v < 10 ? v.toFixed(1) + " h" : Math.round(v) + " h";
const fmtN = n => n.toLocaleString("en-US");
const month = iso => iso ? iso.slice(0, 7) : "";
function quantile(vals, q) {
  if (!vals.length) return null; const a = [...vals].sort((x, y) => x - y); const pos = (a.length - 1) * q;
  const lo = Math.floor(pos), hi = Math.ceil(pos); return a[lo] + (a[hi] - a[lo]) * (pos - lo);
}
const byThread = arr => { const seen = new Set(); return arr.filter(f => !seen.has(f.t) && seen.add(f.t)); };
const count = (arr, fn) => { const m = new Map(); arr.forEach(x => { const k = fn(x); m.set(k, (m.get(k) || 0) + 1); }); return m; };
function person(id) {
  if (id === null || id === undefined) return "–";
  const p = DATA.people[String(id)];
  if (!p) return "Unknown user";
  if (p.kind === "bot") return (S.names ? p.name : (p.label || "Bot")) + " (bot)";
  if (p.kind === "deleted") return "Deleted user";
  return S.names ? p.name : p.label;
}
const unmask = text => (text || "").replace(/⟦u:(\d+)⟧/g, (_, id) => person(Number(id))).replace(/⟦u:\?⟧/g, "@someone").replace(/⟦p:(\d+)⟧/g, (_, id) => projName(Number(id)));
const projName = id => { const p = projById.get(id); return p ? (S.names ? p.path : p.label) : String(id); };
function tag(dict, key, extraTip) {
  const d = dict[key] || [key, C.gray, ""]; const col = d.length > 2 ? d[1] : C.gray; const desc = d.length > 2 ? d[2] : d[1];
  return h("span", { class: "tag", style: "background:" + col + "1A;color:" + shade(col) + ";border-color:" + col + "55", tip: d[0] + ": " + desc + (extraTip ? "\n" + extraTip : "") }, h("span", { class: "swatch", style: "background:" + col }), d[0]);
}
function shade(hex) { const n = parseInt(hex.slice(1), 16); const f = 0.62; const r = Math.round(((n >> 16) & 255) * f), g = Math.round(((n >> 8) & 255) * f), b = Math.round((n & 255) * f); return "rgb(" + r + "," + g + "," + b + ")"; }

/* ---------- tooltips: every element with data-tip ---------- */
const tipEl = document.getElementById("tip");
function showTip(target, x, y) {
  tipEl.textContent = target.dataset.tip; tipEl.hidden = false;
  const r = tipEl.getBoundingClientRect(); let left = x + 14, top = y + 16;
  if (left + r.width > innerWidth - 8) left = x - r.width - 14; if (top + r.height > innerHeight - 8) top = y - r.height - 12;
  tipEl.style.left = Math.max(6, left) + "px"; tipEl.style.top = Math.max(6, top) + "px";
}
document.addEventListener("mousemove", e => { const t = e.target.closest && e.target.closest("[data-tip]"); if (t) showTip(t, e.clientX, e.clientY); else tipEl.hidden = true; });
document.addEventListener("focusin", e => { const t = e.target.closest && e.target.closest("[data-tip]"); if (t) { const r = t.getBoundingClientRect(); showTip(t, r.left, r.bottom); } });
document.addEventListener("focusout", () => { tipEl.hidden = true; });
document.addEventListener("scroll", () => { tipEl.hidden = true; }, true);

/* ---------- filtering ---------- */
function inPeriod(iso) { const m = month(iso); return (!S.from || m >= S.from) && (!S.to || m <= S.to); }
function involves(t) {
  if (!S.person) return true; const id = Number(S.person);
  if (S.role === "giver") return t.giver === id; if (S.role === "recipient") return t.rec === id;
  return t.giver === id || t.rec === id || t.resp.includes(id);
}
const fromSource = t => S.source === "all" || (S.source === "bot" ? t.gk === "bot" : t.gk !== "bot");
const fThreads = () => DATA.threads.filter(t => S.projects.has(t.p) && inPeriod(t.created) && involves(t) && fromSource(t));
const fFindings = () => DATA.findings.filter(f => S.projects.has(f.T.p) && inPeriod(f.T.created) && involves(f.T) && fromSource(f.T));
function fMrs() {
  const id = Number(S.person);
  // one pass over the threads (was: one scan per MR, about 50 million checks with a person filter)
  const inv = S.person ? new Set(DATA.threads.filter(involves).map(t => t.p + ":" + t.iid)) : null;
  return DATA.mrs.filter(m => S.projects.has(m.p) && inPeriod(m.created) && (!S.person || (S.role !== "giver" && m.author === id) ||
    inv.has(m.p + ":" + m.iid)));
}

/* ---------- charts ---------- */
function bars(rows, opts) {
  opts = opts || {}; const max = Math.max(1, ...rows.map(r => r.value)); const total = opts.total || rows.reduce((a, r) => a + r.value, 0);
  if (!rows.length) return h("div", { class: "empty", text: "No data in the current filter." });
  return h("div", { class: "bars" }, rows.map(r => h("div", { class: "bar" + (r.onclick ? " click" : ""), onclick: r.onclick, tip: r.tip || (r.label + ": " + fmtN(r.value) + " of " + fmtN(total) + " (" + pct(r.value, total) + ")") },
    h("span", { class: "lab" }, h("span", { class: "swatch", style: "background:" + (r.color || C.blue) }), r.label),
    h("div", { class: "track" }, h("div", { class: "fill", style: "width:" + (100 * r.value / max) + "%;background:" + (r.color || C.blue) })),
    h("span", { class: "num", text: opts.fmt ? opts.fmt(r) : fmtN(r.value) + " · " + pct(r.value, total) }))));
}
function stack(parts, onPick, unit) {
  const total = parts.reduce((a, p) => a + p.value, 0); unit = unit || "findings";
  if (!total) return h("div", { class: "empty", text: "No data in the current filter." });
  const vis = parts.filter(p => p.value > 0);
  return h("div", {},
    h("div", { class: "stack", role: "img", "aria-label": vis.map(p => p.label + " " + p.value).join(", ") },
      vis.map(p => h("div", { style: "width:" + (100 * p.value / total) + "%;background:" + p.color, tip: p.label + ": " + fmtN(p.value) + " of " + fmtN(total) + " " + unit + " (" + pct(p.value, total) + ")\n" + (p.desc || "") + (onPick ? "\nClick to see the cases." : ""), onclick: onPick ? () => onPick(p.key) : null }, p.value / total > 0.07 ? pct(p.value, total) : ""))),
    h("div", { class: "legend" }, vis.map(p => h("span", { class: "item", tip: p.desc || p.label, onclick: onPick ? () => onPick(p.key) : null }, h("span", { class: "swatch", style: "background:" + p.color }), p.label + " " + fmtN(p.value)))));
}
function dictParts(dict, counts) { return Object.keys(dict).map(k => ({ key: k, label: dict[k][0], color: dict[k][1], desc: dict[k][2], value: counts.get(k) || 0 })); }
function lineChart(series, opts) {
  opts = opts || {}; const W = opts.wide ? Math.max(760, Math.min(1500, document.documentElement.clientWidth - 110)) : 760, H = 230, L = 40, R = 12, T = 12, B = 34;
  const ms = months.filter(m => (!S.from || m >= S.from) && (!S.to || m <= S.to));
  if (!ms.length) return h("div", { class: "empty", text: "No months in the current filter." });
  const max = Math.max(1, ...series.flatMap(se => ms.map(m => se.values.get(m) || 0)));
  const log = S.scale === "log"; // owner request: a burst must not hide the quiet months
  const frac = v => log ? Math.log10(v + 1) / Math.log10(max + 1) : v / max;
  const x = i => L + (ms.length === 1 ? (W - L - R) / 2 : i * (W - L - R) / (ms.length - 1)); const y = v => T + (H - T - B) * (1 - frac(v));
  const svg = s("svg", { class: "chart", viewBox: "0 0 " + W + " " + H, role: "img", "aria-label": opts.label || "time series" });
  const g = s("g", { class: "grid" });
  const ticks = log ? [...new Set([0, ...[1, 10, 100, 1000, 10000, 100000].filter(v => v < max), max])] : [0, 1, 2, 3, 4].map(k => Math.round(max * k / 4));
  for (const v of ticks) { g.append(s("line", { x1: L, x2: W - R, y1: y(v), y2: y(v) }), s("text", { x: L - 6, y: y(v) + 4, "text-anchor": "end", text: String(v) })); }
  svg.append(g);
  const step = Math.ceil(ms.length / 12);
  ms.forEach((m, i) => { if (i % step === 0) svg.append(s("text", { x: x(i), y: H - 12, "text-anchor": "middle", text: m })); });
  series.forEach(se => {
    const pts = ms.map((m, i) => [x(i), y(se.values.get(m) || 0)]);
    if (se.area) svg.append(s("path", { d: "M" + pts.map(p => p.join(",")).join("L") + "L" + x(ms.length - 1) + "," + y(0) + "L" + x(0) + "," + y(0) + "Z", fill: se.color, "fill-opacity": "0.10" }));
    svg.append(s("path", { d: "M" + pts.map(p => p.join(",")).join("L"), fill: "none", stroke: se.color, "stroke-width": "2.2", "stroke-linejoin": "round" }));
    pts.forEach((p, i) => svg.append(s("circle", { class: "dot", cx: p[0], cy: p[1], r: 3.2, fill: "#fff", stroke: se.color, "stroke-width": 2, tip: se.name + ", " + ms[i] + ": " + fmtN(se.values.get(ms[i]) || 0) })));
  });
  const colW = (W - L - R) / Math.max(1, ms.length - 1);
  ms.forEach((m, i) => svg.append(s("rect", { class: "hit", x: x(i) - colW / 2, y: T, width: colW, height: H - T - B,
    tip: m + "\n" + series.map(se => se.name + ": " + fmtN(se.values.get(m) || 0)).join("\n") + (opts.extra ? "\n" + opts.extra(m) : ""), onclick: opts.onMonth ? () => opts.onMonth(m) : null })));
  const legend = h("div", { class: "legend" }, series.map(se => h("span", { class: "item", tip: se.tip || se.name }, h("span", { class: "swatch", style: "background:" + se.color }), se.name)));
  const sw = (key, label, tip) => h("button", { class: "btn scale-" + key, "aria-pressed": String((S.scale || "lin") === key), tip, onclick: () => { S.scale = key; render(); } }, label);
  const scale = h("div", { class: "scalesw" }, sw("lin", "Linear", "Linear axis: the height is the absolute number. A large burst can flatten the other months."),
    sw("log", "Logarithmic", "Logarithmic axis (log10 of n+1): quiet months stay visible next to a burst. Equal steps mean equal ratios. Hover shows the absolute numbers."));
  return h("div", {}, scale, svg, legend);
}
const BUCKETS = [[0, 1, "<1 h"], [1, 4, "1–4 h"], [4, 10, "4–10 h"], [10, 20, "1–2 d"], [20, 50, "2–5 d"], [50, 100, "5–10 d"], [100, Infinity, ">10 d"]];
function timingCard(title, key, list, tipText) {
  const unit = key === "fr" || key === "re" ? "threads" : "findings";
  if (key === "fr" || key === "re") list = byThread(list);
  const obs = list.filter(f => f.tm[key][0] === "o"); const pend = list.filter(f => f.tm[key][0] === "p");
  const biz = obs.map(f => f.tm[key][2]); const wall = obs.map(f => f.tm[key][1]);
  const counts = BUCKETS.map(b => biz.filter(v => v >= b[0] && v < b[1]).length); const max = Math.max(1, ...counts, pend.length);
  const low = biz.length < MIN_N;
  const col = (label, n, color, tip) => h("div", { class: "col", tip: tip }, h("div", { class: "cv", text: n ? String(n) : "" }), h("div", { class: "colbar", style: "height:" + (100 * n / max) + "%;background:" + color }), h("div", { class: "cl", text: label }));
  return h("div", { class: "card" }, h("h3", {}, title, info(tipText + "\nBusiness hours: Mon–Fri " + M.hours[0] + ":00–" + M.hours[1] + ":00, " + M.timezone + ". 1 d = one business day = " + (M.hours[1] - M.hours[0]) + " h. An estimate, not a measure of effort or availability.")),
    h("div", { class: "hist", role: "img", "aria-label": title + " histogram" },
      BUCKETS.map((b, i) => col(b[2], counts[i], C.blue, b[2] + " (business time): " + counts[i] + " of " + obs.length + " observed " + unit + " (" + pct(counts[i], obs.length) + ")")),
      col("pending", pend.length, "repeating-linear-gradient(45deg,#CBD5E1,#CBD5E1 4px,#E2E8F0 4px,#E2E8F0 8px)", "Pending: " + pend.length + " " + unit + " had no such event by the snapshot. They are not counted as zero; they are excluded from the median.")),
    h("div", { class: "stats" },
      h("span", { tip: "Median of observed business hours. Half the cases were faster." }, "median ", h("b", { class: low ? "lowN" : "", text: fmtH(quantile(biz, .5)) })),
      h("span", { tip: "75th percentile of observed business hours." }, "p75 ", h("b", { text: fmtH(quantile(biz, .75)) })),
      h("span", { tip: "90th percentile of observed business hours." }, "p90 ", h("b", { text: fmtH(quantile(biz, .9)) })),
      h("span", { tip: "Median of raw wall-clock hours, including nights and weekends." }, "wall median ", h("b", { text: fmtH(quantile(wall, .5)) })),
      h("span", { tip: "Observed " + unit + " (n) and " + unit + " still pending at the snapshot. Thread-level times count each thread once." }, "n ", h("b", { text: String(obs.length) }), " · pending ", h("b", { text: String(pend.length) }))),
    low ? h("div", { class: "small muted", text: "Fewer than " + MIN_N + " observed cases: do not interpret." }) : null);
}

/* ---------- evidence facets (drill-down) ---------- */
const FACETS = {
  outcome: [v => f => f.outcome === v, v => "Outcome: " + (OUTCOME[v] || [v])[0]],
  ver: [v => f => f.ver === v, v => "Verification: " + (VER[v] || [v])[0]],
  intent: [v => f => f.intent === v, v => "Intent: " + (INTENT[v] || [v])[0]],
  primary: [v => f => f.primary === v, v => "Response: " + (RESP[v] || [v])[0]],
  tone: [v => f => f.tone === v, v => "Tone: " + (TONE[v] || [v])[0]],
  validity: [v => f => f.validity === v, v => "Validity: " + (VALIDITY[v] || [v])[0]],
  act: [v => f => f.act === v, v => "Actionability: " + (ACT[v] || [v])[0]],
  project: [v => f => f.T.p === Number(v), v => "Project: " + projName(Number(v))],
  month: [v => f => month(f.T.created) === v, v => "Month: " + v],
  giver: [v => f => f.T.giver === Number(v), v => "Giver: " + person(Number(v))],
  rec: [v => f => f.T.rec === Number(v), v => "Recipient: " + person(Number(v))],
  clue: [v => CLUE_PRED[v], v => "Clue: " + (CLUE_NAME[v] || v)],
};
const CLUE_PRED = {
  resolved_no_code: f => f.T.resolved && CHANGE.has(f.outcome) && f.ver === "textual_only",
  promise_open: f => f.text === "promised" && f.outcome === "open" && !f.cens,
  silent_fix: f => (f.outcome === "open" || f.outcome === "unknown") && f.ev === "direct" && f.primary === "none_observed",
  unanswered_merged: f => f.primary === "none_observed" && f.MR && f.MR.state === "merged" && (f.outcome === "open" || f.outcome === "unknown"),
  legit_no_change: f => LEGIT.has(f.outcome),
  harsh: f => f.tone === "dismissive" || f.tone === "confrontational" || f.target === "person",
  deferred_noref: f => f.outcome === "deferred" && !f.ref,
  abstained: f => f.abstain || f.validity === "indeterminate",
  open_unattended: f => f.outcome === "open" && !f.cens,
  unknown: f => f.outcome === "unknown",
  verified: f => CHANGE.has(f.outcome) && f.ver === "direct",
};
const CLUE_NAME = { unknown: "Outcome unknown", resolved_no_code: "Resolved, fix claimed, no code change", promise_open: "Promised, not confirmed", silent_fix: "Code changed, no reply",
  unanswered_merged: "Merged with unanswered finding", legit_no_change: "Legitimate no-change closure", harsh: "Dismissive or personal tone",
  deferred_noref: "Deferred without a reference", abstained: "Ambiguous, needs a human", open_unattended: "Open, not recent", verified: "Verified remediation" };
function drill(facets) { S.ev.facets = facets; S.ev.page = 0; S.ev.open = null; S.tab = "evidence"; render(); window.scrollTo(0, 0); }

/* ---------- clues: hints that point at patterns, with sample-size guards ---------- */
function clues(F, T) {
  const MRF = fMrs();
  const out = []; const add = (icon, color, title, desc, key, n) => out.push({ icon, color, title, desc, key, n });
  const n = key => F.filter(CLUE_PRED[key]).length;
  const changeClaims = F.filter(f => CHANGE.has(f.outcome)).length;
  const rnc = n("resolved_no_code");
  if (rnc) add("⚑", V.warn, rnc + " resolved threads claim a fix that no later code change shows", pct(rnc, changeClaims) + " of " + changeClaims + " change claims. A resolved thread is not proof of a fix. Check these first.", "resolved_no_code", rnc);
  const po = n("promise_open");
  if (po) add("⏳", V.warn, po + " promised fixes have no confirmation and no code evidence", "'Will fix' is a promise, not a fix. Recent open MRs are excluded (censored).", "promise_open", po);
  const sf = n("silent_fix");
  if (sf) add("⚙", C.teal, sf + " findings got a code change but no written answer", "The commented lines changed later, nobody reacted, and no outcome is stated. Possibly a silent fix: check by hand.", "silent_fix", sf);
  const um = n("unanswered_merged");
  if (um) add("✉", V.bad, um + " findings had no response and the MR was merged anyway", "No reply, no decision, no change claim. These may be lost findings.", "unanswered_merged", um);
  const lg = n("legit_no_change");
  if (lg) add("✓", C.teal, lg + " findings closed with a reasoned no-change decision", "Reasoned disagreement and declined nits count as legitimate closure, not as failure.", "legit_no_change", lg);
  const dn = n("deferred_noref");
  if (dn) add("↷", V.warn, dn + " deferrals have no issue or MR reference", "A deferral without a link is hard to follow up.", "deferred_noref", dn);
  const hs = n("harsh");
  if (hs) add("!", V.bad, hs + " exchanges read as dismissive or personal", "Model reading of tone. Verify the text before you draw a conclusion.", "harsh", hs);
  const ab = n("abstained");
  if (ab >= 1) add("?", C.gray, ab + " findings are ambiguous (indeterminate or abstained)", "These need a human check before they count either way.", "abstained", ab);
  // project with clearly higher open rate
  const byP = new Map(); F.forEach(f => { const a = byP.get(f.T.p) || { n: 0, open: 0 }; a.n++; if (CLUE_PRED.open_unattended(f)) a.open++; byP.set(f.T.p, a); });
  const tot = F.length, totOpen = F.filter(CLUE_PRED.open_unattended).length;
  for (const [p, a] of byP) {
    const restN = tot - a.n, restOpen = totOpen - a.open;
    if (a.n >= 10 && restN >= 10 && a.open / a.n - restOpen / restN >= 0.15)
      out.push({ icon: "◎", color: V.bad, title: projName(p) + ": " + pct(a.open, a.n) + " of findings stay open (not recent)", desc: "Elsewhere " + pct(restOpen, restN) + " (" + restOpen + "/" + restN + "). n = " + a.n + ". A difference, not a cause: workload and norms differ.", facets: [["project", String(p)], ["clue", "open_unattended"]], n: a.open });
  }
  // response-time trend: last 3 months vs 3 months before
  const ms = [...new Set(F.map(f => month(f.T.created)))].sort();
  if (ms.length >= 6) {
    const last = new Set(ms.slice(-3)), prev = new Set(ms.slice(-6, -3));
    const v = set => F.filter(f => set.has(month(f.T.created)) && f.tm.fr[0] === "o").map(f => f.tm.fr[2]);
    const a = v(last), b = v(prev);
    if (a.length >= MIN_N && b.length >= MIN_N) {
      const ma = quantile(a, .5), mb = quantile(b, .5);
      if (mb > 0 && Math.abs(ma - mb) / mb >= 0.25)
        out.push({ icon: ma > mb ? "↗" : "↘", color: ma > mb ? V.warn : V.good, title: "First responses got " + (ma > mb ? "slower" : "faster") + ": median " + fmtH(mb) + " → " + fmtH(ma), desc: "Business hours, last 3 months (n=" + a.length + ") against the 3 months before (n=" + b.length + "). Rule: shown only at ≥25% change and n ≥ " + MIN_N + " each.", facets: [], n: a.length });
    }
  }
  // most intensive project
  const ints = selectedProjects.filter(p => S.projects.has(p.id)).map(p => { const mrs = MRF.filter(m => m.p === p.id).length; const th = T.filter(t => t.p === p.id && t.sub).length; return { p, mrs, th, r: mrs ? th / mrs : 0 }; }).filter(x => x.mrs >= 10).sort((a, b) => b.r - a.r);
  if (ints.length >= 2) out.push({ icon: "★", color: C.blue, title: "Most review per MR: " + projName(ints[0].p.id) + " (" + ints[0].r.toFixed(1) + " threads/MR)", desc: "Lowest: " + projName(ints[ints.length - 1].p.id) + " (" + ints[ints.length - 1].r.toFixed(1) + "). Review intensity, not quality.", facets: [["project", String(ints[0].p.id)]], n: ints[0].th });
  const ver = n("verified");
  if (ver) add("✔", V.good, ver + " findings have direct code evidence of a change", "The commented lines changed after the comment, and the text states a change.", "verified", ver);
  return out;
}

/* ---------- layout ---------- */
const app = document.getElementById("app");
function header() {
  const cov = M.coverage;
  const toggle = h("label", { class: "switch", tip: "Show real names of people and projects instead of pseudonyms everywhere: tables, charts, tooltips, excerpts and search.\nOff (default): screenshots show only pseudonyms such as 'Jade Crane' and 'Project Orion'.\nThis is a display switch, not access control: the names are inside this file." },
    h("input", { type: "checkbox", id: "names", "aria-label": "Show real names", onchange: e => { S.names = e.target.checked; render(); } }), "Show real names");
  toggle.querySelector("input").checked = S.names;
  if (M.share) toggle.replaceChildren(h("span", { class: "chip", tip: "Share build: this file holds no real names, paths or GitLab links (mrreview report --share)." }, "Pseudonymised file"));
  return h("header", { class: "top" },
    h("div", {}, h("h1", {}, "Review & Collaboration ", h("span", { text: "Analytics" })),
      h("div", { class: "subtitle", text: fmtN(selectedProjects.length) + " of " + fmtN(cov.projects_visible) + " projects analysed · " + fmtN(cov.mrs) + " merge requests · activity window since " + (M.window_start || "–").slice(0, 10) })),
    h("div", { class: "chips" },
      M.demo ? h("span", { class: "chip warn", tip: "This file uses invented demo data from the synthetic GitLab fixture. No real person or project is in it." }, "Synthetic demo data") : null,
      h("span", { class: "chip", tip: "Snapshot: the observation cutoff. Outcomes and pending times are judged at this instant.\nGenerated: when this file was built." }, "Snapshot " + (M.snapshot_at || "–").replace("T", " ").slice(0, 16) + " UTC"),
      M.stub ? h("span", { class: "chip bad", tip: "The classifications come from a keyword stub (model stub-rules), not from a language model. Use them only to check the pipeline." }, "Stub classifier, not an LLM")
        : h("span", { class: "chip" + (M.provenance.length > 1 ? " warn" : ""), tip: "Classifications by model and prompt:\n" + M.provenance.map(p => p.n + " × " + p.model + ", prompt " + p.prompt_version + ", schema " + p.schema_version).join("\n") + "\nOllama " + (M.ollama_version || "–") + (M.provenance.length > 1 ? "\nMore than one model or prompt: results mix." : "") }, "Model " + (M.provenance[0] ? M.provenance[0].model + " · " + M.provenance[0].prompt_version : "–") + (M.provenance.length > 1 ? " (+" + (M.provenance.length - 1) + ")" : "")),
      cov.state === "complete" ? h("span", { class: "chip ok", tip: "All selected MRs were collected, all substantive threads have a current classification, and the findings are up to date. No API gaps." }, "Coverage complete")
        : cov.state === "complete_with_gaps" ? h("span", { class: "chip warn", tip: "Complete, but GitLab did not return some data: " + Object.entries(cov.gaps).map(([k, v]) => k + " " + v).join(", ") + (cov.work.mr && cov.work.mr.skipped ? ", MRs not accessible " + cov.work.mr.skipped : "") + ". See Methodology → Coverage." }, "Complete, with gaps")
        : h("span", { class: "chip bad", tip: "Partial data:\n• " + cov.partial_reasons.join("\n• ") + "\nSee Methodology → Coverage." }, "Partial coverage"),
      toggle));
}
const TABS = [["overview", "Overview"], ["projects", "Projects"], ["effect", "Review effectiveness"], ["people", "Participants"], ["evidence", "Evidence"], ["method", "Methodology"]];
const TAB_TIPS = { overview: "Key numbers, clues and trends for the current filter.", projects: "Activity and review intensity per project, and the skipped projects.", effect: "What reviews find, how people respond, what happens, and how long it takes.", people: "Per-person context, split into giving and receiving review. No score and no ranking.", evidence: "Every finding with its classification, rationale, evidence and GitLab link.", method: "Definitions, denominators, assumptions, coverage and limits." };
function tabs() { return h("nav", { class: "tabs", role: "tablist" }, TABS.map(([k, l]) => h("button", { role: "tab", "aria-selected": String(S.tab === k), tip: TAB_TIPS[k], onclick: () => { S.tab = k; render(); } }, l))); }
function filters() {
  const pc = h("div", { class: "pchips" }, h("button", { class: "btn pall", tip: "Select all projects.", onclick: () => { S.projects = new Set(selectedProjects.map(p => p.id)); render(); } }, "All"),
    h("button", { class: "btn pnone", tip: "Clear the project selection. Then click single projects to add them.", onclick: () => { S.projects = new Set(); render(); } }, "None"), selectedProjects.map(p => h("button", { class: "pchip", "aria-pressed": String(S.projects.has(p.id)), tip: projName(p.id) + "\nClick to include or exclude this project.", onclick: () => { if (S.projects.has(p.id)) S.projects.delete(p.id); else S.projects.add(p.id); render(); } }, projName(p.id))));
  const opt = (v, l, sel) => { const o = h("option", { value: v }, l); if (sel) o.selected = true; return o; };
  const humans = Object.entries(DATA.people).filter(([, p]) => p.kind === "human").sort((a, b) => person(Number(a[0])).localeCompare(person(Number(b[0]))));
  return h("section", { class: "filters", "aria-label": "Filters" },
    h("label", { tip: "Projects in scope. Only analysed projects are listed." }, "Projects", pc),
    h("label", { tip: "First month (by thread start, or MR creation for MR counts)." }, "From", h("input", { type: "month", value: S.from, min: months[0], max: months[months.length - 1], onchange: e => { S.from = e.target.value; render(); } })),
    h("label", { tip: "Last month, inclusive." }, "To", h("input", { type: "month", value: S.to, min: months[0], max: months[months.length - 1], onchange: e => { S.to = e.target.value; render(); } })),
    h("label", { tip: "Limit everything to threads that involve one person." }, "Person", h("select", { onchange: e => { S.person = e.target.value; render(); } }, opt("", "Everyone", !S.person), humans.map(([id]) => opt(id, person(Number(id)), S.person === id)))),
    h("label", { tip: "Role of the person: giver = wrote the first comment; recipient = the person the comment addresses (usually the MR author); any = also as responder." }, "Role", h("select", { onchange: e => { S.role = e.target.value; render(); } }, opt("any", "any role", S.role === "any"), opt("giver", "review giver", S.role === "giver"), opt("recipient", "review recipient", S.role === "recipient"))),
    h("label", { tip: "Who wrote the first comment: a human reviewer or an automated reviewer (bot). Bot threads count only when a human replied." }, "Source", h("select", { onchange: e => { S.source = e.target.value; render(); } }, opt("all", "humans and bots", S.source === "all"), opt("human", "human reviews", S.source === "human"), opt("bot", "bot reviews", S.source === "bot"))),
    h("button", { class: "btn", tip: "Reset all filters to the full dataset.", onclick: () => { S.projects = new Set(selectedProjects.map(p => p.id)); S.from = months[0] || ""; S.to = months[months.length - 1] || ""; S.person = ""; S.role = "any"; S.source = "all"; render(); } }, "Reset"));
}
function kpi(label, value, sub, tip, accent, onclick, id) {
  return h("div", { class: "kpi" + (onclick ? " click" : ""), style: "--accent:" + accent, tip: tip + (onclick ? "\nClick to see the cases." : ""), onclick, "data-kpi": id },
    h("div", { class: "k" }, label), h("div", { class: "v", text: value }), h("div", { class: "s", text: sub || "" }));
}

/* ---------- sections ---------- */
function overview(root) {
  const T = fThreads(), F = fFindings(), MRS = fMrs();
  const subst = T.filter(t => t.sub); const actionable = F.filter(f => f.act === "change_request");
  const verified = actionable.filter(CLUE_PRED.verified); const openU = F.filter(CLUE_PRED.open_unattended); const rnc = F.filter(CLUE_PRED.resolved_no_code);
  const FT = byThread(F); const fr = FT.filter(f => f.tm.fr[0] === "o").map(f => f.tm.fr[2]); const frPend = FT.filter(f => f.tm.fr[0] === "p").length;
  const unk = F.filter(CLUE_PRED.unknown).length;
  const cov = M.coverage;
  if (cov.state === "partial") root.append(h("div", { class: "banner b-warn" }, "⚠ ", h("div", {}, h("b", {}, "Partial data. "), cov.partial_reasons.join(" · ") + ". Numbers below cover only the finished part.")));
  if (M.stub) root.append(h("div", { class: "banner b-info" }, "ℹ ", h("div", {}, "The classifications in this file come from the keyword stub, not from a language model. They show how the dashboard works; they are not an analysis.")));
  root.append(h("div", { class: "kpis" },
    kpi("Merge requests", fmtN(MRS.length), "in the filter", "MRs created in the period, in the selected projects. Merged, open and closed MRs all count.", C.blue, null, "mrs"),
    kpi("Substantive threads", fmtN(subst.length), pct(subst.length, T.length) + " of " + fmtN(T.length) + " threads · " + subst.filter(t => t.gk === "bot").length + " bot reviews", "Threads where a human adds more than routine approval, plus bot reviews that a human replied to. Denominator: all non-system threads, including LGTM, bot and author notes.", C.teal, null, "subst"),
    kpi("Findings", fmtN(F.length), "classified issues", "Distinct issues the model found in substantive threads. One thread can hold several findings.", C.deep, () => drill([]), "findings"),
    kpi("Actionable", fmtN(actionable.length), pct(actionable.length, F.length) + " of findings", "Findings that ask for a code change (change requests). Questions and optional nits are not actionable.", C.purple, () => drill([["act", "change_request"]]), "actionable"),
    kpi("Verified remediation", pct(verified.length, actionable.length), fmtN(verified.length) + " of " + fmtN(actionable.length) + " actionable", "Numerator: actionable findings with a stated change AND direct code evidence (the commented lines changed later).\nDenominator: all actionable findings.\nUnverified and unknown outcomes stay in the denominator; see Review effectiveness.", V.good, () => drill([["act", "change_request"], ["clue", "verified"]]), "verified"),
    kpi("Open, not recent", fmtN(openU.length), pct(openU.length, F.length) + " of findings · " + unk + " unknown", "Findings with outcome open that are not recent (an open MR with activity in the last " + M.censor_days + " days is censored and excluded).\nOutcome unknown (no reliable evidence, or the model abstained) is counted apart: " + unk + ".", V.bad, () => drill([["clue", "open_unattended"]]), "open"),
    kpi("Resolved, no code evidence", fmtN(rnc.length), "resolved + change claimed", "Threads marked resolved where the text claims a change, but no later MR version shows one. A resolved thread is not proof of a fix.", V.warn, () => drill([["clue", "resolved_no_code"]]), "rnc"),
    kpi("First response", fmtH(quantile(fr, .5)), "median, business hours · n=" + fr.length + (frPend ? ", " + frPend + " pending" : ""), "Median business hours from the first comment to the first meaningful human reply by someone else (LGTM, thanks and emoji do not count). Counted once per thread. Unanswered threads are pending and excluded, never counted as zero.", C.blue, null, "fr")));
  root.append(h("h2", {}, "Clues", info("Automatic hints that point at patterns worth a look. Each is a count with its denominator. Click a clue to see the cases. A clue is a question for a human, not a verdict.")));
  const cl = clues(F, T);
  root.append(cl.length ? h("div", { class: "clues" }, cl.map(c => h("div", { class: "clue", tip: c.desc + "\nClick to open the " + c.n + " cases in Evidence.", onclick: () => drill(c.facets || [["clue", c.key]]) }, h("div", { class: "ic", style: "background:" + c.color, text: c.icon }), h("div", {}, h("div", { class: "t", text: c.title }), h("div", { class: "d", text: c.desc }))))) : h("div", { class: "empty", text: "No clues for the current filter." }));
  const byMonth = (arr, fn) => { const m = new Map(); arr.forEach(x => { const k = month(fn(x)); m.set(k, (m.get(k) || 0) + 1); }); return m; };
  root.append(h("div", { class: "grid g2", style: "margin-top:16px" },
    h("div", { class: "card" }, h("h3", {}, "Activity over time", info("MRs created per month, substantive threads and findings per month (by thread start). Hover a month for the numbers; click to open its findings.")),
      lineChart([{ name: "Merge requests", color: C.blue, values: byMonth(MRS, m => m.created), area: true, tip: "MRs created in the month." }, { name: "Substantive threads", color: C.teal, values: byMonth(subst, t => t.created), tip: "Threads with real review content." }, { name: "Findings", color: C.purple, values: byMonth(F, f => f.T.created), tip: "Classified findings." }], { label: "activity per month", onMonth: m => drill([["month", m]]) })),
    h("div", { class: "card" }, h("h3", {}, "What happened to the findings", info("Outcome of every finding in the filter. Green tones: a change is stated. Teal and steel: legitimate closure without change. Red: open. Click a segment to see the cases.")),
      stack(dictParts(OUTCOME, count(F, f => f.outcome)), k => drill([["outcome", k]])),
      h("h3", { style: "margin-top:18px" }, "How strong is the evidence for stated changes", info("For findings with a stated change only: direct = the commented lines changed later; indirect = only the file changed; text only = no code change visible; unavailable = diffs missing.")),
      stack(dictParts(VER, count(F.filter(f => CHANGE.has(f.outcome)), f => f.ver)), k => drill([["ver", k]]), "stated changes"))));
  const res = { "resolved": F.filter(f => f.T.resolved), "not resolved": F.filter(f => !f.T.resolved && f.T.resolvable) };
  root.append(h("div", { class: "card", style: "margin-top:16px" }, h("h3", {}, "Thread resolution versus outcome", info("GitLab's 'resolved' flag and the real outcome are different things. Each row shows the outcomes of findings in resolved and in unresolved threads.")),
    Object.entries(res).map(([k, arr]) => h("div", { style: "margin:8px 0" }, h("div", { class: "small muted", text: k + " threads · " + arr.length + " findings" }), stack(dictParts(OUTCOME, count(arr, f => f.outcome)), o => drill([["outcome", o]]))))));
}
function projectsTab(root) {
  const T = fThreads(), F = fFindings(), MRF = fMrs();
  const rows = selectedProjects.filter(p => S.projects.has(p.id)).map(p => {
    const mrs = MRF.filter(m => m.p === p.id); const th = T.filter(t => t.p === p.id); const sub = th.filter(t => t.sub);
    const fs = F.filter(f => f.T.p === p.id); const act = fs.filter(f => f.act === "change_request"); const ver = act.filter(CLUE_PRED.verified); const op = fs.filter(CLUE_PRED.open_unattended);
    const fr = byThread(fs).filter(f => f.tm.fr[0] === "o").map(f => f.tm.fr[2]);
    return { p, mrs: mrs.length, merged: mrs.filter(m => m.state === "merged").length, sub: sub.length, inten: mrs.length ? sub.length / mrs.length : 0, f: fs.length, act: act.length, ver: ver.length, open: op.length, fr: quantile(fr, .5), frn: fr.length, appr: mrs.reduce((a, m) => a + m.approvals, 0) };
  });
  root.append(h("h2", {}, "Projects", info("Analysed projects in the filter. Raw volume (MRs) and review intensity (substantive threads per MR) are shown apart. Click a row to open its findings.")));
  root.append(table([
    ["Project", r => projName(r.p.id), r => h("span", {}, (r.p.web_url ? h("a", { href: r.p.web_url, tip: "Open the project in GitLab (needs GitLab access)." }, projName(r.p.id)) : projName(r.p.id))), "Project pseudonym, or the full path when real names are shown. Linked to GitLab."],
    ["MRs", r => r.mrs, null, "MRs created in the period (all states).", "n"],
    ["Merged", r => r.merged, null, "Of these, merged.", "n"],
    ["Approvals", r => r.appr, null, "Approval events on these MRs. Counted once per approver and MR; not part of threads.", "n"],
    ["Subst. threads", r => r.sub, null, "Threads with real review content.", "n"],
    ["Threads / MR", r => r.inten, r => r.inten.toFixed(2), "Review intensity: substantive threads divided by MRs. Not a quality measure.", "n"],
    ["Findings", r => r.f, null, "Classified findings.", "n"],
    ["Actionable", r => r.act, null, "Change requests.", "n"],
    ["Verified", r => r.act ? r.ver / r.act : -1, r => lowN(r.ver + " / " + r.act + " (" + pct(r.ver, r.act) + ")", r.act), "Actionable findings with a stated change and direct code evidence, over all actionable findings.", "n"],
    ["Open, not recent", r => r.f ? r.open / r.f : -1, r => lowN(r.open + " / " + r.f + " (" + pct(r.open, r.f) + ")", r.f), "Open or unknown findings, excluding recent open MRs, over all findings.", "n"],
    ["1st response", r => r.fr === null ? Infinity : r.fr, r => lowN(fmtH(r.fr), r.frn), "Median business hours to the first reply (observed cases only).", "n"],
  ], rows, r => drill([["project", String(r.p.id)]]), ["Threads / MR", -1]));
  // Three fixed series colours pass the colour-blindness check for all pairs; the rest is one gray "Other" line.
  const ranked = selectedProjects.filter(p => S.projects.has(p.id)).map(p => ({ p, n: T.filter(t => t.p === p.id && t.sub).length })).filter(x => x.n).sort((a, b) => b.n - a.n);
  const top = ranked.slice(0, 3), rest = new Set(ranked.slice(3).map(x => x.p.id));
  const series = top.map((x, i) => ({ name: projName(x.p.id), color: ["#257de0", "#f47230", "#00b894"][i], values: count(T.filter(t => t.p === x.p.id && t.sub), t => month(t.created)) }));
  if (rest.size) series.push({ name: "Other projects (" + rest.size + ")", color: V.none, tip: "All other selected projects together. Use the project chips to look at one of them.", values: count(T.filter(t => rest.has(t.p) && t.sub), t => month(t.created)) });
  root.append(h("div", { class: "card", style: "margin-top:16px" }, h("h3", {}, "Substantive threads per month and project", info("The three projects with the most substantive threads in the filter, and all others as one gray line. Hover a month for the values.")), lineChart(series, { label: "threads per project and month", wide: true })));
  const shown = new Set(selectedProjects.map(p => p.id)); const skipped = DATA.projects.filter(p => !shown.has(p.id));
  root.append(h("h2", {}, "Not analysed", info("Projects found by discovery but not analysed in depth, with the reason. Low activity is not poor collaboration.")));
  root.append(skipped.length ? table([
    ["Project", p => projName(p.id), p => p.web_url ? h("a", { href: p.web_url, tip: "Open the project in GitLab (needs GitLab access)." }, projName(p.id)) : projName(p.id), "Project pseudonym, or the full path when real names are shown."],
    ["MRs in window", p => p.window_mrs || 0, null, "MRs updated in the activity window.", "n"],
    ["Last activity", p => p.last_activity_at || "", p => (p.last_activity_at || "–").slice(0, 10), "Last activity date reported by GitLab."],
    ["Reason", p => p.skip_reason || "", null, "Why the project was not analysed."],
  ], skipped, null) : h("div", { class: "empty", text: "Every discovered project was analysed." }));
}
function lowN(text, n) { return n < MIN_N ? h("span", { class: "lowN", tip: "Only " + n + " cases (fewer than " + MIN_N + "). Do not interpret." }, text) : text; }
function effectTab(root) {
  const F = fFindings();
  root.append(h("h2", {}, "What the reviews raise", info("Model classification of each finding. Click any bar to open the cases.")));
  root.append(h("div", { class: "grid g3" },
    h("div", { class: "card" }, h("h3", {}, "Intent", info("What kind of issue the finding raises.")), bars(Object.keys(INTENT).map(k => ({ label: INTENT[k][0], value: F.filter(f => f.intent === k).length, color: INTENT[k][1], onclick: () => drill([["intent", k]]), tip: INTENT[k][0] + ": " + INTENT[k][2] + "\n" + F.filter(f => f.intent === k).length + " of " + F.length + " findings" })).filter(r => r.value))),
    h("div", { class: "card" }, h("h3", {}, "Actionability", info("Does the finding ask for a change, suggest optionally, or only ask?")), bars(Object.keys(ACT).map((k, i) => ({ label: ACT[k][0], value: F.filter(f => f.act === k).length, color: [C.purple, C.steel, C.blue, C.gray][i], onclick: () => drill([["act", k]]), tip: ACT[k][0] + ": " + ACT[k][1] })).filter(r => r.value))),
    h("div", { class: "card" }, h("h3", {}, "Validity", info("Is the finding supported by the thread? The model must say 'indeterminate' when unsure. This is not a judgement of code quality.")), bars(Object.keys(VALIDITY).map(k => ({ label: VALIDITY[k][0], value: F.filter(f => f.validity === k).length, color: VALIDITY[k][1], onclick: () => drill([["validity", k]]), tip: VALIDITY[k][0] + ": " + VALIDITY[k][2] })).filter(r => r.value)))));
  root.append(h("h2", {}, "How people respond", info("The main reaction of the recipient, and the tone of the exchange. Response and outcome are independent: a polite reply can still leave a finding open.")));
  root.append(h("div", { class: "grid g2" },
    h("div", { class: "card" }, h("h3", {}, "Primary response", info("The main act of the recipient. 'No response' means nobody reacted.")), bars(Object.keys(RESP).map(k => ({ label: RESP[k][0], value: F.filter(f => f.primary === k).length, color: RESP[k][1], onclick: () => drill([["primary", k]]), tip: RESP[k][0] + ": " + RESP[k][2] })).filter(r => r.value))),
    h("div", { class: "card" }, h("h3", {}, "Tone of the exchange", info("Model reading of the language. Uncertain is a valid answer. Criticism of code is not criticism of a person.")), bars(Object.keys(TONE).map(k => ({ label: TONE[k][0], value: F.filter(f => f.tone === k).length, color: TONE[k][1], onclick: () => drill([["tone", k]]), tip: TONE[k][0] + ": " + TONE[k][2] })).filter(r => r.value)),
      h("div", { class: "stats" }, h("span", { tip: "Findings where the model reads criticism of a person instead of the code." }, "aimed at a person: ", h("b", { text: String(F.filter(f => f.target === "person").length) }))))));
  root.append(h("h2", {}, "Outcome by intent", info("Each row: the outcomes of findings with that intent. Click a segment to open the cases.")));
  root.append(h("div", { class: "card" }, Object.keys(INTENT).filter(k => F.some(f => f.intent === k)).map(k => { const arr = F.filter(f => f.intent === k); return h("div", { style: "margin:6px 0 12px" }, h("div", { class: "small", style: "display:flex;gap:8px;align-items:center" }, h("span", { class: "swatch", style: "background:" + INTENT[k][1] }), INTENT[k][0] + " · " + arr.length), stack(dictParts(OUTCOME, count(arr, f => f.outcome)), o => drill([["intent", k], ["outcome", o]]))); })));
  root.append(h("h2", {}, "How long it takes", info("Elapsed time from the first comment of a thread. Business hours by default; wall-clock medians in the stats line. Pending cases are shown apart and never count as zero.")));
  root.append(h("div", { class: "grid g2" },
    timingCard("First response", "fr", F, "From the first comment to the first reply by another human."),
    timingCard("Decision", "de", F, "From the first comment to the note that states a decision (agreement, reasoned disagreement, alternative, deferral, rejection)."),
    timingCard("Implementation", "im", F.filter(f => CHANGE.has(f.outcome)), "From the first comment to the first later MR version with a code change, for findings with a stated change. Pending = no change visible."),
    timingCard("Thread resolution", "re", F.filter(f => f.T.resolvable), "From the first comment to GitLab's resolved timestamp. Resolution is not a fix.")));
  root.append(h("h2", {}, "Periods compared", info("Quarter by quarter, with explicit denominators. Grey italic values have fewer than " + MIN_N + " cases.")));
  const qs = [...new Set(F.map(f => quarter(f.T.created)))].sort();
  root.append(table([
    ["Quarter", r => r.q, null, "Calendar quarter of the thread start."],
    ["Findings", r => r.f.length, null, "All findings.", "n"],
    ["Actionable", r => r.a.length, null, "Change requests.", "n"],
    ["Verified", r => r.a.length ? r.v / r.a.length : -1, r => lowN(r.v + " / " + r.a.length + " (" + pct(r.v, r.a.length) + ")", r.a.length), "Direct code evidence over actionable findings.", "n"],
    ["Legit. no change", r => r.l, r => r.l + " (" + pct(r.l, r.f.length) + ")", "Justified no change or declined nit, over all findings.", "n"],
    ["Open, not recent", r => r.o, r => r.o + " (" + pct(r.o, r.f.length) + ")", "Over all findings.", "n"],
    ["Unknown", r => r.u, null, "Outcome unknown (model abstained or no evidence).", "n"],
    ["1st response", r => r.fr === null ? Infinity : r.fr, r => lowN(fmtH(r.fr), r.frn), "Median business hours.", "n"],
  ], qs.map(q => { const f = F.filter(x => quarter(x.T.created) === q); const a = f.filter(x => x.act === "change_request"); const fr = byThread(f).filter(x => x.tm.fr[0] === "o").map(x => x.tm.fr[2]);
    return { q, f, a, v: a.filter(CLUE_PRED.verified).length, l: f.filter(x => LEGIT.has(x.outcome)).length, o: f.filter(CLUE_PRED.open_unattended).length, u: f.filter(x => x.outcome === "unknown").length, fr: quantile(fr, .5), frn: fr.length }; }), null, ["Quarter", 1]));
}
function quarter(iso) { const m = Number(iso.slice(5, 7)); return iso.slice(0, 4) + "-Q" + Math.ceil(m / 3); }
function peopleTab(root) {
  const F = fFindings(); const T = fThreads().filter(t => t.sub);
  root.append(h("div", { class: "banner b-info" }, "ℹ ", h("div", {}, h("b", {}, "Context, not a score. "), "These tables describe observable interactions. They do not rank people, rate performance or read personality. Role, workload, review difficulty and project norms explain much of any difference. Rows with fewer than " + MIN_N + " cases are marked ⚠. Click a row to read the actual threads.")));
  const ids = [...new Set(T.flatMap(t => [t.giver, t.rec]).filter(id => id !== null && DATA.people[String(id)] && DATA.people[String(id)].kind === "human"))];
  const giv = ids.map(id => { const th = T.filter(t => t.giver === id); const fs = F.filter(f => f.T.giver === id); const act = fs.filter(f => f.act === "change_request");
    return { id, th: th.length, f: fs.length, act: act.length, ver: act.filter(CLUE_PRED.verified).length, legit: fs.filter(f => LEGIT.has(f.outcome)).length, open: fs.filter(CLUE_PRED.open_unattended).length, unk: fs.filter(CLUE_PRED.unknown).length, noresp: fs.filter(f => f.primary === "none_observed").length }; }).filter(r => r.th);
  const personOpts = { sortable: ["Person", "Findings"], lowRow: r => r.f < MIN_N, noSortTip: "Not sortable: person tables are context, not a ranking." };
  root.append(h("h2", {}, "Giving review", info("Per review giver: the person who wrote the first comment of a thread. Counts are about the findings they raised.")));
  root.append(table([
    ["Person", r => person(r.id), null, "Pseudonym by default. Switch 'Show real names' in the header to see names."],
    ["Threads", r => r.th, null, "Substantive threads started.", "n"],
    ["Findings", r => r.f, r => lowN(String(r.f), r.f), "Findings raised.", "n"],
    ["Actionable", r => r.act, r => r.act + " (" + pct(r.act, r.f) + ")", "Change requests among them.", "n"],
    ["Verified changes", r => r.ver, r => lowN(r.ver + " / " + r.act, r.act), "Their actionable findings with direct code evidence of a change.", "n"],
    ["Legit. no change", r => r.legit, null, "Their findings closed by a reasoned no-change decision or a declined nit.", "n"],
    ["No response", r => r.noresp, null, "Their findings that got no reaction.", "n"],
    ["Open, not recent", r => r.open, null, "Their findings with outcome open (not counting recent open MRs).", "n"],
    ["Unknown", r => r.unk, null, "Their findings with no reliable outcome.", "n"],
  ], giv, r => drill([["giver", String(r.id)]]), ["Person", 1], personOpts));
  const rec = ids.map(id => { const fs = F.filter(f => f.T.rec === id); const c = (...acts) => fs.filter(f => f.racts.some(a => acts.includes(a))).length; const fr = byThread(fs).filter(f => f.tm.fr[0] === "o").map(f => f.tm.fr[2]);
    const ask = fs.filter(f => f.act === "change_request"); const fixed = ask.filter(f => f.ev === "direct").length; const thr = byThread(fs);
    const answered = byThread(fs).filter(f => f.T.rw !== null && f.T.rw !== undefined);
    return { id, ask: ask.length, fixed, depth: quantile(answered.map(f => f.T.rw), .5), ans: answered.length, thx: answered.filter(f => f.T.rthx).length,
      nthr: thr.length, appr: thr.filter(f => f.tone === "appreciative" || f.tone === "constructive").length, harsh: thr.filter(f => f.tone === "dismissive" || f.tone === "confrontational").length,
      f: fs.length, agree: c("agreement", "partial_agreement"), reasoned: c("reasoned_disagreement", "explanation"), alt: c("alternative_proposal"), defer: c("deferral"), reject: c("unsupported_rejection"), none: fs.filter(f => !f.racts.length).length,
      reacted: fs.filter(f => f.racts.length).length, declR: fs.filter(f => LEGIT.has(f.outcome)).length, declN: fs.filter(f => f.outcome === "declined_unjustified").length,
      ver: fs.filter(f => CHANGE.has(f.outcome) && f.ver === "direct").length, textonly: fs.filter(f => CHANGE.has(f.outcome) && f.ver === "textual_only").length, open: fs.filter(CLUE_PRED.open_unattended).length, unk: fs.filter(f => f.outcome === "unknown").length, fr: quantile(fr, .5), frn: fr.length }; }).filter(r => r.f);
  root.append(h("h2", {}, "Receiving review", info("Per review recipient: usually the MR author. Only reactions written by the recipient count, each kind once per finding. The person who replies is not always the person who implements.")));
  root.append(table([
    ["Person", r => person(r.id), null, "Pseudonym by default."],
    ["Findings", r => r.f, r => lowN(String(r.f), r.f), "Findings addressed to the person.", "n"],
    ["Reaction rate", r => r.f ? r.reacted / r.f : 0, r => r.reacted + " / " + r.f + " (" + pct(r.reacted, r.f) + ")", "Findings the recipient reacted to in writing, over all findings addressed to the recipient. Bots and other people do not count.", "n"],
    ["Fix rate", r => r.ask ? r.fixed / r.ask : -1, r => r.ask ? lowN(r.fixed + " / " + r.ask + " (" + pct(r.fixed, r.ask) + ")", r.ask) : "–", "Change requests to this person where the commented lines changed after the comment (direct code evidence), whatever the text says. Code-based, so it is the most reliable column. A change is evidence, not proof of a correct fix.", "n"],
    ["Reply depth", r => r.depth === null ? -1 : r.depth, r => r.depth === null ? "–" : lowN(Math.round(r.depth) + " words", r.ans), "Median number of words the person wrote per answered thread, without quotes, code and links. Deterministic. Long is not always better: a precise short answer can be best.", "n"],
    ["Thanks", r => r.ans ? r.thx / r.ans : -1, r => r.ans ? lowN(r.thx + " / " + r.ans + " (" + pct(r.thx, r.ans) + ")", r.ans) : "–", "Answered threads where the person's own reply thanks or credits the feedback (thanks, good catch, danke, guter Punkt). Deterministic word match; agrees with Opus labels at kappa 0.82 (n=60).", "n"],
    ["Positive tone", r => r.nthr ? r.appr / r.nthr : -1, r => r.nthr ? lowN(r.appr + " / " + r.nthr + " (" + pct(r.appr, r.nthr) + ")", r.nthr) : "–", "Threads whose exchange the model reads as appreciative or constructive, counted once per thread. Tone of the whole exchange, not only this person. Low reliability: kappa 0.26 against Opus labels (n=60). Check cases before you conclude.", "n"],
    ["Dismissive tone", r => r.nthr ? r.harsh / r.nthr : -1, r => r.nthr ? lowN(r.harsh + " / " + r.nthr + " (" + pct(r.harsh, r.nthr) + ")", r.nthr) : "–", "Threads (once each) whose exchange the model reads as dismissive or confrontational. Low reliability: the model misses most dismissive cases (kappa 0.26). Check cases before you conclude.", "n"],
    ["Agreement", r => r.agree, null, "Full or partial agreement.", "n"],
    ["Reasoned / explained", r => r.reasoned, null, "Reasoned disagreement or explanation. These can be good outcomes.", "n"],
    ["Alternative", r => r.alt, null, "Proposed a different solution.", "n"],
    ["Deferral", r => r.defer, null, "Moved to later work.", "n"],
    ["Rejection, no reason", r => r.reject, null, "Rejected without a technical reason.", "n"],
    ["Declined, with reason", r => r.declR, null, "Outcome: justified no change or declined optional suggestion. A legitimate closure.", "n"],
    ["Declined, no reason", r => r.declN, null, "Outcome: a requested change was declined without a reason.", "n"],
    ["No reaction", r => r.none, null, "The recipient wrote no reaction to the finding (others may have).", "n"],
    ["Verified changes", r => r.ver, null, "Stated change with direct code evidence.", "n"],
    ["Change, text only", r => r.textonly, null, "Stated change without code evidence.", "n"],
    ["Open, not recent", r => r.open, null, "Still open, excluding recent open MRs.", "n"],
    ["Unknown", r => r.unk, null, "No reliable outcome.", "n"],
    ["1st response", r => r.fr === null ? Infinity : r.fr, r => lowN(fmtH(r.fr), r.frn), "Median business hours to the first meaningful reply by someone other than the giver, once per thread.", "n"],
  ], rec, r => drill([["rec", String(r.id)]]), ["Person", 1], personOpts));
}
function evidenceTab(root) {
  let F = fFindings();
  for (const [k, v] of S.ev.facets) { const pred = FACETS[k][0](v); F = F.filter(pred); }
  const q = S.ev.search.trim().toLowerCase();
  const text = f => [unmask(f.summary), unmask(f.T.excerpt), unmask(f.why), projName(f.T.p), person(f.T.giver), person(f.T.rec), f.MR ? unmask(f.MR.title) : ""].join(" ").toLowerCase();
  if (q) F = F.filter(f => text(f).includes(q));
  const [sk, sd] = S.ev.sort; const keyf = { created: f => f.T.created, project: f => projName(f.T.p), outcome: f => f.outcome, intent: f => f.intent, ver: f => f.ver }[sk] || (f => f.T.created);
  F.sort((a, b) => (keyf(a) < keyf(b) ? -1 : keyf(a) > keyf(b) ? 1 : 0) * sd);
  root.append(h("h2", {}, "Evidence", info("Every finding behind the numbers. Each row links to the GitLab thread. Expand a row for the rationale, timings and evidence notes. Search looks at the visible text, so it respects the identity toggle.")));
  root.append(h("div", { class: "evtools" },
    h("input", { type: "search", placeholder: "Search text, project, person…", value: S.ev.search, "aria-label": "Search findings", tip: "Search in summary, excerpt, rationale, MR title, project and displayed person labels.", oninput: e => { S.ev.search = e.target.value; S.ev.page = 0; const pos = e.target.selectionStart; render(); const el = document.querySelector(".evtools input[type=search]"); el.focus(); el.setSelectionRange(pos, pos); } }),
    h("span", { class: "muted small", text: fmtN(F.length) + " findings" }),
    S.ev.facets.length ? h("button", { class: "btn", onclick: () => { S.ev.facets = []; render(); }, tip: "Remove all drill-down filters." }, "Clear filters") : null));
  if (S.ev.facets.length) root.append(h("div", { class: "facets" }, S.ev.facets.map(([k, v], i) => h("span", { class: "facet", tip: "Drill-down filter. Click × to remove." }, FACETS[k][1](v), h("button", { "aria-label": "remove filter", onclick: () => { S.ev.facets.splice(i, 1); render(); } }, "×")))));
  const PAGE = 50; const pages = Math.max(1, Math.ceil(F.length / PAGE)); S.ev.page = Math.min(S.ev.page, pages - 1);
  const slice = F.slice(S.ev.page * PAGE, (S.ev.page + 1) * PAGE);
  const th = (label, key, tip) => h("th", { class: S.ev.sort[0] === key ? "sorted" + (S.ev.sort[1] > 0 ? " asc" : "") : "", tip: tip + (key ? "\nClick to sort." : ""), onclick: key ? () => { S.ev.sort = [key, S.ev.sort[0] === key ? -S.ev.sort[1] : -1]; render(); } : null }, label);
  const tbl = h("table", {}, h("thead", {}, h("tr", {}, th("Date", "created", "Start of the thread."), th("Project / MR", "project", "Project path and MR; the link opens the thread in GitLab."), th("Giver → recipient", null, "Who raised it, and to whom it was addressed."), th("Finding", null, "Model summary and the start of the first comment."), th("Intent", "intent", "Kind of issue."), th("Response", null, "Main reaction of the recipient."), th("Outcome", "outcome", "What happened."), th("Evidence", "ver", "Strength of the code evidence for stated changes."), th("Thread", null, "GitLab resolution flag and censoring."))),
    h("tbody", {}, slice.flatMap(f => {
      const key = f.t + ":" + f.i; const open = S.ev.open === key;
      const row = h("tr", { class: "click", onclick: () => { S.ev.open = open ? null : key; render(); }, tip: "Click to show or hide details." },
        h("td", { class: "small", text: f.T.created.slice(0, 10) }),
        h("td", { class: "small" }, h("div", { text: projName(f.T.p) }), (f.T.url ? h("a", { href: f.T.url, tip: "Open this thread in GitLab (needs access). " + (f.MR ? unmask(f.MR.title) : ""), onclick: e => e.stopPropagation() }, "!" + f.T.iid + " ↗") : "!" + f.T.iid)),
        h("td", { class: "small", text: person(f.T.giver) + " → " + person(f.T.rec) }),
        h("td", {}, h("div", { style: "font-weight:600", text: unmask(f.summary) }), h("div", { class: "excerpt small muted", text: unmask(f.T.excerpt) })),
        h("td", {}, tag(INTENT, f.intent), h("div", { class: "small muted", text: ACT[f.act] ? ACT[f.act][0] : f.act })),
        h("td", {}, tag(RESP, f.primary)),
        h("td", {}, tag(OUTCOME, f.outcome, f.text === "promised" ? "The text holds a promise only." : ""), f.ref ? h("div", { class: "small muted", text: "ref " + f.ref }) : null),
        h("td", {}, tag(VER, f.ver), f.changed && !CHANGE.has(f.outcome) ? h("div", { class: "small muted", tip: "The code changed after the comment, but the text does not state a change.", text: "code changed" }) : null),
        h("td", { class: "small" }, f.T.resolved ? h("span", { tip: "GitLab thread is resolved. This is not proof of a fix." }, "resolved") : f.T.resolvable ? h("span", { tip: "Thread is not resolved." }, "unresolved") : "–", f.cens ? h("div", { class: "muted", tip: "Right-censored: the MR is open with recent activity, so the outcome may still change." }, "recent") : null));
      if (!open) return [row];
      const tmr = (k, l) => { const v = f.tm[k]; return [h("dt", { text: l }), h("dd", { text: v[0] === "o" ? fmtH(v[2]) + " business · " + fmtH(v[1]) + " wall" : v[0] === "p" ? "pending (" + fmtH(v[1]) + " open at snapshot)" : "n/a" })]; };
      const mrUrl = f.MR ? f.MR.url : "";
      return [row, h("tr", { class: "detail" }, h("td", { colspan: "9" }, h("dl", {},
        h("dt", { text: "Rationale" }), h("dd", { text: unmask(f.why) || "–" }),
        h("dt", { text: "Text outcome" }), h("dd", { text: f.text + (f.abstain ? " (model abstained)" : "") }),
        h("dt", { text: "Validity" }), h("dd", {}, tag(VALIDITY, f.validity)),
        h("dt", { text: "Tone / target" }), h("dd", {}, tag(TONE, f.tone), " ", h("span", { class: "small muted", text: "criticism of: " + f.target })),
        h("dt", { text: "All response acts" }), h("dd", { text: f.acts.join(", ") || "none" }),
        tmr("fr", "First response"), tmr("de", "Decision"), tmr("im", "Implementation"), tmr("re", "Resolution"),
        h("dt", { text: "Evidence notes" }), h("dd", {}, f.evidence.map(id => mrUrl ? h("a", { href: mrUrl + "#note_" + id, style: "margin-right:8px" }, "#" + id) : h("span", { style: "margin-right:8px", text: "#" + id }))),
        h("dt", { text: "Location" }), h("dd", { text: (f.T.path || "general comment") + (f.T.line ? ":" + f.T.line : "") }),
        h("dt", { text: "MR" }), h("dd", {}, mrUrl ? h("a", { href: mrUrl }, f.MR ? unmask(f.MR.title) : "–") : (f.MR ? unmask(f.MR.title) : "–"), h("span", { class: "muted", text: f.MR ? " · " + f.MR.state : "" })))))];
    })));
  root.append(h("div", { class: "tablewrap" }, tbl));
  if (!F.length) root.append(h("div", { class: "empty", text: "No findings match." }));
  root.append(h("div", { class: "pager" }, h("button", { class: "btn", disabled: S.ev.page === 0, onclick: () => { S.ev.page--; render(); } }, "‹ Prev"), "Page " + (S.ev.page + 1) + " of " + pages, h("button", { class: "btn", disabled: S.ev.page >= pages - 1, onclick: () => { S.ev.page++; render(); } }, "Next ›")));
}
function methodTab(root) {
  const cov = M.coverage;
  root.append(h("h2", {}, "Coverage", info("What was collected and analysed. A partial report says so.")));
  const kv = (pairs) => h("div", { class: "kv" }, pairs.flatMap(([k, v, tip]) => [h("div", { tip: tip || k }, k), h("div", { text: String(v) })]));
  root.append(h("div", { class: "grid g2" },
    h("div", { class: "card" }, h("h3", {}, "Data"), kv([["Projects visible", cov.projects_visible, "Projects the token can see."], ["Projects analysed", selectedProjects.length, "Projects with collected MRs (all widening steps so far)."], ["Merge requests", cov.mrs, "Full history of the analysed projects."], ["Notes", cov.notes, "All notes including system notes."],
      ["Threads by kind", Object.entries(cov.thread_reasons).map(([k, v]) => (REASON[k] ? REASON[k][0] : k) + " " + v).join(", "), "Every non-system discussion, by the deterministic substantive check."],
      ["Classification", Object.entries(cov.classification).map(([k, v]) => k + " " + v).join(", "), "Status of substantive threads: ok, invalid (bad model output), failed (server error), pending, stale (input changed)."],
      ["MR collection", JSON.stringify(cov.work.mr || {}), "Work state per MR."], ["Coverage state", cov.state + (cov.partial_reasons.length ? ": " + cov.partial_reasons.join("; ") : ""), "complete, complete_with_gaps, or partial with the reasons."], ["API gaps", Object.entries(cov.gaps).map(([k, v]) => k + " " + v).join(", ") || "none", "Data GitLab did not return, for example missing diffs."]])),
    h("div", { class: "card" }, h("h3", {}, "Run"), kv([["Tool version", M.tool_version], ["Classifications", M.provenance.map(p => p.n + " × " + p.model + " (" + (p.model_digest || "").slice(0, 12) + "), prompt " + p.prompt_version + ", schema " + p.schema_version).join("; ") || "–", "Model, digest and prompt of each stored classification. More than one line means the results mix."], ["Current prompt / schema", M.prompt_version + " / " + M.schema_version, "Changing either re-classifies the threads."], ["Ollama", M.ollama_version || "–"], ["Findings evaluated", M.evaluated_at || "never", "When the outcome and timing step last ran."],
      ["Snapshot (cutoff)", M.snapshot_at], ["Window start", M.window_start, "Rolling window of " + M.window_months + " months for project selection only; analysed projects keep their full history."], ["Generated", M.generated_at],
      ["Business hours", "Mon–Fri " + M.hours[0] + ":00–" + M.hours[1] + ":00, " + M.timezone], ["Holidays", M.holidays.length ? M.holidays.join(", ") : "none excluded"], ["Censoring", "open MR with activity in the last " + M.censor_days + " days"]]))));
  root.append(h("h2", {}, "Definitions", info("Every category used in this dashboard.")));
  const defs = [["Thread kind", REASON], ["Intent", INTENT], ["Actionability", ACT], ["Validity", VALIDITY], ["Response", RESP], ["Tone", TONE], ["Outcome", OUTCOME], ["Verification", VER]];
  root.append(h("div", { class: "tablewrap" }, h("table", { class: "defs" }, h("thead", {}, h("tr", {}, h("th", { tip: "The classification dimension." }, "Dimension"), h("th", { tip: "The label used in tables and charts." }, "Category"), h("th", { tip: "What the label means. The same text appears in the tooltips." }, "Meaning"))),
    h("tbody", {}, defs.flatMap(([dim, d]) => Object.values(d).map(v => h("tr", {}, h("td", { class: "muted", text: dim }), h("td", { text: v[0] }), h("td", { text: v.length > 2 ? v[2] : v[1] }))))))));
  root.append(h("h2", {}, "Rates and denominators"));
  root.append(h("div", { class: "card" }, h("ul", {},
    h("li", { text: "Verified remediation = actionable findings with a stated change and direct code evidence ÷ all actionable findings. Indirect, text-only and unknown outcomes stay in the denominator." }),
    h("li", { text: "Open, not recent = findings with outcome open or unknown, minus censored ones (open MR, activity in the last " + M.censor_days + " days) ÷ all findings." }),
    h("li", { text: "Legitimate closure = justified no change + declined optional suggestion. It is not counted as a failure." }),
    h("li", { text: "Times run from the first comment of the thread. Pending events are excluded from medians and shown apart; they are never zero." }),
    h("li", { text: "Values with fewer than " + MIN_N + " cases are grey and marked ⚠. Medians and percentiles use linear interpolation." }))));
  root.append(h("h2", {}, "Limits and responsible use"));
  root.append(h("div", { class: "card" }, h("ul", {},
    h("li", { text: "The classifications come from a language model and can be wrong. Self-reported model certainty is not a probability. Check the evidence before you act." }),
    h("li", { text: "Code evidence shows that lines changed, not that a fix is correct. A resolved thread and a merged MR are not proof that a finding was handled." }),
    h("li", { text: "Business hours are an estimate. Personal schedules, leave and workload are unknown." }),
    h("li", { text: "Person-level numbers are context, not a performance score or a ranking, and say nothing about personality or motives. Use aggregate trends, and review individual cases with the people involved." }),
    h("li", { text: "Names in free text are masked when they match a known username, full name or name part (3+ letters); unknown @mentions are masked too. Project paths and project names (4+ characters) are masked the same way. Nicknames, misspellings and file paths stay visible." }),
    h("li", { text: "The identity toggle is a display switch, not access control or anonymisation. Names are inside this file. Project paths and links can re-identify people. Keep this file confidential and share it only with approved recipients." }),
    h("li", { text: "Observational associations do not show causes. Role, review difficulty, language and team norms can explain differences." }))));
}

/* ---------- generic sortable table ---------- */
function table(cols, rows, onRow, defSort, opts) {
  opts = opts || {};
  const wrap = h("div", { class: "tablewrap" }); let sort = defSort ? [cols.findIndex(c => c[0] === defSort[0]), defSort[1]] : [0, 1];
  const canSort = i => !opts.sortable || opts.sortable.includes(cols[i][0]);
  const cell = (c, r) => { const v = c[2] ? c[2](r) : String(c[1](r)); return opts.lowRow && opts.lowRow(r) && c[4] === "n" && typeof v === "string" ? h("span", { class: "lowN", tip: "Fewer than " + MIN_N + " findings in this row. Do not interpret." }, v) : v; };
  const draw = () => {
    const [ci, dir] = sort; const keyf = cols[ci][1];
    const sorted = [...rows].sort((a, b) => { const x = keyf(a), y = keyf(b); return (x < y ? -1 : x > y ? 1 : 0) * dir; });
    wrap.replaceChildren(h("table", {}, h("thead", {}, h("tr", {}, cols.map((c, i) => h("th", { class: (c[4] || "") + (i === ci ? " sorted" + (dir > 0 ? " asc" : "") : ""), scope: "col", tip: c[3] + (canSort(i) ? "\nClick to sort." : opts.noSortTip ? "\n" + opts.noSortTip : ""), onclick: canSort(i) ? () => { sort = [i, sort[0] === i ? -sort[1] : -1]; draw(); } : null }, c[0])))),
      h("tbody", {}, sorted.map(r => h("tr", { class: onRow ? "click" : "", onclick: onRow ? () => onRow(r) : null, tip: onRow ? "Click to open the findings behind this row." : null }, cols.map(c => h("td", { class: c[4] || "" }, cell(c, r))))))));
    if (!rows.length) wrap.append(h("div", { class: "empty", style: "padding:12px", text: "No rows in the current filter." }));
  };
  draw(); return wrap;
}

function render() {
  const y = window.scrollY;
  const main = h("main", { id: "main" });
  ({ overview, projects: projectsTab, effect: effectTab, people: peopleTab, evidence: evidenceTab, method: methodTab })[S.tab](main);
  app.replaceChildren(header(), tabs(), filters(), main, h("footer", {}, "mrreview " + M.tool_version + " · single offline file, no network access · confidential: share only with approved recipients · ", h("span", { tip: "Pseudonyms are stable labels stored in the local database. They are not anonymisation." }, "pseudonymous by default")));
  window.scrollTo(0, y);
  document.title = "Review analytics · " + TABS.find(t => t[0] === S.tab)[1];
}
window.__mrreview = { state: S, render, data: DATA };
render();
})();
