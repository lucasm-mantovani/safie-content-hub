/* main.js — home. Recentes (9) + grid de nichos. Depende de card.js (SafieCard). */
(function () {
  "use strict";
  function init() {
    var recentes = document.getElementById("recentes-lista");
    if (recentes) {
      var limite = parseInt(recentes.getAttribute("data-limite") || "9", 10);
      SafieCard.fetchIndice().then(function (idx) {
        SafieCard.renderGrid(recentes, idx === null ? null : SafieCard.ordenarRecentes(idx).slice(0, limite),
          "Em breve, os primeiros artigos.");
      });
    }
    var nichosEl = document.getElementById("nichos-lista");
    if (nichosEl) {
      fetch("/config/site.json").then(function (r) { return r.ok ? r.json() : {}; })
        .catch(function () { return {}; })
        .then(function (site) {
          var nichos = (site && site.nichos) || {};
          var html = Object.keys(nichos).map(function (n) {
            return '<a class="nicho-card" href="/categorias/' + n + '">' +
              "<h3>" + SafieCard.escapeHtml(nichos[n].nome || n) + "</h3>" +
              (nichos[n].descricao ? "<p>" + SafieCard.escapeHtml(nichos[n].descricao) + "</p>" : "") +
              "</a>";
          }).join("\n");
          nichosEl.innerHTML = html || '<p class="lista-vazia">Categorias em breve.</p>';
        });
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
