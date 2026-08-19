"""
backfill_consent.py — migra as páginas JÁ PUBLICADAS para o fluxo de
consentimento de cookies (assets/js/consent.js). Em cada HTML:

  A) remove os dois <script> do embed HubSpot (js.hsforms.net + hbspt.forms.create),
     preservando a div #hs-form-rodape — o consent.js passa a carregar o form
     só após aceite de marketing;
  B) insere <script src="/assets/js/consent.js" defer></script> antes de </body>,
     só se ainda não existir;
  C) insere o link /politica-de-cookies/ na coluna "Links" do footer,
     só se ainda não existir.

Alvos: artigos/*.html, categorias/*.html, index.html, busca.html.
A fonte (templates/ e partials/) é trocada à parte; este script cobre só os
HTMLs baked. Idempotente: página já migrada não é tocada.

Uso:
  python3 scripts/backfill_consent.py --dry-run          # só reporta, não escreve
  python3 scripts/backfill_consent.py --pilot <trecho>   # roda em 1 página
  python3 scripts/backfill_consent.py                    # rollout completo

Hard-fail (exit 1) no rollout se restar js.hsforms.net, se alguma página ficar
sem (ou com mais de uma) tag do consent.js, ou se perder a div #hs-form-rodape.
"""

import argparse
import sys
from pathlib import Path

WT = Path(__file__).resolve().parent.parent

BLOCO_HUBSPOT = (
    '<script charset="utf-8" type="text/javascript" src="//js.hsforms.net/forms/embed/v2.js"></script>\n'
    '<script type="text/javascript">\n'
    '  if (window.hbspt) hbspt.forms.create({ portalId: "50182013", formId: "1802e1da-b81b-44ed-9bab-7db51bd9e6b5", region: "na1", target: "#hs-form-rodape" });\n'
    '</script>\n'
)
TAG_CONSENT = '<script src="/assets/js/consent.js" defer></script>'
LI_CONTATO = '<li><a href="mailto:contato@safie.com.br">contato@safie.com.br</a></li>'
LI_POLITICA = '<li><a href="/politica-de-cookies/">Política de Cookies</a></li>'
DIV_FORM = 'id="hs-form-rodape"'


def alvos_todos():
    paginas = sorted((WT / "artigos").glob("*.html"))
    paginas += sorted((WT / "categorias").glob("*.html"))
    paginas += [WT / "index.html", WT / "busca.html"]
    return paginas


def migrar_pagina(txt):
    """Aplica A/B/C. Retorna (novo_txt, ops) onde ops marca o que foi feito."""
    ops = {"A_hubspot": False, "B_consent": False, "C_politica": False}

    if BLOCO_HUBSPOT in txt:
        txt = txt.replace(BLOCO_HUBSPOT, "")
        ops["A_hubspot"] = True

    if TAG_CONSENT not in txt:
        pos = txt.rfind("</body>")
        if pos == -1:
            raise ValueError("</body> não encontrado")
        txt = txt[:pos] + TAG_CONSENT + "\n" + txt[pos:]
        ops["B_consent"] = True

    if "/politica-de-cookies/" not in txt:
        if LI_CONTATO not in txt:
            raise ValueError("li de contato não encontrado no footer")
        txt = txt.replace(LI_CONTATO, LI_CONTATO + "\n            " + LI_POLITICA, 1)
        ops["C_politica"] = True

    return txt, ops


def main():
    ap = argparse.ArgumentParser(description="Migra páginas publicadas para o fluxo de consentimento de cookies.")
    ap.add_argument("--dry-run", action="store_true", help="só reporta, não escreve")
    ap.add_argument("--pilot", metavar="TRECHO", help="roda em 1 página (nome ou trecho do arquivo)")
    args = ap.parse_args()

    alvos = alvos_todos()
    if args.pilot:
        alvos = [p for p in alvos if args.pilot in str(p.relative_to(WT))]
        if len(alvos) != 1:
            sys.exit(f"[erro] --pilot '{args.pilot}' casou com {len(alvos)} arquivos (esperado 1)")

    print("=" * 60)
    modo = "DRY-RUN" if args.dry_run else (f"PILOTO ({args.pilot})" if args.pilot else "ROLLOUT")
    print(f"BACKFILL CONSENT — {modo}")

    c = {"A_hubspot": 0, "B_consent": 0, "C_politica": 0, "tocadas": 0, "ja_ok": 0}
    erros = []
    for p in alvos:
        txt = p.read_text(encoding="utf-8")
        try:
            novo, ops = migrar_pagina(txt)
        except ValueError as e:
            erros.append(f"{p.relative_to(WT)}: {e}")
            continue
        if any(ops.values()):
            if not args.dry_run:
                p.write_text(novo, encoding="utf-8")
            c["tocadas"] += 1
            for k, v in ops.items():
                if v:
                    c[k] += 1
        else:
            c["ja_ok"] += 1

    print(f"[backfill] páginas-alvo: {len(alvos)} | tocadas: {c['tocadas']} | já migradas: {c['ja_ok']}")
    print(f"  A) bloco HubSpot removido:   {c['A_hubspot']}")
    print(f"  B) consent.js inserido:      {c['B_consent']}")
    print(f"  C) link política inserido:   {c['C_politica']}")
    if erros:
        print(f"[FALHA] páginas fora do padrão ({len(erros)}):")
        for e in erros[:10]:
            print(f"  - {e}")
        sys.exit(1)

    # ── Validação (sempre sobre TODOS os alvos) ──
    print("-" * 60)
    todos = alvos_todos()
    com_hsforms = [p for p in todos if "js.hsforms.net" in p.read_text(encoding="utf-8")]
    consent_errado = [
        (p, n) for p in todos
        if (n := p.read_text(encoding="utf-8").count(TAG_CONSENT)) != 1
    ]
    sem_div = [p for p in todos if DIV_FORM not in p.read_text(encoding="utf-8")]
    sem_politica = [p for p in todos if "/politica-de-cookies/" not in p.read_text(encoding="utf-8")]
    print("VALIDAÇÃO:")
    print(f"  páginas-alvo totais:             {len(todos)}")
    print(f"  ainda com js.hsforms.net:        {len(com_hsforms)}  (esperado 0 no rollout)")
    print(f"  consent.js != exatamente 1 tag:  {len(consent_errado)}  (esperado 0 no rollout)")
    print(f"  sem div #hs-form-rodape:         {len(sem_div)}  (esperado 0 SEMPRE)")
    print(f"  sem link da política:            {len(sem_politica)}  (esperado 0 no rollout)")
    print("=" * 60)
    if not args.dry_run and not args.pilot:
        problemas = com_hsforms or consent_errado or sem_div or sem_politica
        if problemas:
            for p in (com_hsforms + [x[0] for x in consent_errado] + sem_div + sem_politica)[:10]:
                print(f"[FALHA] {p.relative_to(WT)}")
            sys.exit(1)
    if sem_div:
        print(f"[FALHA] div #hs-form-rodape perdida em: {[str(p.relative_to(WT)) for p in sem_div[:10]]}")
        sys.exit(1)


if __name__ == "__main__":
    main()
