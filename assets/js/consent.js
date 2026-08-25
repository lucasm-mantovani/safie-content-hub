/* SAFIE — Consentimento de cookies. Sem dependência externa.
   Três categorias: necessarios (sempre ativo), estatisticas (opt-in) e
   marketing (opt-in). GA4 e o formulário HubSpot só carregam após aceite. */
(function () {
  'use strict';

  var CFG = {
    versao: '1.1',
    chave: 'safie_consent',
    validadeDias: 365,
    ga4: { id: 'G-HVJV03RFR8' },
    hubspot: {
      portalId: '50182013',
      formId: '1802e1da-b81b-44ed-9bab-7db51bd9e6b5',
      region: 'na1',
      target: '#hs-form-rodape'
    },
    whatsapp: 'https://wa.me/5511955937070?text=Ol%C3%A1!%20Vim%20pelo%20blog%20da%20SAFIE%20e%20gostaria%20de%20conversar.',
    politica: '/politica-de-cookies/'
  };

  var CSS = '' +
  '.sf-cc{position:fixed;left:16px;right:16px;bottom:16px;z-index:99999;background:#0f0f29;color:#f5f7fd;' +
  'border:1px solid rgba(245,247,253,.14);border-radius:14px;padding:20px 22px;max-width:760px;margin:0 auto;' +
  'font-family:Inter,system-ui,-apple-system,sans-serif;font-size:14px;line-height:1.55;' +
  'box-shadow:0 18px 48px rgba(4,4,31,.45)}' +
  '.sf-cc h2{margin:0 0 8px;font-family:"General Sans",Inter,system-ui,sans-serif;font-size:16px;font-weight:600;color:#fff}' +
  '.sf-cc p{margin:0 0 16px;color:rgba(245,247,253,.82)}' +
  '.sf-cc a{color:#7fa4ff;text-decoration:underline}' +
  '.sf-cc-acoes{display:flex;flex-wrap:wrap;gap:10px}' +
  '.sf-b{font:inherit;font-weight:600;padding:11px 18px;border-radius:8px;cursor:pointer;border:1px solid transparent;flex:1 1 auto;min-width:132px}' +
  '.sf-b-1{background:#154efa;color:#fff}.sf-b-1:hover{background:#002bab}' +
  '.sf-b-2{background:transparent;color:#f5f7fd;border-color:rgba(245,247,253,.32)}' +
  '.sf-b-2:hover{border-color:#f5f7fd}' +
  '.sf-b-3{background:transparent;color:rgba(245,247,253,.72);border-color:transparent;text-decoration:underline;flex:0 0 auto}' +
  '.sf-ov{position:fixed;inset:0;z-index:100000;background:rgba(4,4,31,.72);display:flex;align-items:center;justify-content:center;padding:16px}' +
  '.sf-md{background:#04041f;color:#f5f7fd;border:1px solid rgba(245,247,253,.14);border-radius:14px;padding:24px;max-width:520px;width:100%;' +
  'font-family:Inter,system-ui,sans-serif;font-size:14px;line-height:1.55;max-height:86vh;overflow:auto}' +
  '.sf-md h2{margin:0 0 16px;font-family:"General Sans",Inter,sans-serif;font-size:17px;color:#fff}' +
  '.sf-cat{border-top:1px solid rgba(245,247,253,.12);padding:14px 0}' +
  '.sf-cat-t{display:flex;justify-content:space-between;align-items:center;gap:12px;font-weight:600;color:#fff}' +
  '.sf-cat-d{margin:6px 0 0;color:rgba(245,247,253,.7);font-size:13px}' +
  '.sf-fix{font-size:12px;color:rgba(245,247,253,.55);font-weight:500}' +
  '.sf-sw{position:relative;width:44px;height:24px;flex:0 0 auto}' +
  '.sf-sw input{position:absolute;opacity:0;width:100%;height:100%;margin:0;cursor:pointer}' +
  '.sf-sw span{position:absolute;inset:0;background:rgba(245,247,253,.22);border-radius:24px;transition:.15s;pointer-events:none}' +
  '.sf-sw span:after{content:"";position:absolute;width:18px;height:18px;left:3px;top:3px;background:#fff;border-radius:50%;transition:.15s}' +
  '.sf-sw input:checked+span{background:#154efa}.sf-sw input:checked+span:after{transform:translateX(20px)}' +
  '.sf-fb{border:1px dashed rgba(21,78,250,.35);border-radius:12px;padding:20px;text-align:center;font-family:Inter,system-ui,sans-serif}' +
  '.sf-fb p{margin:0 0 14px;font-size:14px;line-height:1.5}' +
  '.sf-fb .sf-wa{display:inline-block;background:#154efa;color:#fff;font-weight:600;font-size:14px;' +
  'padding:12px 22px;border-radius:8px;text-decoration:none}' +
  '.sf-fb .sf-wa:hover{background:#002bab}' +
  '.sf-fb small{display:block;margin-top:12px;font-size:12px;opacity:.75}' +
  '.sf-fb button{background:none;border:0;padding:0;color:#154efa;font:inherit;font-size:12px;text-decoration:underline;cursor:pointer}' +
  '.sf-pref-link{display:inline-block;margin-top:12px;background:none;border:0;padding:0;font:inherit;font-size:13px;' +
  'color:inherit;opacity:.7;text-decoration:underline;cursor:pointer}' +
  '@media(max-width:520px){.sf-cc{padding:18px}.sf-b{flex:1 1 100%}}';

  var estado = null;

  function ler() {
    try {
      var raw = localStorage.getItem(CFG.chave);
      if (!raw) return null;
      var d = JSON.parse(raw);
      if (d.versao !== CFG.versao) return null;
      if (Date.now() - d.ts > CFG.validadeDias * 864e5) return null;
      return d;
    } catch (e) { return null; }
  }

  function salvar(prefs) {
    estado = {
      versao: CFG.versao,
      ts: Date.now(),
      marketing: !!(prefs && prefs.marketing),
      estatisticas: !!(prefs && prefs.estatisticas)
    };
    try { localStorage.setItem(CFG.chave, JSON.stringify(estado)); } catch (e) {}
    aplicar();
  }

  function estilos() {
    if (document.getElementById('sf-cc-css')) return;
    var s = document.createElement('style');
    s.id = 'sf-cc-css';
    s.textContent = CSS;
    document.head.appendChild(s);
  }

  function slot() { return document.querySelector(CFG.hubspot.target); }

  function carregarGA4() {
    if (window.__sfGa4) return;
    if (!CFG.ga4.id || CFG.ga4.id.indexOf('XXXX') !== -1) return;
    window.__sfGa4 = true;
    window['ga-disable-' + CFG.ga4.id] = false;
    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag('js', new Date());
    window.gtag('config', CFG.ga4.id);
    var s = document.createElement('script');
    s.async = true;
    s.src = 'https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(CFG.ga4.id);
    document.head.appendChild(s);
  }

  function desligarGA4() {
    if (!CFG.ga4.id) return;
    window['ga-disable-' + CFG.ga4.id] = true;
  }

  function carregarHubSpot() {
    var el = slot();
    if (!el || el.getAttribute('data-carregado')) return;
    el.setAttribute('data-carregado', '1');
    el.innerHTML = '';
    var s = document.createElement('script');
    s.src = 'https://js.hsforms.net/forms/embed/v2.js';
    s.charset = 'utf-8';
    s.onload = function () {
      if (window.hbspt && window.hbspt.forms) {
        window.hbspt.forms.create({
          region: CFG.hubspot.region,
          portalId: CFG.hubspot.portalId,
          formId: CFG.hubspot.formId,
          target: CFG.hubspot.target
        });
      }
    };
    document.body.appendChild(s);
  }

  function fallback() {
    var el = slot();
    if (!el) return;
    el.removeAttribute('data-carregado');
    el.innerHTML =
      '<div class="sf-fb">' +
      '<p>O formulário usa cookies de marketing. Enquanto isso, fale direto com a gente:</p>' +
      '<a class="sf-wa" href="' + CFG.whatsapp + '" target="_blank" rel="noopener">Falar no WhatsApp</a>' +
      '<small><button type="button" data-sf-abrir>Ajustar preferências de cookies</button></small>' +
      '</div>';
  }

  function aplicar() {
    if (estado && estado.estatisticas) carregarGA4();
    else desligarGA4();
    if (estado && estado.marketing) carregarHubSpot();
    else fallback();
  }

  function fechar(id) {
    var n = document.getElementById(id);
    if (n) n.remove();
  }

  function banner() {
    if (document.getElementById('sf-cc')) return;
    estilos();
    var d = document.createElement('div');
    d.id = 'sf-cc';
    d.className = 'sf-cc';
    d.setAttribute('role', 'dialog');
    d.setAttribute('aria-label', 'Preferências de cookies');
    d.innerHTML =
      '<h2>Cookies neste site</h2>' +
      '<p>Usamos cookies necessários ao funcionamento do site e, com o seu consentimento, ' +
      'cookies de estatísticas, que medem como o blog é utilizado, e de marketing, que ' +
      'identificam a origem do seu contato quando você envia o formulário. ' +
      'Detalhes na <a href="' + CFG.politica + '">Política de Cookies</a>.</p>' +
      '<div class="sf-cc-acoes">' +
      '<button type="button" class="sf-b sf-b-1" data-sf="aceitar">Aceitar cookies</button>' +
      '<button type="button" class="sf-b sf-b-2" data-sf="recusar">Recusar não necessários</button>' +
      '<button type="button" class="sf-b sf-b-3" data-sf="config">Configurar</button>' +
      '</div>';
    document.body.appendChild(d);
  }

  function modal() {
    if (document.getElementById('sf-ov')) return;
    estilos();
    var mkOn = estado && estado.marketing ? ' checked' : '';
    var estOn = estado && estado.estatisticas ? ' checked' : '';
    var o = document.createElement('div');
    o.id = 'sf-ov';
    o.className = 'sf-ov';
    o.setAttribute('role', 'dialog');
    o.setAttribute('aria-modal', 'true');
    o.innerHTML =
      '<div class="sf-md">' +
      '<h2>Preferências de cookies</h2>' +

      '<div class="sf-cat"><div class="sf-cat-t"><span>Necessários</span>' +
      '<span class="sf-fix">Sempre ativos</span></div>' +
      '<p class="sf-cat-d">Registram a sua decisão sobre cookies e mantêm o site funcionando. ' +
      'Não podem ser desativados.</p></div>' +

      '<div class="sf-cat"><div class="sf-cat-t"><span>Estatísticas</span>' +
      '<label class="sf-sw"><input type="checkbox" id="sf-est" aria-label="Cookies de estatísticas"' + estOn + '><span></span></label>' +
      '</div><p class="sf-cat-d">Google Analytics, que mede páginas lidas, tempo de leitura e ' +
      'origem do acesso. Nos ajuda a entender quais conteúdos são úteis.</p></div>' +

      '<div class="sf-cat"><div class="sf-cat-t"><span>Marketing</span>' +
      '<label class="sf-sw"><input type="checkbox" id="sf-mk" aria-label="Cookies de marketing"' + mkOn + '><span></span></label>' +
      '</div><p class="sf-cat-d">Cookie do HubSpot, que identifica a origem do seu contato quando você ' +
      'envia o formulário. Sem o aceite, o formulário não é carregado e o contato segue por ' +
      'WhatsApp ou e-mail.</p></div>' +

      '<div class="sf-cc-acoes" style="margin-top:18px">' +
      '<button type="button" class="sf-b sf-b-1" data-sf="salvar">Salvar preferências</button>' +
      '<button type="button" class="sf-b sf-b-2" data-sf="cancelar">Cancelar</button>' +
      '</div></div>';
    document.body.appendChild(o);
  }

  function linkRodape() {
    if (document.querySelector('.sf-pref-link')) return;
    var alvo = document.querySelector('.footer-base') || document.querySelector('footer');
    if (!alvo) return;
    var b = document.createElement('button');
    b.type = 'button';
    b.className = 'sf-pref-link';
    b.setAttribute('data-sf-abrir', '');
    b.textContent = 'Preferências de cookies';
    alvo.appendChild(b);
  }

  document.addEventListener('click', function (ev) {
    var t = ev.target.closest('[data-sf],[data-sf-abrir]');
    if (!t) return;
    if (t.hasAttribute('data-sf-abrir')) { modal(); return; }
    var a = t.getAttribute('data-sf');
    if (a === 'aceitar') { salvar({ marketing: true, estatisticas: true }); fechar('sf-cc'); }
    else if (a === 'recusar') { salvar({ marketing: false, estatisticas: false }); fechar('sf-cc'); }
    else if (a === 'config') { modal(); }
    else if (a === 'salvar') {
      var mk = document.getElementById('sf-mk');
      var est = document.getElementById('sf-est');
      salvar({ marketing: mk && mk.checked, estatisticas: est && est.checked });
      fechar('sf-ov'); fechar('sf-cc');
    }
    else if (a === 'cancelar') { fechar('sf-ov'); }
  });

  function iniciar() {
    estilos();
    linkRodape();
    estado = ler();
    if (!estado) { desligarGA4(); banner(); fallback(); }
    else aplicar();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', iniciar);
  else iniciar();
})();
