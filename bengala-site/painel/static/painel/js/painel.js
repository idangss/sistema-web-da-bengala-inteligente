// Gráfico e mapa do Painel. Os dados vêm do servidor pelo json_script.
(function () {
  const ler = (id) => JSON.parse(document.getElementById(id).textContent);
  const reduzirMovimento = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const grafico = ler("dados-grafico");
  const canvas = document.getElementById("grafico-dias");
  if (canvas && window.Chart) {
    new Chart(canvas, {
      type: "bar",
      data: {
        labels: grafico.rotulos,
        datasets: [{ label: "Detecções", data: grafico.valores, backgroundColor: "#0B2545", borderColor: "#F2B705", borderWidth: 2 }],
      },
      options: {
        animation: reduzirMovimento ? false : undefined,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
      },
    });
  }

  const mapa = ler("dados-mapa");
  const buracos = ler("dados-buracos");
  const div = document.getElementById("mapa");
  if (div && mapa && window.L) {
    const m = L.map(div).setView([mapa.lat, mapa.lng], 16);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: "&copy; colaboradores do OpenStreetMap",
    }).addTo(m);
    L.marker([mapa.lat, mapa.lng], { title: "Última localização de " + mapa.titular })
      .addTo(m)
      .bindPopup(mapa.titular + " (" + mapa.bengala + ")<br>" + mapa.origem + " em " + mapa.quando);
    buracos.forEach((p) => {
      L.circleMarker([p.lat, p.lng], { radius: 6 + p.ocorrencias, color: "#0B2545", fillColor: "#F2B705", fillOpacity: 0.8 })
        .addTo(m)
        .bindPopup(p.ocorrencias + " buracos detectados neste ponto");
    });
  }
})();
