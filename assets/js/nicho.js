/* nicho.js — /categorias/{nicho}. Lista as categorias do nicho + recentes do nicho.
   Depende de card.js. */
(function () {
  "use strict";
  function init() {
    var catsEl = document.getElementById("categorias-lista");
    var lista = document.getElementById("artigos-lista");
    var nav = document.getElementById("paginacao");
    var nichoAlvo = (catsEl && catsEl.getAttribute("data-filtro-nicho")) ||
                    (lista && lista.getAttribute("data-filtro-nicho")) || "";

    // categorias do nicho (de config/categorias.json)
    if (catsEl) {
      fetch("/config/categorias.json").then(function (r) { return r.ok ? r.json() : []; })
        .catch(function () { return []; })
        .then(function (cats) {
          var doNicho = (Array.isArray(cats) ? cats : []).filter(function (c) { return c.nicho === nichoAlvo; });
          catsEl.innerHTML = doNicho.length
            ? doNicho.map(function (c) {
                return '<a class="nicho-card" href="/categorias/' + c.slug + '">' +
                  "<h3>" + SafieCard.escapeHtml(c.nome || c.slug) + "</h3>" +
                  (c.descricao ? "<p>" + SafieCard.escapeHtml(c.descricao) + "</p>" : "") + "</a>";
              }).join("\n")
            : '<p class="lista-vazia">Categorias em breve.</p>';
        });
    }

    // artigos recentes do nicho (de artigos/indice.json)
    if (lista) {
      var por = parseInt(lista.getAttribute("data-por-pagina") || "9", 10);
      SafieCard.fetchIndice().then(function (idx) {
        if (idx === null) { SafieCard.renderPaginado(lista, nav, null, por, 1); return; }
        var doNicho = SafieCard.ordenarRecentes(idx).filter(function (a) { return a.nicho === nichoAlvo; });
        SafieCard.renderPaginado(lista, nav, doNicho, por, 1, "Nenhum artigo neste nicho ainda.");
      });
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
