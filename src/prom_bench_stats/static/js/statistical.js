let statisticalCharts = [];

function destroyStatisticalCharts() {
  statisticalCharts.forEach((c) => c.destroy());
  statisticalCharts = [];
  const grid = document.getElementById("statistical-dash-grid");
  if (grid) grid.innerHTML = "";
}

async function renderStatisticalAnalysis() {
  showErr("");
  showEmpty("");
  
  const dashboardRaw = document.getElementById("grafana-json").value.trim();
  const runsRaw = document.getElementById("runs-json").value.trim();
  const numPoints = parseInt(document.getElementById("num-points").value) || 100;
  
  if (!dashboardRaw) {
    showErr("Paste Grafana dashboard JSON first.");
    return;
  }
  
  if (!runsRaw) {
    showErr("Paste runs JSON array first.");
    return;
  }
  
  let dashboard, runs;
  try {
    dashboard = JSON.parse(dashboardRaw);
    runs = JSON.parse(runsRaw);
  } catch (e) {
    showErr("Invalid JSON: " + e.message);
    return;
  }
  
  if (!Array.isArray(runs)) {
    showErr("Runs must be a JSON array.");
    return;
  }
  
  const btn = document.getElementById("statistical-render-btn");
  btn.disabled = true;
  btn.textContent = "Analyzing...";
  
  // Array to store charts with no data
  const noDataCharts = [];
  
  try {
    const stepV = document.getElementById("step-select").value;
    const body = {
      dashboard: dashboard,
      runs: runs,
      num_points: numPoints
    };
    
    if (stepV) body.step = stepV;
    
    const r = await fetch("/api/grafana/statistical-analysis", {
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
            : r.statusText || "statistical analysis failed"
      );
      return;
    }
    
    if (!j.success) {
      showErr(j.detail || "Statistical analysis failed");
      return;
    }
    
    const analysis = j.analysis;
    document.getElementById("statistical-note").textContent = j.note || "";
    
    destroyStatisticalCharts();
    const grid = document.getElementById("statistical-dash-grid");
    grid.innerHTML = "";
    
    (analysis.panels || []).forEach((panel) => {
      const gp = panel.gridPos || { x: 0, w: 24, h: 8 };
      const panelEl = document.createElement("div");
      panelEl.className = "gf-dash-panel";
      panelEl.style.gridColumn = `${gp.x + 1} / span ${gp.w}`;
      
      const title = document.createElement("h3");
      title.textContent = `${panel.title || "Statistical Analysis"} (${analysis.total_runs} runs)`;
      panelEl.appendChild(title);
      
      // Process each target in the panel
      (panel.targets || []).forEach((target, targetIndex) => {
        if (target.error) {
          // Add to no data list
          const chartName = target.legendFormat || target.expr || `Target ${targetIndex + 1}`;
          noDataCharts.push({
            panel: panel.title || 'Unknown Panel',
            chart: chartName,
            error: target.error
          });
          return;
        }
        
        if (!target.statistics || !target.statistics.datasets) {
          // Add to no data list
          const chartName = target.legendFormat || target.expr || `Target ${targetIndex + 1}`;
          noDataCharts.push({
            panel: panel.title || 'Unknown Panel',
            chart: chartName,
            error: 'No statistical data available'
          });
          return;
        }
        
        const stats = target.statistics;
        
        const tb = document.createElement("div");
        tb.className = "gf-target-block";
        
        const ex = document.createElement("div");
        ex.className = "gf-expr";
        ex.textContent = target.legendFormat || target.expr || `Target ${targetIndex + 1}`;
        tb.appendChild(ex);
        
        // Add info
        const info = document.createElement("div");
        info.className = "gf-smooth-hint";
        info.textContent = `${stats.num_runs} runs · ${stats.sample_count} samples/point · ${analysis.num_points} interpolated points`;
        tb.appendChild(info);
        
        // Add CSV button after info
        const downloadBtn = document.createElement("button");
        downloadBtn.className = "csv-download-btn";
        downloadBtn.innerHTML = "↓ CSV";
        downloadBtn.title = "Download this chart as CSV";
        downloadBtn.onclick = () => downloadIndividualChartCsv(target, stats, analysis, targetIndex);
        tb.appendChild(downloadBtn);
        
        // Create chart container
        const chartContainer = document.createElement("div");
        chartContainer.className = "gf-chart-combined";
        const inner = document.createElement("div");
        inner.className = "chart-inner";
        const canvas = document.createElement("canvas");
        inner.appendChild(canvas);
        chartContainer.appendChild(inner);
        
        tb.appendChild(chartContainer);
        
        const ctx = canvas.getContext("2d");
        const chart = new Chart(ctx, {
          type: "line",
          data: {
            labels: stats.labels,
            datasets: stats.datasets
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: "index", intersect: false },
            elements: {
              point: {
                radius: stats.labels.length > 50 ? 0 : 1,
                hoverRadius: 3
              }
            },
            plugins: {
              legend: {
                display: true,
                position: "bottom",
                labels: {
                  color: "#c4b5fd",
                  boxWidth: 14,
                  padding: 10,
                  font: { size: 11 }
                }
              },
              title: {
                display: false
              }
            },
            scales: {
              x: {
                title: {
                  display: true,
                  text: "Relative Time (%)",
                  color: "#9b92b8"
                },
                ticks: { color: "#9b92b8", maxTicksLimit: 16 },
                grid: { color: "rgba(139,92,246,0.12)" }
              },
              y: {
                title: {
                  display: true,
                  text: "Value",
                  color: "#9b92b8"
                },
                ticks: { color: "#9b92b8" },
                grid: { color: "rgba(139,92,246,0.12)" }
              }
            }
          }
        });
        
        statisticalCharts.push(chart);
        panelEl.appendChild(tb);
      });
      
      grid.appendChild(panelEl);
    });
    
    // Update data log with charts that have no data
    updateDataLog(noDataCharts);
    
    document.getElementById("statistical-results-section").hidden = false;
    
    // Store response for CSV download
    window.currentStatisticalResponse = j;
    
    // Show download buttons
    const downloadButtons = document.getElementById("download-buttons");
    if (downloadButtons) {
      downloadButtons.style.display = "block";
    }
    
    showEmpty(`Statistical analysis completed for ${analysis.total_runs} runs`);
    
  } catch (e) {
    showErr(String(e));
  } finally {
    btn.disabled = false;
    btn.textContent = "Analyze Runs";
  }
}

// Show/hide statistical section when dashboard JSON is pasted
document.getElementById("grafana-json").addEventListener("input", (e) => {
  const hasDashboard = e.target.value.trim().length > 0;
  document.getElementById("statistical-section").hidden = !hasDashboard;
});


document.getElementById("statistical-render-btn").addEventListener("click", renderStatisticalAnalysis);

// Function to update data log with charts that have no data
function updateDataLog(noDataCharts) {
  const dataLogSection = document.getElementById("data-log");
  const dataLogList = document.getElementById("data-log-list");
  
  if (!dataLogSection || !dataLogList) return;
  
  // Clear previous log entries
  dataLogList.innerHTML = "";
  
  if (noDataCharts.length === 0) {
    const emptyMessage = document.createElement("div");
    emptyMessage.className = "data-log-empty";
    emptyMessage.textContent = "All charts have data successfully loaded.";
    dataLogList.appendChild(emptyMessage);
    dataLogSection.hidden = true;
    return;
  }
  
  // Show log section and add entries
  dataLogSection.hidden = false;
  
  noDataCharts.forEach((item, index) => {
    const logItem = document.createElement("div");
    logItem.className = "data-log-item";
    logItem.innerHTML = `<strong>Panel:</strong> ${item.panel}<br><strong>Chart:</strong> ${item.chart}<br><strong>Reason:</strong> ${item.error}`;
    dataLogList.appendChild(logItem);
  });
}

// CSV download functionality
function escapeCsvField(field) {
  if (field === null || field === undefined) return '';
  const stringField = String(field);
  if (stringField.includes(',') || stringField.includes('"') || stringField.includes('\n')) {
    return `"${stringField.replace(/"/g, '""')}"`;
  }
  return stringField;
}

function downloadCsv(data, filename) {
  const csvContent = data.join('\n');
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);
  link.setAttribute('href', url);
  link.setAttribute('download', filename);
  link.style.visibility = 'hidden';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

function downloadAllChartsCsv() {
  const response = window.currentStatisticalResponse;
  if (!response || !response.panels) {
    showErr('No statistical data available for download');
    return;
  }

  let allCsvData = [];
  let headersAdded = false;

  response.panels.forEach(panel => {
    if (!panel.chart_data || !panel.chart_data.labels || !panel.chart_data.datasets) {
      return;
    }

    const labels = panel.chart_data.labels;
    const datasets = panel.chart_data.datasets;

    if (!headersAdded) {
      // Add headers
      const headerRow = ['Time', 'Relative Time (%)'];
      datasets.forEach(dataset => {
        headerRow.push(`${dataset.label} - Mean`);
        headerRow.push(`${dataset.label} - Std Dev`);
        headerRow.push(`${dataset.label} - Upper Bound`);
        headerRow.push(`${dataset.label} - Lower Bound`);
      });
      allCsvData.push(headerRow.map(escapeCsvField).join(','));
      headersAdded = true;
    }

    // Add data rows
    labels.forEach((label, index) => {
      const row = [label, (index / (labels.length - 1) * 100).toFixed(2)];
      datasets.forEach(dataset => {
        row.push(dataset.data[index] || '');
        row.push(dataset.std_data ? dataset.std_data[index] : '');
        row.push(dataset.upper_data ? dataset.upper_data[index] : '');
        row.push(dataset.lower_data ? dataset.lower_data[index] : '');
      });
      allCsvData.push(row.map(escapeCsvField).join(','));
    });
  });

  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
  downloadCsv(allCsvData, `statistical-analysis-all-${timestamp}.csv`);
}

function downloadIndividualChartCsv(target, stats, analysis, targetIndex) {
  if (!stats || !stats.labels || !stats.datasets) {
    showErr('No data available for this chart');
    return;
  }

  let csvData = [];
  const labels = stats.labels;
  const datasets = stats.datasets;
  const chartTitle = target.legendFormat || target.expr || `Chart-${targetIndex + 1}`;
  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);

  // Add headers
  const headerRow = ['Time', 'Relative Time (%)'];
  datasets.forEach(dataset => {
    headerRow.push(`${dataset.label} - Mean`);
    headerRow.push(`${dataset.label} - Std Dev`);
    headerRow.push(`${dataset.label} - Upper Bound`);
    headerRow.push(`${dataset.label} - Lower Bound`);
  });
  csvData.push(headerRow.map(escapeCsvField).join(','));

  // Add data rows
  labels.forEach((label, index) => {
    const row = [label, (index / (labels.length - 1) * 100).toFixed(2)];
    datasets.forEach(dataset => {
      const dataValue = dataset.data && dataset.data[index] !== undefined ? dataset.data[index] : '';
      const stdValue = dataset.std_data && dataset.std_data[index] !== undefined ? dataset.std_data[index] : '';
      const upperValue = dataset.upper_data && dataset.upper_data[index] !== undefined ? dataset.upper_data[index] : '';
      const lowerValue = dataset.lower_data && dataset.lower_data[index] !== undefined ? dataset.lower_data[index] : '';
      
      row.push(dataValue);
      row.push(stdValue);
      row.push(upperValue);
      row.push(lowerValue);
    });
    csvData.push(row.map(escapeCsvField).join(','));
  });

  const filename = `statistical-analysis-${chartTitle.replace(/[^a-zA-Z0-9]/g, '-')}-${timestamp}.csv`;
  downloadCsv(csvData, filename);
}

function downloadIndividualChartsCsv() {
  const response = window.currentStatisticalResponse;
  if (!response || !response.panels) {
    showErr('No statistical data available for download');
    return;
  }

  const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);

  response.panels.forEach((panel, panelIndex) => {
    if (!panel.chart_data || !panel.chart_data.labels || !panel.chart_data.datasets) {
      return;
    }

    let csvData = [];
    const labels = panel.chart_data.labels;
    const datasets = panel.chart_data.datasets;
    const panelTitle = panel.title || `Panel-${panelIndex + 1}`;

    // Add headers
    const headerRow = ['Time', 'Relative Time (%)'];
    datasets.forEach(dataset => {
      headerRow.push(`${dataset.label} - Mean`);
      headerRow.push(`${dataset.label} - Std Dev`);
      headerRow.push(`${dataset.label} - Upper Bound`);
      headerRow.push(`${dataset.label} - Lower Bound`);
    });
    csvData.push(headerRow.map(escapeCsvField).join(','));

    // Add data rows
    labels.forEach((label, index) => {
      const row = [label, (index / (labels.length - 1) * 100).toFixed(2)];
      datasets.forEach(dataset => {
        row.push(dataset.data[index] || '');
        row.push(dataset.std_data ? dataset.std_data[index] : '');
        row.push(dataset.upper_data ? dataset.upper_data[index] : '');
        row.push(dataset.lower_data ? dataset.lower_data[index] : '');
      });
      csvData.push(row.map(escapeCsvField).join(','));
    });

    const filename = `statistical-analysis-${panelTitle.replace(/[^a-zA-Z0-9]/g, '-')}-${timestamp}.csv`;
    downloadCsv(csvData, filename);
  });
}

// Add event listeners for download buttons
document.addEventListener("DOMContentLoaded", () => {
  const downloadAllBtn = document.getElementById("download-all-csv");
  const downloadIndividualBtn = document.getElementById("download-individual-csv");

  if (downloadAllBtn) {
    downloadAllBtn.addEventListener("click", downloadAllChartsCsv);
  }

  if (downloadIndividualBtn) {
    downloadIndividualBtn.addEventListener("click", downloadIndividualChartsCsv);
  }
});
