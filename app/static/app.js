const REFRESH_MS = 5000;

function fmtBytes(bytesPerSec) {
  if (bytesPerSec === null || bytesPerSec === undefined) return "-";
  if (bytesPerSec < 1024) return `${bytesPerSec.toFixed(0)} B/s`;
  return `${(bytesPerSec / 1024).toFixed(1)} KB/s`;
}

function fmtTime(unixSeconds) {
  return new Date(unixSeconds * 1000).toLocaleTimeString();
}

async function getJSON(url, options) {
  const res = await fetch(url, options);
  if (!res.ok) throw new Error(`${url} -> ${res.status}`);
  return res.json();
}

async function refreshDongle() {
  const state = await getJSON("/api/dongle/power");
  const badge = document.getElementById("dongle-state");
  const button = document.getElementById("dongle-toggle");
  const hint = document.getElementById("dongle-hint");

  if (!state.available) {
    badge.textContent = "unavailable";
    badge.className = "badge unavailable";
    button.disabled = true;
    hint.textContent = state.reason
      ? `Relay not connected: ${state.reason}`
      : "Relay hardware not connected yet.";
    return;
  }

  badge.textContent = state.state;
  badge.className = `badge ${state.state}`;
  button.disabled = false;
  hint.textContent = `GPIO pin ${state.gpio_pin}`;

  button.onclick = async () => {
    button.disabled = true;
    await getJSON("/api/dongle/power", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ state: state.state !== "on" }),
    });
    await refreshDongle();
    await refreshLog();
  };
}

async function refreshModem() {
  const modem = await getJSON("/api/dongle/modem");
  const dl = document.getElementById("modem-fields");
  dl.innerHTML = "";
  const rows = modem.connected
    ? {
        State: modem.state,
        Operator: modem.operator || "-",
        Signal: modem.signal_quality_percent !== null ? `${modem.signal_quality_percent}%` : "-",
        Technology: modem.access_technology || "-",
      }
    : { Status: "Not connected", Reason: modem.reason };
  for (const [k, v] of Object.entries(rows)) {
    const row = document.createElement("div");
    row.innerHTML = `<dt>${k}</dt><dd>${v}</dd>`;
    dl.appendChild(row);
  }
}

async function refreshInternet() {
  const data = await getJSON("/api/network/status");
  const dl = document.getElementById("internet-fields");
  dl.innerHTML = "";
  const net = data.internet;
  const rows = net.reachable
    ? { Status: "Reachable", Latency: `${net.latency_ms} ms`, Probe: net.probe_host }
    : { Status: "Unreachable", Error: net.error || "-" };
  for (const [k, v] of Object.entries(rows)) {
    const row = document.createElement("div");
    row.innerHTML = `<dt>${k}</dt><dd>${v}</dd>`;
    dl.appendChild(row);
  }

  const tbody = document.querySelector("#interfaces-table tbody");
  tbody.innerHTML = "";
  for (const iface of data.interfaces) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${iface.name}</td>
      <td>${iface.role}</td>
      <td>${iface.is_up ? "yes" : "no"}</td>
      <td>${iface.ipv4 || "-"}</td>
      <td>${fmtBytes(iface.rx_bytes_per_sec)}</td>
      <td>${fmtBytes(iface.tx_bytes_per_sec)}</td>`;
    tbody.appendChild(tr);
  }
}

async function refreshClients() {
  const data = await getJSON("/api/network/clients");
  const tbody = document.querySelector("#clients-table tbody");
  tbody.innerHTML = "";
  for (const c of data.clients) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${c.ip || "-"}</td><td>${c.mac || "-"}</td><td>${c.state || "-"}</td>`;
    tbody.appendChild(tr);
  }
}

async function refreshLog() {
  const data = await getJSON("/api/dongle/log");
  const list = document.getElementById("log-list");
  list.innerHTML = "";
  for (const entry of data.log) {
    const li = document.createElement("li");
    li.textContent = `${fmtTime(entry.timestamp)} — ${entry.action}`;
    list.appendChild(li);
  }
}

function tickClock() {
  document.getElementById("clock").textContent = new Date().toLocaleString();
}

async function refreshAll() {
  tickClock();
  await Promise.allSettled([
    refreshDongle(),
    refreshModem(),
    refreshInternet(),
    refreshClients(),
    refreshLog(),
  ]);
}

refreshAll();
setInterval(refreshAll, REFRESH_MS);
setInterval(tickClock, 1000);
