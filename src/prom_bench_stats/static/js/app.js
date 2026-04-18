const errEl = document.getElementById("err");
const emptyHint = document.getElementById("empty-hint");
const form = document.getElementById("form");
const grid = document.getElementById("grid");
const meta = document.getElementById("meta");
const charts = [];
let dashCharts = [];
let panelChartMap = new Map(); // panelId -> {targetIndex: chart}

function destroyDashboardCharts() {
  dashCharts.forEach((c) => c.destroy());
  dashCharts = [];
  panelChartMap.clear();
  const dg = document.getElementById("grafana-dash-grid");
  if (dg) dg.innerHTML = "";
}

function appendPerSeriesCharts(parentEl, per, chartsStore) {
  per.forEach((s, i) => {
    const card = document.createElement("div");
    card.className = "chart-card";
    const h = document.createElement("h3");
    h.textContent = s.title || s.metric_name || "Series " + (i + 1);
    const sub = document.createElement("div");
    sub.className = "sub";
    sub.textContent = s.subtitle || "";
    const inner = document.createElement("div");
    inner.className = "chart-inner";
    const canvas = document.createElement("canvas");
    inner.appendChild(canvas);
    card.appendChild(h);
    card.appendChild(sub);
    card.appendChild(inner);
    parentEl.appendChild(card);

    const color = s.color || "#818cf8";
    const ctx = canvas.getContext("2d");
    const ch = new Chart(ctx, {
      ...chartOpts(null, color),
      data: {
        labels: s.labels,
        datasets: [
          {
            label: s.metric_name,
            data: s.data,
            borderColor: color,
            backgroundColor: color + "33",
            fill: false,
            tension: 0,
            spanGaps: true,
            pointRadius: s.point_count > 120 ? 0 : 2,
          },
        ],
      },
    });
    chartsStore.push(ch);
  });
}

/**
 * One Chart.js with multiple colored datasets (series share time axis).
 * @param {string|null} titleText - optional chart title
 * @param {boolean} fullWidth - use chart-card--large
 */
function mountCombinedChart(parentEl, c, titleText, chartsStore, fullWidth) {
  if (!c || !c.datasets || !c.datasets.length) return null;
  const nLab = (c.labels && c.labels.length) || 0;
  const pr = nLab > 100 ? 0 : 2;
  const card = document.createElement("div");
  card.className = "chart-card" + (fullWidth ? " chart-card--large" : "");
  if (!fullWidth) card.classList.add("gf-chart-combined");
  const inner = document.createElement("div");
  inner.className = "chart-inner";
  const canvas = document.createElement("canvas");
  inner.appendChild(canvas);
  card.appendChild(inner);
  parentEl.appendChild(card);
  const multi = c.datasets.length > 1;
  const ds = c.datasets.map((d) => ({
    ...d,
    tension: 0,
    pointRadius: pr,
    borderWidth: multi ? 2 : 1.5,
  }));
  const ctx = canvas.getContext("2d");
  const ch = new Chart(ctx, {
    type: "line",
    data: { labels: c.labels, datasets: ds },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: {
          display: multi,
          position: "bottom",
          labels: {
            color: "#c4b5fd",
            boxWidth: 14,
            padding: 10,
            font: { size: 11 },
          },
        },
        title: titleText
          ? { display: true, text: titleText, color: "#e9e4ff", font: { size: 13 } }
          : { display: false },
      },
      scales: {
        x: {
          ticks: { color: "#9b92b8", maxTicksLimit: 16 },
          grid: { color: "rgba(139,92,246,0.12)" },
        },
        y: { ticks: { color: "#9b92b8" }, grid: { color: "rgba(139,92,246,0.12)" } },
      },
    },
  });
  chartsStore.push(ch);
  return ch;
}

function showErr(msg) {
  errEl.textContent = msg;
  errEl.hidden = !msg;
}
function showEmpty(msg) {
  emptyHint.textContent = msg;
  emptyHint.hidden = !msg;
}

function chartOpts(title, color) {
  return {
    type: "line",
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { display: false },
        title: { display: !!title, text: title, color: "#e9e4ff", font: { size: 11 } },
      },
      scales: {
        x: { ticks: { color: "#9b92b8", maxTicksLimit: 8 }, grid: { color: "rgba(139,92,246,0.12)" } },
        y: { ticks: { color: "#9b92b8" }, grid: { color: "rgba(139,92,246,0.12)" } },
      },
    },
  };
}

async function refreshDiagnostics() {
  const dot = document.getElementById("conn-dot");
  const text = document.getElementById("conn-text");
  const urlEl = document.getElementById("prom-url");
  try {
    const r = await fetch("/api/diagnostics");
    const d = await r.json();
    urlEl.textContent = d.prometheus_url || "";
    if (d.error || !d.reachable) {
      dot.className = "dot bad";
      text.textContent = d.error ? "Cannot reach Prometheus" : "Unreachable";
      return;
    }
    dot.className = "dot ok";
    const n = d.instant_up_series;
    const mcount = d.metric_name_count;
    text.textContent =
      n != null
        ? `Scrape targets (up): ${n} · Metric names: ${mcount ?? "?"}`
        : "Connected";
  } catch (e) {
    document.getElementById("conn-dot").className = "dot bad";
    document.getElementById("conn-text").textContent = "Diagnostics failed";
  }
}

let dashboardAutoRefreshTimer = null;

function scheduleAutoRefresh(enabled) {
  if (dashboardAutoRefreshTimer) {
    clearInterval(dashboardAutoRefreshTimer);
    dashboardAutoRefreshTimer = null;
  }
  if (!enabled || currentWindowOffset > 0) return;
  const fromTime = document.getElementById("from-time").value;
  const toTime = document.getElementById("to-time").value;
  if (fromTime || toTime) return;
  dashboardAutoRefreshTimer = setInterval(() => {
    renderGrafanaDashboard();
  }, 30000);
}

function parseLocalISO(value) {
  return value ? new Date(value).toISOString() : null;
}