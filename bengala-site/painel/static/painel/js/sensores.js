// Gráfico da tela Sensores: bateria (%) e sinal Bluetooth (dBm).
(function () {
  const dados = JSON.parse(document.getElementById("dados-telemetria").textContent);
  const canvas = document.getElementById("grafico-telemetria");
  if (!canvas || !window.Chart) return;
  const reduzirMovimento = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const cor = (nome) => getComputedStyle(document.documentElement).getPropertyValue(nome).trim();
  Chart.defaults.font.family = '"Atkinson Hyperlegible", system-ui, sans-serif';
  Chart.defaults.font.size = 14;
  const chart = new Chart(canvas, {
    type: "line",
    data: {
      labels: dados.rotulos,
      datasets: [
        { label: "Bateria (%)", data: dados.bateria, borderColor: cor("--bar"), backgroundColor: cor("--bar"), borderWidth: 3, tension: 0.3, yAxisID: "y", pointRadius: 4 },
        { label: "Sinal Bluetooth (dBm)", data: dados.rssi, borderColor: "#B88A00", backgroundColor: "#F2B705", borderWidth: 3, borderDash: [6, 4], tension: 0.3, yAxisID: "y2", pointRadius: 4, pointStyle: "rectRot" },
      ],
    },
    options: {
      animation: reduzirMovimento ? false : { duration: 1200, easing: "easeOutCubic" },
      maintainAspectRatio: false,
      plugins: { legend: { labels: { color: cor("--nv-text") } } },
      scales: {
        x: { grid: { display: false }, ticks: { color: cor("--nv-muted") } },
        y: { min: 0, max: 100, title: { display: true, text: "Bateria (%)", color: cor("--nv-text") }, ticks: { color: cor("--nv-muted") }, grid: { color: cor("--nv-line") } },
        y2: { position: "right", grid: { drawOnChartArea: false }, title: { display: true, text: "Sinal (dBm)", color: cor("--nv-text") }, ticks: { color: cor("--nv-muted") } },
      },
    },
  });
  const caixa = canvas.closest(".nv-carregando");
  if (caixa) caixa.classList.remove("nv-carregando");
  window.addEventListener("nv-tema", () => {
    const o = chart.options;
    chart.data.datasets[0].borderColor = chart.data.datasets[0].backgroundColor = cor("--bar");
    o.plugins.legend.labels.color = cor("--nv-text");
    o.scales.x.ticks.color = o.scales.y.ticks.color = o.scales.y2.ticks.color = cor("--nv-muted");
    o.scales.y.title.color = o.scales.y2.title.color = cor("--nv-text");
    o.scales.y.grid.color = cor("--nv-line");
    chart.update("none");
  });
})();