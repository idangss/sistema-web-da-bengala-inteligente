// Gráfico da tela Sensores: bateria (%) e sinal Bluetooth (dBm).
(function () {
  const dados = JSON.parse(document.getElementById("dados-telemetria").textContent);
  const canvas = document.getElementById("grafico-telemetria");
  if (!canvas || !window.Chart) return;
  const reduzirMovimento = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  new Chart(canvas, {
    type: "line",
    data: {
      labels: dados.rotulos,
      datasets: [
        { label: "Bateria (%)", data: dados.bateria, borderColor: "#0B2545", backgroundColor: "#0B2545", yAxisID: "y", pointRadius: 4 },
        { label: "Sinal Bluetooth (dBm)", data: dados.rssi, borderColor: "#B88A00", backgroundColor: "#F2B705", borderDash: [6, 4], yAxisID: "y2", pointRadius: 4, pointStyle: "rectRot" },
      ],
    },
    options: {
      animation: reduzirMovimento ? false : undefined,
      maintainAspectRatio: false,
      scales: {
        y: { min: 0, max: 100, title: { display: true, text: "Bateria (%)" } },
        y2: { position: "right", grid: { drawOnChartArea: false }, title: { display: true, text: "Sinal (dBm)" } },
      },
    },
  });
})();
