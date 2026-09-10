function formatToday() {
  return new Date().toLocaleDateString(undefined, {
    weekday: "short",
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function updateDate() {
  document.getElementById("date").textContent = formatToday();
}

updateDate();
setInterval(updateDate, 60 * 1000);
