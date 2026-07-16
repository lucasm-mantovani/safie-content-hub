/* footer-form.js — envia o form do rodapé à HubSpot Forms Submissions API.
   portalId + formGuid são públicos por design; NENHUMA chave/token aqui.
   Sucesso: segue o redirectUri retornado pelo HubSpot (redireciona ao WhatsApp).
   Mapa: nome→firstname, email→email, telefone→mobilephone, empresa→company. */
(function () {
  "use strict";
  var PORTAL = "50182013";
  var GUID = "1802e1da-b81b-44ed-9bab-7db51bd9e6b5";
  var ENDPOINT = "https://api.hsforms.com/submissions/v3/integration/submit/" + PORTAL + "/" + GUID;
  var EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

  function setStatus(el, tipo, msg) {
    if (!el) return;
    el.textContent = msg;
    el.setAttribute("data-tipo", tipo);
    el.hidden = false;
  }

  function init() {
    var form = document.querySelector('form[data-form="rodape"]');
    if (!form) return;
    var status = form.querySelector(".footer-form-status");
    var btn = form.querySelector('button[type="submit"]');

    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var nome = (form.nome.value || "").trim();
      var email = (form.email.value || "").trim();
      var telefone = (form.telefone.value || "").trim();
      var empresa = (form.empresa.value || "").trim();

      if (!nome || !email || !telefone || !empresa || !EMAIL_RE.test(email)) {
        setStatus(status, "erro", "Preencha nome, e-mail válido, telefone e empresa.");
        return;
      }

      var rotulo = btn ? btn.textContent : "";
      if (btn) { btn.disabled = true; btn.textContent = "Enviando…"; }
      if (status) status.hidden = true;

      var payload = {
        fields: [
          { name: "firstname", value: nome },
          { name: "email", value: email },
          { name: "mobilephone", value: telefone },
          { name: "company", value: empresa }
        ],
        context: { pageUri: location.href, pageName: document.title }
      };

      fetch(ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      })
        .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, body: j }; }); })
        .then(function (res) {
          if (!res.ok) throw new Error("submit falhou");
          var uri = res.body && res.body.redirectUri;
          if (uri) { window.location.href = uri; return; }
          setStatus(status, "ok", "Recebemos seu contato. Em breve falamos com você.");
          form.reset();
        })
        .catch(function () {
          setStatus(status, "erro", "Não foi possível enviar agora. Fale conosco em contato@safie.com.br.");
        })
        .finally(function () {
          if (btn) { btn.disabled = false; btn.textContent = rotulo; }
        });
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
