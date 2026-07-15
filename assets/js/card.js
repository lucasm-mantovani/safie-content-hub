/* card.js — componente de card compartilhado + helpers para todas as páginas
   navegacionais (home, listagem, categoria, nicho). Vanilla, sem dependências.
   Expõe window.SafieCard. Deve ser carregado ANTES dos scripts de página. */

window.SafieCard = (function () {
  "use strict";

  var FONTE = "/artigos/indice.json";
  var MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

  function norm(s) {
    return (s || "").toString().toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  }

  function escapeHtml(s) {
    return (s || "").replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function dataFmt(iso) {
    try {
      var d = new Date(iso);
      if (isNaN(d)) return "";
      return d.getUTCDate() + " " + MESES[d.getUTCMonth()] + " " + d.getUTCFullYear();
    } catch (e) { return ""; }
  }

  // Card com capa; fallback gracioso se o SVG não existir (onerror → placeholder)
  function cardHtml(a) {
    var slug = encodeURIComponent(a.slug || "");
    var capa = "/assets/img/artigos/" + slug + ".svg";
    var d = dataFmt(a.data);
    var inicial = escapeHtml((a.tema || a.titulo || "S").trim().charAt(0).toUpperCase());
    return (
      '<article class="card-artigo">' +
      '<a href="/artigos/' + slug + '">' +
      '<div class="card-capa">' +
      '<img src="' + capa + '" alt="" loading="lazy" ' +
      "onerror=\"this.style.display='none';this.parentNode.classList.add('sem-capa');this.parentNode.setAttribute('data-inicial','" + inicial + "')\">" +
      "</div>" +
      '<div class="card-corpo">' +
      (a.tema ? '<span class="card-tema">' + escapeHtml(a.tema) + "</span>" : "") +
      "<h2>" + escapeHtml(a.titulo || "") + "</h2>" +
      (a.resumo ? '<p class="card-resumo">' + escapeHtml(a.resumo) + "</p>" : "") +
      (d ? '<span class="card-data">' + d + "</span>" : "") +
      "</div></a></article>"
    );
  }

  function fetchIndice() {
    return fetch(FONTE)
      .then(function (r) { return r.ok ? r.json() : []; })
      .then(function (d) { return Array.isArray(d) ? d : []; })
      .catch(function () { return null; }); // null = fetch-fail (distingue de vazio)
  }

  function ordenarRecentes(artigos) {
    return artigos.slice().sort(function (a, b) {
      return (b.data || "").localeCompare(a.data || "");
    });
  }

  function renderGrid(container, artigos, vazioMsg) {
    if (!container) return;
    if (artigos === null) {
      container.innerHTML = '<p class="lista-vazia">Não foi possível carregar os artigos.</p>';
      return;
    }
    if (!artigos.length) {
      container.innerHTML = '<p class="lista-vazia">' + (vazioMsg || "Nenhum artigo ainda.") + "</p>";
      return;
    }
    container.innerHTML = artigos.map(cardHtml).join("\n");
  }

  // Paginação: renderiza página `pag` (1-based) e monta controles em navEl
  function renderPaginado(container, navEl, artigos, porPagina, pag, vazioMsg) {
    if (artigos === null) { renderGrid(container, null); if (navEl) navEl.innerHTML = ""; return; }
    var total = artigos.length;
    var paginas = Math.max(1, Math.ceil(total / porPagina));
    pag = Math.min(Math.max(1, pag), paginas);
    var fatia = artigos.slice((pag - 1) * porPagina, pag * porPagina);
    renderGrid(container, fatia, vazioMsg);
    if (!navEl) return;
    if (paginas <= 1) { navEl.innerHTML = ""; return; }
    var html = "";
    html += pag > 1 ? '<button data-pag="' + (pag - 1) + '" class="pag-btn">← Anterior</button>' : "";
    html += '<span class="pag-info">Página ' + pag + " de " + paginas + "</span>";
    html += pag < paginas ? '<button data-pag="' + (pag + 1) + '" class="pag-btn">Próxima →</button>' : "";
    navEl.innerHTML = html;
    navEl.querySelectorAll("[data-pag]").forEach(function (b) {
      b.addEventListener("click", function () {
        renderPaginado(container, navEl, artigos, porPagina, parseInt(b.getAttribute("data-pag"), 10), vazioMsg);
        window.scrollTo({ top: 0, behavior: "smooth" });
      });
    });
  }

  // UI genérica (menu mobile + FAQ accordion) — vale em todas as páginas que
  // carregam card.js. Roda automaticamente no DOM ready.
  function initUI() {
    var toggle = document.querySelector(".menu-toggle");
    var nav = document.querySelector(".nav-principal");
    if (toggle && nav) toggle.addEventListener("click", function () { nav.classList.toggle("aberto"); });
    document.querySelectorAll(".faq-pergunta").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var item = btn.closest(".faq-item");
        if (!item) return;
        var aberto = item.classList.contains("aberto");
        document.querySelectorAll(".faq-item.aberto").forEach(function (i) { i.classList.remove("aberto"); });
        if (!aberto) item.classList.add("aberto");
      });
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initUI);
  else initUI();

  return {
    norm: norm, escapeHtml: escapeHtml, dataFmt: dataFmt, cardHtml: cardHtml,
    fetchIndice: fetchIndice, ordenarRecentes: ordenarRecentes,
    renderGrid: renderGrid, renderPaginado: renderPaginado,
  };
})();
