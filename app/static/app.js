const CLIENTS_REFRESH_MS = 1000;

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

updateDate();
setInterval(updateDate, 1000);

refreshClients();
setInterval(refreshClients, CLIENTS_REFRESH_MS);
