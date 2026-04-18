function formatTimestampLabel(ts) {
  return new Date(ts * 1000).toISOString().slice(11, 19);
}

function buildPanelCombinedChart(panelTargets) {
  const timestamps = new Set();
  const rawDatasets = [];
  const palette = [
    "#60a5fa",
    "#4ade80",
    "#fbbf24",
    "#fb7185",
    "#c084fc",
    "#2dd4bf",
    "#f472b6",
    "#a3e635",
    "#fb923c",
    "#818cf8",
    "#34d399",
    "#facc15",
    "#e879f9",
    "#38bdf8",
    "#4d7c0f",
    "#be123c",
  ];

  panelTargets.forEach((tgt, tgtIndex) => {
    const targetLabel = (tgt.legendFormat || tgt.expr || `Target ${tgtIndex + 1}`).trim();

    if (tgt.chart?.datasets?.length && Array.isArray(tgt.chart.timestamps)) {
      tgt.chart.timestamps.forEach((ts) => timestamps.add(ts));
      tgt.chart.datasets.forEach((ds, dsIndex) => {
        const label = tgt.chart.datasets.length === 1
          ? targetLabel
          : `${targetLabel} / ${ds.label || `series ${dsIndex + 1}`}`;
        rawDatasets.push({
          label,
          values: tgt.chart.timestamps.map((ts, idx) => [ts, ds.data[idx]]),
        });
      });
      return;
    }

    if (Array.isArray(tgt.per_series) && tgt.per_series.length) {
      tgt.per_series.forEach((series, seriesIndex) => {
        (series.timestamps || []).forEach((ts) => timestamps.add(ts));
        const label = tgt.per_series.length === 1
          ? targetLabel
          : `${targetLabel} / ${series.metric_name || `Series ${seriesIndex + 1}`}`;
        rawDatasets.push({
          label,
          values: (series.timestamps || []).map((ts, idx) => [ts, series.data[idx]]),
        });
      });
    }
  });

  if (!rawDatasets.length) {
    return null;
  }

  const sortedTimestamps = Array.from(timestamps).sort((a, b) => a - b);
  const labels = sortedTimestamps.map(formatTimestampLabel);
  const datasets = rawDatasets.map((raw, idx) => {
    const color = palette[idx % palette.length];
    const valueMap = new Map(raw.values);
    return {
      label: raw.label,
      borderColor: color,
      backgroundColor: color + "33",
      fill: false,
      tension: 0,
      spanGaps: true,
      pointRadius: sortedTimestamps.length > 120 ? 0 : 2,
      data: sortedTimestamps.map((ts) => (valueMap.has(ts) ? valueMap.get(ts) : null)),
    };
  });

  return { labels, datasets, timestamps: sortedTimestamps };
}

async function renderGrafanaDashboard() {
  showErr("");
  showEmpty("");
  const raw = document.getElementById("grafana-json").value.trim();
  if (!raw) {
    showErr("Paste Grafana dashboard JSON first.");
    return;
  }
  let payload;
  try {
    payload = JSON.parse(raw);
  } catch (e) {
    showErr("Invalid JSON: " + e.message);
    return;
  }
  const btn = document.getElementById("grafana-render-dash");
  btn.disabled = true;
  try {
    const minutes = parseFloat(document.getElementById("minutes").value, 10);
    const fromTimeElement = document.getElementById("from-time");
    const toTimeElement = document.getElementById("to-time");
    const fromTime = fromTimeElement ? parseLocalISO(fromTimeElement.value) : null;
    const toTime = toTimeElement ? parseLocalISO(toTimeElement.value) : null;
    const body = { dashboard: payload };
    if (fromTime && toTime) {
      body.from = fromTime;
      body.to = toTime;
    } else {
      body.minutes = minutes;
      if (currentWindowOffset > 0) {
        body.end_offset_minutes = currentWindowOffset;
      }
    }
    const stepV = document.getElementById("step-select").value;
    if (stepV) body.step = stepV;
    const r = await fetch("/api/grafana/render-dashboard", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) {
      const d = j.detail;
      showErr(
        typeof d === "string"
          ? d
          : Array.isArray(d)
            ? d.map((x) => x.msg || x).join("; ")
            : r.statusText || "render-dashboard failed"
      );
      return;
    }
    document.getElementById("grafana-dash-note").textContent = j.note || "";
    const mount = document.getElementById("grafana-dash-grid");
    destroyDashboardCharts();
    mount.innerHTML = "";
    (j.panels || []).forEach((panel) => {
        const gp = panel.gridPos || { x: 0, w: 24 };
      const pel = document.createElement("div");
      pel.className = "gf-dash-panel";
      pel.style.gridColumn = `${gp.x + 1} / span ${gp.w}`;

      const ht = document.createElement("h3");
      ht.textContent = panel.title || "Panel";
      pel.appendChild(ht);

      const renderableTargets = (panel.targets || []).filter((tgt) => !tgt.error);
      const panelChart = buildPanelCombinedChart(renderableTargets);
      if (panelChart) {
        const tb = document.createElement("div");
        tb.className = "gf-target-block";
        const exprBlock = document.createElement("div");
        exprBlock.className = "gf-expr";
        renderableTargets.forEach((tgt, idx) => {
          const line = document.createElement("div");
          line.textContent = tgt.legendFormat ? tgt.legendFormat : tgt.expr || `Target ${idx + 1}`;
          exprBlock.appendChild(line);
        });
        tb.appendChild(exprBlock);
        mountCombinedChart(tb, panelChart, null, dashCharts, false);
        pel.appendChild(tb);
      } else if (renderableTargets.length) {
        const tb = document.createElement("div");
        tb.className = "gf-target-block";
        const exprBlock = document.createElement("div");
        exprBlock.className = "gf-expr";
        renderableTargets.forEach((tgt, idx) => {
          const line = document.createElement("div");
          line.textContent = tgt.legendFormat ? tgt.legendFormat : tgt.expr || `Target ${idx + 1}`;
          exprBlock.appendChild(line);
        });
        tb.appendChild(exprBlock);
        const nd = document.createElement("div");
        nd.className = "gf-no-data";
        nd.textContent = "No Data";
        tb.appendChild(nd);
        pel.appendChild(tb);
      }

      (panel.targets || []).forEach((tgt) => {
        if (!tgt.error) return;
        const tb = document.createElement("div");
        tb.className = "gf-target-block";
        const ex = document.createElement("div");
        ex.className = "gf-expr";
        ex.textContent = tgt.expr || "";
        tb.appendChild(ex);
        if (tgt.smoothing_hint) {
          const sh = document.createElement("div");
          sh.className = "gf-smooth-hint";
          sh.textContent = tgt.smoothing_hint;
          tb.appendChild(sh);
        }
        const er = document.createElement("div");
        er.className = "gf-err";
        er.textContent = tgt.error;
        tb.appendChild(er);
        pel.appendChild(tb);
      });

      mount.appendChild(pel);
    });
    document.getElementById("grafana-dash-section").hidden = false;
    showEmpty("Dashboard rendered below. Prometheus step: " + (j.step || "—"));
  } catch (e) {
    showErr(String(e));
  } finally {
    btn.disabled = false;
    scheduleAutoRefresh(document.getElementById("auto-refresh").checked);
  }
}

let currentWindowOffset = 0; // in minutes, how much to shift back from now

function updateWindowLabel() {
  const minutes = parseFloat(document.getElementById('minutes').value);
  if (currentWindowOffset === 0) {
    document.getElementById('window-label').textContent = `Last ${minutes}m`;
  } else {
    const offsetStr = currentWindowOffset > 0 ? `-${currentWindowOffset}m` : `+${-currentWindowOffset}m`;
    document.getElementById('window-label').textContent = `Last ${minutes}m (${offsetStr})`;
  }
}

document.querySelectorAll('.time-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.time-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('minutes').value = btn.dataset.minutes;
    currentWindowOffset = 0;
    updateWindowLabel();
  });
});

document.getElementById('shift-back').addEventListener('click', () => {
  const minutes = parseFloat(document.getElementById('minutes').value);
  currentWindowOffset += minutes;
  updateWindowLabel();
  renderGrafanaDashboard();
});

document.getElementById('shift-forward').addEventListener('click', () => {
  const minutes = parseFloat(document.getElementById('minutes').value);
  currentWindowOffset = Math.max(0, currentWindowOffset - minutes);
  updateWindowLabel();
  renderGrafanaDashboard();
});

document.getElementById("form").addEventListener("submit", (e) => {
  e.preventDefault();
  renderGrafanaDashboard();
});

document.getElementById("auto-refresh").addEventListener("change", (e) => {
  scheduleAutoRefresh(e.target.checked);
});

refreshDiagnostics();
setInterval(refreshDiagnostics, 30000);
updateWindowLabel();
scheduleAutoRefresh(document.getElementById("auto-refresh").checked);