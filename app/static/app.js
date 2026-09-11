const CLIENTS_REFRESH_MS = 1000;
const STATS_REFRESH_MS = 1000;
const SYSTEM_REFRESH_MS = 2000;

const THROUGHPUT_HISTORY_CAP = 300;  // 5 min at 1s/poll, in-memory only
const HISTORY_REFRESH_MS = 60000;    // CPU/temperature history is server-side, sampled once/min

const CHART_PALETTE = ["#2563eb", "#e8590c", "#2f9e44", "#ae3ec9", "#f08c00", "#0c8599"];

function formatNow() {
  const now = new Date();
  const date = now.toLocaleDateString(undefined, {
    weekday: "short",
    year: "numeric",
    month: "short",
    day: "numeric",
  });
  const time = now.toLocaleTimeString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
  return `${date}, ${time}`;
}

function updateDate() {
  document.getElementById("date").textContent = formatNow();
}

async function getJSON(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`${url} -> ${res.status}`);
  return res.json();
}

async function refreshClients() {
  const data = await getJSON("/api/network/clients");
  const tbody = document.querySelector("#clients-table tbody");
  tbody.innerHTML = "";

  if (data.clients.length === 0) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td colspan="4" class="empty">No devices detected yet</td>`;
    tbody.appendChild(tr);
    return;
  }

  for (const c of data.clients) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${c.ip}</td><td>${c.mac}</td><td>${c.name || "-"}</td><td>${c.vendor || "-"}</td>`;
    tbody.appendChild(tr);
  }
}

function formatRate(bytesPerSec) {
  if (bytesPerSec < 1024) return `${bytesPerSec.toFixed(0)} B/s`;
  if (bytesPerSec < 1024 * 1024) return `${(bytesPerSec / 1024).toFixed(1)} KB/s`;
  return `${(bytesPerSec / (1024 * 1024)).toFixed(1)} MB/s`;
}

function formatTemp(c) {
  return `${c.toFixed(1)}°C`;
}

function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function pushCapped(arr, point, cap) {
  arr.push(point);
  if (arr.length > cap) arr.shift();
}

function toPoints(rows) {
  return rows.map(([t, v]) => ({ t, v }));
}

function filterWindow(points, windowH) {
  if (!windowH) return points;
  const cutoff = Date.now() - windowH * 3600 * 1000;
  return points.filter((p) => p.t >= cutoff);
}

// key -> {windowH, minV, maxV}; null means "auto". Only charts created with
// opts.controls=true (CPU/temperature) get an entry and on-page inputs.
const chartSettings = {};

function wireChartControls(block, key, onChange) {
  const windowInput = block.querySelector(".ctl-window");
  const minInput = block.querySelector(".ctl-min");
  const maxInput = block.querySelector(".ctl-max");
  const resetBtn = block.querySelector(".ctl-reset");

  const apply = () => {
    const w = parseFloat(windowInput.value);
    const mn = parseFloat(minInput.value);
    const mx = parseFloat(maxInput.value);
    chartSettings[key] = {
      windowH: windowInput.value !== "" && w > 0 ? w : null,
      minV: minInput.value !== "" && !Number.isNaN(mn) ? mn : null,
      maxV: maxInput.value !== "" && !Number.isNaN(mx) ? mx : null,
    };
    onChange();
  };

  windowInput.addEventListener("input", apply);
  minInput.addEventListener("input", apply);
  maxInput.addEventListener("input", apply);
  resetBtn.addEventListener("click", () => {
    windowInput.value = "";
    minInput.value = "";
    maxInput.value = "";
    apply();
  });
}

function ensureChartBlock(container, key, opts) {
  let block = container.querySelector(`[data-key="${key}"]`);
  if (block) return block;
  block = document.createElement("div");
  block.className = "chart-block";
  block.dataset.key = key;

  const controlsHtml = opts.controls
    ? `<div class="chart-controls">
        <label>Window (h)<input type="number" class="ctl-window" step="0.5" min="0" placeholder="auto"></label>
        <label>Min<input type="number" class="ctl-min" step="any" placeholder="auto"></label>
        <label>Max<input type="number" class="ctl-max" step="any" placeholder="auto"></label>
        <button type="button" class="ctl-reset">Reset</button>
      </div>`
    : "";
  block.innerHTML = `<div class="chart-title"></div>${controlsHtml}<canvas></canvas><div class="chart-legend"></div>`;
  container.appendChild(block);

  if (opts.controls) {
    chartSettings[key] = { windowH: null, minV: null, maxV: null };
    wireChartControls(block, key, opts.onChange);
  }
  return block;
}

// Plain canvas line chart, no dependencies: auto-scaled Y axis (unless
// opts.minV/maxV pin it), gridlines, one line per series.
function drawChart(canvas, series, opts = {}) {
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  const w = rect.width, h = rect.height;
  if (w === 0 || h === 0) return;
  canvas.width = w * dpr;
  canvas.height = h * dpr;
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);

  const points = series.flatMap((s) => s.points);
  if (points.length < 2) return;

  const minT = Math.min(...points.map((p) => p.t));
  const maxT = Math.max(...points.map((p) => p.t));
  let minV = opts.minV ?? Math.min(...points.map((p) => p.v));
  let maxV = opts.maxV ?? Math.max(...points.map((p) => p.v));
  if (maxV - minV < 1e-6) { minV -= 1; maxV += 1; }
  if (opts.minV === undefined || opts.maxV === undefined) {
    const pad = (maxV - minV) * 0.1;
    if (opts.minV === undefined) minV -= pad;
    if (opts.maxV === undefined) maxV += pad;
  }

  const fmt = opts.fmt || ((v) => v.toFixed(0));
  ctx.font = "10px system-ui, sans-serif";
  const labelMax = fmt(maxV), labelMin = fmt(minV);
  const padL = Math.max(24, ctx.measureText(labelMax).width, ctx.measureText(labelMin).width) + 8;
  const padB = 4, padT = 6, padR = 4;
  const plotW = w - padL - padR, plotH = h - padT - padB;

  const x = (t) => padL + ((t - minT) / (maxT - minT || 1)) * plotW;
  const y = (v) => padT + plotH - ((v - minV) / (maxV - minV || 1)) * plotH;

  ctx.strokeStyle = cssVar("--border");
  ctx.lineWidth = 1;
  ctx.beginPath();
  for (let i = 0; i <= 2; i++) {
    const gy = padT + (plotH / 2) * i;
    ctx.moveTo(padL, gy);
    ctx.lineTo(w - padR, gy);
  }
  ctx.stroke();

  ctx.fillStyle = cssVar("--muted");
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  ctx.fillText(labelMax, padL - 6, padT + 2);
  ctx.fillText(labelMin, padL - 6, padT + plotH - 2);

  for (const s of series) {
    if (s.points.length < 2) continue;
    ctx.strokeStyle = s.color;
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    s.points.forEach((p, i) => {
      const px = x(p.t), py = y(p.v);
      if (i === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    });
    ctx.stroke();
  }
}

function updateLegend(block, series) {
  block.querySelector(".chart-legend").innerHTML = series
    .map((s) => `<span class="legend-item"><span class="legend-dot" style="background:${s.color}"></span>${s.label}</span>`)
    .join("");
}

function renderChart(container, key, title, series, opts = {}) {
  const block = ensureChartBlock(container, key, opts);
  block.querySelector(".chart-title").textContent = title;
  drawChart(block.querySelector("canvas"), series, opts);
  updateLegend(block, series);
}

let lastStatsSample = null;
const throughputHistory = {}; // interface -> {rx: [{t,v}], tx: [{t,v}]}

async function refreshStats() {
  const data = await getJSON("/api/stats/throughput");
  const tbody = document.querySelector("#stats-table tbody");
  tbody.innerHTML = "";

  if (data.interfaces.length === 0) {
    tbody.innerHTML = `<tr><td colspan="3" class="empty">No interfaces configured</td></tr>`;
    return;
  }

  const prev = lastStatsSample;
  lastStatsSample = {};
  const chartsContainer = document.getElementById("throughput-charts");

  for (const s of data.interfaces) {
    lastStatsSample[s.interface] = s;
    const p = prev && prev[s.interface];
    const dt = p ? s.timestamp - p.timestamp : 0;
    const rxDelta = p ? s.rx_bytes - p.rx_bytes : -1;
    const txDelta = p ? s.tx_bytes - p.tx_bytes : -1;

    const tr = document.createElement("tr");
    if (dt <= 0 || rxDelta < 0 || txDelta < 0) {
      tr.innerHTML = `<td>${s.interface}</td><td colspan="2" class="empty">Measuring...</td>`;
      tbody.appendChild(tr);
      continue;
    }

    const rxRate = rxDelta / dt, txRate = txDelta / dt;
    tr.innerHTML = `<td>${s.interface}</td><td>${formatRate(rxRate)}</td><td>${formatRate(txRate)}</td>`;
    tbody.appendChild(tr);

    const hist = throughputHistory[s.interface] || (throughputHistory[s.interface] = { rx: [], tx: [] });
    const t = Date.now();
    pushCapped(hist.rx, { t, v: rxRate }, THROUGHPUT_HISTORY_CAP);
    pushCapped(hist.tx, { t, v: txRate }, THROUGHPUT_HISTORY_CAP);

    renderChart(
      chartsContainer,
      s.interface,
      s.interface,
      [
        { label: "Download", color: CHART_PALETTE[0], points: hist.rx },
        { label: "Upload", color: CHART_PALETTE[1], points: hist.tx },
      ],
      { fmt: formatRate, minV: 0 }
    );
  }
}

async function refreshSystem() {
  const data = await getJSON("/api/stats/system");
  const tbody = document.querySelector("#system-table tbody");
  tbody.innerHTML = "";

  const rows = [["CPU (overall)", `${data.cpu_percent.toFixed(0)}%`]];
  data.cpu_percent_per_core.forEach((pct, i) => {
    rows.push([`CPU core ${i}`, `${pct.toFixed(0)}%`]);
  });

  if (data.temperatures.length === 0) {
    rows.push(["Temperature", "Not available"]);
  } else {
    for (const t of data.temperatures) {
      const extra = t.high != null ? ` (high: ${formatTemp(t.high)})` : "";
      rows.push([t.sensor, `${formatTemp(t.current)}${extra}`]);
    }
  }

  for (const [label, value] of rows) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${label}</td><td>${value}</td>`;
    tbody.appendChild(tr);
  }
}

// CPU/temperature charts are backed by the server-side history file
// (app/services/history_service.py) instead of an in-memory buffer, so
// they survive a page reload and don't need the tab left open for hours.
// The fetched data is cached so the Window/Min/Max controls can redraw
// instantly, without waiting for the next poll.
let latestHistory = { cpu: [], temperatures: {} };

function windowLabel(settings) {
  return settings.windowH ? `${settings.windowH}h` : "auto";
}

function renderCpuChart() {
  const settings = chartSettings.cpu || { windowH: null, minV: null, maxV: null };
  const points = filterWindow(toPoints(latestHistory.cpu), settings.windowH);
  renderChart(
    document.getElementById("cpu-charts"),
    "cpu",
    `CPU usage (${windowLabel(settings)})`,
    [{ label: "CPU", color: CHART_PALETTE[0], points }],
    { fmt: (v) => `${v.toFixed(0)}%`, minV: settings.minV ?? undefined, maxV: settings.maxV ?? undefined, controls: true, onChange: renderCpuChart }
  );
}

function renderTempChart() {
  const sensors = Object.keys(latestHistory.temperatures);
  if (sensors.length === 0) return;
  const settings = chartSettings.temp || { windowH: null, minV: null, maxV: null };
  const series = sensors.map((sensor, i) => ({
    label: sensor,
    color: CHART_PALETTE[i % CHART_PALETTE.length],
    points: filterWindow(toPoints(latestHistory.temperatures[sensor]), settings.windowH),
  }));
  renderChart(
    document.getElementById("temp-charts"),
    "temp",
    `Temperature (${windowLabel(settings)})`,
    series,
    { fmt: formatTemp, minV: settings.minV ?? undefined, maxV: settings.maxV ?? undefined, controls: true, onChange: renderTempChart }
  );
}

async function refreshHistory() {
  latestHistory = await getJSON("/api/stats/history");
  renderCpuChart();
  renderTempChart();
}

function initTabs() {
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const tab = btn.dataset.tab;
      document.querySelectorAll("[data-panel]").forEach((panel) => {
        panel.hidden = panel.dataset.panel !== tab;
      });
    });
  });
}

initTabs();

updateDate();
setInterval(updateDate, 1000);

refreshClients();
setInterval(refreshClients, CLIENTS_REFRESH_MS);

refreshStats();
setInterval(refreshStats, STATS_REFRESH_MS);

refreshSystem();
setInterval(refreshSystem, SYSTEM_REFRESH_MS);

refreshHistory();
setInterval(refreshHistory, HISTORY_REFRESH_MS);
