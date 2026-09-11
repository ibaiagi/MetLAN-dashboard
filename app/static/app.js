const CLIENTS_REFRESH_MS = 1000;
const STATS_REFRESH_MS = 1000;
const SYSTEM_REFRESH_MS = 2000;

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

let lastStatsSample = null;

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

  for (const s of data.interfaces) {
    lastStatsSample[s.interface] = s;
    const p = prev && prev[s.interface];
    const dt = p ? s.timestamp - p.timestamp : 0;
    const rxDelta = p ? s.rx_bytes - p.rx_bytes : -1;
    const txDelta = p ? s.tx_bytes - p.tx_bytes : -1;

    const tr = document.createElement("tr");
    if (dt <= 0 || rxDelta < 0 || txDelta < 0) {
      tr.innerHTML = `<td>${s.interface}</td><td colspan="2" class="empty">Measuring...</td>`;
    } else {
      tr.innerHTML = `<td>${s.interface}</td><td>${formatRate(rxDelta / dt)}</td><td>${formatRate(txDelta / dt)}</td>`;
    }
    tbody.appendChild(tr);
  }
}

function formatTemp(c) {
  return `${c.toFixed(1)}°C`;
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
