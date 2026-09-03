/* SAFIE — Consentimento de cookies. Sem dependência externa.
   Três categorias: necessarios (sempre ativo), estatisticas (opt-in) e
   marketing (opt-in). GA4 e o formulário HubSpot só carregam após aceite. */
(function () {
  'use strict';

  var CFG = {
    versao: '1.1',  // 1.1 mantida: só o visual mudou em 02/09/2026, não as categorias
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

  // Visual alinhado ao CookieConsent.astro dos sites (02/09/2026): barra compacta
  // ancorada embaixo, texto à esquerda, dois botões fantasma de mesmo peso à direita.
  // Todo valor vem dos tokens de tokens.css (carregado em todas as páginas via style.css).
  // A lógica de consentimento e o texto de finalidade não mudaram.
  var CSS = '' +
  '.sf-cc{position:fixed;left:16px;right:16px;bottom:16px;z-index:99999;display:grid;gap:10px;' +
  'background:var(--color-bg-page);color:var(--color-text-on-dark);border:1px solid var(--color-border-dark);' +
  'border-radius:var(--radius-nav);padding:18px 22px;max-width:760px;margin:0 auto;' +
  'font-family:var(--font-body);font-size:14px;line-height:1.55;box-shadow:var(--shadow-modal)}' +
  '@media(min-width:720px){.sf-cc{max-width:980px;grid-template-columns:minmax(0,1fr) auto;column-gap:24px;row-gap:4px;align-items:center}' +
  '.sf-cc h2,.sf-cc p{grid-column:1}.sf-cc-acoes{grid-column:2;grid-row:1/span 2;flex-wrap:nowrap}.sf-cc .sf-b{flex:0 0 auto}}' +
  '.sf-cc h2{margin:0;font-family:var(--font-display);font-size:15px;font-weight:600;line-height:1.3;letter-spacing:0;color:var(--color-text-on-dark)}' +
  '.sf-cc p{margin:0;font-size:13.5px;color:var(--color-text-secondary)}' +
  '.sf-cc a{color:var(--color-link-on-dark);text-decoration:underline;text-underline-offset:3px}' +
  '.sf-cc-acoes{display:flex;flex-wrap:wrap;gap:10px;align-items:center}' +
  '.sf-b{display:inline-flex;align-items:center;justify-content:center;font:inherit;font-size:14px;font-weight:500;line-height:1;' +
  'padding:12px 18px;border-radius:var(--radius-btn);cursor:pointer;flex:1 1 0;min-width:104px;white-space:nowrap;' +
  'background:transparent;color:var(--color-text-on-dark);border:1px solid var(--color-border-dark-strong);' +
  'transition:border-color .2s ease,color .2s ease}' +
  '.sf-b:hover{border-color:var(--color-text-on-dark)}' +
  '.sf-b-3{flex:0 0 auto;min-width:0;padding:12px 6px;border-color:transparent;color:var(--color-text-secondary);text-decoration:underline;text-underline-offset:3px}' +
  '.sf-b-3:hover{border-color:transparent;color:var(--color-text-on-dark)}' +
  '.sf-ov{position:fixed;inset:0;z-index:100000;background:var(--color-overlay);display:flex;align-items:center;justify-content:center;padding:16px}' +
  '.sf-md{background:var(--color-bg-deeper);color:var(--color-text-on-dark);border:1px solid var(--color-border-dark);border-radius:var(--radius-nav);padding:24px;max-width:520px;width:100%;' +
  'font-family:var(--font-body);font-size:14px;line-height:1.55;max-height:86vh;overflow:auto}' +
  '.sf-md h2{margin:0 0 16px;font-family:var(--font-display);font-size:17px;line-height:1.3;letter-spacing:0;color:var(--color-text-on-dark)}' +
  '.sf-cat{border-top:1px solid var(--color-border-dark);padding:14px 0}' +
  '.sf-cat-t{display:flex;justify-content:space-between;align-items:center;gap:12px;font-weight:600;color:var(--color-text-on-dark)}' +
  '.sf-cat-d{margin:6px 0 0;color:var(--color-text-secondary);font-size:13px}' +
  '.sf-fix{font-size:12px;color:var(--color-text-muted);font-weight:500}' +
  '.sf-sw{position:relative;width:44px;height:24px;flex:0 0 auto}' +
  '.sf-sw input{position:absolute;opacity:0;width:100%;height:100%;margin:0;cursor:pointer}' +
  '.sf-sw span{position:absolute;inset:0;background:var(--color-border-dark-strong);border-radius:var(--radius-pill);transition:.15s;pointer-events:none}' +
  '.sf-sw span:after{content:"";position:absolute;width:18px;height:18px;left:3px;top:3px;background:var(--color-surface-card-light);border-radius:var(--radius-pill);transition:.15s}' +
  '.sf-sw input:checked+span{background:var(--color-primary)}.sf-sw input:checked+span:after{transform:translateX(20px)}' +
  '.sf-fb{border:1px dashed var(--color-border-accent);border-radius:var(--radius-card);padding:20px;text-align:center;font-family:var(--font-body)}' +
  '.sf-fb p{margin:0 0 14px;font-size:14px;line-height:1.5}' +
  '.sf-fb .sf-wa{display:inline-flex;align-items:center;background:var(--color-primary);color:var(--color-surface-card-light);font-weight:500;font-size:var(--font-size-button);line-height:1;' +
  'padding:14px 28px;border-radius:var(--radius-btn);box-shadow:var(--shadow-btn-primary);text-decoration:none}' +
  '.sf-fb .sf-wa:hover{background:var(--color-primary-hover)}' +
  '.sf-fb small{display:block;margin-top:12px;font-size:12px;opacity:.75}' +
  '.sf-fb button{background:none;border:0;padding:0;color:var(--color-primary);font:inherit;font-size:12px;text-decoration:underline;cursor:pointer}' +
  '.sf-pref-link{display:inline-block;margin-top:12px;background:none;border:0;padding:0;font:inherit;font-size:13px;' +
  'color:inherit;opacity:.7;text-decoration:underline;cursor:pointer}' +
  '@media(max-width:520px){.sf-cc{padding:18px}.sf-b{flex:1 1 100%}.sf-b-3{flex:1 1 100%}}';

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
