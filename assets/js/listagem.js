/* listagem.js — /artigos. Todos os artigos, paginação 9/página. Depende de card.js. */
(function () {
  "use strict";
  function init() {
    var lista = document.getElementById("artigos-lista");
    var nav = document.getElementById("paginacao");
    if (!lista) return;
    var por = parseInt(lista.getAttribute("data-por-pagina") || "9", 10);
    SafieCard.fetchIndice().then(function (idx) {
      var artigos = idx === null ? null : SafieCard.ordenarRecentes(idx);
      SafieCard.renderPaginado(lista, nav, artigos, por, 1, "Nenhum artigo publicado ainda.");
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
