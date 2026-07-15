/* categoria.js — /categorias/{slug}. Filtra por tema_slug, paginação 9/página.
   Depende de card.js. */
(function () {
  "use strict";
  function init() {
    var lista = document.getElementById("artigos-lista");
    var nav = document.getElementById("paginacao");
    if (!lista) return;
    var temaSlug = lista.getAttribute("data-filtro-tema") || "";
    var por = parseInt(lista.getAttribute("data-por-pagina") || "9", 10);
    SafieCard.fetchIndice().then(function (idx) {
      if (idx === null) { SafieCard.renderPaginado(lista, nav, null, por, 1); return; }
      var filtrados = SafieCard.ordenarRecentes(idx).filter(function (a) {
        return a.tema_slug === temaSlug;
      });
      SafieCard.renderPaginado(lista, nav, filtrados, por, 1, "Nenhum artigo nesta categoria ainda.");
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
