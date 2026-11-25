// Gráfico e mapa do Painel. Os dados vêm do servidor pelo json_script.
(function () {
  const ler = (id) => JSON.parse(document.getElementById(id).textContent);
  const reduzirMovimento = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const cor = (nome) => getComputedStyle(document.documentElement).getPropertyValue(nome).trim();
  const tiraSkeleton = (el) => { if (el) { const caixa = el.closest(".nv-carregando") || el; caixa.classList.remove("nv-carregando"); } };

  const grafico = ler("dados-grafico");
  const canvas = document.getElementById("grafico-dias");
  if (canvas && window.Chart) {
    Chart.defaults.font.family = '"Atkinson Hyperlegible", system-ui, sans-serif';
    Chart.defaults.font.size = 14;
    const maior = Math.max(...grafico.valores, 0);
    const coresBarras = () => grafico.valores.map((v) => (v === maior && maior > 0 ? cor("--bar-dest") : cor("--bar")));
    const chart = new Chart(canvas, {
      type: "bar",
      data: {
        labels: grafico.rotulos,
        datasets: [{ label: "Detecções", data: grafico.valores, backgroundColor: coresBarras(), borderRadius: 6, borderSkipped: false, maxBarThickness: 48 }],
      },
      options: {
        animation: reduzirMovimento ? false : { duration: 700, easing: "easeOutCubic", delay: (c) => (c.type === "data" ? c.dataIndex * 60 : 0) },
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { display: false }, ticks: { color: cor("--nv-text") } },
          y: { beginAtZero: true, ticks: { precision: 0, color: cor("--nv-muted") }, grid: { color: cor("--nv-line") }, border: { display: false } },
        },
      },
    });
    tiraSkeleton(canvas);
    window.addEventListener("nv-tema", () => {
      chart.data.datasets[0].backgroundColor = coresBarras();
      chart.options.scales.x.ticks.color = cor("--nv-text");
      chart.options.scales.y.ticks.color = cor("--nv-muted");
      chart.options.scales.y.grid.color = cor("--nv-line");
      chart.update("none");
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
    tiraSkeleton(div);
    // o menu recolhido muda a largura do mapa
    window.addEventListener("resize", () => m.invalidateSize());
  }
})();