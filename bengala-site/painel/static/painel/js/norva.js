// Norva · comportamento da interface (loading, tema, menu, busca Ctrl+K, toasts e microinterações).
// Só front-end: não chama API nem altera dados; as buscas usam as páginas de listagem que já existem.
(function () {
  "use strict";
  var html = document.documentElement;
  var reduz = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var ms = function (n) { return reduz ? 0 : n; };
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var guarda = {
    get: function (k, sessao) { try { return (sessao ? sessionStorage : localStorage).getItem(k); } catch (e) { return null; } },
    set: function (k, v, sessao) { try { (sessao ? sessionStorage : localStorage).setItem(k, v); } catch (e) {} },
    del: function (k, sessao) { try { (sessao ? sessionStorage : localStorage).removeItem(k); } catch (e) {} },
  };
  var paginaLogin = html.getAttribute("data-pagina") === "login";

  /* ---------------------------------------------------------- Toasts */
  function toast(msg, tipo) {
    var area = $("#nv-toasts");
    if (!area) return;
    var erro = tipo === "error";
    var el = document.createElement("div");
    el.className = "nv-toast" + (erro ? " erro" : "");
    el.innerHTML = '<i class="ic bi ' + (erro ? "bi-exclamation-triangle" : tipo === "info" ? "bi-info-circle" : "bi-check2") + '" aria-hidden="true"></i><span style="flex:1"></span>' +
      '<button type="button" class="fechar" aria-label="Fechar aviso"><i class="bi bi-x-lg" aria-hidden="true"></i></button>';
    el.querySelector("span").textContent = msg;
    area.appendChild(el);
    var foi = false;
    function some() {
      if (foi) return; foi = true;
      el.classList.add("saindo");
      setTimeout(function () { el.remove(); }, ms(260));
    }
    el.querySelector(".fechar").addEventListener("click", some);
    if (!erro) setTimeout(some, 5000); // erros ficam até a pessoa fechar
  }
  window.NorvaToast = toast;

  function mensagensDoDjango() {
    var caixa = $(".nv-mensagens");
    if (!caixa) return;
    $$(".alert", caixa).forEach(function (a) { toast(a.textContent.trim(), a.getAttribute("data-tipo")); });
    caixa.remove();
  }

  /* ---------------------------------------------------------- Tema */
  function aplicaTema(escuro) {
    html.setAttribute("data-tema", escuro ? "escuro" : "claro");
    html.setAttribute("data-bs-theme", escuro ? "dark" : "light");
    $$("[data-tema-btn]").forEach(function (b) {
      b.setAttribute("aria-pressed", escuro);
      var i = b.querySelector("i");
      if (i) i.className = "bi " + (escuro ? "bi-sun" : "bi-moon");
    });
  }
  aplicaTema(html.getAttribute("data-tema") === "escuro");
  document.addEventListener("click", function (ev) {
    if (!ev.target.closest("[data-tema-btn]")) return;
    var escuro = html.getAttribute("data-tema") !== "escuro";
    if (!reduz) { html.classList.add("troca-tema"); setTimeout(function () { html.classList.remove("troca-tema"); }, 400); }
    aplicaTema(escuro);
    guarda.set("nv-tema", escuro ? "escuro" : "claro");
    window.dispatchEvent(new CustomEvent("nv-tema", { detail: { escuro: escuro } }));
    toast(escuro ? "Tema escuro ativado." : "Tema claro ativado.");
  });

  /* ---------------------------------------------------------- Indicador do menu */
  function moveIndicador(anima) {
    var ind = $("#nv-indicador"), ativo = $('.menu a[aria-current="page"]');
    if (!ind) return;
    if (!ativo) { ind.style.opacity = 0; return; }
    ind.classList.toggle("anima", !!anima && !reduz);
    ind.style.opacity = 1;
    ind.style.transform = "translateY(" + ativo.offsetTop + "px)";
    ind.style.height = ativo.offsetHeight + "px";
    guarda.set("nv-ind-top", String(ativo.offsetTop), true);
    html.classList.add("com-indicador");
  }
  function iniciaIndicador() {
    var ind = $("#nv-indicador"), ativo = $('.menu a[aria-current="page"]');
    if (!ind || !ativo) return;
    var antes = guarda.get("nv-ind-top", true);
    if (antes !== null && !reduz && +antes !== ativo.offsetTop) {
      // começa onde estava na página anterior e desliza até o item atual
      ind.style.transform = "translateY(" + antes + "px)";
      ind.style.height = ativo.offsetHeight + "px";
      ind.style.opacity = 1;
      html.classList.add("com-indicador");
      requestAnimationFrame(function () { requestAnimationFrame(function () { moveIndicador(true); }); });
    } else {
      moveIndicador(false);
    }
  }
  window.addEventListener("resize", function () { moveIndicador(false); });

  /* ---------------------------------------------------------- Menu recolhido e gaveta no celular */
  var movel = window.matchMedia("(max-width: 992px)");
  var btnRecolher = $("#nv-recolher");
  function defineRecolhido(sim) {
    html.classList.toggle("nv-recolhido", sim);
    if (!btnRecolher) return;
    btnRecolher.setAttribute("aria-expanded", !sim);
    btnRecolher.setAttribute("title", sim ? "Expandir menu" : "Recolher menu");
    var r = btnRecolher.querySelector(".rotulo"); if (r) r.textContent = sim ? "Expandir menu" : "Recolher menu";
  }
  if (btnRecolher) {
    defineRecolhido(html.classList.contains("nv-recolhido"));
    btnRecolher.addEventListener("click", function () {
      var sim = !html.classList.contains("nv-recolhido");
      defineRecolhido(sim);
      guarda.set("nv-recolhido", sim ? "1" : "0");
      setTimeout(function () { moveIndicador(false); window.dispatchEvent(new Event("resize")); }, ms(470));
    });
  }
  var btnMenu = $("#nv-abrir-menu"), fundoMenu = $("#nv-fundo-menu");
  function abreMenu() {
    html.classList.add("menu-aberto");
    if (fundoMenu) fundoMenu.hidden = false;
    btnMenu.setAttribute("aria-expanded", "true");
    setTimeout(function () { var a = $('.menu a[aria-current="page"]') || $(".menu a"); if (a) a.focus(); moveIndicador(false); }, ms(60));
  }
  function fechaMenu(devolveFoco) {
    if (!html.classList.contains("menu-aberto")) return;
    html.classList.remove("menu-aberto");
    if (fundoMenu) fundoMenu.hidden = true;
    if (btnMenu) { btnMenu.setAttribute("aria-expanded", "false"); if (devolveFoco) btnMenu.focus(); }
  }
  if (btnMenu) btnMenu.addEventListener("click", abreMenu);
  if (fundoMenu) fundoMenu.addEventListener("click", function () { fechaMenu(true); });

  /* ---------------------------------------------------------- Busca global (Ctrl+K) */
  var busca = $("#nv-busca"), fundoCamada = $("#nv-fundo-camada"), entrada = $("#nv-busca-input"), lista = $("#nv-busca-lista");
  var resultados = [], ativo = 0, origemFoco = null;
  var sem = function (t) { return String(t).normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase(); };
  function url(nome) { return busca ? busca.getAttribute("data-url-" + nome) : "#"; }
  function itensFixos() {
    return [
      { g: "Telas", rot: "Painel", det: "Visão geral", ic: "bi-grid-1x2", href: url("painel") },
      { g: "Telas", rot: "Usuários", det: "Pessoas que usam a bengala", ic: "bi-people", href: url("usuarios") },
      { g: "Telas", rot: "Bengalas", det: "Dispositivos cadastrados", ic: "bi-cpu", href: url("bengalas") },
      { g: "Telas", rot: "Sensores", det: "Bateria, sinal e detecções", ic: "bi-activity", href: url("sensores") },
      { g: "Telas", rot: "Eventos", det: "Histórico completo", ic: "bi-clock-history", href: url("eventos") },
      { g: "Ações", rot: "Cadastrar usuário", det: "Novo titular", ic: "bi-person-plus", href: url("usuario-novo") },
      { g: "Ações", rot: "Cadastrar bengala", det: "Novo dispositivo", ic: "bi-plus-circle", href: url("bengala-nova") },
    ];
  }
  function renderBusca() {
    var q = entrada.value.trim(), qs = sem(q);
    var itens = itensFixos().filter(function (i) { return !qs || sem(i.rot + " " + i.det).indexOf(qs) > -1; });
    if (q) {
      itens.unshift(
        { g: "Buscar", rot: "Usuários com “" + q + "”", det: "Nome, e-mail ou telefone", ic: "bi-search", href: url("usuarios") + "?q=" + encodeURIComponent(q) + "&status=todos" },
        { g: "Buscar", rot: "Bengalas com “" + q + "”", det: "Número de série ou Bluetooth", ic: "bi-search", href: url("bengalas") + "?q=" + encodeURIComponent(q) + "&status=todas" }
      );
    }
    resultados = itens;
    var h = "", grupo = null;
    itens.forEach(function (it, n) {
      if (it.g !== grupo) { grupo = it.g; h += '<li role="presentation" class="busca-grupo">' + grupo + "</li>"; }
      h += '<li role="option" class="busca-op" id="nv-op-' + n + '" data-op="' + n + '" aria-selected="false"><i class="bi ' + it.ic + '" aria-hidden="true"></i>' +
        '<span style="flex:1;display:flex;flex-direction:column"><b></b><span class="det"></span></span></li>';
    });
    lista.innerHTML = h;
    itens.forEach(function (it, n) {
      var li = $("#nv-op-" + n); li.querySelector("b").textContent = it.rot; li.querySelector(".det").textContent = it.det;
    });
    ativo = 0; marca();
    $("#nv-busca-status").textContent = itens.length ? itens.length + " resultados." : "Nenhum resultado.";
  }
  function marca() {
    $$(".busca-op", lista).forEach(function (o) { o.setAttribute("aria-selected", +o.getAttribute("data-op") === ativo); });
    var at = $("#nv-op-" + ativo);
    entrada.setAttribute("aria-activedescendant", at ? at.id : "");
    if (at) at.scrollIntoView({ block: "nearest" });
  }
  function abreBusca() {
    if (!busca) return;
    fechaMenu(false);
    origemFoco = document.activeElement;
    entrada.value = ""; renderBusca();
    busca.hidden = false; busca.classList.remove("saindo");
    fundoCamada.hidden = false; fundoCamada.classList.remove("saindo");
    entrada.focus();
  }
  function fechaBusca() {
    if (!busca || busca.hidden) return;
    busca.classList.add("saindo"); fundoCamada.classList.add("saindo");
    setTimeout(function () { busca.hidden = true; fundoCamada.hidden = true; busca.classList.remove("saindo"); fundoCamada.classList.remove("saindo"); }, ms(200));
    if (origemFoco && document.contains(origemFoco)) origemFoco.focus({ preventScroll: true });
  }
  function abreResultado(n) { var r = resultados[n]; if (r) window.location.href = r.href; }
  if (busca) {
    $("#nv-abrir-busca").addEventListener("click", abreBusca);
    fundoCamada.addEventListener("click", fechaBusca);
    entrada.addEventListener("input", renderBusca);
    entrada.addEventListener("keydown", function (ev) {
      if (ev.key === "ArrowDown") { ev.preventDefault(); if (resultados.length) { ativo = (ativo + 1) % resultados.length; marca(); } }
      else if (ev.key === "ArrowUp") { ev.preventDefault(); if (resultados.length) { ativo = (ativo - 1 + resultados.length) % resultados.length; marca(); } }
      else if (ev.key === "Enter") { ev.preventDefault(); abreResultado(ativo); }
      else if (ev.key === "Tab") { ev.preventDefault(); }
    });
    lista.addEventListener("click", function (ev) { var o = ev.target.closest("[data-op]"); if (o) abreResultado(+o.getAttribute("data-op")); });
  }

  /* ---------------------------------------------------------- Teclado */
  document.addEventListener("keydown", function (ev) {
    if ((ev.ctrlKey || ev.metaKey) && (ev.key === "k" || ev.key === "K") && busca) {
      ev.preventDefault();
      if (busca.hidden) abreBusca(); else fechaBusca();
      return;
    }
    if (ev.key === "Escape") {
      if (busca && !busca.hidden) { ev.preventDefault(); fechaBusca(); return; }
      if (html.classList.contains("menu-aberto")) fechaMenu(true);
    }
  });

  /* ---------------------------------------------------------- Botões que mostram que estão trabalhando */
  document.addEventListener("submit", function (ev) {
    var form = ev.target;
    if (ev.defaultPrevented) return;
    var btn = ev.submitter || form.querySelector('[type="submit"]');
    if (!btn || btn.hasAttribute("data-sem-espera")) return;
    // espera o próximo quadro para não interferir no envio do valor do botão
    requestAnimationFrame(function () { btn.setAttribute("aria-busy", "true"); });
  });
  window.addEventListener("pageshow", function () { $$('[aria-busy="true"]').forEach(function (b) { b.removeAttribute("aria-busy"); }); });

  /* ---------------------------------------------------------- Login */
  if (paginaLogin) {
    guarda.del("nv-pos-login", true);
    var form = $("#form-login");
    if (form) {
      form.addEventListener("submit", function () { guarda.set("nv-pos-login", "1", true); });
      var senha = form.querySelector('input[type="password"]');
      if (senha) {
        var caixa = document.createElement("div");
        caixa.className = "campo-senha";
        senha.parentNode.insertBefore(caixa, senha);
        caixa.appendChild(senha);
        var ver = document.createElement("button");
        ver.type = "button"; ver.className = "btn btn-contorno"; ver.textContent = "Mostrar"; ver.setAttribute("aria-pressed", "false");
        ver.setAttribute("aria-label", "Mostrar senha");
        ver.addEventListener("click", function () {
          var mostrar = senha.type === "password";
          senha.type = mostrar ? "text" : "password";
          ver.textContent = mostrar ? "Ocultar" : "Mostrar";
          ver.setAttribute("aria-pressed", mostrar);
          ver.setAttribute("aria-label", mostrar ? "Ocultar senha" : "Mostrar senha");
        });
        caixa.appendChild(ver);
      }
    }
  }

  /* ---------------------------------------------------------- Contagem dos indicadores */
  function fmt(n) { return n.toLocaleString("pt-BR"); }
  function contaIndicadores() {
    $$(".indicador-valor").forEach(function (el) {
      var t = el.textContent.trim();
      if (!/^\d+$/.test(t)) return;
      var alvo = +t;
      if (reduz || alvo === 0) { el.textContent = fmt(alvo); return; }
      var t0 = performance.now(), dur = 900;
      el.setAttribute("aria-label", fmt(alvo));
      (function passo(agora) {
        var p = Math.min(1, (agora - t0) / dur), e = 1 - Math.pow(1 - p, 3);
        el.textContent = fmt(Math.round(alvo * e));
        if (p < 1) requestAnimationFrame(passo); else el.removeAttribute("aria-label");
      })(t0);
    });
  }

  /* ---------------------------------------------------------- Loading */
  function terminaAbertura() {
    var loader = $("#nv-loader");
    if (loader && html.classList.contains("nv-abrindo")) {
      loader.classList.add("is-hidden");
      loader.setAttribute("aria-hidden", "true");
      setTimeout(function () { html.classList.remove("nv-abrindo", "nv-curto"); loader.classList.remove("is-hidden"); }, 520);
    }
    contaIndicadores();
    mensagensDoDjango();
  }

  /* ---------------------------------------------------------- Início */
  iniciaIndicador();
  // segurança: tira o skeleton se o gráfico ou o mapa não carregarem
  setTimeout(function () { $$(".nv-carregando").forEach(function (e) { e.classList.remove("nv-carregando"); }); }, 4000);
  if (html.classList.contains("nv-abrindo")) {
    var minimo = html.classList.contains("nv-curto") ? (reduz ? 300 : 1500) : (reduz ? 600 : 2800);
    setTimeout(terminaAbertura, minimo);
  } else {
    terminaAbertura();
  }
})();