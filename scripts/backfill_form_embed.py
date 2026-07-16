"""
backfill_form_embed.py — troca o placeholder inerte do rodapé pelo embed oficial
HubSpot v2 em todas as páginas baked (artigos + páginas de navegação), exceto
index.html (a home já recebeu o embed) e templates/.

Operação cirúrgica no snapshot local (não re-migra; não toca os 5 blogs de origem).
Duas substituições por página:
  1. bloco do form placeholder (A5)  -> <div#hs-form-rodape> + consent
  2. </footer>                       -> </footer> + <script v2.js> + hbspt.forms.create

Uso: python3 scripts/backfill_form_embed.py
"""

import sys
from pathlib import Path

WT = Path(__file__).resolve().parent.parent

OLD_FORM = (
    '    <!-- TODO A5/A6: HubSpot — este form ainda NÃO envia. -->\n'
    '    <form class="footer-form" data-form="rodape" onsubmit="return false" novalidate>\n'
    '      <label>Nome*\n'
    '        <input type="text" name="nome" autocomplete="name" required>\n'
    '      </label>\n'
    '      <label>E-mail*\n'
    '        <input type="email" name="email" autocomplete="email" required>\n'
    '      </label>\n'
    '      <label>Empresa\n'
    '        <input type="text" name="empresa" autocomplete="organization">\n'
    '      </label>\n'
    '      <label>Mensagem\n'
    '        <textarea name="mensagem" rows="3"></textarea>\n'
    '      </label>\n'
    '      <button type="submit" class="cta-btn" disabled aria-disabled="true">Enviar (em breve)</button>\n'
    '      <p class="footer-form-nota">Formulário em configuração. Por ora, fale conosco em\n'
    '        <a href="mailto:contato@safie.com.br">contato@safie.com.br</a>.</p>\n'
    '    </form>'
)

NEW_FORM = (
    '    <!-- Form via embed oficial HubSpot v2 — carrega o hutk (submissão legítima: CRM + tarefa do workflow + redirect WhatsApp já configurado no form). -->\n'
    '    <div class="footer-form-hs-wrap">\n'
    '      <div id="hs-form-rodape" class="footer-form-hs"></div>\n'
    '      <p class="footer-form-consent">Prefere falar por e-mail? <a href="mailto:contato@safie.com.br">contato@safie.com.br</a>.</p>\n'
    '    </div>'
)

SCRIPTS = (
    '</footer>\n'
    '<script charset="utf-8" type="text/javascript" src="//js.hsforms.net/forms/embed/v2.js"></script>\n'
    '<script type="text/javascript">\n'
    '  if (window.hbspt) hbspt.forms.create({ portalId: "50182013", formId: "1802e1da-b81b-44ed-9bab-7db51bd9e6b5", region: "na1", target: "#hs-form-rodape" });\n'
    '</script>'
)


def main():
    print("=" * 60)
    print("BACKFILL FORM EMBED — início")
    c = {"form": 0, "scripts": 0, "arquivos": 0, "sem_form": []}
    for p in WT.rglob("*.html"):
        if "templates" in p.parts:
            continue
        if p.name == "index.html" and p.parent == WT:
            continue  # home já tem o embed
        txt = orig = p.read_text(encoding="utf-8")
        if OLD_FORM in txt:
            txt = txt.replace(OLD_FORM, NEW_FORM); c["form"] += 1
        else:
            c["sem_form"].append(str(p.relative_to(WT)))
        if "</footer>" in txt and "hs-form-rodape" in txt and "js.hsforms.net/forms/embed/v2.js" not in txt:
            txt = txt.replace("</footer>", SCRIPTS, 1); c["scripts"] += 1
        if txt != orig:
            p.write_text(txt, encoding="utf-8"); c["arquivos"] += 1
    print(f"[backfill] arquivos alterados: {c['arquivos']} | form trocado: {c['form']} | scripts add: {c['scripts']}")
    if c["sem_form"]:
        print(f"[aviso] {len(c['sem_form'])} html SEM o bloco placeholder esperado (não tocados): {c['sem_form'][:10]}")

    # ── Validação ──
    print("-" * 60)
    htmls = [p for p in WT.rglob("*.html") if "templates" not in p.parts]
    def conta(sub):
        return sum(1 for p in htmls if sub in p.read_text(encoding="utf-8"))
    s_embed = 'id="hs-form-rodape"'
    s_dataform = 'data-form="rodape"'
    print("VALIDAÇÃO:")
    print(f"  html (excl templates): {len(htmls)}")
    print(f"  com embed (#hs-form-rodape):        {conta(s_embed)}")
    print(f"  com script hbspt.forms.create:      {conta('hbspt.forms.create')}")
    print(f"  placeholder 'Enviar (em breve)':    {conta('Enviar (em breve)')}  (esperado 0)")
    print(f"  form fetch antigo data-form rodape: {conta(s_dataform)}  (esperado 0)")
    print("=" * 60)


if __name__ == "__main__":
    main()
