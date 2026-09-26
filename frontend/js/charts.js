/**
 * Depth-profile, model-vs-observation and difference charts.
 * Chart.js throughout, so the whole visual layer stays in one library.
 */

export class ProfileCharts {
  constructor(canvasId) {
    this.ctx = document.getElementById(canvasId).getContext("2d");
    this.chart = null;
  }

  renderProfile({ modelProfile, observationProfile, variable, unit }) {
    if (this.chart) this.chart.destroy();

    this.chart = new Chart(this.ctx, {
      type: "line",
      data: {
        datasets: [
          {
            label: "Model (derived)",
            data: modelProfile,
            borderColor: "#f59e0b",
            backgroundColor: "rgba(245,158,11,0.12)",
            parsing: { xAxisKey: "value", yAxisKey: "depth" },
            tension: 0.2,
          },
          {
            label: "Observation (measured)",
            data: observationProfile,
            borderColor: "#22d3ee",
            backgroundColor: "rgba(34,211,238,0.15)",
            parsing: { xAxisKey: "value", yAxisKey: "depth" },
            pointRadius: 3,
            tension: 0.2,
          },
        ],
      },
      options: {
        indexAxis: "y",                 // depth on the vertical axis
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            reverse: true,
            title: { display: true, text: "Depth (m)" },
          },
          x: { title: { display: true, text: `${variable} (${unit})` } },
        },
        plugins: {
          legend: { labels: { color: "#cbd5e1" } },
          tooltip: { callbacks: { label: (c) => `${c.dataset.label}: ${c.parsed.x}` } },
        },
      },
    });
  }

  renderDifference(matchedPairs, unit) {
    if (this.chart) this.chart.destroy();

    this.chart = new Chart(this.ctx, {
      type: "bar",
      data: {
        labels: matchedPairs.map((p) => `${p.depth} m`),
        datasets: [{
          label: `Model − Observation (${unit})`,
          data: matchedPairs.map((p) => p.difference),
          backgroundColor: matchedPairs.map((p) =>
            p.difference >= 0 ? "rgba(239,68,68,0.75)" : "rgba(59,130,246,0.75)"
          ),
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            // Diverging scale centred on zero, so sign reads at a glance.
            suggestedMin: -Math.max(...matchedPairs.map((p) => Math.abs(p.difference))),
            suggestedMax: Math.max(...matchedPairs.map((p) => Math.abs(p.difference))),
            grid: { color: (c) => (c.tick.value === 0 ? "#94a3b8" : "rgba(148,163,184,0.15)") },
            title: { display: true, text: "Model − Observation" },
          },
        },
      },
    });
  }
}
