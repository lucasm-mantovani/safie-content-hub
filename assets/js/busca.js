/* busca.js — busca client-side do SAFIE Blog.
   Lê /artigos/indice.json (sem backend), filtra por título + categoria + resumo,
   renderiza resultados. Vanilla JS, sem dependências. Enhancement progressivo:
   o form do header é um GET para /busca?q=... que funciona mesmo sem este script. */

(function () {
  "use strict";

  var FONTE = "/artigos/indice.json";

  // normaliza: minúsculas + remove acentos (busca acento-insensível)
  function norm(s) {
    return (s || "")
      .toString()
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "");
  }

  function getParamQ() {
    try {
      return new URLSearchParams(window.location.search).get("q") || "";
    } catch (e) {
      return "";
    }
  }

  function filtrar(artigos, q) {
    var termos = norm(q).split(/\s+/).filter(Boolean);
    if (!termos.length) return [];
    return artigos.filter(function (a) {
      var alvo = norm((a.titulo || "") + " " + (a.tema || "") + " " + (a.resumo || ""));
      return termos.every(function (t) { return alvo.indexOf(t) !== -1; });
    });
  }

  function dataFmt(iso) {
    try {
      var d = new Date(iso);
      if (isNaN(d)) return "";
      var m = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
      return d.getUTCDate() + " " + m[d.getUTCMonth()] + " " + d.getUTCFullYear();
    } catch (e) { return ""; }
  }

  function escapeHtml(s) {
    return (s || "").replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function cardHtml(a) {
    var d = dataFmt(a.data);
    return (
      '<article class="busca-item">' +
      '<a href="/artigos/' + encodeURIComponent(a.slug) + '">' +
      (a.tema ? '<span class="busca-item-tema">' + escapeHtml(a.tema) + "</span>" : "") +
      "<h2>" + escapeHtml(a.titulo) + "</h2>" +
      (a.resumo ? "<p>" + escapeHtml(a.resumo) + "</p>" : "") +
      (d ? '<span class="busca-item-data">' + d + "</span>" : "") +
      "</a></article>"
    );
  }

  function render(container, statusEl, artigos, q) {
    if (!q.trim()) {
      statusEl.textContent = "Digite um termo para buscar nos artigos.";
      container.innerHTML = "";
      return;
    }
    var res = filtrar(artigos, q);
    if (!res.length) {
      statusEl.textContent = 'Nenhum resultado para "' + q + '".';
      container.innerHTML = "";
      return;
    }
    statusEl.textContent = res.length + (res.length === 1 ? " resultado" : " resultados") + ' para "' + q + '".';
    container.innerHTML = res.map(cardHtml).join("\n");
  }

  function initPaginaBusca() {
    var container = document.getElementById("busca-resultados");
    var statusEl = document.getElementById("busca-status");
    var input = document.getElementById("busca-q-pagina");
    if (!container || !statusEl) return; // não é a página de busca

    var artigos = [];
    var q0 = getParamQ();
    if (input) input.value = q0;

    fetch(FONTE)
      .then(function (r) { return r.ok ? r.json() : []; })
      .then(function (data) {
        artigos = Array.isArray(data) ? data : [];
        render(container, statusEl, artigos, q0);
      })
      .catch(function () {
        statusEl.textContent = "Não foi possível carregar o índice de artigos.";
      });

    if (input) {
      var t;
      input.addEventListener("input", function () {
        clearTimeout(t);
        t = setTimeout(function () {
          var q = input.value;
          render(container, statusEl, artigos, q);
          try {
            var url = q.trim() ? "?q=" + encodeURIComponent(q) : window.location.pathname;
            window.history.replaceState(null, "", url);
          } catch (e) {}
        }, 120);
      });
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initPaginaBusca);
  } else {
    initPaginaBusca();
  }
})();
