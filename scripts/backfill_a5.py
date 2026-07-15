"""
backfill_a5.py — Aplica os ajustes A5 (chrome baked) no worktree unificado.

Opera SOMENTE em ~/CLAUDE/safie-blog-unificado (nunca lê os 5 blogs de origem),
preservando o snapshot congelado de 476 artigos. Faz:
  1. Remove "Sobre" do nav do header e do footer (baked em todas as páginas).
  2. Substitui os 3 CNPJs por 1 (novo texto com endereço).
  3. Regenera index.html (home) e categorias/index.html a partir dos templates/
     funções atualizadas (H1 novo, cards de ferramenta, cards de categoria).
  4. Deleta sobre.html e remove /sobre do sitemap.xml.
  5. Valida (0 CNPJ antigo, 0 /sobre, footer em todas) e reporta.

Uso: python3 scripts/backfill_a5.py
"""

import re
import sys
from pathlib import Path

WT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WT / "scripts"))

import migrar as M  # reusa gerar_pagina_de_template, gerar_categorias_index, _ler, constantes

# ── Substituições cirúrgicas (strings exatas, injetadas do mesmo partial no A3) ──

HEADER_SOBRE = '\n      <a href="/sobre">Sobre</a>'
FOOTER_SOBRE = '\n            <li><a href="/sobre">Sobre</a></li>'

CNPJ_OLD = (
    '    <div class="footer-cnpjs" aria-label="CNPJs SAFIE">\n'
    '      <span>SAFIE Consultoria e Contabilidade Ltda — 59.931.854/0001-34</span>\n'
    '      <span>SAFIE Tecnologia e Consultoria Ltda — 42.224.278/0001-92</span>\n'
    '      <span>Cunha &amp; Mantovani Advogados Associados — 34.924.976/0001-72</span>\n'
    '    </div>'
)
CNPJ_NEW = (
    '    <div class="footer-cnpjs" aria-label="CNPJ SAFIE">\n'
    '      <span>SAFIE TECNOLOGIA E CONSULTORIA LTDA, inscrita no CNPJ sob o nº '
    '42.224.278/0001-92, sediada à Av. Brigadeiro Faria Lima, Conj. 1102, '
    'Jardim Paulistano, CEP nº 01452922, São Paulo-SP</span>\n'
    '    </div>'
)


def surgical_pass():
    contadores = {"header_sobre": 0, "footer_sobre": 0, "cnpj": 0, "arquivos": 0}
    for p in WT.rglob("*.html"):
        if "templates" in p.parts:
            continue
        txt = orig = p.read_text(encoding="utf-8")
        if HEADER_SOBRE in txt:
            txt = txt.replace(HEADER_SOBRE, ""); contadores["header_sobre"] += 1
        if FOOTER_SOBRE in txt:
            txt = txt.replace(FOOTER_SOBRE, ""); contadores["footer_sobre"] += 1
        if CNPJ_OLD in txt:
            txt = txt.replace(CNPJ_OLD, CNPJ_NEW); contadores["cnpj"] += 1
        if txt != orig:
            p.write_text(txt, encoding="utf-8")
            contadores["arquivos"] += 1
    return contadores


def fix_sitemap():
    sm = M.SITEMAP
    if not sm.exists():
        return False
    txt = sm.read_text(encoding="utf-8")
    novo = re.sub(r"\s*<url>\s*<loc>[^<]*/sobre</loc>.*?</url>", "", txt, flags=re.S)
    if novo != txt:
        sm.write_text(novo, encoding="utf-8")
        return True
    return False


def main():
    print("=" * 60)
    print("BACKFILL A5 — início")

    # 1. Substituições cirúrgicas (chrome baked)
    c = surgical_pass()
    print(f"[1] Cirúrgico: {c['arquivos']} arquivos alterados "
          f"(header Sobre: {c['header_sobre']}, footer Sobre: {c['footer_sobre']}, CNPJ: {c['cnpj']})")

    # 2. Deleta sobre.html
    sobre = WT / "sobre.html"
    if sobre.exists():
        sobre.unlink(); print("[2] sobre.html deletado")
    else:
        print("[2] sobre.html já ausente")

    # 3. Regenera home + categorias/index a partir dos templates/funções atualizados
    M.gerar_pagina_de_template(M.T_HOME, M.INDEX_HTML)
    print("[3a] index.html (home) regenerado do template")
    site = M._ler(M.CONFIG_SITE, {})
    categorias = M._ler(M.CONFIG_CAT, [])
    indice = M._ler(M.INDICE_JSON, [])
    M.gerar_categorias_index(categorias, site, indice)
    print(f"[3b] categorias/index.html regenerado ({len(categorias)} categorias, {len(indice)} artigos p/ contagem)")

    # 4. Sitemap
    print(f"[4] sitemap.xml /sobre removido: {fix_sitemap()}")

    # 5. Validações
    print("-" * 60)
    print("VALIDAÇÃO:")
    htmls = [p for p in WT.rglob("*.html") if "templates" not in p.parts]
    def conta(sub):
        return sum(1 for p in htmls if sub in p.read_text(encoding="utf-8"))
    print(f"  arquivos html (excl. templates): {len(htmls)}")
    print(f"  CNPJ antigo 59.931.854: {conta('59.931.854')}  (esperado 0)")
    print(f"  CNPJ antigo 34.924.976: {conta('34.924.976')}  (esperado 0)")
    print(f"  refs /sobre:            {conta('/sobre')}  (esperado 0)")
    print(f"  CNPJ novo (endereço):   {conta('CEP nº 01452922')}  (esperado = todos c/ footer)")
    footer_tag = '<footer class="site-footer"'
    print(f"  footer site-footer:     {conta(footer_tag)}")
    print(f"  CNPJ 42.224.278:        {conta('42.224.278')}")
    print("=" * 60)


if __name__ == "__main__":
    main()
