"use strict";
const $ = (id) => document.getElementById(id);
const el = { code: $("code"), gutter: $("gutter"), run: $("run"), banner: $("banner"), source: $("source") };
let config = null, last = null, lastText = "", view = "xy";

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
function fmtTime(s) {
  if (s == null) return "–";
  if (s < 60) return s.toFixed(1) + " s";
  const m = Math.floor(s / 60), r = Math.round(s - m * 60);
  if (m < 60) return `${m} min ${String(r).padStart(2, "0")} s`;
  return `${Math.floor(m / 60)} h ${String(m % 60).padStart(2, "0")} min`;
}
const fmtWh = (w) => (w == null ? "–" : w >= 1000 ? (w / 1000).toFixed(2) + " kWh" : w.toFixed(w < 10 ? 1 : 0) + " Wh");

function show(which) {
  for (const id of ["empty", "loading", "error", "report"]) $(id).hidden = id !== which;
}
let warning = "", stale = false;
function setBanner(text) { warning = text || ""; drawBanner(); }
function drawBanner() {
  const parts = [];
  if (stale) parts.push("The program has changed since this check. The results below describe the earlier version.");
  if (warning) parts.push(warning);
  el.banner.hidden = !parts.length;
  el.banner.textContent = parts.join(" ");
  el.banner.className = "banner" + (stale && !warning ? " info" : "");
}
function syncGutter() {
  const n = el.code.value.split("\n").length;
  if (el.gutter.dataset.n !== String(n)) {
    el.gutter.textContent = Array.from({ length: n }, (_, i) => i + 1).join("\n");
    el.gutter.dataset.n = n;
  }
  el.gutter.scrollTop = el.code.scrollTop;
}
function goToLine(line) {
  if (!line) return;
  const lines = el.code.value.split("\n");
  let start = 0;
  for (let i = 0; i < line - 1 && i < lines.length; i++) start += lines[i].length + 1;
  el.code.focus();
  el.code.setSelectionRange(start, start + (lines[line - 1] || "").length);
  el.code.scrollTop = Math.max(0, (line - 6) * 12.5 * 1.55);
  syncGutter();
}
function markStale() {
  stale = Boolean(last) && el.code.value !== lastText && !$("report").hidden;
  drawBanner();
}

async function api(path, body) {
  const res = await fetch(path, body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : undefined);
  if (!res.ok) {
    let msg = `The service answered with status ${res.status}.`;
    try { const j = await res.json(); if (typeof j.detail === "string") msg = j.detail; else if (Array.isArray(j.detail)) msg = j.detail.map((d) => d.msg).join(" "); } catch (_) { /* keep default */ }
    const e = new Error(msg); e.status = res.status; throw e;
  }
  return res.json();
}

function sourceBadge() {
  const m = config.machines.find((x) => x.id === $("machine").value);
  if (!m) return;
  if (!m.calibrated) { el.source.className = "source none"; el.source.textContent = "No calibration for this machine: physics estimate only"; }
  else if (m.calibration_source === "simulated") { el.source.className = "source sim"; el.source.textContent = `Calibrated on SIMULATED data (${m.calibration_jobs} generated jobs)`; }
  else { el.source.className = "source"; el.source.textContent = `Calibrated on ${m.calibration_source} data (${m.calibration_jobs} jobs)`; }
}

async function init() {
  try {
    config = await api("/api/config");
  } catch (e) {
    show("error");
    $("errorTitle").textContent = "Cannot reach the estimator service";
    $("errorText").textContent = "The page loaded but the service behind it did not answer. Check that it is running, then try again.";
    return;
  }
  $("machine").innerHTML = config.machines.map((m) => `<option value="${esc(m.id)}">${esc(m.name)}</option>`).join("");
  $("material").innerHTML = `<option value="">from program</option>` + config.materials.map((m) => `<option>${esc(m)}</option>`).join("");
  $("sample").innerHTML = `<option value="">Choose an example…</option>` + config.samples.map((s) => `<option value="${esc(s.id)}">${esc(s.name)}</option>`).join("");
  sourceBadge();
}

async function run() {
  const program = el.code.value;
  if (!program.trim()) {
    show("error");
    $("errorTitle").textContent = "There is no program to check";
    $("errorText").textContent = "Paste an NC program, open a file, or choose an example first.";
    return;
  }
  el.run.disabled = true; stale = false; setBanner(""); show("loading");
  const num = (id) => ($(id).value === "" ? null : Number($(id).value));
  try {
    const r = await api("/api/analyze", {
      program, machine: $("machine").value, level: Number($("level").value),
      material: $("material").value || null, tool_diameter: num("tool"), depth_of_cut: num("depth"),
    });
    last = r; lastText = program; render(r);
  } catch (e) {
    show("error");
    $("errorTitle").textContent = e.status ? "The program could not be checked" : "Cannot reach the estimator service";
    $("errorText").textContent = e.status ? e.message : "The request did not get through. Check that the service is running, then try again. Your program text is still in the editor.";
  } finally { el.run.disabled = false; }
}

function card(title, est, lo, hi, refs, fmt, level, sub) {
  const all = [est, lo, hi, ...refs.map((r) => r.v)].filter((v) => v != null);
  const min = Math.min(...all) * 0.9, max = Math.max(...all) * 1.08;
  const pos = (v) => (((v - min) / (max - min)) * 100).toFixed(2) + "%";
  const hasRange = lo != null && hi != null;
  return `<div class="k">${title}</div><div class="v">${fmt(est)}</div>
    <div class="r">${hasRange ? `${fmt(lo)} to ${fmt(hi)} <span class="sub">(${Math.round(level * 100)} % range)</span>` : `<span class="sub">No range: this machine has no calibration data.</span>`}</div>
    <div class="bar"><div class="track"></div>
      ${hasRange ? `<div class="range" style="left:${pos(lo)};width:calc(${pos(hi)} - ${pos(lo)})"></div>` : ""}
      <div class="tick" style="left:${pos(est)}"></div>
      ${refs.map((r) => `<div class="ref" style="left:${pos(r.v)}"><span>${r.label}</span></div>`).join("")}
    </div><div class="sub">${sub}</div>`;
}

function render(r) {
  show("report");
  renderIssues(r.issues || []);
  if (!r.ok) {
    $("timeCard").innerHTML = `<div class="k">Cycle time</div><div class="v">–</div><div class="sub">No motion was found, so nothing could be estimated.</div>`;
    $("energyCard").innerHTML = `<div class="k">Drive energy</div><div class="v">–</div>`;
    $("calNote").textContent = ""; $("hot").tBodies[0].innerHTML = ""; $("stats").innerHTML = ""; drawPath(null);
    return;
  }
  const t = r.time, e = r.energy, c = r.calibration;
  $("timeCard").innerHTML = card("Cycle time", t.estimate_s, t.low_s, t.high_s, [{ v: t.nominal_s, label: "length ÷ feed" }], fmtTime, c.level,
    `Length ÷ feed gives ${fmtTime(t.nominal_s)}. With acceleration and corners the planner gives ${fmtTime(t.planned_s)}.`);
  $("energyCard").innerHTML = card("Drive energy", e.estimate_wh, e.low_wh, e.high_wh, [{ v: e.physics_wh, label: "physics model" }], fmtWh, c.level,
    `Idle, spindle, axis and cutting power over the run. ${esc(r.job.material)}, Ø${r.job.tool_diameter} mm tool, ${r.job.depth_of_cut} mm deep.`);
  if (c.state === "uncalibrated") {
    $("calNote").textContent = "This machine profile has no logged runs, so the figures are the physics model alone and carry no range.";
  } else {
    $("calNote").textContent = `Ranges come from ${c.jobs} ${c.source} runs across ${c.groups} part families. ` +
      (c.source === "simulated" ? "They show how the method behaves; they are not measurements from a real machine." : "");
  }
  if (c.state === "out_of_range") {
    setBanner(`This program is unlike the jobs used for calibration (${c.outside.slice(0, 3).join(", ")}). Treat the range as unreliable; in the simulated tests, ranges missed far more often on programs like this.`);
  }
  const maxShare = Math.max(...r.hotspots.map((h) => h.share), 1e-9);
  $("hot").tBodies[0].innerHTML = r.hotspots.map((h) =>
    `<tr tabindex="0" role="button" aria-label="Go to line ${h.line_from}" data-line="${h.line_from}"><td>${h.line_from}–${h.line_to}</td>
     <td><div class="share"><i style="width:${(h.share / maxShare * 70).toFixed(1)}%"></i>${(h.share * 100).toFixed(0)} %</div></td>
     <td class="num">${fmtTime(h.time_s)}</td><td class="num ${h.slowdown > 1.25 ? "hot" : ""}">${h.slowdown.toFixed(2)}×</td></tr>`).join("");
  const s = r.stats;
  $("stats").innerHTML = [["Lines", s.lines], ["Blocks with motion or events", s.blocks], ["Cutting path", (s.cut_length_mm / 1000).toFixed(2) + " m"],
    ["Rapid travel", (s.rapid_length_mm / 1000).toFixed(2) + " m"], ["Tool changes", s.tool_changes],
    ["Extent X × Y × Z", s.bounds_max.map((v, i) => (v - s.bounds_min[i]).toFixed(0)).join(" × ") + " mm"]]
    .map(([k, v]) => `<div><dt>${k}</dt><dd>${v}</dd></div>`).join("");
  drawPath(r);
}

function renderIssues(list) {
  const n = { error: 0, warning: 0, info: 0 };
  list.forEach((i) => n[i.severity]++);
  $("issueCount").textContent = list.length ? `· ${n.error} to fix, ${n.warning} to review, ${n.info} notes` : "";
  $("issues").innerHTML = list.length ? list.map((i) =>
    `<li class="${i.severity}" ${i.line ? `tabindex="0" role="button"` : ""} data-line="${i.line}">
      <div class="head"><span class="tag">${{ error: "Fix", warning: "Review", info: "Note" }[i.severity]}</span><b>${esc(i.title)}</b>
      <span class="where">${i.line ? "line " + i.line : "whole program"} · ${esc(i.code)}</span></div>
      <div class="d">${esc(i.detail)}</div><div class="a">${esc(i.action)}</div></li>`).join("")
    : `<li class="none">No rule fired. This covers the listed rules only; it is not a collision or machine simulation.</li>`;
}

function drawPath(r) {
  const cv = $("plot"), ctx = cv.getContext("2d"), css = getComputedStyle(document.documentElement);
  const col = (n) => css.getPropertyValue(n).trim();
  const dpr = window.devicePixelRatio || 1, W = 640, H = 420;
  cv.width = W * dpr; cv.height = H * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, W, H);
  $("plotNote").textContent = "";
  if (!r || !r.path.length) return;
  const ax = view === "xy" ? [0, 1] : [0, 2];
  let lo = [Infinity, Infinity], hi = [-Infinity, -Infinity];
  for (const s of r.path) for (const p of s.pts) for (let k = 0; k < 2; k++) { lo[k] = Math.min(lo[k], p[ax[k]]); hi[k] = Math.max(hi[k], p[ax[k]]); }
  const pad = 28, sx = (W - 2 * pad) / Math.max(hi[0] - lo[0], 1e-6), sy = (H - 2 * pad) / Math.max(hi[1] - lo[1], 1e-6), sc = Math.min(sx, sy);
  const ox = pad + (W - 2 * pad - (hi[0] - lo[0]) * sc) / 2, oy = pad + (H - 2 * pad - (hi[1] - lo[1]) * sc) / 2;
  const X = (p) => ox + (p[ax[0]] - lo[0]) * sc, Y = (p) => H - oy - (p[ax[1]] - lo[1]) * sc;
  const stroke = (filter, style, dash, width) => {
    ctx.beginPath(); ctx.setLineDash(dash); ctx.strokeStyle = style; ctx.lineWidth = width;
    for (const s of r.path) { if (!filter(s)) continue; ctx.moveTo(X(s.pts[0]), Y(s.pts[0])); for (let i = 1; i < s.pts.length; i++) ctx.lineTo(X(s.pts[i]), Y(s.pts[i])); }
    ctx.stroke();
  };
  stroke((s) => s.k === "r", col("--rapid"), [4, 4], 1);
  stroke((s) => s.k !== "r" && !s.slow, col("--fast"), [], 1.4);
  stroke((s) => s.k !== "r" && s.slow, col("--slow"), [], 1.4);
  cv.setAttribute("aria-label", `Tool path, ${view === "xy" ? "top" : "front"} view, ${r.path.length} drawn moves, ${r.path.filter((s) => s.slow).length} of them well below the programmed feed`);
  ctx.setLineDash([]); ctx.fillStyle = col("--muted"); ctx.font = "11px " + css.getPropertyValue("--mono");
  const names = view === "xy" ? ["X", "Y"] : ["X", "Z"];
  ctx.fillText(`${names[0]} ${lo[0].toFixed(0)} … ${hi[0].toFixed(0)} mm`, pad, H - 8);
  ctx.save(); ctx.translate(12, H - pad); ctx.rotate(-Math.PI / 2); ctx.fillText(`${names[1]} ${lo[1].toFixed(0)} … ${hi[1].toFixed(0)} mm`, 0, 0); ctx.restore();
  if (r.stats.blocks > r.path.length * 1.5) $("plotNote").textContent = "Drawing thinned for display.";
}

el.code.addEventListener("input", () => { syncGutter(); markStale(); });
el.code.addEventListener("scroll", syncGutter);
el.run.addEventListener("click", run);
$("retry").addEventListener("click", () => (config ? run() : init().then(() => config && show("empty"))));
$("machine").addEventListener("change", sourceBadge);
$("sample").addEventListener("change", async (ev) => {
  if (!ev.target.value) return;
  try { el.code.value = (await api("/api/samples/" + encodeURIComponent(ev.target.value))).program; el.code.scrollTop = 0; syncGutter(); markStale(); }
  catch (e) { setBanner("The example could not be loaded: " + e.message); }
});
$("file").addEventListener("change", async (ev) => {
  const f = ev.target.files[0];
  if (!f) return;
  if (f.size > 5e6) { setBanner("That file is larger than 5 MB and was not loaded."); return; }
  el.code.value = await f.text(); $("sample").value = ""; syncGutter(); markStale();
});
for (const b of document.querySelectorAll(".seg button")) b.addEventListener("click", () => {
  view = b.dataset.view; document.querySelectorAll(".seg button").forEach((x) => x.classList.toggle("on", x === b)); drawPath(last && last.ok ? last : null);
});
function lineClick(ev) { const t = ev.target.closest("[data-line]"); if (t && (ev.type === "click" || ev.key === "Enter")) goToLine(Number(t.dataset.line)); }
for (const id of ["issues", "hot"]) { $(id).addEventListener("click", lineClick); $(id).addEventListener("keydown", lineClick); }
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => drawPath(last && last.ok ? last : null));
init();
